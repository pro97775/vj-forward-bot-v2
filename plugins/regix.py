"""Forwarding engines.

Two engines share one code path:

* ``ROUND_ROBIN`` — N bot clients pulling from a shared queue *concurrently*
  (the old version awaited one send at a time and only shrank the sleep, so
  extra bots added almost no throughput).
* ``SINGLE_USERBOT`` — one userbot, sequential, for private sources.

Memory notes: duplicate tracking is fully database-backed (nothing is kept
in RAM), task state is released in ``finally``, and MongoDB progress writes
are rate-limited.
"""

import asyncio
import logging
import math
import re
import time

import psutil
from pyrogram import Client, filters
from pyrogram.errors import FloodWait, MessageNotModified
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from config import Config, temp
from database import db
from script import Script

from .db import connect_user_db
from .test import CLIENT, build_client, close_client, iter_messages
from .utils import STS, DupStore, status_size, sweep_status

CLIENT = CLIENT()
logger = logging.getLogger(__name__)
TEXT = Script.TEXT

PROGRESS = """<b>📊 Forward Progress</b>

<b>📈 Percentage:</b> <code>{}%</code>
<b>🕵 Fetched:</b> <code>{}</code>
<b>✅ Forwarded:</b> <code>{}</code>
<b>⏳ Remaining:</b> <code>{}</code>
<b>📌 Status:</b> <code>{}</code>
<b>⏱ Est. Time:</b> <code>{}</code>
<b>🔁 Runtime:</b> <code>{}</code>"""

# How many FloodWait retries a single send gets before it is counted failed.
MAX_FLOOD_RETRIES = 3
# Longest FloodWait we will sit through for one message.
MAX_FLOOD_SECONDS = 15 * 60
# Progress message refresh cadence, in fetched messages.
UI_REFRESH_EVERY = 25

# user_id -> DupStore, so /memory can report live duplicate-store stats.
ACTIVE_DUP_STORES = {}


# ==================================================================
# BOT POOL
# ==================================================================
class BotPool:
    """Owns started clients for a task and hands them out round-robin."""

    def __init__(self):
        self.clients = []
        self.current_index = 0
        self.lock = asyncio.Lock()

    async def initialize(self, bot_list):
        for i, bot_info in enumerate(bot_list):
            client = build_client(
                bot_info["token"], is_bot=True, name=f"BOT_{bot_info['id']}"
            )
            try:
                await client.start()
            except Exception as exc:
                logger.error(
                    "Failed to start bot %s: %s", bot_info.get("username"), exc
                )
                await close_client(client)
                continue
            self.clients.append(
                {
                    "client": client,
                    "info": bot_info,
                    "is_bot": True,
                    "index": i,
                    "active": True,
                }
            )
        if not self.clients:
            raise RuntimeError("No bots could be started. Check your tokens.")

    @property
    def active_count(self):
        return sum(1 for b in self.clients if b["active"])

    def active_clients(self):
        return [b for b in self.clients if b["active"]]

    async def get_next_bot(self):
        async with self.lock:
            if not self.clients:
                return None
            for _ in range(len(self.clients)):
                entry = self.clients[self.current_index]
                self.current_index = (self.current_index + 1) % len(self.clients)
                if entry["active"]:
                    return entry
            return None

    async def mark_inactive(self, bot_info):
        async with self.lock:
            for entry in self.clients:
                if entry["info"]["id"] == bot_info["id"]:
                    entry["active"] = False
                    break

    async def stop_all(self):
        for entry in self.clients:
            await close_client(entry["client"])
        self.clients = []


# ==================================================================
# FILTERS
# ==================================================================
def _file_meta(message):
    """Return (file_name, file_size) for any media message."""
    if not getattr(message, "media", None):
        return None, None
    media_attr = getattr(message.media, "value", None)
    if not media_attr:
        return None, None
    obj = getattr(message, media_attr, None)
    if obj is None:
        return None, None
    return getattr(obj, "file_name", None), getattr(obj, "file_size", None)


def _file_id(message):
    if not getattr(message, "media", None):
        return None
    media_attr = getattr(message.media, "value", None)
    if not media_attr:
        return None
    obj = getattr(message, media_attr, None)
    return getattr(obj, "file_id", None) if obj else None


def keyword_skip(keywords, file_name):
    """True when the file should be skipped because it matches no keyword."""
    if not keywords:
        return False
    if not file_name:
        return True
    return re.search(keywords, file_name, re.IGNORECASE) is None


def extension_skip(extensions, file_name, mode="block"):
    """True when the file should be skipped based on its extension.

    ``mode`` is ``"block"`` (skip files whose extension is listed — the
    default and previous behaviour) or ``"allow"`` (skip everything whose
    extension is *not* listed, i.e. a whitelist).
    """
    if not extensions:
        return False
    if mode == "allow":
        # A file with no name has no extension to whitelist, so it is skipped.
        if not file_name:
            return True
        return re.search(extensions, file_name, re.IGNORECASE) is None
    if not file_name:
        return False
    return re.search(extensions, file_name, re.IGNORECASE) is not None


