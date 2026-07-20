# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

import re
import asyncio 
from .utils import STS
from database import Db, db
from config import temp 
from script import Script
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait 
from pyrogram.errors.exceptions.not_acceptable_406 import ChannelPrivate as PrivateChat
from pyrogram.errors.exceptions.bad_request_400 import ChannelInvalid, ChatAdminRequired, UsernameInvalid, UsernameNotModified, ChannelPrivate
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

@Client.on_message(filters.private & filters.command(["forward"]))
async def run(bot, message):
    buttons = []
    btn_data = {}
    user_id = message.from_user.id

    # FIX: Get ALL bots for multi-bot display
    bots = await db.get_all_bots(user_id)
    userbot = await db.get_userbot(user_id)

    if not bots and not userbot:
        return await message.reply("<code>You didn't added any bot. Please add a bot using /settings !</code>")

    # Build bot display string for confirmation
    bot_names = []
    if bots:
        for b in bots:
            bot_names.append(f"[{b['name']}](t.me/{b['username']})")
    if userbot:
        bot_names.append(f"[{userbot['name']}](t.me/{userbot['username']}) (UserBot)")

    bots_display = "\n".join([f"  • {name}" for name in bot_names])
    active_count = len(bots) + (1 if userbot else 0)
    speed_text = f"\n<b>⚡ Estimated Speed:</b> <code>{active_count * 20} msgs/min</code>" if active_count > 1 else ""

    channels = await db.get_user_channels(user_id)
    if not channels:
       return await message.reply_text("please set a to channel in /settings before forwarding")
    if len(channels) > 1:
       for channel in channels:
          buttons.append([KeyboardButton(f"{channel['title']}")])
          btn_data[channel['title']] = channel['chat_id']
       buttons.append([KeyboardButton("cancel")]) 
       _toid = await bot.ask(message.chat.id, Script.TO_MSG.format(bots[0]['name'] if bots else userbot['name'], bots[0]['username'] if bots else userbot['username']), reply_markup=ReplyKeyboardMarkup(buttons, one_time_keyboard=True, resize_keyboard=True))
       if _toid.text.startswith(('/', 'cancel')):
          return await message.reply_text(Script.CANCEL, reply_markup=ReplyKeyboardRemove())
       to_title = _toid.text
       toid = btn_data.get(to_title)
       if not toid:
          return await message.reply_text("wrong channel choosen !", reply_markup=ReplyKeyboardRemove())
    else:
       toid = channels[0]['chat_id']
       to_title = channels[0]['title']
    fromid = await bot.ask(message.chat.id, Script.FROM_MSG, reply_markup=ReplyKeyboardRemove())
    if fromid.text and fromid.text.startswith('/'):
        await message.reply(Script.CANCEL)
        return 
    if fromid.text and not fromid.forward_date:
        regex = re.compile("(https://)?(t\.me/|telegram\.me/|telegram\.dog/)(c/)?(\d+|[a-zA-Z_0-9]+)/(\d+)$")
        match = regex.match(fromid.text.replace("?single", ""))
        if not match:
            return await message.reply('Invalid link')
        chat_id = match.group(4)
        last_msg_id = int(match.group(5))
        if chat_id.isnumeric():
            chat_id  = int(("-100" + chat_id))
    elif fromid.forward_from_chat.type in [enums.ChatType.CHANNEL, 'supergroup']:
        last_msg_id = fromid.forward_from_message_id
        chat_id = fromid.forward_from_chat.username or fromid.forward_from_chat.id
        if last_msg_id == None:
           return await message.reply_text("**This may be a forwarded message from a group and sended by anonymous admin. instead of this please send last message link from group**")
    else:
        await message.reply_text("**invalid !**")
        return 
    try:
        title = (await bot.get_chat(chat_id)).title
    except (PrivateChat, ChannelPrivate, ChannelInvalid):
        title = "private" if fromid.text else fromid.forward_from_chat.title
    except (UsernameInvalid, UsernameNotModified):
        return await message.reply('Invalid Link specified.')
    except Exception as e:
        return await message.reply(f'Errors - {e}')
    skipno = await bot.ask(message.chat.id, Script.SKIP_MSG)
    if skipno.text.startswith('/'):
        await message.reply(Script.CANCEL)
        return
    forward_id = f"{user_id}-{skipno.id}"

    # Build engine choice buttons based on what user has
    engine_buttons = []
    if bots:
        engine_buttons.append(
            InlineKeyboardButton(f'🤖 Bots ({len(bots)}) — {len(bots)*20} msgs/min', callback_data=f"start_public_{forward_id}_bots")
        )
    if userbot:
        engine_buttons.append(
            InlineKeyboardButton(f'👤 Userbot — 20 msgs/min', callback_data=f"start_public_{forward_id}_userbot")
        )
    if bots and userbot:
        engine_buttons.append(
            InlineKeyboardButton(f'⚡ Auto (Smart Router)', callback_data=f"start_public_{forward_id}_auto")
        )

    buttons = [
        engine_buttons,
        [InlineKeyboardButton('❌ No / Cancel', callback_data="close_btn")]
    ]
    reply_markup = InlineKeyboardMarkup(buttons)

    DOUBLE_CHECK_MULTI = """<b><u>DOUBLE CHECKING ⚠️</u></b>
<code>Before forwarding the messages click a button below to choose engine</code>

<b>★ YOUR BOT(S):</b>{bots_display}{speed_text}
<b>★ FROM CHANNEL:</b> <code>{from_chat}</code>
<b>★ TO CHANNEL:</b> <code>{to_chat}</code>
<b>★ SKIP MESSAGES:</b> <code>{skip}</code>

<i>° All bots must be admin in <b>TARGET CHAT</b></i> (<code>{to_chat}</code>)
<i>° If <b>SOURCE CHAT</b> is private, your userbot must be member or bots must be admin</i>

<b>Choose your forwarding engine below 👇</b>"""

    await message.reply_text(
        text=DOUBLE_CHECK_MULTI.format(
            bots_display=bots_display,
            speed_text=speed_text,
            from_chat=title,
            to_chat=to_title,
            skip=skipno.text
        ),
        disable_web_page_preview=True,
        reply_markup=reply_markup
    )
    STS(forward_id).store(chat_id, toid, int(skipno.text), int(last_msg_id))

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01
