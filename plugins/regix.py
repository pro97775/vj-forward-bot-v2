# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

import math
import time
import re
import asyncio
import logging
from .utils import (
    STS,
    extract_media_file_id,
    get_media_meta,
    build_smart_caption,
)
from database import db
from .test import CLIENT, BotPool, get_client, iter_messages
from config import temp
from script import Script
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait, MessageNotModified
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from .db import connect_user_db

CLIENT = CLIENT()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
TEXT = Script.TEXT


def _compile_regex_patterns(keyword_list, ext_list):
    keywords_pattern = None
    extensions_pattern = None
    if keyword_list:
        escaped = [re.escape(k.strip()) for k in keyword_list if k and k.strip()]
        if escaped:
            keywords_pattern = "|".join(escaped)
    if ext_list:
        escaped = [
            r"\." + re.escape(e.strip().lstrip(".")) + r"$"
            for e in ext_list
            if e and e.strip()
        ]
        if escaped:
            extensions_pattern = "|".join(escaped)
    return keywords_pattern, extensions_pattern


@Client.on_callback_query(filters.regex(r"^start_public"))
async def pub_(bot, callback_query):
    user = callback_query.from_user.id
    temp.CANCEL[user] = False
    temp.PAUSE[user] = False
    frwd_id = callback_query.data.split("_", 2)[2]

    if temp.lock.get(user) and str(temp.lock.get(user)) == "True":
        return await callback_query.answer(
            "⚠️ A forwarding task is already running! Use /stop to pause it first.",
            show_alert=True,
        )

    sts = STS(frwd_id)
    if not sts.verify():
        await callback_query.answer("This confirmation button has expired.", show_alert=True)
        return await callback_query.message.delete()

    i = sts.get(full=True)
    if i.TO in temp.IS_FRWD_CHAT:
        return await callback_query.answer(
            "⚠️ Another task is currently forwarding to this target chat. Please wait.",
            show_alert=True,
        )

    m = await msg_edit(
        callback_query.message,
        "<blockquote><b>⏳ Initializing worker pool & verifying chat access...</b></blockquote>",
    )
    await execute_forwarding_task(bot, user, m, sts, is_resume=False)