def size_skip(min_size, max_size, file_size):
    """True when the file falls outside the configured size window.

    The previous implementation returned False for every file whenever a max
    was set and min was still at its default 0, so the max limit never applied.
    """
    if not file_size:
        return False
    min_size = float(min_size or 0)
    max_size = float(max_size or 0)
    if min_size <= 0 and max_size <= 0:
        return False
    size_mb = file_size / 1024 / 1024
    if min_size > 0 and size_mb < min_size:
        return True
    if max_size > 0 and size_mb > max_size:
        return True
    return False


def _compile_list(values):
    """Join a config list into one regex, escaping each entry."""
    if not values:
        return None
    parts = [re.escape(str(v).strip()) for v in values if str(v).strip()]
    return "|".join(parts) if parts else None


def _compile_extensions(values):
    """Build a regex that matches a filename ending in one of ``values``.

    Anchored at the end of the name (with an optional leading dot added when
    the user omitted it), so ``mp4`` no longer matches ``my.mp4.part`` or a
    file merely containing ``mp4`` in its title.
    """
    if not values:
        return None
    parts = []
    for value in values:
        ext = str(value).strip().lstrip(".").lower()
        if ext:
            parts.append(re.escape(ext))
    if not parts:
        return None
    return r"\.(?:" + "|".join(parts) + r")$"


# ==================================================================
# SEND HELPERS  (iterative FloodWait handling, never recursive)
# ==================================================================
async def send_copy(client, sts, details, targets):
    """Copy one message to every target. Returns True if all sends worked."""
    ok = True
    for target in targets:
        for attempt in range(MAX_FLOOD_RETRIES):
            try:
                if details.get("media") and details.get("caption"):
                    await client.send_cached_media(
                        chat_id=target,
                        file_id=details["media"],
                        caption=details.get("caption"),
                        reply_markup=details.get("button"),
                        protect_content=details.get("protect"),
                    )
                else:
                    await client.copy_message(
                        chat_id=target,
                        from_chat_id=sts.get("FROM"),
                        message_id=details["msg_id"],
                        caption=details.get("caption"),
                        reply_markup=details.get("button"),
                        protect_content=details.get("protect"),
                    )
                break
            except FloodWait as exc:
                if exc.value > MAX_FLOOD_SECONDS or attempt == MAX_FLOOD_RETRIES - 1:
                    logger.warning("Giving up on %s after FloodWait %ss", target, exc.value)
                    ok = False
                    break
                await asyncio.sleep(exc.value + 1)
            except Exception as exc:
                logger.warning("copy to %s failed: %s", target, exc)
                ok = False
                break
    return ok


async def send_forward(client, sts, message_ids, targets, protect):
    """Forward a batch (keeps the forward tag). Returns True if all worked."""
    ok = True
    for target in targets:
        for attempt in range(MAX_FLOOD_RETRIES):
            try:
                await client.forward_messages(
                    chat_id=target,
                    from_chat_id=sts.get("FROM"),
                    message_ids=message_ids,
                    protect_content=protect,
                )
                break
            except FloodWait as exc:
                if exc.value > MAX_FLOOD_SECONDS or attempt == MAX_FLOOD_RETRIES - 1:
                    ok = False
                    break
                await asyncio.sleep(exc.value + 1)
            except Exception as exc:
                logger.warning("forward to %s failed: %s", target, exc)
                ok = False
                break
    return ok


# ==================================================================
# CONCURRENT QUEUE PROCESSING
# ==================================================================
async def process_queue_multi(bot_pool, user_id, message_queue, sts,
                              base_sleep=3.0, stagger=0.2):
    """Drain ``message_queue`` using every active bot in parallel.

    One worker per bot, all pulling from a shared queue. Each worker paces
    itself with ``base_sleep`` so per-bot rate limits are respected while the
    aggregate throughput scales with the bot count.
    """
    if not message_queue:
        return

    queue = asyncio.Queue()
    for item in message_queue:
        queue.put_nowait(item)

    targets = sts.all_targets()
    dry_run = sts.get("dry_run")

    async def worker(entry, start_delay):
        if start_delay:
            await asyncio.sleep(start_delay)
        while not queue.empty():
            if temp.is_cancelled(user_id):
                return
            try:
                details = queue.get_nowait()
            except asyncio.QueueEmpty:
                return
            try:
                if dry_run:
                    sts.add("total_files")
                elif await send_copy(entry["client"], sts, details, targets):
                    sts.add("total_files")
                else:
                    sts.add("deleted")
            finally:
                queue.task_done()
            await asyncio.sleep(base_sleep)

    workers = [
        asyncio.create_task(worker(entry, i * stagger))
        for i, entry in enumerate(bot_pool.active_clients())
    ]
    if not workers:
        return
    await asyncio.gather(*workers, return_exceptions=True)


