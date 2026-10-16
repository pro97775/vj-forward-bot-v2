# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

import re
import asyncio
from database import db
from config import temp
from .test import CLIENT, get_client
from .utils import unpack_new_file_id, get_media_object
from script import Script
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

CLIENT = CLIENT()

COMPLETED_BTN = InlineKeyboardMarkup(
    [
        [InlineKeyboardButton("💬 Support Group", url="https://t.me/VJ_Bot_Disscussion")],
        [InlineKeyboardButton("📢 Update Channel", url="https://t.me/vj_botz")],
    ]
)
CANCEL_BTN = InlineKeyboardMarkup(
    [[InlineKeyboardButton("⏹ Stop Deduplication", callback_data="terminate_frwd")]]
)


@Client.on_message(filters.command("unequify") & filters.private)
async def unequify(client, message):
    user_id = message.from_user.id
    temp.CANCEL[user_id] = False
    if temp.lock.get(user_id) and str(temp.lock.get(user_id)) == "True":
        return await message.reply(
            "<blockquote><b>⚠️ Please wait until your active task finishes or /stop it first.</b></blockquote>"
        )

    _bot = await db.get_userbot(user_id)
    if not _bot:
        return await message.reply(
            "<blockquote><b>⚠️ Userbot Required for /unequify</b>\n\n"
            "Please add a Userbot session in <code>/settings</code> ➔ <b>🤖 Bot Manager</b> to scan and delete duplicate media.</blockquote>"
        )

    target = await client.ask(
        user_id,
        text=(
            "<blockquote><b>🧹 CHANNEL DEDUPLICATION (/unequify)</b></blockquote>\n\n"
            "<blockquote>Forward the <b>last message</b> from the target chat or send its <b>message link</b>.</blockquote>\n\n"
            "<i>Send /cancel to abort.</i>"
        ),
    )
    if not target.text and not target.forward_from_chat:
        return await message.reply("<blockquote><b>❌ Invalid input. Process cancelled.</b></blockquote>")
    if target.text and target.text.startswith("/"):
        return await message.reply("<blockquote><b>🚫 Process cancelled!</b></blockquote>")
    elif target.text:
        regex = re.compile(r"(https://)?(t\.me/|telegram\.me/|telegram\.dog/)(c/)?(\d+|[a-zA-Z_0-9]+)/(\d+)$")
        match = regex.match(target.text.replace("?single", "").strip())
        if not match:
            return await message.reply("<blockquote><b>❌ Invalid message link provided.</b></blockquote>")
        chat_id = match.group(4)
        if chat_id.isnumeric():
            chat_id = int("-100" + chat_id)
    elif target.forward_from_chat and target.forward_from_chat.type in [enums.ChatType.CHANNEL, enums.ChatType.SUPERGROUP, "supergroup"]:
        chat_id = target.forward_from_chat.username or target.forward_from_chat.id
    else:
        return await message.reply_text("<blockquote><b>❌ Invalid chat! Please forward from a channel or supergroup.</b></blockquote>")

    confirm = await client.ask(
        user_id,
        text="<blockquote><b>✅ Send <code>/yes</code> to begin removing duplicate media, or <code>/no</code> to cancel.</b></blockquote>",
    )
    if not confirm.text or confirm.text.strip().lower() != "/yes":
        return await confirm.reply("<blockquote><b>🚫 Process cancelled!</b></blockquote>")

    sts = await confirm.reply("<blockquote><b>⏳ Starting Userbot & verifying permissions...</b></blockquote>")
    try:
        bot = await get_client(_bot["session"], is_bot=False)
        await bot.start()
    except Exception as e:
        return await sts.edit(f"<blockquote><b>❌ Failed to start Userbot:</b> <code>{e}</code></blockquote>")

    try:
        k = await bot.send_message(chat_id, text="🔍 Checking delete permissions...")
        await k.delete()
    except Exception:
        await sts.edit(
            f"<blockquote><b>❌ Admin Permission Required!</b>\n\n"
            f"Please make your Userbot (<code>@{_bot.get('username')}</code>) an <b>Admin</b> with 'Delete Messages' permission in the target chat.</blockquote>"
        )
        return await bot.stop()

    seen_files = set()
    dup_msg_ids = []
    total = deleted = 0
    temp.lock[user_id] = True
    temp.CANCEL[user_id] = False

    try:
        await sts.edit(Script.DUPLICATE_TEXT.format(total, deleted, "Scanning..."), reply_markup=CANCEL_BTN)
        for media_filter in (
            enums.MessagesFilter.DOCUMENT,
            enums.MessagesFilter.VIDEO,
            enums.MessagesFilter.AUDIO,
        ):
            async for msg in bot.search_messages(chat_id=chat_id, filter=media_filter):
                if temp.CANCEL.get(user_id) is True:
                    if dup_msg_ids:
                        await bot.delete_messages(chat_id, dup_msg_ids)
                        deleted += len(dup_msg_ids)
                    await sts.edit(Script.DUPLICATE_TEXT.format(total, deleted, "Cancelled 🚫"), reply_markup=COMPLETED_BTN)
                    temp.lock[user_id] = False
                    return await bot.stop()

                media_obj = get_media_object(msg)
                if not media_obj or not getattr(media_obj, "file_id", None):
                    continue

                unpacked_id = unpack_new_file_id(media_obj.file_id)
                if unpacked_id in seen_files:
                    dup_msg_ids.append(msg.id)
                else:
                    seen_files.add(unpacked_id)

                total += 1
                if total % 200 == 0:
                    try:
                        await sts.edit(Script.DUPLICATE_TEXT.format(total, deleted, "Scanning..."), reply_markup=CANCEL_BTN)
                    except Exception:
                        pass

                if len(dup_msg_ids) >= 100:
                    try:
                        await bot.delete_messages(chat_id, dup_msg_ids)
                    except FloodWait as e:
                        await asyncio.sleep(e.value)
                        await bot.delete_messages(chat_id, dup_msg_ids)
                    deleted += len(dup_msg_ids)
                    dup_msg_ids = []
                    await sts.edit(Script.DUPLICATE_TEXT.format(total, deleted, "Deleting Duplicates..."), reply_markup=CANCEL_BTN)

        if dup_msg_ids:
            await bot.delete_messages(chat_id, dup_msg_ids)
            deleted += len(dup_msg_ids)

    except Exception as e:
        temp.lock[user_id] = False
        await sts.edit(f"<blockquote><b>❌ Error during deduplication:</b>\n<code>{e}</code></blockquote>")
        return await bot.stop()

    temp.lock[user_id] = False
    await sts.edit(Script.DUPLICATE_TEXT.format(total, deleted, "Completed ✅"), reply_markup=COMPLETED_BTN)
    await bot.stop()