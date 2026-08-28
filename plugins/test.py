"""Client factories, the message iterator, and the login flows.

Every temporary ``Client`` created here is closed on every exit path — the
previous version leaked a connected client (socket + dispatcher tasks) on each
failed OTP, invalid password, or cancelled login.
"""

import asyncio
import logging
import re
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional, Union

from pyrogram import Client, filters
from pyrogram.errors import (
    FloodWait,
    PasswordHashInvalid,
    PhoneCodeExpired,
    PhoneCodeInvalid,
    PhoneNumberInvalid,
    SessionPasswordNeeded,
)
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from config import Config
from database import db

logger = logging.getLogger(__name__)

BTN_URL_REGEX = re.compile(r"(\[([^\[]+?)\]\[buttonurl:/{0,2}(.+?)(:same)?\])")
BOT_TOKEN_TEXT = (
    "<b>1) create a bot using @BotFather\n"
    "2) Then you will get a message with bot token\n"
    "3) Send or forward that message to me</b>"
)
SESSION_STRING_SIZE = 351

# Telegram accepts at most 200 message ids per get_messages call.
MAX_IDS_PER_CALL = 200


# ── client factories ───────────────────────────────────────────────


def build_client(credential, is_bot=True, name=None):
    """Create (but do not start) a client for a bot token or session string."""
    if is_bot:
        return Client(
            name or "BOT",
            Config.API_ID,
            Config.API_HASH,
            bot_token=credential,
            in_memory=True,
            sleep_threshold=120,
        )
    return Client(
        name or "USERBOT",
        Config.API_ID,
        Config.API_HASH,
        session_string=credential,
        in_memory=True,
        sleep_threshold=120,
    )


async def get_client(bot_token, is_bot=True):
    """Backward-compatible factory. Caller is responsible for start/stop."""
    return build_client(bot_token, is_bot=is_bot)


@asynccontextmanager
async def temporary_client(credential, is_bot=True, name=None):
    """Start a client and guarantee it is stopped, even on exceptions."""
    client = build_client(credential, is_bot=is_bot, name=name)
    started = False
    try:
        await client.start()
        started = True
        yield client
    finally:
        if started:
            try:
                await client.stop()
            except Exception as exc:
                logger.debug("client stop failed: %s", exc)


async def close_client(client):
    """Best-effort teardown that tolerates any client state."""
    if client is None:
        return
    for method in ("stop", "disconnect"):
        try:
            await getattr(client, method)()
            return
        except Exception:
            continue


class CLIENT:
    def __init__(self):
        self.api_id = Config.API_ID
        self.api_hash = Config.API_HASH

    def user_session(self, data):
        return build_client(data, is_bot=False)

    # ── add a bot ───────────────────────────────────────────────────

    async def add_bot(self, bot, message):
        user_id = int(message.from_user.id)
        msg = await bot.ask(chat_id=user_id, text=BOT_TOKEN_TEXT)
        if msg.text == "/cancel":
            await msg.reply("<b>process cancelled !</b>")
            return False
        if not msg.text:
            await msg.reply_text("<b>Send the bot token as text.</b>")
            return False

        found = re.findall(r"\d[0-9]{8,10}:[0-9A-Za-z_-]{35}", msg.text, re.IGNORECASE)
        if not found:
            await msg.reply_text("<b>There is no valid bot token in that message</b>")
            return False
        bot_token = found[0]

        try:
            async with temporary_client(bot_token, is_bot=True) as client:
                me = client.me
                details = {
                    "id": me.id,
                    "is_bot": True,
                    "user_id": user_id,
                    "name": me.first_name,
                    "token": bot_token,
                    "username": me.username,
                }
        except Exception as exc:
            await msg.reply_text(f"<b>BOT ERROR:</b> <code>{exc}</code>")
            return False

        added = await db.add_bot_to_list(user_id, details)
        if not added:
            await msg.reply_text("<b>That bot is already added.</b>")
            return False
        return True

    # ── add a userbot ───────────────────────────────────────────────

    async def _save_session(self, user_id, session_string):
        """Validate a session string and persist it. Returns (ok, error)."""
        try:
            async with temporary_client(session_string, is_bot=False) as client:
                me = client.me
                details = {
                    "id": me.id,
                    "is_bot": False,
                    "user_id": user_id,
                    "name": me.first_name,
                    "session": session_string,
                    "username": me.username,
                }
        except Exception as exc:
            return False, str(exc)
        await db.add_userbot(details)
        return True, None

    async def add_session(self, bot, message):
        user_id = int(message.from_user.id)
        await bot.send_message(
            user_id,
            "<b>⚠️ DISCLAIMER ⚠️</b>\n\n<code>A userbot lets you forward from private "
            "chats your bots cannot see. Adding a session carries a risk of the "
            "account being limited or banned. Use an account you can afford to "
            "lose. Your session string is stored in the bot's database — only add "
            "it if you trust this deployment.</code>",
        )
        prompt = await bot.ask(
            chat_id=user_id,
            text="<b>Send your pyrogram session string, OR send your phone number "
            "(with country code) to log in here instead.</b>\n"
            "<b>Example phone:</b> <code>+13124562345</code>\n\n"
            "/cancel - cancel this process",
        )
        if not prompt.text or prompt.text == "/cancel":
            await prompt.reply("<b>process cancelled !</b>")
            return False

        # ── direct session string ────────────────────────────────────
        text = prompt.text.strip()
        if len(text) >= SESSION_STRING_SIZE:
            ok, error = await self._save_session(user_id, text)
            if not ok:
                await prompt.reply_text(f"<b>USER BOT ERROR:</b> <code>{error}</code>")
                return False
            return True

        # ── phone number / OTP login ─────────────────────────────────
        phone_number = text
        client = Client(
            "login", Config.API_ID, Config.API_HASH, in_memory=True
        )
        try:
            await client.connect()
        except Exception as exc:
            await prompt.reply_text(f"<b>CONNECT ERROR:</b> <code>{exc}</code>")
            return False

        try:
            await prompt.reply("Sending OTP...")
            try:
                code = await client.send_code(phone_number)
            except PhoneNumberInvalid:
                await prompt.reply("<code>PHONE_NUMBER</code> <b>is invalid.</b>")
                return False
            except FloodWait as exc:
                await prompt.reply(
                    f"<b>Telegram asked us to wait {exc.value}s before trying again.</b>"
                )
                return False

            code_msg = await bot.ask(
                user_id,
                "Check the official Telegram app for the login code.\n\n"
                "If the code is `12345`, **send it as** `1 2 3 4 5`.\n\n"
                "/cancel - cancel this process",
                filters=filters.text,
                timeout=600,
            )
            if code_msg.text == "/cancel":
                await code_msg.reply("<b>process cancelled !</b>")
                return False

            try:
                await client.sign_in(
                    phone_number, code.phone_code_hash, code_msg.text.replace(" ", "")
                )
            except PhoneCodeInvalid:
                await code_msg.reply("<b>The code is invalid.</b>")
                return False
            except PhoneCodeExpired:
                await code_msg.reply("<b>The code has expired.</b>")
                return False
            except SessionPasswordNeeded:
                pwd_msg = await bot.ask(
                    user_id,
                    "<b>This account has two-step verification. Send the password.</b>\n\n"
                    "/cancel - cancel this process",
                    filters=filters.text,
                    timeout=300,
                )
                if pwd_msg.text == "/cancel":
                    await pwd_msg.reply("<b>process cancelled !</b>")
                    return False
                try:
                    await client.check_password(password=pwd_msg.text)
                except PasswordHashInvalid:
                    await pwd_msg.reply("<b>Invalid password.</b>")
                    return False

            session_string = await client.export_session_string()
        except asyncio.TimeoutError:
            await bot.send_message(user_id, "<b>Timed out. Process cancelled.</b>")
            return False
        finally:
            # This is the leak the old code had: every early return above
            # left a connected client behind.
            await close_client(client)

        if len(session_string) < SESSION_STRING_SIZE:
            await prompt.reply("<b>Invalid session string generated</b>")
            return False

        ok, error = await self._save_session(user_id, session_string)
        if not ok:
            await prompt.reply_text(f"<b>USER BOT ERROR:</b> <code>{error}</code>")
            return False
        return True