# ==================================================================
# SHARED TASK BODY
# ==================================================================
async def _run_task(
    user_id,
    progress_msg,
    sts,
    send_batch,
    send_one,
    pace,
    offset_skip=None,
    engine_choice="auto",
    bot_pool=None,
    single_client=None,
):
    """Walk the source chat once, applying filters and dispatching sends.

    ``send_batch(ids)`` and ``send_one(details)`` are engine-specific; both
    return the number of successfully delivered messages.
    """
    info = sts.get(full=True)
    _bot_data, caption, forward_tag, datas, protect, button = await sts.get_data(user_id)

    skip_types = datas["filters"]
    keywords = _compile_list(datas["keywords"])
    extensions = _compile_extensions(datas["extensions"])
    ext_mode = datas["extension_mode"]
    min_size, max_size = datas["min_size"], datas["max_size"]
    dry_run = datas["dry_run"]
    sts.set("dry_run", dry_run)
    sts.set("protect", protect)

    user_db = None
    if datas["db_uri"] and datas["skip_duplicate"]:
        connected, candidate = await connect_user_db(user_id, datas["db_uri"], info.TO)
        if connected:
            user_db = candidate

    # Nothing is held in RAM: every duplicate check is one atomic upsert
    # against the user's own MongoDB, or the bot's own TTL-expired store.
    # The key is derived from the user and target rather than the task id, so
    # a task resumed after a restart keeps the duplicates it already recorded
    # (resume generates a fresh task id).
    dup_store = (
        DupStore(key=f"{user_id}:{info.TO}", user_db=user_db)
        if datas["skip_duplicate"]
        else None
    )
    if dup_store is not None:
        ACTIVE_DUP_STORES[user_id] = dup_store

    speed = await db.get_batch_settings(user_id)
    queue_size = max(1, int(speed.get("batch_size", 20)))
    base_sleep = float(speed.get("base_sleep", 3.0))
    stagger = float(speed.get("stagger_delay", 0.2))

    targets = sts.all_targets()
    cancelled = False
    error = None

    # Mark every target busy so a second task cannot interleave into them.
    temp.begin_task(user_id, info.TO)
    for target in targets:
        temp.IS_FRWD_CHAT.add(target)

    try:
        MSG = []
        message_queue = []
        seen = 0
        start_at = offset_skip if offset_skip is not None else sts.get("start_id")

        await edit(user_id, progress_msg, "ᴘʀᴏɢʀᴇssɪɴɢ", 5, sts, engine_choice)

        source_client = single_client or bot_pool.active_clients()[0]["client"]

        async for message in iter_messages(
            source_client,
            chat_id=sts.get("FROM"),
            limit=sts.get("limit"),
            offset=start_at,
            skip_types=skip_types,
        ):
            if temp.is_cancelled(user_id):
                cancelled = True
                break

            seen += 1
            sts.add("fetched")
            # Remember where we are by message id, so a resume picks up here
            # rather than at a message count (they diverge on sparse channels).
            if message != "FILTERED" and getattr(message, "id", None):
                sts.set("cursor", message.id)
            if seen % UI_REFRESH_EVERY == 0:
                await edit(user_id, progress_msg, "ᴘʀᴏɢʀᴇssɪɴɢ", 5, sts, engine_choice)

            if message == "FILTERED":
                sts.add("filtered")
                continue
            if getattr(message, "empty", False) or getattr(message, "service", False):
                sts.add("deleted")
                continue

            file_name, file_size = _file_meta(message)
            if extension_skip(extensions, file_name, ext_mode):
                sts.add("filtered")
                continue
            if keyword_skip(keywords, file_name):
                sts.add("filtered")
                continue
            if size_skip(min_size, max_size, file_size):
                sts.add("filtered")
                continue

            file_id = _file_id(message)
            if dup_store is not None and file_id:
                if await dup_store.check_and_add(file_id):
                    sts.add("duplicate")
                    continue

            if forward_tag:
                MSG.append(message.id)
                if len(MSG) >= 100:
                    delivered = await send_batch(MSG)
                    sts.add("total_files", delivered)
                    if delivered < len(MSG):
                        sts.add("deleted", len(MSG) - delivered)
                    MSG = []
                    await asyncio.sleep(pace)
            else:
                message_queue.append(
                    {
                        "msg_id": message.id,
                        "media": file_id,
                        "caption": custom_caption(message, caption),
                        "button": button,
                        "protect": protect,
                    }
                )
                if len(message_queue) >= queue_size:
                    await send_one(message_queue, base_sleep, stagger)
                    message_queue = []

        # ── drain leftovers ─────────────────────────────────────────
        if not cancelled and MSG:
            delivered = await send_batch(MSG)
            sts.add("total_files", delivered)
            if delivered < len(MSG):
                sts.add("deleted", len(MSG) - delivered)
        if not cancelled and message_queue:
            await send_one(message_queue, base_sleep, stagger)

    except Exception as exc:
        error = exc
        logger.exception("Forward task failed for %s", user_id)
    finally:
        # Order matters: report first (clients still alive), then tear down.
        try:
            if error is not None:
                await msg_edit(
                    progress_msg, f"<b>ERROR:</b>\n<code>{error}</code>", wait=True
                )
                await edit(user_id, progress_msg, "ᴄᴀɴᴄᴇʟʟᴇᴅ", "cancelled", sts, engine_choice)
            elif cancelled:
                await edit(user_id, progress_msg, "ᴄᴀɴᴄᴇʟʟᴇᴅ", "cancelled", sts, engine_choice)
                await _notify(bot_pool, single_client, user_id,
                              "<b>❌ ғᴏʀᴡᴀʀᴅɪɴɢ ᴄᴀɴᴄᴇʟʟᴇᴅ</b>")
            else:
                await edit(user_id, progress_msg, "ᴄᴏᴍᴘʟᴇᴛᴇᴅ", "completed", sts, engine_choice)
                mode = " (dry run)" if dry_run else ""
                await _notify(bot_pool, single_client, user_id,
                              f"<b>🎉 ғᴏʀᴡᴀʀᴅɪɴɢ ᴄᴏᴍᴘʟᴇᴛᴇᴅ{mode}</b>")
        except Exception as exc:
            logger.debug("final UI update failed: %s", exc)

        # History before the state is released.
        try:
            snap = sts.snapshot()
            await db.add_history(
                user_id,
                {
                    "from_chat": snap.get("FROM"),
                    "to_chat": snap.get("TO"),
                    "targets": snap.get("TARGETS") or [],
                    "fetched": snap.get("fetched", 0),
                    "forwarded": snap.get("total_files", 0),
                    "duplicate": snap.get("duplicate", 0),
                    "filtered": snap.get("filtered", 0),
                    "failed": snap.get("deleted", 0),
                    "engine": engine_choice,
                    "dry_run": dry_run,
                    "status": "error" if error else ("cancelled" if cancelled else "completed"),
                    "started_at": snap.get("start"),
                },
            )
        except Exception as exc:
            logger.debug("history write failed: %s", exc)

        if user_db is not None:
            try:
                await user_db.drop_all()
            except Exception:
                pass
            try:
                await user_db.close()
            except Exception:
                pass

        if dup_store is not None:
            # Drop this task's rows so the store does not grow between runs.
            try:
                await dup_store.reset()
            except Exception:
                pass
            dup_store.clear()
        ACTIVE_DUP_STORES.pop(user_id, None)

        if bot_pool is not None:
            await bot_pool.stop_all()
        if single_client is not None:
            await close_client(single_client)

        await db.rmve_frwd(user_id)
        temp.forwardings = max(0, temp.forwardings - 1)
        temp.end_task(user_id, info.TO)
        for extra in targets:
            temp.IS_FRWD_CHAT.discard(extra)
        sts.release()
        sweep_status()


