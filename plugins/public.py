# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

import re
from .utils import STS
from database import db
from config import temp 
from script import Script
from pyrogram import Client, filters, enums
from pyrogram.errors import ListenerTimeout
from pyrogram.errors.exceptions.not_acceptable_406 import ChannelPrivate as PrivateChat
from pyrogram.errors.exceptions.bad_request_400 import ChannelInvalid, UsernameInvalid, UsernameNotModified, ChannelPrivate
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

LINK_REGEX = re.compile(r"(?:https?://)?(?:t\.me/|telegram\.me/|telegram\.dog/)(c/)?([\w\d_]+)/(\d+)")


def parse_chat(text):
    """Return (chat_id, last_msg_id) from a message link or a raw chat id.

    Supports:
      - https://t.me/channel/123        (public link)
      - https://t.me/c/1234567890/123   (private link)
      - -1001234567890                  (raw chat id, no last id)
      - @username                       (username, no last id)
    """
    text = (text or "").strip().replace("?single", "")
    match = LINK_REGEX.match(text)
    if match:
        chat_id = match.group(2)
        last_id = int(match.group(3))
        if chat_id.isnumeric():
            chat_id = int("-100" + chat_id)
        return chat_id, last_id
    if text.startswith("@"):
        return text, None
    if text.lstrip("-").isnumeric():
        return int(text), None
    return None, None

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

async def last_message_id(bot, chat_id):
    """Best effort read of the last message id of a chat."""
    try:
        async for msg in bot.get_chat_history(chat_id, limit=1):
            return msg.id
    except Exception:
        pass
    return None

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01


# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

async def get_source(bot, message):
    """Ask the user for the source chat and return (chat_id, last_id, title)."""
    try:
        fromid = await bot.ask(message.chat.id, Script.FROM_MSG, timeout=300)
    except ListenerTimeout:
        await message.reply("<b>time out ! process cancelled.</b>")
        return None, None, None
    if fromid.text and fromid.text.strip().startswith('/'):
        await message.reply(Script.CANCEL)
        return None, None, None
    chat_id = last_msg_id = None
    forwarded = fromid.forward_from_chat
    if forwarded and forwarded.type in [enums.ChatType.CHANNEL, enums.ChatType.SUPERGROUP]:
        last_msg_id = fromid.forward_from_message_id
        chat_id = forwarded.username or forwarded.id
        if last_msg_id is None:
            await message.reply_text("**This may be a forwarded message from a group and sended by anonymous admin. instead of this please send last message link from group**")
            return None, None, None
    elif fromid.text:
        chat_id, last_msg_id = parse_chat(fromid.text)
        if chat_id is None:
            await message.reply('**Invalid link / chat id**')
            return None, None, None
        if last_msg_id is None:
            # a plain chat id / username was given, read the last message id
            last_msg_id = await last_message_id(bot, chat_id)
            if not last_msg_id:
                await message.reply("**I can't read the last message id of that chat. Please send the last message link instead.**")
                return None, None, None
    else:
        await message.reply_text("**invalid !**")
        return None, None, None
    try:
        title = (await bot.get_chat(chat_id)).title
    except (PrivateChat, ChannelPrivate, ChannelInvalid):
        title = forwarded.title if forwarded else "private"
    except (UsernameInvalid, UsernameNotModified):
        await message.reply('Invalid Link specified.')
        return None, None, None
    except Exception as e:
        await message.reply(f'Errors - {e}')
        return None, None, None
    return chat_id, last_msg_id, title

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

@Client.on_message(filters.private & filters.command(["forward"]))
async def run(bot, message):
    """Ask everything needed for a task then show the double check message."""
    user_id = message.from_user.id
    if temp.lock.get(user_id) and str(temp.lock.get(user_id)) == "True":
        return await message.reply("**please wait until previous task complete**")
    bots = await db.get_bots(user_id)
    userbot = await db.get_userbot(user_id)
    if not bots and not userbot:
        return await message.reply("<code>You didn't added any bot. Please add a bot using /settings !</code>")
    channels = await db.get_user_channels(user_id)
    if not channels:
        return await message.reply_text("please set a to channel in /settings before forwarding")
    if len(channels) > 1:
        buttons, btn_data = [], {}
        for channel in channels:
            buttons.append([InlineKeyboardButton(channel['title'], f"tochat#{channel['chat_id']}")])
            btn_data[str(channel['chat_id'])] = channel['title']
        buttons.append([InlineKeyboardButton("• ᴄᴀɴᴄᴇʟ", "close_btn")])
        try:
            choice = await bot.ask(message.chat.id, Script.TO_MSG,
                                   listener_type=enums.ListenerTypes.CALLBACK_QUERY,
                                   reply_markup=InlineKeyboardMarkup(buttons), timeout=300)
        except ListenerTimeout:
            return await message.reply("<b>time out ! process cancelled.</b>")
        if not choice.data.startswith("tochat#"):
            return await message.reply_text(Script.CANCEL)
        await choice.answer()
        toid = int(choice.data.split("#")[1])
        to_title = btn_data.get(str(toid), str(toid))
        try:
            await choice.message.delete()
        except Exception:
            pass
    else:
        toid = channels[0]['chat_id']
        to_title = channels[0]['title']
    chat_id, last_msg_id, title = await get_source(bot, message)
    if chat_id is None:
        return
    try:
        skipno = await bot.ask(message.chat.id, Script.SKIP_MSG, timeout=300)
    except ListenerTimeout:
        return await message.reply("<b>time out ! process cancelled.</b>")
    if not skipno.text or skipno.text.strip().startswith('/'):
        return await message.reply(Script.CANCEL)
    if not skipno.text.strip().isnumeric():
        return await message.reply("**skip number must be a number**")
    skip = int(skipno.text.strip())
    configs = await db.get_configs(user_id)
    names = ", ".join(f"@{b['username']}" for b in bots) if bots else f"@{userbot['username']}"
    speed = (configs['bot_rate'] * len(bots)) if bots else int(60 / max(1, configs['userbot_delay']))
    forward_id = f"{user_id}-{skipno.id}"
    reply_markup = InlineKeyboardMarkup([[
        InlineKeyboardButton('✅ Yᴇs', callback_data=f"start_public_{forward_id}"),
        InlineKeyboardButton('❌ Nᴏ', callback_data="close_btn")
    ]])
    STS(forward_id).store(chat_id, toid, skip, int(last_msg_id))
    await message.reply_text(
        text=Script.DOUBLE_CHECK.format(bots=names, from_chat=title, to_chat=to_title,
                                        skip=skip, speed=speed),
        disable_web_page_preview=True,
        reply_markup=reply_markup
    )

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01