# ── message iteration ──────────────────────────────────────────────


async def iter_messages(
    client,
    chat_id: Union[int, str],
    limit: int,
    offset: int = 0,
    skip_types=None,
    batch: int = MAX_IDS_PER_CALL,
) -> Optional[AsyncGenerator]:
    """Walk a chat by message id, yielding messages one at a time.

    ``limit`` is the highest message id to reach; ``offset`` is where to start.
    Yields the sentinel string ``"FILTERED"`` for messages whose media type the
    user disabled, so the caller can count them without holding the object.

    Fixes over the previous implementation:
      * requests at most 200 ids per call (Telegram's cap; it asked for 201)
      * survives FloodWait instead of aborting the whole task
      * advances the cursor exactly once per batch (it used to double-advance
        and silently skip ranges)
      * ``skip_types`` replaces the ``filters`` parameter name, which shadowed
        ``pyrogram.filters`` inside this module
    """
    skip_types = list(skip_types or [])
    current = int(offset)
    limit = int(limit)
    batch = max(1, min(int(batch), MAX_IDS_PER_CALL))

    while current <= limit:
        size = min(batch, limit - current + 1)
        if size <= 0:
            return
        ids = list(range(current, current + size))

        try:
            messages = await client.get_messages(chat_id, ids)
        except FloodWait as exc:
            await asyncio.sleep(exc.value)
            continue
        except Exception as exc:
            logger.warning("get_messages failed for %s..%s: %s", ids[0], ids[-1], exc)
            current += size
            continue

        if messages is None:
            messages = []
        elif not isinstance(messages, list):
            messages = [messages]

        for message in messages:
            if message is None:
                continue
            if skip_types and any(
                getattr(message, media_type, None) for media_type in skip_types
            ):
                yield "FILTERED"
            else:
                yield message

        # Advance past the whole requested window exactly once.
        current += size
        # Let the event loop breathe between batches.
        await asyncio.sleep(0)


# ── config helpers ─────────────────────────────────────────────────

CONFIG_KEYS = (
    "caption",
    "duplicate",
    "db_uri",
    "forward_tag",
    "protect",
    "min_size",
    "max_size",
    "extension",
    "extension_mode",
    "keywords",
    "button",
    "dry_run",
)


async def get_configs(user_id):
    return await db.get_configs(user_id)


async def update_configs(user_id, key, value):
    current = await db.get_configs(user_id)
    if key in CONFIG_KEYS:
        current[key] = value
    else:
        current["filters"][key] = value
    await db.update_configs(user_id, current)


# ── button parsing ─────────────────────────────────────────────────


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
            button = InlineKeyboardButton(
                text=match.group(2), url=match.group(3).replace(" ", "")
            )
            if bool(match.group(4)) and buttons:
                buttons[-1].append(button)
            else:
                buttons.append([button])
    if markup and buttons:
        return InlineKeyboardMarkup(buttons)
    return buttons if buttons else None