async def _notify(bot_pool, single_client, user_id, text):
    if single_client is not None:
        await send(single_client, user_id, text)
        return
    if bot_pool is not None:
        await send_multi(bot_pool, user_id, text)


# ==================================================================
# ENGINE A: MULTI-BOT ROUND-ROBIN
# ==================================================================
async def run_round_robin_task(bot, user_id, forward_id, progress_msg, valid_bots,
                               offset_skip=None, engine_choice="bots"):
    sts = STS(forward_id)
    if not sts.verify():
        return await msg_edit(progress_msg, "<code>Task expired. Run /forward again.</code>")

    bot_pool = BotPool()
    try:
        await bot_pool.initialize(valid_bots)
    except Exception as exc:
        await bot_pool.stop_all()
        await _abort(user_id, sts, progress_msg, f"<b>Init error:</b> {exc}")
        return

    # Every bot must be able to post to every target.
    for target in sts.all_targets():
        for entry in bot_pool.clients:
            try:
                probe = await entry["client"].send_message(target, "Testing")
                await probe.delete()
            except Exception:
                await msg_edit(
                    progress_msg,
                    f"**Make [{entry['info']['name']}](t.me/{entry['info']['username']}) "
                    f"an admin in the target chat** (<code>{target}</code>)",
                    retry_btn(forward_id, engine_choice),
                    True,
                )
                await bot_pool.stop_all()
                await _abort(user_id, sts, progress_msg, None)
                return

    async def send_batch(ids):
        entry = await bot_pool.get_next_bot()
        if not entry:
            return 0
        if sts.get("dry_run"):
            return len(ids)
        ok = await send_forward(
            entry["client"], sts, ids, sts.all_targets(), sts.get("protect")
        )
        return len(ids) if ok else 0

    async def send_one(queue, base_sleep, stagger):
        await process_queue_multi(
            bot_pool, user_id, queue, sts, base_sleep, stagger
        )

    await _run_task(
        user_id,
        progress_msg,
        sts,
        send_batch=send_batch,
        send_one=send_one,
        pace=2,
        offset_skip=offset_skip,
        engine_choice=engine_choice,
        bot_pool=bot_pool,
    )


