# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

import re
import time
import asyncio
import logging
from collections import deque
from typing import Union, Optional, AsyncGenerator
from database import db, DEFAULT_CONFIGS
from config import Config
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.errors import (
    FloodWait,
    PhoneNumberInvalid,
    PhoneCodeInvalid,
    PhoneCodeExpired,
    SessionPasswordNeeded,
    PasswordHashInvalid,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

BTN_URL_REGEX = re.compile(r"(\[([^\[]+?)]\[buttonurl:/{0,2}(.+?)(:same)?])")
TOKEN_REGEX = re.compile(r"\d{8,12}:[0-9A-Za-z_-]{35}")

BOT_TOKEN_TEXT = (
    "<blockquote><b>🤖 ADD WORKER BOT(S) TO ROUND-ROBIN POOL</b></blockquote>\n\n"
    "<blockquote>You can add <b>one or multiple</b> worker bots at once!\n"
    "• Paste one or more <b>Bot Tokens</b> separated by newlines or spaces, OR\n"
    "• Forward the token message from @BotFather.\n\n"
    "⚡ Each bot adds <code>+20 msgs/min</code> capacity and scales down forwarding delay automatically.</blockquote>\n\n"
    "<i>Send /cancel to abort.</i>"
)

SESSION_STRING_SIZE = 300


def compute_pool_delay(num_bots: int) -> float:
    """
    Auto-Adjusted Bot Delay:
      1 bot = 3.0s, 2 bots = 1.5s, 3 bots = 1.0s, 6 bots = 0.5s
    """
    if num_bots <= 0:
        return Config.SINGLE_BOT_BASE_DELAY
    return max(Config.MIN_POOL_DELAY, round(Config.SINGLE_BOT_BASE_DELAY / num_bots, 2))


class BotPool:
    """
    Multi-Bot Round-Robin Pool with:
      - Strict 20 messages per 60s sliding window per bot
      - Round-Robin rotation across all active bots
      - Auto-scaled base delay (1 bot = 3.0s, 2 = 1.5s, 3 = 1.0s, 6 = 0.5s)
      - Dynamic FloodWait adaptation per bot and across the pool
    """

    def __init__(self, bots_data: list = None, userbot_data: dict = None, mode: str = "pool"):
        self.bots_data = bots_data or []
        self.userbot_data = userbot_data
        self.mode = mode  # 'pool' or 'userbot'
        self.entries = []
        self.rr_index = 0
        self.base_delay = Config.SINGLE_BOT_BASE_DELAY
        self.dynamic_extra_delay = 0.0
        self.max_per_min = Config.MAX_MSGS_PER_MINUTE_PER_BOT
        self.window_sec = Config.RATE_LIMIT_WINDOW_SECONDS
        self._lock = asyncio.Lock()

    @property
    def current_delay(self) -> float:
        return round(self.base_delay + self.dynamic_extra_delay, 2)

    @property
    def active_count(self) -> int:
        return len(self.entries)

    @property
    def mode_label(self) -> str:
        if self.mode == "userbot":
            uname = self.entries[0]["username"] if self.entries else "Userbot"
            return f"Userbot (@{uname})"
        return f"Multi-Bot Pool ({self.active_count} Bot{'s' if self.active_count != 1 else ''})"

    async def start_all(self):
        self.entries = []
        if self.mode == "userbot" and self.userbot_data:
            client = await get_client(self.userbot_data["session"], is_bot=False)
            await client.start()
            self.entries.append({
                "id": self.userbot_data["id"],
                "name": self.userbot_data["name"],
                "username": self.userbot_data.get("username", "userbot"),
                "is_bot": False,
                "client": client,
                "window": deque(),
                "flood_until": 0.0,
            })
            self.base_delay = Config.SINGLE_BOT_BASE_DELAY
            return self.entries

        # Start all worker bots in Multi-Bot Pool
        for idx, bdata in enumerate(self.bots_data):
            try:
                client = await get_client(
                    bdata["token"],
                    is_bot=True,
                    name=f"POOL_BOT_{bdata['id']}_{idx}"
                )
                await client.start()
                self.entries.append({
                    "id": bdata["id"],
                    "name": bdata["name"],
                    "username": bdata.get("username", ""),
                    "is_bot": True,
                    "client": client,
                    "window": deque(),
                    "flood_until": 0.0,
                })
            except Exception as e:
                logger.warning(f"Failed to start worker bot {bdata.get('username')}: {e}")

        if not self.entries and self.userbot_data:
            self.mode = "userbot"
            client = await get_client(self.userbot_data["session"], is_bot=False)
            await client.start()
            self.entries.append({
                "id": self.userbot_data["id"],
                "name": self.userbot_data["name"],
                "username": self.userbot_data.get("username", "userbot"),
                "is_bot": False,
                "client": client,
                "window": deque(),
                "flood_until": 0.0,
            })

        self.base_delay = compute_pool_delay(len(self.entries))
        return self.entries

    async def stop_all(self):
        for entry in self.entries:
            try:
                await entry["client"].stop()
            except Exception:
                pass
        self.entries = []

    def primary_client(self):
        return self.entries[0]["client"] if self.entries else None

    def record_floodwait(self, entry: dict, wait_seconds: int):
        """Mark a specific bot on cooldown and dynamically adapt pool delay."""
        now = time.monotonic()
        entry["flood_until"] = max(entry["flood_until"], now + float(wait_seconds))
        self.dynamic_extra_delay = min(5.0, round(self.dynamic_extra_delay + 0.5, 2))
        logger.info(
            f"Bot @{entry.get('username')} hit FloodWait({wait_seconds}s). "
            f"Adjusted pool delay to {self.current_delay}s."
        )

    def record_success(self):
        """Gradually decay dynamic FloodWait penalty after clean sends."""
        if self.dynamic_extra_delay > 0:
            self.dynamic_extra_delay = max(0.0, round(self.dynamic_extra_delay - 0.05, 2))

    async def acquire_bot(self) -> dict:
        """
        Select the next worker bot in Round-Robin order that respects:
          1. Not in FloodWait cooldown
          2. Strictly < 20 messages sent within the last 60.0s sliding window
        """
        async with self._lock:
            n = len(self.entries)
            if n == 0:
                raise RuntimeError("No active bots in pool.")

            while True:
                now = time.monotonic()
                earliest_ready = None

                for step in range(n):
                    idx = (self.rr_index + step) % n
                    entry = self.entries[idx]
                    win = entry["window"]

                    while win and (now - win[0]) >= self.window_sec:
                        win.popleft()

                    ready_at = entry["flood_until"]
                    if len(win) >= self.max_per_min:
                        window_ready = win[0] + self.window_sec
                        if window_ready > ready_at:
                            ready_at = window_ready

                    if ready_at <= now:
                        self.rr_index = (idx + 1) % n
                        win.append(now)
                        return entry

                    if earliest_ready is None or ready_at < earliest_ready:
                        earliest_ready = ready_at

                sleep_for = max(0.05, (earliest_ready - now) if earliest_ready else 0.5)
                await asyncio.sleep(sleep_for)


class CLIENT:
    def __init__(self):
        self.api_id = Config.API_ID
        self.api_hash = Config.API_HASH

    def user_session(self, data):
        return Client("USERBOT", self.api_id, self.api_hash, session_string=data)

    async def add_bot(self, bot, message):
        user_id = int(message.from_user.id)
        msg = await bot.ask(chat_id=user_id, text=BOT_TOKEN_TEXT)
        if not msg.text:
            await msg.reply_text("<blockquote><b>❌ Please send valid text containing one or more bot tokens.</b></blockquote>")
            return False
        if msg.text.strip().startswith("/cancel"):
            await msg.reply_text("<blockquote><b>🚫 Process cancelled.</b></blockquote>")
            return False

        tokens = TOKEN_REGEX.findall(msg.text)
        unique_tokens = list(dict.fromkeys(tokens))
        if not unique_tokens:
            await msg.reply_text(
                "<blockquote><b>❌ No valid bot tokens found!</b>\n"
                "Make sure your token looks like <code>123456789:ABCdefGHIjklMNOpqrSTUvwxYZ</code>.</blockquote>"
            )
            return False

        status_msg = await msg.reply_text(
            f"<blockquote><b>⏳ Verifying {len(unique_tokens)} bot token(s)...</b></blockquote>"
        )
        added = []
        failed = []

        for idx, token in enumerate(unique_tokens, start=1):
            try:
                _client = Client(
                    f"VERIFY_BOT_{user_id}_{idx}",
                    Config.API_ID,
                    Config.API_HASH,
                    bot_token=token,
                    in_memory=True,
                )
                await _client.start()
                _bot = _client.me
                await _client.stop()
                details = {
                    "id": _bot.id,
                    "is_bot": True,
                    "user_id": user_id,
                    "name": _bot.first_name,
                    "token": token,
                    "username": _bot.username,
                }
                await db.add_bot(details)
                added.append(f"• <b>{_bot.first_name}</b> (@{_bot.username})")
            except Exception as e:
                failed.append(f"• <code>{token[:12]}...</code> — <i>{e}</i>")

        all_bots = await db.get_bots(user_id)
        delay = compute_pool_delay(len(all_bots))
        summary = [
            "<blockquote><b>✅ MULTI-BOT POOL UPDATED</b></blockquote>",
            "<blockquote><b>🤖 Added / Updated ({0}):</b>\n{1}</blockquote>".format(
                len(added), "\n".join(added) if added else "• None"
            ),
            "<blockquote>"
            f"┌ <b>⚡ Total Pool Size:</b> <code>{len(all_bots)} Bot(s)</code>\n"
            f"├ <b>🚀 Pool Capacity:</b> <code>{len(all_bots) * 20} msgs/min</code>\n"
            f"└ <b>⏱ Auto-Adjusted Delay:</b> <code>{delay}s / msg</code>"
            "</blockquote>",
        ]
        if failed:
            summary.append(f"<blockquote><b>⚠️ Failed ({len(failed)}):</b>\n" + "\n".join(failed) + "</blockquote>")

        await status_msg.edit_text("\n\n".join(summary))
        return bool(added)

    async def add_session(self, bot, message):
        user_id = int(message.from_user.id)
        disclaimer = (
            "<blockquote><b>👤 ADD USERBOT SESSION</b></blockquote>\n\n"
            "<blockquote>Use a Userbot session to forward messages from <b>private or restricted chats</b> "
            "where worker bots cannot be added.\n\n"
            "<b>Choose how to connect:</b>\n"
            "• Send your <b>Phone Number</b> with country code (e.g. <code>+13124562345</code>) to log in via OTP, OR\n"
            "• Paste an existing <b>Pyrogram Session String</b> directly.</blockquote>\n\n"
            "<i>Send /cancel to abort.</i>"
        )
        first_msg = await bot.ask(chat_id=user_id, text=disclaimer)
        if not first_msg.text or first_msg.text.strip().startswith("/cancel"):
            await first_msg.reply("<blockquote><b>🚫 Process cancelled.</b></blockquote>")
            return False

        raw_input = first_msg.text.strip()

        if len(raw_input) >= SESSION_STRING_SIZE and not raw_input.startswith("+") and " " not in raw_input:
            string_session = raw_input
        else:
            phone_number = raw_input
            client = Client(":memory:", Config.API_ID, Config.API_HASH, in_memory=True)
            await client.connect()
            await first_msg.reply("<blockquote><b>📲 Sending OTP code to your Telegram account...</b></blockquote>")
            try:
                code = await client.send_code(phone_number)
                phone_code_msg = await bot.ask(
                    user_id,
                    "<blockquote><b>📩 ENTER TELEGRAM OTP CODE</b></blockquote>\n\n"
                    "<blockquote>Check your official Telegram account for the login code.\n"
                    "• If the code is <code>12345</code>, send it spaced as <code>1 2 3 4 5</code>.</blockquote>\n\n"
                    "<i>Send /cancel to abort.</i>",
                    filters=filters.text,
                    timeout=600,
                )
            except PhoneNumberInvalid:
                await first_msg.reply("<blockquote><b>❌ Invalid phone number format.</b></blockquote>")
                await client.disconnect()
                return False
            except Exception as e:
                await first_msg.reply(f"<blockquote><b>❌ Error sending OTP:</b> <code>{e}</code></blockquote>")
                await client.disconnect()
                return False

            if phone_code_msg.text.strip().startswith("/cancel"):
                await phone_code_msg.reply("<blockquote><b>🚫 Process cancelled.</b></blockquote>")
                await client.disconnect()
                return False

            try:
                phone_code = phone_code_msg.text.replace(" ", "").strip()
                await client.sign_in(phone_number, code.phone_code_hash, phone_code)
            except PhoneCodeInvalid:
                await phone_code_msg.reply("<blockquote><b>❌ Invalid OTP code.</b></blockquote>")
                await client.disconnect()
                return False
            except PhoneCodeExpired:
                await phone_code_msg.reply("<blockquote><b>❌ OTP code has expired.</b></blockquote>")
                await client.disconnect()
                return False
            except SessionPasswordNeeded:
                two_step_msg = await bot.ask(
                    user_id,
                    "<blockquote><b>🔐 TWO-STEP VERIFICATION (2FA)</b></blockquote>\n\n"
                    "<blockquote>Please send your 2FA cloud password to complete login.</blockquote>\n\n"
                    "<i>Send /cancel to abort.</i>",
                    filters=filters.text,
                    timeout=300,
                )
                if two_step_msg.text.strip().startswith("/cancel"):
                    await two_step_msg.reply("<blockquote><b>🚫 Process cancelled.</b></blockquote>")
                    await client.disconnect()
                    return False
                try:
                    await client.check_password(password=two_step_msg.text.strip())
                except PasswordHashInvalid:
                    await two_step_msg.reply("<blockquote><b>❌ Invalid 2FA password provided.</b></blockquote>")
                    await client.disconnect()
                    return False

            string_session = await client.export_session_string()
            await client.disconnect()

        try:
            _client = Client(
                f"VERIFY_USERBOT_{user_id}",
                self.api_id,
                self.api_hash,
                session_string=string_session,
                in_memory=True,
            )
            await _client.start()
            user = _client.me
            await _client.stop()
        except Exception as e:
            await first_msg.reply_text(f"<blockquote><b>❌ Userbot Login Error:</b> <code>{e}</code></blockquote>")
            return False

        details = {
            "id": user.id,
            "is_bot": False,
            "user_id": user_id,
            "name": user.first_name,
            "session": string_session,
            "username": user.username or "NoUsername",
        }
        await db.add_userbot(details)
        return True


@Client.on_message(filters.private & filters.command("reset"))
async def reset_user_settings(bot, m):
    import copy
    await db.update_configs(m.from_user.id, copy.deepcopy(DEFAULT_CONFIGS))
    await db.clear_dup_files(m.from_user.id)
    await m.reply("<blockquote><b>✅ All settings and deduplication caches have been reset to default!</b></blockquote>")


@Client.on_message(filters.command("resetall") & filters.user(Config.BOT_OWNER))
async def resetall(bot, message):
    users = await db.get_all_users()
    sts = await message.reply("<blockquote><b>⏳ Resetting all user configurations...</b></blockquote>")
    TEXT = (
        "<blockquote><b>🔄 Reset Progress</b>\n"
        "• Total: <code>{}</code>\n"
        "• Success: <code>{}</code>\n"
        "• Failed: <code>{}</code></blockquote>"
    )
    total = success = failed = 0
    errors = []
    async for user in users:
        user_id = user["id"]
        default = await get_configs(user_id)
        default["db_uri"] = None
        total += 1
        if total % 10 == 0:
            await sts.edit(TEXT.format(total, success, failed))
        try:
            await db.update_configs(user_id, default)
            success += 1
        except Exception as e:
            errors.append(str(e))
            failed += 1
    if errors:
        await message.reply("\n".join(errors[:20]))
    await sts.edit("<blockquote><b>✅ Reset All Completed!</b></blockquote>\n\n" + TEXT.format(total, success, failed))


async def get_configs(user_id):
    return await db.get_configs(user_id)


async def update_configs(user_id, key, value):
    current = await db.get_configs(user_id)
    top_level_keys = {
        "caption",
        "prefix",
        "suffix",
        "duplicate",
        "db_uri",
        "forward_tag",
        "protect",
        "min_size",
        "max_size",
        "size_limit",
        "extension",
        "keywords",
        "button",
        "forward_mode",
        "cleaners",
        "replacements",
    }
    if key in top_level_keys:
        current[key] = value
    elif key in current.get("cleaners", {}):
        current["cleaners"][key] = value
    else:
        current["filters"][key] = value
    await db.update_configs(user_id, current)


async def iter_messages(
    client,
    chat_id: Union[int, str],
    limit: int,
    offset: int = 0,
    filters: list = None,
    max_size: int = None,
) -> Optional[AsyncGenerator["types.Message", None]]:
    current = max(1, int(offset)) if int(offset) > 0 else 1
    filters = filters or []
    while True:
        new_diff = min(200, int(limit) - current + 1)
        if new_diff <= 0:
            return

        batch_ids = list(range(current, current + new_diff))
        try:
            messages = await client.get_messages(chat_id, batch_ids)
        except FloodWait as e:
            await asyncio.sleep(e.value)
            messages = await client.get_messages(chat_id, batch_ids)

        if not isinstance(messages, list):
            messages = [messages]

        for message in messages:
            if message is None:
                current += 1
                continue
            if any(getattr(message, media_type, False) for media_type in filters):
                yield "FILTERED"
            else:
                yield message
            current += 1


async def get_client(bot_token, is_bot=True, name=None):
    if is_bot:
        session_name = name or f"BOT_{bot_token[:10]}"
        return Client(
            session_name,
            Config.API_ID,
            Config.API_HASH,
            bot_token=bot_token,
            in_memory=True,
        )
    else:
        session_name = name or "USERBOT"
        return Client(
            session_name,
            Config.API_ID,
            Config.API_HASH,
            session_string=bot_token,
            in_memory=True,
        )


def parse_buttons(text, markup=True):
    if not text:
        return None
    buttons = []
    for match in BTN_URL_REGEX.finditer(text):
        n_escapes = 0
        to_check = match.start(1) - 1
        while to_check > 0 and text[to_check] == "\\":
            n_escapes += 1
            to_check -= 1

        if n_escapes % 2 == 0:
            if bool(match.group(4)) and buttons:
                buttons[-1].append(
                    InlineKeyboardButton(
                        text=match.group(2),
                        url=match.group(3).replace(" ", ""),
                    )
                )
            else:
                buttons.append(
                    [
                        InlineKeyboardButton(
                            text=match.group(2),
                            url=match.group(3).replace(" ", ""),
                        )
                    ]
                )
    if markup and buttons:
        buttons = InlineKeyboardMarkup(buttons)
    return buttons if buttons else None