async def execute_forwarding_task(bot, user: int, m, sts: STS, is_resume: bool = False):
    _bot, caption, forward_tag, datas, protect, button = await sts.get_data(user)
    i = sts.get(full=True)

    bots_list = datas.get("bots") or []
    userbot_data = datas.get("userbot")
    chosen_mode = sts.get("mode") or datas.get("forward_mode", "pool")
    if chosen_mode == "pool" and not bots_list and userbot_data:
        chosen_mode = "userbot"
    elif chosen_mode == "userbot" and not userbot_data and bots_list:
        chosen_mode = "pool"

    if not bots_list and not userbot_data:
        return await msg_edit(
            m,
            "<blockquote><b>❌ No worker bots or Userbot configured!</b>\n"
            "Add one in <code>/settings</code> ➔ <b>🤖 Bot Manager</b>.</blockquote>",
            wait=True,
        )

    pool = BotPool(bots_data=bots_list, userbot_data=userbot_data, mode=chosen_mode)
    try:
        entries = await pool.start_all()
    except Exception as e:
        return await msg_edit(
            m,
            f"<blockquote><b>❌ Failed to start worker pool:</b>\n<code>{e}</code></blockquote>",
            wait=True,
        )

    if not entries:
        return await msg_edit(
            m,
            "<blockquote><b>❌ Could not start any worker bot or Userbot. Check your tokens in /settings.</b></blockquote>",
            wait=True,
        )

    temp.ACTIVE_POOLS[user] = pool
    reader_client = pool.primary_client()
    extra_reader_client = None

    await msg_edit(
        m,
        f"<blockquote><b>🔍 Checking source & target access ({pool.mode_label})...</b></blockquote>",
    )
    try:
        await reader_client.get_messages(sts.get("FROM"), sts.get("limit"))
    except Exception:
        if pool.mode == "pool" and userbot_data:
            try:
                extra_reader_client = await get_client(
                    userbot_data["session"], is_bot=False, name=f"READER_UBOT_{user}"
                )
                await extra_reader_client.start()
                await extra_reader_client.get_messages(sts.get("FROM"), sts.get("limit"))
                reader_client = extra_reader_client
            except Exception:
                if extra_reader_client:
                    await extra_reader_client.stop()
                await msg_edit(
                    m,
                    "<blockquote><b>❌ Source Chat Inaccessible!</b>\n\n"
                    "Make your worker bot(s) Admin in the source chat or ensure your Userbot is a member there.</blockquote>",
                    retry_btn(i.id),
                    True,
                )
                return await cleanup_task(pool, extra_reader_client, user, remove_db=False)
        else:
            await msg_edit(
                m,
                "<blockquote><b>❌ Source Chat Restricted or Private!</b>\n\n"
                "Use a Userbot (must be a member of the source chat) or make your Worker Bot an Admin there.</blockquote>",
                retry_btn(i.id),
                True,
            )
            return await cleanup_task(pool, extra_reader_client, user, remove_db=False)

    # Verify target chat write access for all bots in the pool
    failed_bots = []
    for entry in list(pool.entries):
        try:
            k = await entry["client"].send_message(i.TO, "⚡")
            await k.delete()
        except Exception:
            failed_bots.append(f"@{entry.get('username')}")

    if failed_bots:
        await msg_edit(
            m,
            "<blockquote><b>❌ Target Channel Permission Error!</b>\n\n"
            "Please promote the following bot(s)/userbot to <b>Admin</b> in the target chat with post permissions:\n"
            f"<code>{', '.join(failed_bots)}</code></blockquote>",
            retry_btn(i.id),
            True,
        )
        return await cleanup_task(pool, extra_reader_client, user, remove_db=False)

    user_have_db = False
    user_db = None
    dburi = datas.get("db_uri")
    if dburi is not None:
        connected, user_db = await connect_user_db(user, dburi, i.TO)
        if connected:
            user_have_db = True

    dup_files = set()
    if datas.get("skip_duplicate"):
        try:
            dup_files = await db.get_dup_files(user, i.TO)
        except Exception:
            dup_files = set()
        if user_have_db:
            try:
                old_files = await user_db.get_all_files()
                async for ofile in old_files:
                    if "file_id" in ofile:
                        dup_files.add(ofile["file_id"])
            except Exception:
                pass

    filter_list = datas["filters"]
    max_size = datas["max_size"]
    min_size = datas["min_size"]
    keywords_pat, extensions_pat = _compile_regex_patterns(
        datas.get("keywords"), datas.get("extensions")
    )
    raw_configs = datas.get("raw_configs") or {}

    if not is_resume:
        temp.forwardings += 1
        await db.add_frwd(user)
        sts.add(time=True)
        await send(bot, user, f"<blockquote><b>🚀 Forwarding started via {pool.mode_label}!</b></blockquote>")
    else:
        temp.forwardings += 1
        await send(bot, user, f"<blockquote><b>▶️ Forwarding resumed via {pool.mode_label}!</b></blockquote>")

    if i.TO not in temp.IS_FRWD_CHAT:
        temp.IS_FRWD_CHAT.append(i.TO)
    temp.lock[user] = True
    temp.CANCEL[user] = False
    temp.PAUSE[user] = False

    start_offset = sts.get("fetched")
    MSG_BATCH = []
    pling = 0

    try:
        await edit_progress(user, m, "🔄 FORWARDING TASK MONITOR", "Running", sts, pool, status_db="running")

        async for message in iter_messages(
            reader_client,
            chat_id=sts.get("FROM"),
            limit=sts.get("limit"),
            offset=start_offset,
            filters=filter_list,
            max_size=max_size,
        ):
            if await check_pause_or_cancel(bot, pool, extra_reader_client, user, m, sts, user_have_db, user_db):
                return

            if pling % 15 == 0:
                await edit_progress(user, m, "🔄 FORWARDING TASK MONITOR", "Running", sts, pool, status_db="running")
            pling += 1
            sts.add("fetched")

            if message == "DUPLICATE":
                sts.add("duplicate")
                continue
            elif message == "FILTERED":
                sts.add("filtered")
                continue
            elif message is None or message.empty or message.service:
                sts.add("deleted")
                continue

            file_name, file_size, _ = get_media_meta(message)
            caption_or_text = (
                (message.caption or "") if getattr(message, "media", None) else (message.text or "")
            )
            searchable_text = f"{file_name} {caption_or_text}".strip()

            if file_name and await extension_filter(extensions_pat, file_name):
                sts.add("filtered")
                continue
            if keywords_pat and await keyword_filter(keywords_pat, searchable_text):
                sts.add("filtered")
                continue
            if file_size and await size_filter(max_size, min_size, file_size):
                sts.add("filtered")
                continue

            unpacked_id = extract_media_file_id(message)
            if unpacked_id and datas.get("skip_duplicate"):
                if unpacked_id in dup_files:
                    sts.add("duplicate")
                    continue
                dup_files.add(unpacked_id)
                await db.add_dup_file(user, i.TO, unpacked_id)
                if user_have_db:
                    await user_db.add_file(unpacked_id)

            if forward_tag:
                MSG_BATCH.append(message.id)
                notcompleted = len(MSG_BATCH)
                completed = sts.get("total") - sts.get("fetched")
                if notcompleted >= 100 or completed <= 100:
                    await forward_with_pool(user, pool, MSG_BATCH, m, sts, protect)
                    sts.add("total_files", notcompleted)
                    await asyncio.sleep(max(2.0, pool.current_delay))
                    MSG_BATCH = []
            else:
                smart_text = build_smart_caption(message, raw_configs)
                details = {
                    "msg_id": message.id,
                    "is_media": bool(getattr(message, "media", None)),
                    "caption": smart_text,
                    "button": button,
                    "protect": protect,
                }
                await copy_with_pool(user, pool, details, m, sts)
                sts.add("total_files")
                await asyncio.sleep(pool.current_delay)

        if forward_tag and MSG_BATCH:
            await forward_with_pool(user, pool, MSG_BATCH, m, sts, protect)
            sts.add("total_files", len(MSG_BATCH))
            MSG_BATCH = []

    except Exception as e:
        await msg_edit(
            m,
            f"<blockquote><b>❌ Task Error:</b>\n<code>{e}</code></blockquote>",
            retry_btn(i.id),
            wait=True,
        )
        logger.error(f"Forwarding error for user {user}: {e}")
        if user_have_db and user_db:
            await user_db.close()
        return await cleanup_task(pool, extra_reader_client, user, remove_db=False, target_chat=sts.get("TO"))

    if sts.get("TO") in temp.IS_FRWD_CHAT:
        temp.IS_FRWD_CHAT.remove(sts.get("TO"))
    if user_have_db and user_db:
        await user_db.drop_all()
        await user_db.close()

    await edit_progress(user, m, "✅ FORWARDING COMPLETED", "completed", sts, pool, status_db="completed")
    await send(bot, user, "<blockquote><b>🎉 Forwarding task completed!</b></blockquote>")
    await cleanup_task(pool, extra_reader_client, user, remove_db=True, target_chat=sts.get("TO"))