# ==================================================================
# ENGINE B: SINGLE USERBOT
# ==================================================================
async def run_single_client_task(bot, user_id, forward_id, progress_msg, userbot_info,
                                 offset_skip=None, engine_choice="userbot"):
    sts = STS(forward_id)
    if not sts.verify():
        return await msg_edit(progress_msg, "<code>Task expired. Run /forward again.</code>")

    client = build_client(userbot_info["session"], is_bot=False)
    try:
        await client.start()
    except Exception as exc:
        await close_client(client)
        await _abort(user_id, sts, progress_msg, f"<b>Session Error:</b> {exc}")
        return

    for target in sts.all_targets():
        try:
            probe = await client.send_message(target, "Testing")
            await probe.delete()
        except Exception:
            await msg_edit(
                progress_msg,
                f"**Your userbot must be able to post in <code>{target}</code>**",
                retry_btn(forward_id, engine_choice),
                True,
            )
            await close_client(client)
            await _abort(user_id, sts, progress_msg, None)
            return

    async def send_batch(ids):
        if sts.get("dry_run"):
            return len(ids)
        ok = await send_forward(client, sts, ids, sts.all_targets(), sts.get("protect"))
        return len(ids) if ok else 0

    async def send_one(queue, base_sleep, stagger):
        targets = sts.all_targets()
        for details in queue:
            if temp.is_cancelled(user_id):
                return
            if sts.get("dry_run"):
                sts.add("total_files")
            elif await send_copy(client, sts, details, targets):
                sts.add("total_files")
            else:
                sts.add("deleted")
            await asyncio.sleep(base_sleep)

    await _run_task(
        user_id,
        progress_msg,
        sts,
        send_batch=send_batch,
        send_one=send_one,
        pace=10,
        offset_skip=offset_skip,
        engine_choice=engine_choice,
        single_client=client,
    )


async def _abort(user_id, sts, progress_msg, text):
    """Roll back the counters a task reserved before it could start."""
    if text:
        await msg_edit(progress_msg, text, wait=True)
    await db.rmve_frwd(user_id)
    temp.forwardings = max(0, temp.forwardings - 1)
    temp.end_task(user_id, sts.get("TO"))
    sts.release()


# ==================================================================
# ROUTER & CALLBACKS
# ==================================================================
async def start_task_router(bot, user_id, forward_id, progress_msg,
                            offset_skip=None, engine_choice="auto"):
    sts = STS(forward_id)
    if not sts.verify():
        return
    temp.CANCEL[int(user_id)] = False

    bots = await db.get_all_bots(user_id)
    userbot = await db.get_userbot(user_id)
    valid_bots = [b for b in bots if b.get("is_bot", True) and b.get("token")]

    if not valid_bots and not userbot:
        await _abort(user_id, sts, progress_msg,
                     "<code>You need to add a bot or userbot via /settings!</code>")
        return

    if engine_choice == "bots":
        if not valid_bots:
            await _abort(user_id, sts, progress_msg,
                         "<code>No bots found. Add one via /settings!</code>")
            return
        engine = "ROUND_ROBIN"
    elif engine_choice == "userbot":
        if not userbot:
            await _abort(user_id, sts, progress_msg,
                         "<code>No userbot found. Add one via /settings!</code>")
            return
        engine = "SINGLE_USERBOT"
    else:
        engine = "ROUND_ROBIN" if valid_bots else "SINGLE_USERBOT"

    if engine == "ROUND_ROBIN":
        await msg_edit(
            progress_msg,
            f"<code>Starting Multi-Bot Engine ({len(valid_bots)} bots)...</code>",
        )
        await run_round_robin_task(
            bot, user_id, forward_id, progress_msg, valid_bots, offset_skip, engine_choice
        )
    else:
        await msg_edit(progress_msg, "<code>Starting Userbot Engine...</code>")
        await run_single_client_task(
            bot, user_id, forward_id, progress_msg, userbot, offset_skip, engine_choice
        )


