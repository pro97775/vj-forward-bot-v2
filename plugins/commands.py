"""Start, help, about, status, and owner commands."""

import asyncio
import logging
import os
import sys
import time

import psutil
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from config import Config, temp
from database import db
from script import Script

from .utils import status_size, sweep_status

logger = logging.getLogger(__name__)
START_TIME = time.time()

main_buttons = [
    [InlineKeyboardButton("❣️ ᴅᴇᴠᴇʟᴏᴘᴇʀ ❣️", url="https://t.me/kingvj01")],
    [
        InlineKeyboardButton("🔍 sᴜᴘᴘᴏʀᴛ ɢʀᴏᴜᴘ", url="https://t.me/vj_bot_disscussion"),
        InlineKeyboardButton("🤖 ᴜᴘᴅᴀᴛᴇ ᴄʜᴀɴɴᴇʟ", url="https://t.me/vj_botz"),
    ],
    [InlineKeyboardButton("💝 sᴜʙsᴄʀɪʙᴇ ᴍʏ ʏᴏᴜᴛᴜʙᴇ ᴄʜᴀɴɴᴇʟ", url="https://youtube.com/@Tech_VJ")],
    [
        InlineKeyboardButton("👨‍💻 ʜᴇʟᴘ", callback_data="help"),
        InlineKeyboardButton("💁 ᴀʙᴏᴜᴛ", callback_data="about"),
    ],
    [InlineKeyboardButton("⚙ sᴇᴛᴛɪɴɢs", callback_data="settings#main")],
]


@Client.on_message(filters.private & filters.command(["start"]))
async def start(client, message):
    user = message.from_user
    if not await db.is_user_exist(user.id):
        await db.add_user(user.id, user.first_name)
    await message.reply_text(
        Script.START_TXT.format(user.first_name),
        reply_markup=InlineKeyboardMarkup(main_buttons),
    )


@Client.on_callback_query(filters.regex(r"^help"))
async def helpcb(bot, query):
    await query.message.edit_text(
        Script.HELP_TXT,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🤔 ʜᴏᴡ ᴛᴏ ᴜsᴇ ᴍᴇ ❓", callback_data="how_to_use")],
            [
                InlineKeyboardButton("Aʙᴏᴜᴛ ✨️", callback_data="about"),
                InlineKeyboardButton("⚙ Sᴇᴛᴛɪɴɢs", callback_data="settings#main"),
            ],
            [InlineKeyboardButton("• back", callback_data="back")],
        ]),
    )


@Client.on_callback_query(filters.regex(r"^how_to_use"))
async def how_to_use(bot, query):
    await query.message.edit_text(
        Script.HOW_USE_TXT,
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("• back", callback_data="help")]]
        ),
        disable_web_page_preview=True,
    )


@Client.on_callback_query(filters.regex(r"^back"))
async def back(bot, query):
    await query.message.edit_text(
        Script.START_TXT.format(query.from_user.first_name),
        reply_markup=InlineKeyboardMarkup(main_buttons),
    )


@Client.on_callback_query(filters.regex(r"^about"))
async def about(bot, query):
    await query.message.edit_text(
        Script.ABOUT_TXT,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("• back", callback_data="help"),
            InlineKeyboardButton("Stats ✨️", callback_data="status"),
        ]]),
        disable_web_page_preview=True,
    )


@Client.on_callback_query(filters.regex(r"^status"))
async def status(bot, query):
    users_count, bots_count = await db.total_users_bots_count()
    forwardings = await db.forwad_count()
    await query.message.edit_text(
        Script.STATUS_TXT.format(
            await get_bot_uptime(START_TIME), users_count, bots_count, forwardings
        ),
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("• back", callback_data="help"),
            InlineKeyboardButton("System Stats ✨️", callback_data="systm_sts"),
        ]]),
        disable_web_page_preview=True,
    )


