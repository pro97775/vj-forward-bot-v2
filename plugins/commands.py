# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

import sys
import asyncio 
from database import db
from config import Config, temp
from script import Script
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
import psutil
import time as time
from os import environ, execle, system

START_TIME = time.time()

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

# every command is registered in telegram when the bot starts
BOT_COMMANDS = [
    BotCommand("start", "check I'm alive"),
    BotCommand("forward", "forward messages"),
    BotCommand("settings", "configure your settings"),
    BotCommand("stats", "your forwarding stats"),
    BotCommand("unequify", "delete duplicate media in a chat"),
    BotCommand("stop", "stop your ongoing task"),
    BotCommand("reset", "reset your settings"),
    BotCommand("help", "how to use me"),
]
OWNER_COMMANDS = [
    BotCommand("dump", "set the owner dump chat"),
    BotCommand("broadcast", "broadcast a message to all users"),
    BotCommand("resetall", "reset all users settings"),
    BotCommand("restart", "restart the server"),
]

main_buttons = [[
    InlineKeyboardButton('❣️ ᴅᴇᴠᴇʟᴏᴘᴇʀ ❣️', url='https://t.me/kingvj01')
],[
    InlineKeyboardButton('🔍 sᴜᴘᴘᴏʀᴛ ɢʀᴏᴜᴘ', url='https://t.me/vj_bot_disscussion'),
    InlineKeyboardButton('🤖 ᴜᴘᴅᴀᴛᴇ ᴄʜᴀɴɴᴇʟ', url='https://t.me/vj_botz')
],[
    InlineKeyboardButton('💝 sᴜʙsᴄʀɪʙᴇ ᴍʏ ʏᴏᴜᴛᴜʙᴇ ᴄʜᴀɴɴᴇʟ', url='https://youtube.com/@Tech_VJ')
],[
    InlineKeyboardButton('👨‍💻 ʜᴇʟᴘ', callback_data='help'),
    InlineKeyboardButton('💁 ᴀʙᴏᴜᴛ', callback_data='about')
],[
    InlineKeyboardButton('⚙ sᴇᴛᴛɪɴɢs', callback_data='settings#main'),
    InlineKeyboardButton('📊 sᴛᴀᴛs', callback_data='settings#stats')
]]

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

async def set_commands(client):
    """Register every command of the bot in telegram."""
    try:
        await client.set_bot_commands(BOT_COMMANDS)
    except Exception as e:
        print(f"can't set bot commands: {e}")
    if not Config.BOT_OWNER:
        return
    try:
        from pyrogram.types import BotCommandScopeChat
        await client.set_bot_commands(BOT_COMMANDS + OWNER_COMMANDS,
                                     scope=BotCommandScopeChat(chat_id=Config.BOT_OWNER))
    except Exception as e:
        print(f"can't set owner commands: {e}")

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

@Client.on_message(filters.private & filters.command(['start']))
async def start(client, message):
    user = message.from_user
    if not await db.is_user_exist(user.id):
        await db.add_user(user.id, user.first_name)
    reply_markup = InlineKeyboardMarkup(main_buttons)
    await client.send_message(
        chat_id=message.chat.id,
        reply_markup=reply_markup,
        text=Script.START_TXT.format(message.from_user.first_name))

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

@Client.on_message(filters.private & filters.command(['help']))
async def help_cmd(client, message):
    buttons = [[
        InlineKeyboardButton('🤔 ʜᴏᴡ ᴛᴏ ᴜsᴇ ᴍᴇ ❓', callback_data='how_to_use')
    ],[
        InlineKeyboardButton('⚙ Sᴇᴛᴛɪɴɢs', callback_data='settings#main'),
        InlineKeyboardButton('📊 Sᴛᴀᴛs', callback_data='settings#stats')
    ]]
    await message.reply_text(text=Script.HELP_TXT, reply_markup=InlineKeyboardMarkup(buttons))

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

@Client.on_message(filters.private & filters.command(['restart']) & filters.user(Config.BOT_OWNER))
async def restart(client, message):
    msg = await message.reply_text(text="<i>Trying to restarting.....</i>")
    await asyncio.sleep(5)
    await msg.edit("<i>Server restarted successfully ✅</i>")
    system("git pull -f && pip3 install --no-cache-dir -r requirements.txt")
    execle(sys.executable, sys.executable, "main.py", environ)

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

@Client.on_callback_query(filters.regex(r'^help$'))
async def helpcb(bot, query):
    buttons = [[
        InlineKeyboardButton('🤔 ʜᴏᴡ ᴛᴏ ᴜsᴇ ᴍᴇ ❓', callback_data='how_to_use')
    ],[
        InlineKeyboardButton('Aʙᴏᴜᴛ ✨️', callback_data='about'),
        InlineKeyboardButton('⚙ Sᴇᴛᴛɪɴɢs', callback_data='settings#main')
    ],[
        InlineKeyboardButton('📊 Sᴛᴀᴛs', callback_data='settings#stats'),
        InlineKeyboardButton('⫷ Bᴀᴄᴋ', callback_data='back')
    ]]
    reply_markup = InlineKeyboardMarkup(buttons)
    await query.message.edit_text(text=Script.HELP_TXT, reply_markup=reply_markup)

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

