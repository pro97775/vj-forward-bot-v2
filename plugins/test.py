# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

import re 
import asyncio 
import logging 
from database import db, DEFAULT_CONFIGS
from config import Config
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from pyrogram.errors import FloodWait, ListenerTimeout
from typing import Union, Optional, AsyncGenerator
from pyrogram.errors import (
    PhoneNumberInvalid,
    PhoneCodeInvalid,
    PhoneCodeExpired,
    SessionPasswordNeeded,
    PasswordHashInvalid
)

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

BTN_URL_REGEX = re.compile(r"(\[([^\[]+?)]\[buttonurl:/{0,2}(.+?)(:same)?])")
TOKEN_REGEX = re.compile(r'\d{5,16}:[0-9A-Za-z_-]{30,}')
BOT_TOKEN_TEXT = """<b>❪ ADD BOT ❫</b>

<b>Send your bot token directly, or forward the @BotFather message which contains the token.</b>

<b>➣ You can send more than one token together (one per line or separated by space) to add multiple bots for round robin forwarding.</b>

<code>eg: 123456789:AAFxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx</code>

/cancel - <code>cancel this process</code>"""
SESSION_TEXT = """<b>❪ ADD USERBOT ❫</b>

<b>Send your pyrogram v2 session string directly, or send your phone number (with country code) to login here.</b>

/cancel - <code>cancel this process</code>"""
SESSION_STRING_SIZE = 351

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