@Client.on_callback_query(filters.regex(r"^systm_sts"))
async def sys_status(bot, query):
    proc = psutil.Process()
    ram = psutil.virtual_memory().percent
    cpu = psutil.cpu_percent()
    usage = psutil.disk_usage("/")
    rss = proc.memory_info().rss / (1024 ** 2)

    text = f"""
╔════❰ sᴇʀᴠᴇʀ sᴛᴀᴛs  ❱═❍⊱❁۪۪
║╭━━━━━━━━━━━━━━━➣
║┣⪼ <b>ᴛᴏᴛᴀʟ ᴅɪsᴋ sᴘᴀᴄᴇ</b>: <code>{usage.total / (1024 ** 3):.2f} GB</code>
║┣⪼ <b>ᴜsᴇᴅ</b>: <code>{usage.used / (1024 ** 3):.2f} GB</code>
║┣⪼ <b>ꜰʀᴇᴇ</b>: <code>{usage.free / (1024 ** 3):.2f} GB</code>
║┣⪼ <b>ᴄᴘᴜ</b>: <code>{cpu}%</code>
║┣⪼ <b>ʀᴀᴍ</b>: <code>{ram}%</code>
║┣⪼ <b>ʙᴏᴛ ʀss</b>: <code>{rss:.1f} MB</code>
║┣⪼ <b>ᴛʜʀᴇᴀᴅs</b>: <code>{proc.num_threads()}</code>
║┣⪼ <b>ᴀᴄᴛɪᴠᴇ ғᴡᴅs</b>: <code>{temp.forwardings}</code>
║╰━━━━━━━━━━━━━━━➣
╚══════════════════❍⊱❁۪۪
"""
    await query.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("• back", callback_data="help")]]
        ),
        disable_web_page_preview=True,
    )


@Client.on_message(filters.private & filters.command(["restart"]) & filters.user(Config.BOT_OWNER))
async def restart(client, message):
    """Restart the process.

    Pulling from git executes remote code on the host, so it is opt-in via
    ALLOW_GIT_RESTART and runs off the event loop.
    """
    msg = await message.reply_text("<i>Restarting…</i>")

    if Config.ALLOW_GIT_RESTART:
        await msg.edit("<i>Pulling latest code and reinstalling deps…</i>")
        proc = await asyncio.create_subprocess_shell(
            "git pull -f && pip3 install --no-cache-dir -r requirements.txt",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        out, _ = await proc.communicate()
        if proc.returncode != 0:
            tail = (out or b"").decode(errors="replace")[-500:]
            return await msg.edit(
                f"<b>Update failed (exit {proc.returncode}). Not restarting.</b>\n"
                f"<code>{tail}</code>"
            )

    await msg.edit("<i>Server restarting ✅</i>")
    db.close()
    os.execle(sys.executable, sys.executable, "main.py", os.environ)


@Client.on_message(filters.private & filters.command(["reset"]))
async def reset_settings(bot, message):
    await db.update_configs(message.from_user.id, db.default_configs())
    await message.reply("<b>✅ Settings reset to defaults.</b>")


@Client.on_message(filters.command(["resetall"]) & filters.user(Config.BOT_OWNER))
async def resetall(bot, message):
    """Clear every user's saved MongoDB URI."""
    users = await db.get_all_users()
    sts = await message.reply("<b>Processing…</b>")
    template = "total: {}\nsuccess: {}\nfailed: {}"
    total = success = failed = 0
    errors = []

    async for user in users:
        user_id = user.get("id")
        if user_id is None:
            continue
        total += 1
        try:
            configs = await db.get_configs(user_id)
            configs["db_uri"] = None
            await db.update_configs(user_id, configs)
            success += 1
        except Exception as exc:
            errors.append(str(exc))
            failed += 1
        if total % 20 == 0:
            await sts.edit(template.format(total, success, failed))

    if errors:
        await message.reply(f"<code>{'; '.join(errors[:10])}</code>")
    await sts.edit("<b>Completed</b>\n" + template.format(total, success, failed))


@Client.on_message(filters.private & filters.command(["sweep"]) & filters.user(Config.BOT_OWNER))
async def sweep_cmd(client, message):
    """Force a sweep of stale in-memory task states."""
    before = status_size()
    dropped = sweep_status(ttl=0)
    await message.reply(
        f"<b>Swept {dropped} task state(s).</b>\n"
        f"<code>{before}</code> → <code>{status_size()}</code>"
    )


async def get_bot_uptime(start_time):
    seconds = int(time.time() - start_time)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    parts = []
    if days:
        parts.append(f"{days}D")
    if hours:
        parts.append(f"{hours}H")
    if minutes:
        parts.append(f"{minutes}M")
    parts.append(f"{seconds}S")
    return " ".join(parts)