@Client.on_callback_query(filters.regex(r"^start_public"))
async def pub_(bot, message):
    user_id = message.from_user.id

    after_prefix = message.data[len("start_public_"):]
    if "_" in after_prefix:
        frwd_id, engine_choice = after_prefix.rsplit("_", 1)
        if engine_choice not in ("bots", "userbot", "auto"):
            frwd_id, engine_choice = after_prefix, "auto"
    else:
        frwd_id, engine_choice = after_prefix, "auto"

    if temp.is_locked(user_id):
        return await message.answer(
            "Please wait until your previous task completes", show_alert=True
        )

    sts = STS(frwd_id)
    if not sts.verify():
        await message.answer("You are clicking on an old button", show_alert=True)
        return await message.message.delete()

    busy = [t for t in sts.all_targets() if t in temp.IS_FRWD_CHAT]
    if busy:
        return await message.answer("Target chat is busy. Please wait.", show_alert=True)

    m = await msg_edit(message.message, "<code>Analyzing channels...</code>")
    if m is None:
        m = message.message

    temp.forwardings += 1
    await db.add_frwd(user_id)
    sts.add(time=True)

    await start_task_router(bot, user_id, frwd_id, m, engine_choice=engine_choice)


# ==================================================================
# RESUME AFTER RESTART
# ==================================================================
async def restart_pending_forwads(bot, user):
    if isinstance(user, dict):
        raw = user.get("user_id", user.get("id"))
    else:
        raw = user
    if raw is None:
        return
    user_id = int(raw)

    settings = await db.get_forward_details(user_id)
    if not settings or settings.get("chat_id") is None:
        return await db.rmve_frwd(user_id)

    try:
        await asyncio.sleep(2)
        forward_id = await store_vars(user_id, settings)
        if forward_id is None:
            return await db.rmve_frwd(user_id)

        sts = STS(forward_id)
        if not sts.verify():
            return await db.rmve_frwd(user_id)

        temp.forwardings += 1
        sts.add("fetched", value=int(settings.get("fetched") or 0))
        sts.add("duplicate", value=int(settings.get("duplicate") or 0))
        sts.add("filtered", value=int(settings.get("filtered") or 0))
        sts.add("deleted", value=int(settings.get("deleted") or 0))
        sts.add("total_files", value=int(settings.get("total") or 0))
        sts.add(time=True, start_time=settings.get("start_time"))

        m = None
        if settings.get("msg_id"):
            try:
                m = await bot.get_messages(user_id, settings["msg_id"])
                if getattr(m, "empty", True):
                    m = None
            except Exception:
                m = None
        if m is None:
            m = await bot.send_message(
                user_id, "<code>🔄 Resuming your forwarding task...</code>"
            )
            settings["msg_id"] = m.id
            await db.update_forward(user_id, settings)

        await start_task_router(
            bot,
            user_id,
            forward_id,
            m,
            offset_skip=settings.get("offset"),
            engine_choice=settings.get("engine_choice", "auto"),
        )
    except Exception as exc:
        logger.error("Failed to resume task for %s: %s", user_id, exc)
        await db.rmve_frwd(user_id)


async def restart_forwards(client):
    users = await db.get_all_frwd()
    pending = [user async for user in users]
    if not pending:
        return
    logger.info("Resuming %s pending forward task(s)", len(pending))
    await asyncio.gather(
        *(restart_pending_forwads(client, user) for user in pending),
        return_exceptions=True,
    )


async def store_vars(user_id, settings=None):
    settings = settings or await db.get_forward_details(user_id)
    if not settings or settings.get("chat_id") is None:
        return None
    forward_id = f"{user_id}-resume-{int(time.time())}"
    STS(forward_id).store(
        settings["chat_id"],
        settings["toid"],
        settings.get("skip") or 0,
        settings.get("limit") or 0,
        total=settings.get("expected_total") or 0,
        engine=settings.get("engine_choice", "auto"),
        extra_targets=settings.get("targets") or [],
        start_id=settings.get("offset"),
    )
    return forward_id


# ==================================================================
# UI
# ==================================================================
async def msg_edit(msg, text, button=None, wait=None):
    try:
        return await msg.edit(text, reply_markup=button)
    except MessageNotModified:
        return msg
    except FloodWait as exc:
        if wait:
            await asyncio.sleep(exc.value)
            return await msg_edit(msg, text, button, wait)
    except Exception as exc:
        logger.debug("msg_edit failed: %s", exc)
    return None