@Client.on_callback_query(filters.regex(r'^how_to_use$'))
async def how_to_use(bot, query):
    buttons = [[InlineKeyboardButton('⫷ Bᴀᴄᴋ', callback_data='help')]]
    reply_markup = InlineKeyboardMarkup(buttons)
    await query.message.edit_text(
        text=Script.HOW_USE_TXT,
        reply_markup=reply_markup,
        disable_web_page_preview=True
    )

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

@Client.on_callback_query(filters.regex(r'^back$'))
async def back(bot, query):
    reply_markup = InlineKeyboardMarkup(main_buttons)
    await query.message.edit_text(
       reply_markup=reply_markup,
       text=Script.START_TXT.format(query.from_user.first_name))

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

@Client.on_callback_query(filters.regex(r'^about$'))
async def about(bot, query):
    buttons = [[
         InlineKeyboardButton('⫷ Bᴀᴄᴋ', callback_data='help'),
         InlineKeyboardButton('Sᴛᴀᴛs ✨️', callback_data='status')
    ]]
    reply_markup = InlineKeyboardMarkup(buttons)
    await query.message.edit_text(
        text=Script.ABOUT_TXT,
        reply_markup=reply_markup,
        disable_web_page_preview=True
    )

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

@Client.on_callback_query(filters.regex(r'^status$'))
async def status(bot, query):
    users_count, bots_count = await db.total_users_bots_count()
    forwardings = await db.forwad_count()
    channels = await db.total_channels_count()
    dump = await db.get_dump_chat()
    upt = await get_bot_uptime(START_TIME)
    buttons = [[
        InlineKeyboardButton('♻️ Rᴇғʀᴇsʜ', callback_data='status')
    ],[
        InlineKeyboardButton('Sʏsᴛᴇᴍ Sᴛᴀᴛs ✨️', callback_data='systm_sts'),
        InlineKeyboardButton('⫷ Bᴀᴄᴋ', callback_data='help')
    ]]
    reply_markup = InlineKeyboardMarkup(buttons)
    await query.message.edit_text(
        text=Script.STATUS_TXT.format(upt, users_count, bots_count, channels,
                                      forwardings, temp.forwardings,
                                      dump if dump else "not set"),
        reply_markup=reply_markup,
        disable_web_page_preview=True,
    )

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

@Client.on_callback_query(filters.regex(r'^systm_sts$'))
async def sys_status(bot, query):
    buttons = [[InlineKeyboardButton('⫷ Bᴀᴄᴋ', callback_data='status')]]
    ram = psutil.virtual_memory().percent
    cpu = psutil.cpu_percent()
    disk_usage = psutil.disk_usage('/')
    total_space = disk_usage.total / (1024**3)  # Convert to GB
    used_space = disk_usage.used / (1024**3)    # Convert to GB
    free_space = disk_usage.free / (1024**3)
    text = f"""
╔════❰ sᴇʀᴠᴇʀ sᴛᴀᴛs  ❱═❍⊱❁۪۪
║╭━━━━━━━━━━━━━━━➣
║┣⪼ <b>ᴛᴏᴛᴀʟ ᴅɪsᴋ sᴘᴀᴄᴇ</b>: <code>{total_space:.2f} GB</code>
║┣⪼ <b>ᴜsᴇᴅ</b>: <code>{used_space:.2f} GB</code>
║┣⪼ <b>ꜰʀᴇᴇ</b>: <code>{free_space:.2f} GB</code>
║┣⪼ <b>ᴄᴘᴜ</b>: <code>{cpu}%</code>
║┣⪼ <b>ʀᴀᴍ</b>: <code>{ram}%</code>
║╰━━━━━━━━━━━━━━━➣
╚══════════════════❍⊱❁۪۪
"""
    reply_markup = InlineKeyboardMarkup(buttons)
    await query.message.edit_text(
        text,
        reply_markup=reply_markup,
        disable_web_page_preview=True,
    )

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

async def get_bot_uptime(start_time):
    # Calculate the uptime in seconds
    uptime_seconds = int(time.time() - start_time)
    uptime_minutes = uptime_seconds // 60
    uptime_hours = uptime_minutes // 60
    uptime_string = ""
    if uptime_hours != 0:
        uptime_string += f" {uptime_hours % 24}H"
    if uptime_minutes != 0:
        uptime_string += f" {uptime_minutes % 60}M"
    uptime_string += f" {uptime_seconds % 60} Sec"
    return uptime_string   

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

@Client.on_message(filters.private & filters.command(['stats']))
async def my_stats(client, message):
    """Show the stats of the user who asked."""
    from .settings import stats_text
    buttons = [[
        InlineKeyboardButton('♻️ Rᴇғʀᴇsʜ', callback_data='settings#stats')
    ],[
        InlineKeyboardButton('🌐 Bᴏᴛ Sᴛᴀᴛs', callback_data='status'),
        InlineKeyboardButton('⚙ Sᴇᴛᴛɪɴɢs', callback_data='settings#main')
    ]]
    await message.reply_text(await stats_text(message.from_user.id),
                             reply_markup=InlineKeyboardMarkup(buttons))

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01