async def copy_with_pool(user, pool: BotPool, msg: dict, m, sts: STS):
    while True:
        entry = await pool.acquire_bot()
        worker_client = entry["client"]
        try:
            if msg.get("is_media"):
                await worker_client.copy_message(
                    chat_id=sts.get("TO"),
                    from_chat_id=sts.get("FROM"),
                    message_id=msg.get("msg_id"),
                    caption=msg.get("caption") or "",
                    parse_mode=enums.ParseMode.HTML,
                    reply_markup=msg.get("button"),
                    protect_content=msg.get("protect"),
                )
            else:
                text_to_send = msg.get("caption")
                if text_to_send:
                    await worker_client.send_message(
                        chat_id=sts.get("TO"),
                        text=text_to_send,
                        parse_mode=enums.ParseMode.HTML,
                        reply_markup=msg.get("button"),
                        protect_content=msg.get("protect"),
                        disable_web_page_preview=True,
                    )
                else:
                    await worker_client.copy_message(
                        chat_id=sts.get("TO"),
                        from_chat_id=sts.get("FROM"),
                        message_id=msg.get("msg_id"),
                        reply_markup=msg.get("button"),
                        protect_content=msg.get("protect"),
                    )
            pool.record_success()
            return
        except FloodWait as e:
            pool.record_floodwait(entry, e.value)
            if pool.active_count == 1:
                await edit_progress(user, m, "⏳ FLOODWAIT COOLDOWN", f"Sleeping {e.value}s", sts, pool)
                await asyncio.sleep(e.value)
        except Exception as e:
            logger.warning(f"Copy message {msg.get('msg_id')} failed: {e}")
            sts.add("deleted")
            return


