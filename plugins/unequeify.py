# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

import asyncio
import base64
import struct
import logging
from database import db
from config import temp
from .test import CLIENT, get_client
from .public import parse_chat
from script import Script
from pyrogram.file_id import FileId
from pyrogram import Client, filters, enums 
from pyrogram.errors import FloodWait, ListenerTimeout
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

logger = logging.getLogger(__name__)

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

CLIENT = CLIENT()
COMPLETED_BTN = InlineKeyboardMarkup(
  [[
    InlineKeyboardButton('💟 sᴜᴘᴘᴏʀᴛ ɢʀᴏᴜᴘ 💟', url='https://t.me/VJ_Bot_Disscussion')
  ],[
    InlineKeyboardButton('💠 ᴜᴘᴅᴀᴛᴇ ᴄʜᴀɴɴᴇʟ 💠', url='https://t.me/vj_botz')
  ]]
)
CANCEL_BTN = InlineKeyboardMarkup([[InlineKeyboardButton('• ᴄᴀɴᴄᴇʟ', 'terminate_frwd')]])
# media types checked for duplicates (every one has a unique file hash)
MEDIA_FILTERS = [
   enums.MessagesFilter.DOCUMENT,
   enums.MessagesFilter.VIDEO,
   enums.MessagesFilter.AUDIO,
   enums.MessagesFilter.PHOTO,
]

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

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

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

def unpack_new_file_id(new_file_id):
    """Return the unique file hash of a telegram file id."""
    decoded = FileId.decode(new_file_id)
    file_id = encode_file_id(
        struct.pack(
            "<iiqq",
            int(decoded.file_type),
            decoded.dc_id,
            decoded.media_id,
            decoded.access_hash
        )
    )
    return file_id

def file_hash(message):
    """Unique hash of any media message, None when there is no media."""
    if not message.media:
        return None
    media = getattr(message, message.media.value, None)
    if not media:
        return None
    unique = getattr(media, 'file_unique_id', None)
    if unique:
        # file_unique_id is the same for every copy of a file
        return unique
    file_id = getattr(media, 'file_id', None)
    if not file_id:
        return None
    try:
        return unpack_new_file_id(file_id)
    except Exception:
        return None

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

@Client.on_message(filters.command("unequify") & filters.private)
async def unequify(client, message):
   """Delete duplicate media of a chat using telegram file hashes."""
   user_id = message.from_user.id
   temp.CANCEL[user_id] = False
   if temp.lock.get(user_id) and str(temp.lock.get(user_id)) == "True":
      return await message.reply("**please wait until previous task complete**")
   _bot = await db.get_userbot(user_id)
   if not _bot:
      return await message.reply("<b>Need userbot to do this process. Please add a userbot using /settings</b>")
   try:
      target = await client.ask(user_id, timeout=300, text=
         "<b>❪ SET TARGET CHAT ❫</b>\n\n"
         "<b>Forward the last message from the target chat, or paste the chat id / username / message link.</b>\n\n"
         "/cancel - <code>cancel this process</code>")
   except ListenerTimeout:
      return await message.reply("<b>time out ! process cancelled.</b>")
   if target.text and target.text.strip().startswith("/"):
      return await message.reply("**process cancelled !**")
   chat_id = None
   if target.forward_from_chat:
      chat_id = target.forward_from_chat.username or target.forward_from_chat.id
   elif target.text:
      chat_id, _ = parse_chat(target.text)
   if chat_id is None:
      return await message.reply('**Invalid link / chat id**')
   try:
      confirm = await client.ask(user_id, timeout=300,
         text="**send /yes to start the process and /no to cancel this process**")
   except ListenerTimeout:
      return await message.reply("<b>time out ! process cancelled.</b>")
   if not confirm.text or confirm.text.strip().lower() != '/yes':
      return await confirm.reply("**process cancelled !**")
   sts = await confirm.reply("`processing..`")
   try:
      bot = await get_client(_bot['session'], is_bot=False, name=f"unq{user_id}")
      await bot.start()
   except Exception as e:
      return await sts.edit(f"**ERROR**\n`{e}`")
   try:
       k = await bot.send_message(chat_id, text="testing")
       await k.delete()
   except Exception:
       await sts.edit(f"**please make your [userbot](t.me/{_bot['username']}) admin in target chat with full permissions**")
       return await bot.stop()
   HASHES = set()
   DUPLICATE = []
   total = deleted = 0
   temp.lock[user_id] = True
   try:
     await sts.edit(Script.DUPLICATE_TEXT.format(total, deleted, "ᴘʀᴏɢʀᴇssɪɴɢ"), reply_markup=CANCEL_BTN)
     for media_filter in MEDIA_FILTERS:
        async for msg in bot.search_messages(chat_id=chat_id, filter=media_filter):
           if temp.CANCEL.get(user_id) == True:
              deleted += await delete_batch(bot, chat_id, DUPLICATE)
              await sts.edit(Script.DUPLICATE_TEXT.format(total, deleted, "ᴄᴀɴᴄᴇʟʟᴇᴅ"), reply_markup=COMPLETED_BTN)
              temp.lock[user_id] = False
              return await bot.stop()
           hash = file_hash(msg)
           if not hash:
              continue
           total += 1
           if hash in HASHES:
              DUPLICATE.append(msg.id)
           else:
              HASHES.add(hash)
           if total % 1000 == 0:
              await sts.edit(Script.DUPLICATE_TEXT.format(total, deleted, "ᴘʀᴏɢʀᴇssɪɴɢ"), reply_markup=CANCEL_BTN)
           if len(DUPLICATE) >= 100:
              deleted += await delete_batch(bot, chat_id, DUPLICATE)
              DUPLICATE = []
              await sts.edit(Script.DUPLICATE_TEXT.format(total, deleted, "ᴘʀᴏɢʀᴇssɪɴɢ"), reply_markup=CANCEL_BTN)
     if DUPLICATE:
        deleted += await delete_batch(bot, chat_id, DUPLICATE)
   except Exception as e:
       temp.lock[user_id] = False 
       await sts.edit(f"**ERROR**\n`{e}`")
       return await bot.stop()
   temp.lock[user_id] = False
   await sts.edit(Script.DUPLICATE_TEXT.format(total, deleted, "ᴄᴏᴍᴘʟᴇᴛᴇᴅ"), reply_markup=COMPLETED_BTN)
   await bot.stop()

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

async def delete_batch(bot, chat_id, msg_ids):
   """Delete a batch of messages, returns how many were deleted."""
   if not msg_ids:
      return 0
   try:
      await bot.delete_messages(chat_id, msg_ids)
      return len(msg_ids)
   except FloodWait as e:
      await asyncio.sleep(e.value)
      return await delete_batch(bot, chat_id, msg_ids)
   except Exception as e:
      logger.warning(f"unequify delete: {e}")
      return 0

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01