class CLIENT: 
  def __init__(self):
     self.api_id = Config.API_ID
     self.api_hash = Config.API_HASH

  def user_session(self, data):
      return Client("USERBOT", self.api_id, self.api_hash, session_string=data)

  async def add_bot(self, bot, message):
     """Add one or more bots. Accepts direct tokens or a BotFather forward."""
     user_id = int(message.from_user.id)
     if await db.count_bots(user_id) >= Config.MAX_BOTS:
        await bot.send_message(user_id, f"<b>You can add maximum {Config.MAX_BOTS} bots. Please remove a bot first.</b>")
        return False
     try:
        msg = await bot.ask(chat_id=user_id, text=BOT_TOKEN_TEXT, timeout=300)
     except ListenerTimeout:
        await bot.send_message(user_id, "<b>time out ! process cancelled.</b>")
        return False
     text = msg.text or msg.caption
     if text and text.strip().startswith('/'):
        await msg.reply('<b>process cancelled !</b>')
        return False
     tokens = list(dict.fromkeys(TOKEN_REGEX.findall(text or ""))) 
     if not tokens:
        await msg.reply_text("<b>There is no bot token in that message</b>")
        return False
     allowed = Config.MAX_BOTS - await db.count_bots(user_id)
     tokens = tokens[:allowed]
     added, failed = [], []
     sts = await msg.reply_text("<code>checking your bots, please wait..</code>")
     for token in tokens:
        _client = Client("BOT", Config.API_ID, Config.API_HASH, bot_token=token, in_memory=True)
        try:
          await _client.start()
          _bot = _client.me
        except Exception as e:
          failed.append(f"<code>{token[:12]}...</code> - {e}")
          continue
        finally:
          try:
             await _client.stop()
          except Exception:
             pass
        details = {
          'id': _bot.id,
          'is_bot': True,
          'user_id': user_id,
          'name': _bot.first_name,
          'token': token,
          'username': _bot.username 
        }
        if await db.add_bot(details):
           added.append(f"@{_bot.username}")
        else:
           failed.append(f"@{_bot.username} - already added")
     result = ""
     if added:
        result += "<b>✅ Added bots:</b>\n" + "\n".join(added)
     if failed:
        result += ("\n\n" if result else "") + "<b>❌ Failed:</b>\n" + "\n".join(failed)
     await sts.edit(result or "<b>No bot added</b>")
     return bool(added)

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

  async def add_session(self, bot, message):
     """Add a userbot from a pasted session string or by phone login."""
     user_id = int(message.from_user.id)
     text = "<b>⚠️ DISCLAIMER ⚠️</b>\n\n<code>you can use your session for forward message from private chat to another chat.\nPlease add your pyrogram session with your own risk. Their is a chance to ban your account. My developer is not responsible if your account may get banned.</code>"
     await bot.send_message(user_id, text=text)
     try:
        first = await bot.ask(chat_id=user_id, text=SESSION_TEXT, timeout=300)
     except ListenerTimeout:
        await bot.send_message(user_id, "<b>time out ! process cancelled.</b>")
        return False
     data = (first.text or "").strip()
     if data.startswith('/'):
        await first.reply('<b>process cancelled !</b>')
        return False
     if len(data) >= SESSION_STRING_SIZE and " " not in data:
        # direct session string paste
        return await self.save_session(first, user_id, data)
     phone_number = data.replace(" ", "")
     if not phone_number.startswith("+") or not phone_number[1:].isdigit():
        await first.reply("<b>Invalid session string or phone number. Phone number must include country code.</b>")
        return False
     client = Client(":memory:", Config.API_ID, Config.API_HASH)
     await client.connect()
     await first.reply("Sending OTP...")
     try:
        code = await client.send_code(phone_number)
        phone_code_msg = await bot.ask(user_id, "Please check for an OTP in official telegram account. If you got it, send OTP here after reading the below format. \n\nIf OTP is `12345`, **please send it as** `1 2 3 4 5`.\n\n**Enter /cancel to cancel The Procces**", filters=filters.text, timeout=600)
     except PhoneNumberInvalid:
        await first.reply('`PHONE_NUMBER` **is invalid.**')
        await client.disconnect()
        return False
     except ListenerTimeout:
        await client.disconnect()
        await bot.send_message(user_id, "<b>time out ! process cancelled.</b>")
        return False
     except Exception as e:
        await first.reply(f"<b>ERROR:</b> `{e}`")
        await client.disconnect()
        return False
     if phone_code_msg.text.strip() == '/cancel':
        await client.disconnect()
        await phone_code_msg.reply('<b>process cancelled !</b>')
        return False
     try:
        phone_code = phone_code_msg.text.replace(" ", "")
        await client.sign_in(phone_number, code.phone_code_hash, phone_code)
     except PhoneCodeInvalid:
        await phone_code_msg.reply('**OTP is invalid.**')
        await client.disconnect()
        return False
     except PhoneCodeExpired:
        await phone_code_msg.reply('**OTP is expired.**')
        await client.disconnect()
        return False
     except SessionPasswordNeeded:
        try:
           two_step_msg = await bot.ask(user_id, '**Your account has enabled two-step verification. Please provide the password.\n\nEnter /cancel to cancel The Procces**', filters=filters.text, timeout=300)
        except ListenerTimeout:
           await client.disconnect()
           await bot.send_message(user_id, "<b>time out ! process cancelled.</b>")
           return False
        if two_step_msg.text.strip() == '/cancel':
           await client.disconnect()
           await two_step_msg.reply('<b>process cancelled !</b>')
           return False
        try:
           await client.check_password(password=two_step_msg.text)
        except PasswordHashInvalid:
           await two_step_msg.reply('**Invalid Password Provided**')
           await client.disconnect()
           return False
     except Exception as e:
        await phone_code_msg.reply(f"<b>ERROR:</b> `{e}`")
        await client.disconnect()
        return False
     string_session = await client.export_session_string()
     await client.disconnect()
     return await self.save_session(phone_code_msg, user_id, string_session)

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

  async def save_session(self, msg, user_id, string_session):
     """Validate a session string and store the userbot."""
     if len(string_session) < SESSION_STRING_SIZE:
        await msg.reply('<b>invalid session string</b>')
        return False
     _client = Client("USERBOT", self.api_id, self.api_hash, session_string=string_session)
     try:
       await _client.start()
       user = _client.me
     except Exception as e:
       await msg.reply_text(f"<b>USER BOT ERROR:</b> `{e}`")
       return False
     finally:
       try:
          await _client.stop()
       except Exception:
          pass
     details = {
       'id': user.id,
       'is_bot': False,
       'user_id': user_id,
       'name': user.first_name,
       'session': string_session,
       'username': user.username
     }
     await db.add_userbot(details)
     return True

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