async def forward_with_pool(user, pool: BotPool, msg_ids: list, m, sts: STS, protect: bool):
    while True:
        entry = await pool.acquire_bot()
        worker_client = entry["client"]
        try:
            await worker_client.forward_messages(
                chat_id=sts.get("TO"),
                from_chat_id=sts.get("FROM"),
                protect_content=protect,
                message_ids=msg_ids,
            )
            pool.record_success()
            return
        except FloodWait as e:
            pool.record_floodwait(entry, e.value)
            if pool.active_count == 1:
                await edit_progress(user, m, "⏳ FLOODWAIT COOLDOWN", f"Sleeping {e.value}s", sts, pool)
                await asyncio.sleep(e.value)
        except Exception as e:
            logger.warning(f"Forward batch failed: {e}")
            return


async def msg_edit(msg, text, button=None, wait=None):
    try:
        return await msg.edit(text, reply_markup=button, disable_web_page_preview=True)
    except MessageNotModified:
        pass
    except FloodWait as e:
        if wait:
            await asyncio.sleep(e.value)
            return await msg_edit(msg, text, button, wait)


async def edit_progress(user, msg, title, status, sts: STS, pool: BotPool = None, status_db: str = "running"):
    i = sts.get(full=True)
    if not i:
        return

    total_target = max(1, int(i.total))
    pct_float = min(100.0, max(0.0, float(i.fetched) * 100.0 / float(total_target)))
    percentage = "{:.0f}".format(pct_float)

    filled_blocks = math.floor(pct_float / 10.0)
    progress_bar = "▰" * filled_blocks + "▱" * (10 - filled_blocks)

    now = time.time()
    diff = max(1, int(now - (i.start or now)))
    processed_since_skip = max(1, i.fetched - i.skip)
    speed = processed_since_skip / diff
    remaining_msgs = max(0, i.total - i.fetched)
    eta_seconds = int(remaining_msgs / speed) if speed > 0 else 0
    eta_str = TimeFormatter(milliseconds=eta_seconds * 1000) or "0s"
    if status in ("completed", "cancelled", "paused"):
        eta_str = "—"

    mode_label = pool.mode_label if pool else (i.mode or "Multi-Bot Pool")
    delay_val = pool.current_delay if pool else 3.0

    text = TEXT.format(
        title=title,
        progress_bar=progress_bar,
        percentage=percentage,
        fetched=i.fetched,
        total=i.total,
        forwarded=i.total_files,
        duplicate=i.duplicate,
        filtered=i.filtered,
        deleted=i.deleted,
        skip=i.skip,
        mode_label=mode_label,
        delay=delay_val,
        status=status.capitalize() if status in ("completed", "cancelled", "paused") else status,
        eta=eta_str,
    )

    if status_db != "completed":
        await update_forward(
            user_id=user,
            last_id=None,
            start_time=i.start,
            limit=i.limit,
            chat_id=i.FROM,
            toid=i.TO,
            forward_id=i.id,
            msg_id=msg.id,
            fetched=i.fetched,
            deleted=i.deleted,
            total=i.total_files,
            duplicate=i.duplicate,
            skip=i.skip,
            filterd=i.filtered,
            mode=pool.mode if pool else (i.mode or "pool"),
            status=status_db,
        )

    estimated_total_ms = (diff + eta_seconds) * 1000
    button = [
        [
            InlineKeyboardButton(
                f"📊 {progress_bar} {percentage}%",
                callback_data=f"fwrdstatus#{status}#{estimated_total_ms}#{percentage}#{i.id}",
            )
        ]
    ]

    if status == "completed":
        button.append([InlineKeyboardButton("🎉 Completed • Updates", url="https://t.me/VJ_BOTZ")])
    elif status == "paused":
        button.append(
            [
                InlineKeyboardButton("▶️ Resume Task", callback_data=f"resume_frwd_{user}"),
                InlineKeyboardButton("🗑 Discard Task", callback_data=f"cancel_frwd_{user}"),
            ]
        )
    elif status == "cancelled":
        button.append([InlineKeyboardButton("🚫 Task Cancelled", callback_data="close_btn")])
    else:
        button.append(
            [
                InlineKeyboardButton("⏸ Pause (/stop)", callback_data="pause_frwd"),
                InlineKeyboardButton("⏹ Cancel", callback_data="terminate_frwd"),
            ]
        )

    await msg_edit(msg, text, InlineKeyboardMarkup(button))