async def edit(user, msg, title, status, sts, engine_choice="auto"):
    if not sts.verify():
        return
    i = sts.get(full=True)
    status = (
        "Forwarding"
        if status == 5
        else f"sleeping {status} s"
        if str(status).isnumeric()
        else status
    )
    total = float(i.total) if i.total else 0.0
    percentage = "{:.0f}".format(min(100.0, float(i.fetched) * 100 / total)) if total > 0 else "0"

    text = TEXT.format(
        i.fetched, i.total_files, i.duplicate, i.deleted, i.skip, i.filtered,
        status, percentage, title,
    )

    # Rate-limited so a long task does not write to Mongo on every tick.
    if sts.should_write_db():
        await update_forward(
            user_id=user, last_id=None, start_time=i.start, limit=i.limit,
            chat_id=i.FROM, toid=i.TO, forward_id=None, msg_id=msg.id,
            fetched=i.fetched, deleted=i.deleted, total=i.total_files,
            duplicate=i.duplicate, skip=i.skip, filterd=i.filtered,
            engine_choice=engine_choice,
            offset=sts.get("cursor") or i.start_id,
            expected_total=i.total,
            targets=i.TARGETS,
        )

    diff = max(0, int(time.time() - i.start)) if i.start else 0
    speed = sts.divide(i.fetched, diff) if diff > 0 else 0
    elapsed_ms = diff * 1000
    remaining = max(0, i.total - i.fetched)
    eta_ms = round(sts.divide(remaining, int(speed))) * 1000 if speed >= 1 else 0

    filled = min(24, math.floor(int(percentage) / 4))
    progress = "●{0}{1}".format("●" * filled, "○" * (24 - filled))

    buttons = [[InlineKeyboardButton(
        progress, f"fwrdstatus#{status}#{elapsed_ms + eta_ms}#{percentage}#{i.id}"
    )]]
    if status in ("cancelled", "completed"):
        buttons.append([InlineKeyboardButton("• ᴄᴏᴍᴘʟᴇᴛᴇᴅ •", url="https://t.me/VJ_BOTZ")])
    else:
        buttons.append([InlineKeyboardButton("• ᴄᴀɴᴄᴇʟ", "terminate_frwd")])

    await msg_edit(msg, text, InlineKeyboardMarkup(buttons))


async def send_multi(bot_pool, user, text):
    for entry in bot_pool.clients:
        try:
            await entry["client"].send_message(user, text=text)
            return
        except Exception:
            continue


async def send(bot, user, text):
    try:
        await bot.send_message(user, text=text)
    except Exception as exc:
        logger.debug("notify failed: %s", exc)


def custom_caption(msg, caption):
    if not getattr(msg, "media", None):
        return None
    if not (msg.video or msg.document or msg.audio or msg.photo):
        return None
    media_attr = getattr(msg.media, "value", None)
    media_obj = getattr(msg, media_attr, None) if media_attr else None
    if media_obj is None:
        return None
    file_name = getattr(media_obj, "file_name", "") or ""
    file_size = getattr(media_obj, "file_size", 0) or 0
    fcaption = msg.caption.html if msg.caption else ""
    if caption:
        try:
            return caption.format(
                filename=file_name, size=get_size(file_size), caption=fcaption
            )
        except (KeyError, IndexError):
            return fcaption or None
    return fcaption or None


def get_size(size):
    units = ["Bytes", "KB", "MB", "GB", "TB", "PB", "EB"]
    size = float(size or 0)
    i = 0
    while size >= 1024.0 and i < len(units) - 1:
        i += 1
        size /= 1024.0
    return "%.2f %s" % (size, units[i])


def TimeFormatter(milliseconds) -> str:
    try:
        milliseconds = int(float(milliseconds))
    except (TypeError, ValueError):
        return "0s"
    seconds, milliseconds = divmod(milliseconds, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if seconds:
        parts.append(f"{seconds}s")
    return ", ".join(parts) if parts else "0s"


def retry_btn(id, engine="auto"):
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("♻️ RETRY ♻️", f"start_public_{id}_{engine}")]]
    )


# ==================================================================
# COMMANDS & CALLBACKS
# ==================================================================
@Client.on_callback_query(filters.regex(r"^terminate_frwd$"))
async def terminate_frwding(bot, m):
    if not temp.request_cancel(m.from_user.id):
        return await m.answer(
            "You have no running task — this button is from an old message.",
            show_alert=True,
        )
    await m.answer("Cancelling — the task will stop shortly.", show_alert=True)


@Client.on_callback_query(filters.regex(r"^fwrdstatus"))
async def status_msg(bot, msg):
    try:
        _, status, est_time, percentage, frwd_id = msg.data.split("#")
    except ValueError:
        return await msg.answer("Bad status button.", show_alert=True)

    sts = STS(frwd_id)
    if not sts.verify():
        return await msg.answer(
            "This task has finished — its live stats are gone. Use /tasks for history.",
            show_alert=True,
        )

    fetched = sts.get("fetched", default=0)
    forwarded = sts.get("total_files", default=0)
    total = sts.get("total", default=0)
    remaining = max(0, total - fetched)
    start = sts.get("start", default=0)
    runtime = TimeFormatter((time.time() - start) * 1000) if start else "0s"

    return await msg.answer(
        PROGRESS.format(
            percentage, fetched, forwarded, remaining, status,
            TimeFormatter(est_time), runtime,
        ),
        show_alert=True,
    )