@Client.on_message(filters.private & filters.command('reset'))
async def reset_settings(bot, m):
   """Reset a user settings to the default values."""
   await db.update_configs(m.from_user.id, DEFAULT_CONFIGS)
   await m.reply("successfully settings reseted ✔️")

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

@Client.on_message(filters.command('resetall') & filters.user(Config.BOT_OWNER))
async def resetall(bot, message):
  users = await db.get_all_users()
  sts = await message.reply("**processing**")
  TEXT = "total: {}\nsuccess: {}\nfailed: {}"
  total = success = failed = 0
  ERRORS = []
  async for user in users:
      user_id = user.get('id')
      if not user_id:
         continue
      total += 1
      if total % 10 == 0:
         try:
            await sts.edit(TEXT.format(total, success, failed))
         except Exception:
            pass
      try: 
         await db.update_configs(user_id, DEFAULT_CONFIGS)
         success += 1
      except Exception as e:
         ERRORS.append(str(e))
         failed += 1
  if ERRORS:
     await message.reply(str(ERRORS[:10])[:4000])
  await sts.edit("completed\n" + TEXT.format(total, success, failed))

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

async def get_configs(user_id):
  configs = await db.get_configs(user_id)
  return configs

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

async def update_configs(user_id, key, value):
  current = await db.get_configs(user_id)
  if key in current and key != 'filters':
     current[key] = value
  else: 
     current['filters'][key] = value
  await db.update_configs(user_id, current)

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

async def iter_messages(
    self,
    chat_id: Union[int, str],
    limit: int,
    offset: int = 0,
    filters: list = None,
) -> Optional[AsyncGenerator["Message", None]]:
        """Iterate a chat message by message.

        Messages which match one of the disabled media `filters` are
        yielded as the string "FILTERED" so the caller can count them.
        """
        filters = filters or []
        current = offset + 1 if offset else 1
        limit = int(limit)
        while current <= limit:
            new_diff = min(200, limit - current + 1)
            if new_diff <= 0:
                return
            ids = list(range(current, current + new_diff))
            try:
                messages = await self.get_messages(chat_id, ids)
            except FloodWait as e:
                await asyncio.sleep(e.value)
                continue
            if not messages:
                return
            for message in messages:
                if filters and any(getattr(message, media_type, False) for media_type in filters):
                    yield "FILTERED"
                else:
                    yield message
            current += len(ids)

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

async def get_client(bot_token, is_bot=True, name=None):
  """Create (not start) a pyrogram client for a bot token / user session."""
  if is_bot:
    return Client(name or "BOT", Config.API_ID, Config.API_HASH, bot_token=bot_token, in_memory=True)
  else:
    return Client(name or "USERBOT", Config.API_ID, Config.API_HASH, session_string=bot_token, in_memory=True)

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

def parse_buttons(text, markup=True):
    buttons = []
    for match in BTN_URL_REGEX.finditer(text):
        n_escapes = 0
        to_check = match.start(1) - 1
        while to_check > 0 and text[to_check] == "\\":
            n_escapes += 1
            to_check -= 1

        if n_escapes % 2 == 0:
            if bool(match.group(4)) and buttons:
                buttons[-1].append(InlineKeyboardButton(
                    text=match.group(2),
                    url=match.group(3).replace(" ", "")))
            else:
                buttons.append([InlineKeyboardButton(
                    text=match.group(2),
                    url=match.group(3).replace(" ", ""))])
    if markup and buttons:
       buttons = InlineKeyboardMarkup(buttons)
    return buttons if buttons else None

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01