async def check_pause_or_cancel(bot, pool, extra_reader_client, user, msg, sts, user_have_db, user_db):
    if temp.PAUSE.get(user) is True:
        if sts.get("TO") in temp.IS_FRWD_CHAT:
            temp.IS_FRWD_CHAT.remove(sts.get("TO"))
        await edit_progress(user, msg, "⏸ TASK PAUSED", "paused", sts, pool, status_db="paused")
        await send(
            bot,
            user,
            "<blockquote><b>⏸ Forwarding Task Paused Safely!</b>\n\n"
            "Your exact progress is saved. Send <code>/resume</code> or tap <b>▶️ Resume Task</b> whenever you're ready.</blockquote>",
        )
        if user_have_db and user_db:
            await user_db.close()
        await cleanup_task(pool, extra_reader_client, user, remove_db=False, target_chat=sts.get("TO"))
        return True

    if temp.CANCEL.get(user) is True:
        if sts.get("TO") in temp.IS_FRWD_CHAT:
            temp.IS_FRWD_CHAT.remove(sts.get("TO"))
        await edit_progress(user, msg, "🚫 TASK CANCELLED", "cancelled", sts, pool, status_db="cancelled")
        await send(bot, user, "<blockquote><b>❌ Forwarding task cancelled and cleared.</b></blockquote>")
        if user_have_db and user_db:
            await user_db.drop_all()
            await user_db.close()
        await cleanup_task(pool, extra_reader_client, user, remove_db=True, target_chat=sts.get("TO"))
        return True

    return False


async def cleanup_task(pool: BotPool, extra_reader_client, user: int, remove_db: bool = True, target_chat=None):
    if target_chat and target_chat in temp.IS_FRWD_CHAT:
        temp.IS_FRWD_CHAT.remove(target_chat)
    try:
        if pool:
            await pool.stop_all()
    except Exception:
        pass
    try:
        if extra_reader_client:
            await extra_reader_client.stop()
    except Exception:
        pass
    temp.ACTIVE_POOLS.pop(user, None)
    if remove_db:
        await db.rmve_frwd(user)
    if temp.forwardings > 0:
        temp.forwardings -= 1
    temp.lock[user] = False
    temp.PAUSE[user] = False


async def send(bot, user, text):
    try:
        await bot.send_message(user, text=text)
    except Exception:
        pass


async def keyword_filter(keywords_pattern, searchable_text):
    if not keywords_pattern:
        return False
    if re.search(keywords_pattern, searchable_text or "", flags=re.IGNORECASE):
        return False
    return True


async def extension_filter(extensions_pattern, file_name):
    if not extensions_pattern or not file_name:
        return False
    if re.search(extensions_pattern, file_name, flags=re.IGNORECASE):
        return True
    return False


async def size_filter(max_size, min_size, file_size):
    size_mb = file_size / (1024 * 1024)
    if max_size == 0 and min_size == 0:
        return False
    if max_size == 0:
        return size_mb < min_size
    if min_size == 0:
        return size_mb > max_size
    return not (min_size <= size_mb <= max_size)


def TimeFormatter(milliseconds: int) -> str:
    seconds, milliseconds = divmod(int(milliseconds), 1000)
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
    return " ".join(parts) if parts else "0s"


def retry_btn(id):
    return InlineKeyboardMarkup([[InlineKeyboardButton("♻️ Retry Task", callback_data=f"start_public_{id}")]])


# ------------------------------------------------------------------
# PAUSE (/stop), RESUME (/resume) & CANCEL HANDLERS
# ------------------------------------------------------------------
@Client.on_callback_query(filters.regex(r"^pause_frwd$"))
async def pause_frwding_cb(bot, query):
    user_id = query.from_user.id
    if not temp.lock.get(user_id):
        return await query.answer("Task is already paused or inactive.", show_alert=True)
    temp.PAUSE[user_id] = True
    await query.answer("⏸ Pausing task safely... Progress will be saved!", show_alert=True)


