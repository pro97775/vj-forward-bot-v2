# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

import sys
import time
import psutil
import asyncio
from os import environ, execle, system
from database import db
from config import Config
from script import Script
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

START_TIME = time.time()

main_buttons = [
    [
        InlineKeyboardButton("⚙️ Control Panel & Bot Pool", callback_data="settings#main"),
    ],
    [
        InlineKeyboardButton("📖 Commands & Help", callback_data="help"),
        InlineKeyboardButton("🚀 Quick Setup Guide", callback_data="how_to_use"),
    ],
    [
        InlineKeyboardButton("📊 Live Bot Stats", callback_data="status"),
        InlineKeyboardButton("ℹ️ About Bot", callback_data="about"),
    ],
    [
        InlineKeyboardButton("💬 Support Group", url="https://t.me/vj_bot_disscussion"),
        InlineKeyboardButton("📢 Update Channel", url="https://t.me/vj_botz"),
    ],
    [
        InlineKeyboardButton("👨‍💻 Developer", url="https://t.me/kingvj01"),
    ],
]


@Client.on_message(filters.private & filters.command(["start"]))
async def start(client, message):
    user = message.from_user
    if not await db.is_user_exist(user.id):
        await db.add_user(user.id, user.first_name)
    reply_markup = InlineKeyboardMarkup(main_buttons)
    await client.send_message(
        chat_id=message.chat.id,
        reply_markup=reply_markup,
        text=Script.START_TXT.format(user.first_name),
        disable_web_page_preview=True,
    )


@Client.on_message(filters.private & filters.command(["help"]))
async def help_cmd(client, message):
    buttons = [
        [InlineKeyboardButton("🚀 Quick Setup Guide", callback_data="how_to_use")],
        [
            InlineKeyboardButton("⚙️ Settings Panel", callback_data="settings#main"),
            InlineKeyboardButton("📊 Live Stats", callback_data="status"),
        ],
        [InlineKeyboardButton("⬅️ Back to Home", callback_data="back")],
    ]
    await message.reply_text(
        text=Script.HELP_TXT,
        reply_markup=InlineKeyboardMarkup(buttons),
        disable_web_page_preview=True,
    )


@Client.on_message(filters.private & filters.command(["restart"]) & filters.user(Config.BOT_OWNER))
async def restart(client, message):
    msg = await message.reply_text(
        text="<blockquote><b>🔄 Restarting server and pulling latest updates...</b></blockquote>"
    )
    await asyncio.sleep(2)
    await msg.edit("<blockquote><b>✅ Server restarted! Rebooting main process...</b></blockquote>")
    system("git pull -f && pip3 install --no-cache-dir -r requirements.txt")
    execle(sys.executable, sys.executable, "main.py", environ)


@Client.on_callback_query(filters.regex(r"^help$"))
async def helpcb(bot, query):
    buttons = [
        [InlineKeyboardButton("🚀 Quick Setup Guide", callback_data="how_to_use")],
        [
            InlineKeyboardButton("ℹ️ About", callback_data="about"),
            InlineKeyboardButton("⚙️ Settings Panel", callback_data="settings#main"),
        ],
        [InlineKeyboardButton("⬅️ Back to Home", callback_data="back")],
    ]
    await query.message.edit_text(
        text=Script.HELP_TXT,
        reply_markup=InlineKeyboardMarkup(buttons),
        disable_web_page_preview=True,
    )


@Client.on_callback_query(filters.regex(r"^how_to_use$"))
async def how_to_use(bot, query):
    buttons = [
        [InlineKeyboardButton("⚙️ Open Control Panel", callback_data="settings#main")],
        [InlineKeyboardButton("⬅️ Back to Help", callback_data="help")],
    ]
    await query.message.edit_text(
        text=Script.HOW_USE_TXT,
        reply_markup=InlineKeyboardMarkup(buttons),
        disable_web_page_preview=True,
    )


@Client.on_callback_query(filters.regex(r"^back$"))
async def back(bot, query):
    reply_markup = InlineKeyboardMarkup(main_buttons)
    await query.message.edit_text(
        reply_markup=reply_markup,
        text=Script.START_TXT.format(query.from_user.first_name),
        disable_web_page_preview=True,
    )


@Client.on_callback_query(filters.regex(r"^about$"))
async def about(bot, query):
    buttons = [
        [
            InlineKeyboardButton("📊 Live Stats", callback_data="status"),
            InlineKeyboardButton("🖥 System Resources", callback_data="systm_sts"),
        ],
        [InlineKeyboardButton("⬅️ Back to Help", callback_data="help")],
    ]
    await query.message.edit_text(
        text=Script.ABOUT_TXT,
        reply_markup=InlineKeyboardMarkup(buttons),
        disable_web_page_preview=True,
    )


@Client.on_callback_query(filters.regex(r"^status$"))
async def status(bot, query):
    users_count, bots_count = await db.total_users_bots_count()
    forwardings = await db.forwad_count()
    upt = await get_bot_uptime(START_TIME)
    buttons = [
        [
            InlineKeyboardButton("🔄 Refresh", callback_data="status"),
            InlineKeyboardButton("🖥 System Resources", callback_data="systm_sts"),
        ],
        [InlineKeyboardButton("⬅️ Back to Help", callback_data="help")],
    ]
    await query.message.edit_text(
        text=Script.STATUS_TXT.format(upt, users_count, bots_count, forwardings),
        reply_markup=InlineKeyboardMarkup(buttons),
        disable_web_page_preview=True,
    )


@Client.on_callback_query(filters.regex(r"^systm_sts$"))
async def sys_status(bot, query):
    buttons = [
        [
            InlineKeyboardButton("🔄 Refresh", callback_data="systm_sts"),
            InlineKeyboardButton("📊 Bot Stats", callback_data="status"),
        ],
        [InlineKeyboardButton("⬅️ Back to Help", callback_data="help")],
    ]
    ram = psutil.virtual_memory().percent
    cpu = psutil.cpu_percent()
    disk_usage = psutil.disk_usage("/")
    total_space = disk_usage.total / (1024**3)
    used_space = disk_usage.used / (1024**3)
    free_space = disk_usage.free / (1024**3)
    text = (
        "<blockquote><b>🖥 SERVER SYSTEM RESOURCES</b></blockquote>\n\n"
        "<blockquote>"
        f"┌ <b>💾 Total Disk:</b> <code>{total_space:.2f} GB</code>\n"
        f"├ <b>📦 Used Disk:</b> <code>{used_space:.2f} GB</code>\n"
        f"├ <b>🟢 Free Disk:</b> <code>{free_space:.2f} GB</code>\n"
        f"├ <b>⚡ CPU Load:</b> <code>{cpu}%</code>\n"
        f"└ <b>🧠 RAM Usage:</b> <code>{ram}%</code>"
        "</blockquote>"
    )
    await query.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(buttons),
        disable_web_page_preview=True,
    )


async def get_bot_uptime(start_time):
    uptime_seconds = int(time.time() - start_time)
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