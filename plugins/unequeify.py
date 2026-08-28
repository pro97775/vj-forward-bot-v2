"""/unequify — delete duplicate media in a chat.

The duplicate tracker here used to be a list scanned linearly for every file,
which grew unbounded. It now keeps nothing in RAM: every file id is checked
with a single atomic upsert against the user's own MongoDB when they added one
under /settings → 🗃 MongoDB, otherwise against the bot's own TTL-expired
store. The client is closed on every exit path.
"""

import asyncio
import base64
import logging
import re
import struct

from pyrogram import Client, enums, filters
from pyrogram.errors import FloodWait
from pyrogram.file_id import FileId
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from config import temp
from database import db
from script import Script

from .db import connect_user_db
from .test import build_client, close_client
from .utils import DupStore

logger = logging.getLogger(__name__)

COMPLETED_BTN = InlineKeyboardMarkup(
    [
        [InlineKeyboardButton("💟 sᴜᴘᴘᴏʀᴛ ɢʀᴏᴜᴘ 💟", url="https://t.me/VJ_Bot_Disscussion")],
        [InlineKeyboardButton("💠 ᴜᴘᴅᴀᴛᴇ ᴄʜᴀɴɴᴇʟ 💠", url="https://t.me/vj_botz")],
    ]
)
CANCEL_BTN = InlineKeyboardMarkup([[InlineKeyboardButton("• ᴄᴀɴᴄᴇʟ", "terminate_frwd")]])

LINK_RE = re.compile(
    r"(https://)?(t\.me/|telegram\.me/|telegram\.dog/)(c/)?(\d+|[a-zA-Z_0-9]+)/(\d+)$"
)

DELETE_CHUNK = 100
UI_EVERY = 500


def encode_file_id(s: bytes) -> str:
    r = b""
    n = 0
    for i in s + bytes([22]) + bytes([4]):
        if i == 0:
            n += 1
        else:
            if n:
                r += b"\x00" + bytes([n])
                n = 0
            r += bytes([i])
    return base64.urlsafe_b64encode(r).decode().rstrip("=")


def unpack_new_file_id(new_file_id):
    """Return a stable, dc-independent id for a file."""
    decoded = FileId.decode(new_file_id)
    return encode_file_id(
        struct.pack(
            "<iiqq",
            int(decoded.file_type),
            decoded.dc_id,
            decoded.media_id,
            decoded.access_hash,
        )
    )


@Client.on_message(filters.command("unequify") & filters.private)
async def unequify(client, message):
    user_id = message.from_user.id

    if temp.is_locked(user_id):
        return await message.reply("**Please wait until your previous task completes.**")

    _bot = await db.get_userbot(user_id)
    if not _bot:
        return await message.reply(
            "<b>This needs a userbot. Add one using /settings</b>"
        )

    target = await client.ask(
        user_id,
        text="**Forward the last message from the target chat, or send its last "
        "message link.**\n/cancel - `cancel this process`",
    )

    chat_id = None
    if target.text and target.text.startswith("/"):
        return await message.reply("**Process cancelled!**")
    if target.text and not target.forward_date:
        match = LINK_RE.match(target.text.strip().replace("?single", ""))
        if not match:
            return await message.reply("**Invalid link**")
        chat_id = match.group(4)
        if chat_id.isnumeric():
            chat_id = int("-100" + chat_id)
    elif target.forward_date and target.forward_from_chat:
        if target.forward_from_chat.type not in (
            enums.ChatType.CHANNEL,
            enums.ChatType.SUPERGROUP,
        ):
            return await message.reply_text("**Forward from a channel or supergroup.**")
        chat_id = target.forward_from_chat.username or target.forward_from_chat.id
    else:
        return await message.reply_text("**Invalid input!**")

    confirm = await client.ask(
        user_id, text="**Send /yes to start, or /no to cancel.**"
    )
    if not confirm.text or confirm.text.lower() != "/yes":
        return await confirm.reply("**Process cancelled!**")

    sts = await confirm.reply("`processing..`")

    bot = build_client(_bot["session"], is_bot=False)
    try:
        await bot.start()
    except Exception as exc:
        await close_client(bot)
        return await sts.edit(f"<b>Session error:</b> <code>{exc}</code>")

    try:
        probe = await bot.send_message(chat_id, text="testing")
        await probe.delete()
    except Exception:
        await close_client(bot)
        return await sts.edit(
            f"**Make your [userbot](t.me/{_bot['username']}) an admin in that chat "
            "with delete permission.**"
        )

    # Nothing is held in RAM: the duplicate check is a database upsert. Use the
    # user's own MongoDB when they configured one, else the bot's own store.
    configs = await db.get_configs(user_id)
    user_db = None
    if configs.get("db_uri"):
        connected, candidate = await connect_user_db(user_id, configs["db_uri"], chat_id)
        if connected:
            user_db = candidate
        else:
            await candidate.close()

    dup_key = f"unequify-{user_id}-{chat_id}"
    store = DupStore(key=dup_key, user_db=user_db)
    duplicates = []
    total = deleted = 0

    temp.begin_task(user_id)
    try:
        await sts.edit(
            Script.DUPLICATE_TEXT.format(total, deleted, "ᴘʀᴏɢʀᴇssɪɴɢ"),
            reply_markup=CANCEL_BTN,
        )

        async for msg in bot.search_messages(
            chat_id=chat_id, filter=enums.MessagesFilter.DOCUMENT
        ):
            if temp.is_cancelled(user_id):
                if duplicates:
                    deleted += await _delete(bot, chat_id, duplicates)
                await sts.edit(
                    Script.DUPLICATE_TEXT.format(total, deleted, "ᴄᴀɴᴄᴇʟʟᴇᴅ"),
                    reply_markup=COMPLETED_BTN,
                )
                return

            total += 1
            doc = msg.document
            if not doc:
                continue

            try:
                file_id = unpack_new_file_id(doc.file_id)
            except Exception as exc:
                logger.debug("could not decode file_id: %s", exc)
                continue

            if await store.check_and_add(file_id):
                duplicates.append(msg.id)

            if total % UI_EVERY == 0:
                await sts.edit(
                    Script.DUPLICATE_TEXT.format(total, deleted, "ᴘʀᴏɢʀᴇssɪɴɢ"),
                    reply_markup=CANCEL_BTN,
                )

            if len(duplicates) >= DELETE_CHUNK:
                deleted += await _delete(bot, chat_id, duplicates)
                duplicates = []

        if duplicates:
            deleted += await _delete(bot, chat_id, duplicates)

        await sts.edit(
            Script.DUPLICATE_TEXT.format(total, deleted, "ᴄᴏᴍᴘʟᴇᴛᴇᴅ"),
            reply_markup=COMPLETED_BTN,
        )
    except Exception as exc:
        logger.exception("unequify failed for %s", user_id)
        await sts.edit(f"**ERROR**\n<code>{exc}</code>")
    finally:
        # Drop this run's records so a later run starts clean.
        try:
            await store.reset()
        except Exception:
            pass
        store.clear()
        if user_db is not None:
            try:
                await user_db.drop_all()
            except Exception:
                pass
            await user_db.close()
        temp.end_task(user_id)
        await close_client(bot)


async def _delete(bot, chat_id, ids):
    """Delete a chunk of messages, tolerating FloodWait. Returns count deleted."""
    if not ids:
        return 0
    for _ in range(3):
        try:
            await bot.delete_messages(chat_id, ids)
            return len(ids)
        except FloodWait as exc:
            await asyncio.sleep(exc.value + 1)
        except Exception as exc:
            logger.warning("delete_messages failed: %s", exc)
            return 0
    return 0