@Client.on_callback_query(filters.regex(r"^close_btn$"))
async def close(bot, update):
    await update.answer()
    await update.message.delete()


@Client.on_message(filters.private & filters.command(["stop"]))
async def stop_forward(client, message):
    user_id = message.from_user.id
    sts = await message.reply("<code>Stopping...</code>")
    in_db = await db.is_forwad_exit(user_id)
    if not in_db and not temp.is_locked(user_id):
        return await sts.edit("**No ongoing forwards to cancel**")
    # ``force`` because a task resumed after a restart is recorded in the
    # database before its in-memory lock is taken.
    temp.request_cancel(user_id, force=in_db)
    await sts.edit("<b>Cancellation requested — the task will stop shortly.</b>")


@Client.on_message(filters.private & filters.command(["tasks"]))
async def task_history(client, message):
    user_id = message.from_user.id
    entries = await db.get_history(user_id, limit=10)
    if not entries:
        return await message.reply("<b>No finished tasks yet.</b>")

    icons = {"completed": "✅", "cancelled": "❌", "error": "⚠️"}
    lines = ["<b>🗂 Your last tasks</b>", ""]
    for entry in entries:
        when = time.strftime("%d %b %H:%M", time.localtime(entry.get("finished_at", 0)))
        icon = icons.get(entry.get("status"), "•")
        dry = " <i>(dry run)</i>" if entry.get("dry_run") else ""
        lines.append(
            f"{icon} <code>{when}</code>{dry}\n"
            f"   from <code>{entry.get('from_chat')}</code> → <code>{entry.get('to_chat')}</code>\n"
            f"   fwd <b>{entry.get('forwarded', 0)}</b> · dup <b>{entry.get('duplicate', 0)}</b>"
            f" · filt <b>{entry.get('filtered', 0)}</b> · fail <b>{entry.get('failed', 0)}</b>"
        )
    await message.reply("\n".join(lines), disable_web_page_preview=True)


@Client.on_message(filters.private & filters.command(["memory"]) & filters.user(Config.BOT_OWNER))
async def memory_report(client, message):
    proc = psutil.Process()
    rss = proc.memory_info().rss / (1024 ** 2)
    vms = proc.memory_info().vms / (1024 ** 2)
    stores = ACTIVE_DUP_STORES
    store_lines = (
        "\n".join(
            f"   • <code>{uid}</code>: {s.checked} checked, {s.hits} dup"
            f" · backend <code>{s.backend}</code> · in RAM {len(s)}"
            for uid, s in stores.items()
        )
        or "   • none"
    )
    await message.reply(
        "<b>🧠 Memory report</b>\n\n"
        f"<b>RSS:</b> <code>{rss:.1f} MB</code>\n"
        f"<b>VMS:</b> <code>{vms:.1f} MB</code>\n"
        f"<b>Open FDs:</b> <code>{proc.num_fds() if hasattr(proc, 'num_fds') else 'n/a'}</code>\n"
        f"<b>Threads:</b> <code>{proc.num_threads()}</code>\n"
        f"<b>asyncio tasks:</b> <code>{len(asyncio.all_tasks())}</code>\n\n"
        f"<b>Task states held:</b> <code>{status_size()}</code>\n"
        f"<b>Active forwards:</b> <code>{temp.forwardings}</code>\n"
        f"<b>Locks / cancels:</b> <code>{len(temp.lock)}</code> / <code>{len(temp.CANCEL)}</code>\n"
        f"<b>Busy targets:</b> <code>{len(temp.IS_FRWD_CHAT)}</code>\n\n"
        f"<b>Duplicate stores</b> (RAM cache {Config.DUP_HOT_CACHE}):\n{store_lines}"
    )


async def update_forward(user_id, chat_id, start_time, toid, last_id, limit, forward_id,
                         msg_id, fetched, total, duplicate, deleted, skip, filterd,
                         engine_choice="auto", offset=None, expected_total=0,
                         targets=None):
    await db.update_forward(
        user_id,
        {
            "chat_id": chat_id,
            "toid": toid,
            "targets": list(targets or []),
            "forward_id": forward_id,
            "last_id": last_id,
            "limit": limit,
            "msg_id": msg_id,
            "start_time": start_time,
            "fetched": fetched,
            # A message id, not a count — this is what a resume seeks to.
            "offset": offset if offset is not None else skip,
            "deleted": deleted,
            "total": total,
            "expected_total": expected_total,
            "duplicate": duplicate,
            "skip": skip,
            "filtered": filterd,
            "engine_choice": engine_choice,
        },
    )


async def get_bot_uptime(start_time):
    return TimeFormatter((time.time() - start_time) * 1000)


async def complete_time(total_files, files_per_minute=30):
    if not total_files or files_per_minute <= 0:
        return "0s"
    return TimeFormatter((total_files / files_per_minute) * 60 * 1000)