@Client.on_callback_query(filters.regex(r"^terminate_frwd$"))
async def terminate_frwding(bot, m):
    user_id = m.from_user.id
    temp.lock[user_id] = False
    temp.CANCEL[user_id] = True
    await m.answer("⏹ Cancelling task...", show_alert=True)


@Client.on_callback_query(filters.regex(r"^cancel_frwd_"))
async def cancel_paused_task_cb(bot, query):
    user_id = query.from_user.id
    await db.rmve_frwd(user_id)
    temp.lock[user_id] = False
    temp.PAUSE[user_id] = False
    temp.CANCEL[user_id] = False
    await query.message.edit_text("<blockquote><b>🗑 Saved forwarding task has been discarded.</b></blockquote>")
    await query.answer("Task discarded!")


@Client.on_message(filters.private & filters.command(["stop"]))
async def stop_forward(client, message):
    user_id = message.from_user.id
    if temp.lock.get(user_id) and str(temp.lock.get(user_id)) == "True":
        temp.PAUSE[user_id] = True
        return await message.reply(
            "<blockquote><b>⏸ Pausing Active Forwarding Task...</b>\n\n"
            "Your exact progress is being saved. Use <code>/resume</code> anytime to continue!</blockquote>"
        )
    if await db.is_forwad_exit(user_id):
        buttons = [
            [
                InlineKeyboardButton("▶️ Resume Task", callback_data=f"resume_frwd_{user_id}"),
                InlineKeyboardButton("🗑 Discard Task", callback_data=f"cancel_frwd_{user_id}"),
            ]
        ]
        return await message.reply(
            "<blockquote><b>ℹ️ Your task is already paused!</b>\n\n"
            "Use <code>/resume</code> to continue or discard it below:</blockquote>",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
    await message.reply("<blockquote><b>⚠️ You have no active forwarding tasks to pause.</b></blockquote>")


@Client.on_message(filters.private & filters.command(["resume"]))
async def resume_forward_cmd(client, message):
    user_id = message.from_user.id
    if temp.lock.get(user_id) and str(temp.lock.get(user_id)) == "True":
        return await message.reply("<blockquote><b>⚠️ Your forwarding task is already running!</b></blockquote>")

    if not await db.is_forwad_exit(user_id):
        return await message.reply(
            "<blockquote><b>⚠️ No Paused or Interrupted Task Found!</b>\n\n"
            "Use <code>/forward</code> to start a new forwarding task.</blockquote>"
        )

    status_msg = await message.reply("<blockquote><b>⏳ Restoring saved task state...</b></blockquote>")
    await resume_saved_task(client, user_id, status_msg_override=status_msg)


@Client.on_callback_query(filters.regex(r"^resume_frwd_"))
async def resume_forward_cb(bot, query):
    user_id = query.from_user.id
    if temp.lock.get(user_id) and str(temp.lock.get(user_id)) == "True":
        return await query.answer("⚠️ A task is already running!", show_alert=True)
    if not await db.is_forwad_exit(user_id):
        return await query.answer("No saved task found to resume.", show_alert=True)
    await query.answer("▶️ Resuming your task...")
    await resume_saved_task(bot, user_id, status_msg_override=query.message)


async def resume_saved_task(bot, user_id: int, status_msg_override=None):
    settings = await db.get_forward_details(user_id)
    if not settings or settings.get("chat_id") is None:
        await db.rmve_frwd(user_id)
        if status_msg_override:
            await msg_edit(
                status_msg_override,
                "<blockquote><b>❌ Saved task data is incomplete or expired.</b></blockquote>",
            )
        return

    forward_id = await store_vars(user_id)
    sts = STS(forward_id)
    if not sts.verify():
        return

    sts.set_val("fetched", int(settings.get("offset") or settings.get("fetched") or settings.get("skip") or 0))
    sts.set_val("duplicate", int(settings.get("duplicate") or 0))
    sts.set_val("filtered", int(settings.get("filtered") or 0))
    sts.set_val("deleted", int(settings.get("deleted") or 0))
    sts.set_val("total_files", int(settings.get("total") or 0))
    sts.set_val("mode", settings.get("mode") or "pool")
    sts.add(time=True, start_time=settings.get("start_time"))

    m = status_msg_override
    if m is None:
        try:
            m = await bot.get_messages(user_id, settings["msg_id"])
            if not m or m.empty:
                m = await bot.send_message(
                    user_id,
                    "<blockquote><b>🔄 Resuming interrupted forwarding task...</b></blockquote>",
                )
        except Exception:
            m = await bot.send_message(
                user_id,
                "<blockquote><b>🔄 Resuming interrupted forwarding task...</b></blockquote>",
            )

    await execute_forwarding_task(bot, user_id, m, sts, is_resume=True)


@Client.on_callback_query(filters.regex(r"^fwrdstatus"))
async def status_msg(bot, msg):
    _, status, est_time, percentage, frwd_id = msg.data.split("#")
    sts = STS(frwd_id)
    if not sts.verify():
        fetched = forwarded = remaining = 0
        uptime = "0s"
        eta = "0s"
    else:
        fetched = sts.get("fetched")
        limit = sts.get("limit")
        forwarded = sts.get("total_files")
        remaining = max(0, limit - fetched)
        start_time = sts.get("start") or time.time()
        uptime = await get_bot_uptime(start_time)
        eta = await complete_time(remaining)

    return await msg.answer(
        Script.PROGRESS_ALERT.format(
            percentage=percentage,
            fetched=fetched,
            forwarded=forwarded,
            remaining=remaining,
            status=status,
            uptime=uptime,
            eta=eta or "0s",
        ),
        show_alert=True,
    )


@Client.on_callback_query(filters.regex(r"^close_btn$"))
async def close(bot, update):
    await update.answer()
    await update.message.delete()


async def store_vars(user_id):
    settings = await db.get_forward_details(user_id)
    fetch = settings.get("offset") or settings.get("fetched") or 0
    forward_id = settings.get("forward_id") or f"{user_id}-{fetch}"
    STS(id=forward_id).store(
        settings["chat_id"],
        settings["toid"],
        settings["skip"],
        settings["limit"],
        mode=settings.get("mode", "pool"),
    )
    return forward_id


async def restart_forwards(client):
    users = await db.get_all_frwd()
    tasks = []
    async for user_doc in users:
        uid = user_doc.get("user_id")
        details = user_doc.get("details") or {}
        if not uid or details.get("chat_id") is None:
            continue
        if details.get("status") == "paused":
            continue
        tasks.append(resume_saved_task(client, int(uid)))
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
    logger.info(f"Recovered {len(tasks)} interrupted forwarding task(s).")


async def update_forward(
    user_id,
    chat_id,
    start_time,
    toid,
    last_id,
    limit,
    forward_id,
    msg_id,
    fetched,
    total,
    duplicate,
    deleted,
    skip,
    filterd,
    mode="pool",
    status="running",
):
    details = {
        "chat_id": chat_id,
        "toid": toid,
        "forward_id": forward_id,
        "last_id": last_id,
        "limit": limit,
        "msg_id": msg_id,
        "start_time": start_time,
        "fetched": fetched,
        "offset": fetched,
        "deleted": deleted,
        "total": total,
        "duplicate": duplicate,
        "skip": skip,
        "filtered": filterd,
        "mode": mode,
        "status": status,
    }
    await db.update_forward(user_id, details)


async def get_bot_uptime(start_time):
    uptime_seconds = max(0, int(time.time() - start_time))
    uptime_minutes = uptime_seconds // 60
    uptime_hours = uptime_minutes // 60
    uptime_days = uptime_hours // 24
    parts = []
    if uptime_days > 0:
        parts.append(f"{uptime_days}d")
    if uptime_hours % 24 > 0:
        parts.append(f"{uptime_hours % 24}h")
    if uptime_minutes % 60 > 0:
        parts.append(f"{uptime_minutes % 60}m")
    parts.append(f"{uptime_seconds % 60}s")
    return " ".join(parts)


async def complete_time(total_files, files_per_minute=20):
    if total_files <= 0:
        return "0s"
    seconds_required = int((total_files / max(1, files_per_minute)) * 60)
    return TimeFormatter(milliseconds=seconds_required * 1000)