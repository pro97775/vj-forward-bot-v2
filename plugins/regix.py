# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

import os
import sys 
import math
import time, re
import asyncio 
import logging
import random
from .utils import STS
from database import Db, db
from .test import CLIENT, get_client, iter_messages
from config import Config, temp
from script import Script
from pyrogram import Client, filters 
from pyrogram.errors import FloodWait, MessageNotModified
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message 
from .db import connect_user_db

CLIENT = CLIENT()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
TEXT = Script.TEXT
PROGRESS = """<b>📊 Forward Progress</b>

<b>📈 Percentage:</b> <code>{}%</code>
<b>🕵 Fetched:</b> <code>{}</code>
<b>✅ Forwarded:</b> <code>{}</code>
<b>⏳ Remaining:</b> <code>{}</code>
<b>📌 Status:</b> <code>{}</code>
<b>⏱ Est. Time:</b> <code>{}</code>
<b>🔁 Uptime:</b> <code>{}</code>"""

BATCH_SIZE = 20        
BASE_SLEEP = 2.7       
STAGGER_DELAY = 0.3    

# ==========================================
# 1. BOT POOL MANAGER (FOR ROUND-ROBIN ONLY)
# ==========================================
class BotPool:
    """Manages standard bots for round-robin forwarding"""
    def __init__(self):
        self.clients = []
        self.current_index = 0
        self.lock = asyncio.Lock()

    async def initialize(self, bot_list):
        for i, bot_info in enumerate(bot_list):
            try:
                client = Client(f"BOT_{bot_info['id']}_{random.randint(1000,9999)}", 
                              Config.API_ID, Config.API_HASH, 
                              bot_token=bot_info['token'], in_memory=True)
                
                await client.start()
                self.clients.append({
                    'client': client,
                    'info': bot_info,
                    'is_bot': True,
                    'index': i,
                    'active': True
                })
            except Exception as e:
                logger.error(f"Failed to start bot {bot_info.get('username', 'unknown')}: {e}")

        if not self.clients:
            raise Exception("No standard bots could be started")

    async def get_next_bot(self):
        async with self.lock:
            if not self.clients: return None
            attempts = 0
            while attempts < len(self.clients):
                bot = self.clients[self.current_index]
                self.current_index = (self.current_index + 1) % len(self.clients)
                if bot['active']: return bot
                attempts += 1
            return None

    async def mark_inactive(self, bot_info):
        for bot in self.clients:
            if bot['info']['id'] == bot_info['id']:
                bot['active'] = False
                break

    async def stop_all(self):
        for bot in self.clients:
            try: await bot['client'].stop()
            except: pass
        self.clients = []

# ==========================================
# 2. ENGINE A: MULTI-BOT ROUND-ROBIN
# ==========================================
async def run_round_robin_task(bot, user_id, forward_id, progress_msg, valid_bots, offset_skip=None):
    """Executes task using standard bots only, sharing workload via auto-handling Round-Robin"""
    sts = STS(forward_id)
    i = sts.get(full=True)
    
    _bot_data, caption, forward_tag, datas, protect, button = await sts.get_data(user_id)
    filter_dict, max_size, min_size = datas['filters'], datas['max_size'], datas['min_size']
    keywords = "|".join(datas['keywords']) if datas['keywords'] else None
    extensions = "|".join(datas['extensions']) if datas['extensions'] else None

    bot_pool = BotPool()
    try: await bot_pool.initialize(valid_bots)
    except Exception as e: return await msg_edit(progress_msg, f"<b>Init error:</b> {e}", wait=True)

    test_bot = bot_pool.clients[0]['client']

    # Target chat check
    for bot_entry in bot_pool.clients:
        try:
            k = await bot_entry['client'].send_message(i.TO, "Testing")
            await k.delete()
        except Exception:
            await msg_edit(progress_msg, f"**Make [Bot](t.me/{bot_entry['info']['username']}) Admin In Target Channel**", retry_btn(forward_id), True)
            return await bot_pool.stop_all()

    user_have_db = False
    dburi = datas['db_uri']
    if dburi is not None:
        connected, user_db = await connect_user_db(user_id, dburi, i.TO)
        if connected: user_have_db = True

    temp.IS_FRWD_CHAT.append(i.TO)
    temp.lock[user_id] = locked = True
    dup_files = []

    if user_have_db and datas['skip_duplicate']:
        old_files = await user_db.get_all_files()
        async for ofile in old_files: dup_files.append(ofile["file_id"])

    # Read speed settings from database
    speed_settings = await db.get_batch_settings(user_id)
    queue_size = int(speed_settings.get('batch_size', 100))
    base_sleep = float(speed_settings.get('base_sleep', 3.0))

    if locked:
        try:
            MSG = []
            message_queue = []
            pling = 0
            current_offset = offset_skip if offset_skip is not None else sts.get("skip")
            await edit(user_id, progress_msg, 'ᴘʀᴏɢʀᴇssɪɴɢ', 5, sts)

            async for message in iter_messages(test_bot, chat_id=sts.get("FROM"), limit=sts.get("limit"), offset=current_offset, filters=filter_dict, max_size=max_size):
                if temp.CANCEL.get(user_id):
                    if user_have_db: await user_db.close()
                    return

                if pling % 20 == 0: await edit(user_id, progress_msg, 'ᴘʀᴏɢʀᴇssɪɴɢ', 5, sts)
                pling += 1
                sts.add('fetched')

                if message == "FILTERED":
                    sts.add('filtered')
                    continue
                elif getattr(message, 'empty', False) or getattr(message, 'service', False):
                    sts.add('deleted')
                    continue
                elif message.document and await extension_filter(extensions, message.document.file_name):
                    sts.add('filtered')
                    continue 
                elif message.document and await keyword_filter(keywords, message.document.file_name):
                    sts.add('filtered')
                    continue 
                elif message.document and await size_filter(max_size, min_size, message.document.file_size):
                    sts.add('filtered')
                    continue 
                elif message.document and message.document.file_id in dup_files:
                    sts.add('duplicate')
                    continue

                if message.document and datas['skip_duplicate']:
                    dup_files.append(message.document.file_id)
                    if user_have_db: await user_db.add_file(message.document.file_id)

                if forward_tag:
                    MSG.append(message.id)
                    if len(MSG) >= 100 or (sts.get('total') - sts.get('fetched')) <= 100:
                        bot_entry = await bot_pool.get_next_bot()
                        if bot_entry:
                            await forward(user_id, bot_entry['client'], MSG, progress_msg, sts, protect)
                            sts.add('total_files', len(MSG))
                            
                            # Auto-handling for forward_tag bulk sends
                            active_bots = sum(1 for b in bot_pool.clients if b['active'])
                            dynamic_sleep = base_sleep / active_bots if active_bots > 0 else base_sleep
                            await asyncio.sleep(dynamic_sleep)
                            
                        MSG = []
                else:
                    message_queue.append({
                        "msg_id": message.id, "from_chat": sts.get("FROM"),
                        "caption": custom_caption(message, caption), 'button': button, "protect": protect
                    })
                    if len(message_queue) >= queue_size:
                        # Passing control to the auto-handling queue processor
                        await process_queue_multi(bot_pool, user_id, message_queue, progress_msg, sts)
                        message_queue = []
                    sts.add('total_files')

            if MSG and forward_tag:
                bot_entry = await bot_pool.get_next_bot()
                if bot_entry:
                    await forward(user_id, bot_entry['client'], MSG, progress_msg, sts, protect)
                    sts.add('total_files', len(MSG))

            if message_queue and not forward_tag:
                await process_queue_multi(bot_pool, user_id, message_queue, progress_msg, sts)

        except Exception as e:
            await msg_edit(progress_msg, f'<b>ERROR:</b>\n<code>{e}</code>', wait=True)
        finally:
            if i.TO in temp.IS_FRWD_CHAT: temp.IS_FRWD_CHAT.remove(i.TO)
            if user_have_db:
                await user_db.drop_all()
                await user_db.close()
            if not temp.CANCEL.get(user_id):
                await send_multi(bot_pool, user_id, "<b>🎉 ғᴏʀᴡᴀᴅɪɴɢ ᴄᴏᴍᴘʟᴇᴛᴇᴅ (Bots)</b>")
                await edit(user_id, progress_msg, 'ᴄᴏᴍᴘʟᴇᴛᴇᴅ', "completed", sts) 
            await bot_pool.stop_all()
            await db.rmve_frwd(user_id)
            temp.forwardings -= 1
            temp.lock[user_id] = False

# ==========================================
# 3. ENGINE B: SINGLE-CLIENT USERBOT (V1)
# ==========================================
async def run_single_client_task(bot, user_id, forward_id, progress_msg, userbot_info, offset_skip=None):
    """Executes task using Userbot only, performing actions directly in loop like V1"""
    sts = STS(forward_id)
    i = sts.get(full=True)
    
    _bot_data, caption, forward_tag, datas, protect, button = await sts.get_data(user_id)
    filter_dict, max_size, min_size = datas['filters'], datas['max_size'], datas['min_size']
    keywords = "|".join(datas['keywords']) if datas['keywords'] else None
    extensions = "|".join(datas['extensions']) if datas['extensions'] else None

    client = await get_client(userbot_info['session'], is_bot=False)
    try:
        await client.start()
    except Exception as e:
        return await msg_edit(progress_msg, f"<b>Session Error:</b> {e}", wait=True)

    try:
        k = await client.send_message(i.TO, "Testing")
        await k.delete()
    except Exception:
        await msg_edit(progress_msg, f"**Make sure Userbot is admin in Target Channel**", retry_btn(forward_id), True)
        return await stop(client, user_id)

    user_have_db = False
    dburi = datas['db_uri']
    if dburi is not None:
        connected, user_db = await connect_user_db(user_id, dburi, i.TO)
        if connected: user_have_db = True

    temp.IS_FRWD_CHAT.append(i.TO)
    temp.lock[user_id] = locked = True
    dup_files = []

    if user_have_db and datas['skip_duplicate']:
        old_files = await user_db.get_all_files()
        async for ofile in old_files: dup_files.append(ofile["file_id"])

    sleep_delay = 2 # Standard safety delay for Userbots
    if locked:
        try:
            MSG = []
            pling = 0
            current_offset = offset_skip if offset_skip is not None else sts.get("skip")
            await edit(user_id, progress_msg, 'ᴘʀᴏɢʀᴇssɪɴɢ', 5, sts)

            async for message in iter_messages(client, chat_id=sts.get("FROM"), limit=sts.get("limit"), offset=current_offset, filters=filter_dict, max_size=max_size):
                if temp.CANCEL.get(user_id):
                    if user_have_db: await user_db.close()
                    return

                if pling % 20 == 0: await edit(user_id, progress_msg, 'ᴘʀᴏɢʀᴇssɪɴɢ', 5, sts)
                pling += 1
                sts.add('fetched')

                if message == "DUPLICATE" or message == "FILTERED":
                    sts.add(message.lower())
                    continue
                elif getattr(message, 'empty', False) or getattr(message, 'service', False):
                    sts.add('deleted')
                    continue
                elif message.document and await extension_filter(extensions, message.document.file_name):
                    sts.add('filtered')
                    continue 
                elif message.document and await keyword_filter(keywords, message.document.file_name):
                    sts.add('filtered')
                    continue 
                elif message.document and await size_filter(max_size, min_size, message.document.file_size):
                    sts.add('filtered')
                    continue 
                elif message.document and message.document.file_id in dup_files:
                    sts.add('duplicate')
                    continue

                if message.document and datas['skip_duplicate']:
                    dup_files.append(message.document.file_id)
                    if user_have_db: await user_db.add_file(message.document.file_id)

                if forward_tag:
                    MSG.append(message.id)
                    if len(MSG) >= 100 or (sts.get('total') - sts.get('fetched')) <= 100:
                        await forward(user_id, client, MSG, progress_msg, sts, protect)
                        sts.add('total_files', len(MSG))
                        await asyncio.sleep(10)
                        MSG = []
                else:
                    details = {
                        "msg_id": message.id, "media": media(message),
                        "caption": custom_caption(message, caption), 'button': button, "protect": protect
                    }
                    await copy(user_id, client, details, progress_msg, sts)
                    sts.add('total_files')
                    await asyncio.sleep(sleep_delay) 

        except Exception as e:
            await msg_edit(progress_msg, f'<b>ERROR:</b>\n<code>{e}</code>', wait=True)
        finally:
            if i.TO in temp.IS_FRWD_CHAT: temp.IS_FRWD_CHAT.remove(i.TO)
            if user_have_db:
                await user_db.drop_all()
                await user_db.close()
            if not temp.CANCEL.get(user_id):
                await send(client, user_id, "<b>🎉 ғᴏʀᴡᴀᴅɪɴɢ ᴄᴏᴍᴘʟᴇᴛᴇᴅ (Userbot)</b>")
                await edit(user_id, progress_msg, 'ᴄᴏᴍᴘʟᴇᴛᴇᴅ', "completed", sts) 
            await stop(client, user_id)

# ==========================================
# 4. SMART ROUTER & CALLBACKS
# ==========================================
async def start_task_router(bot, user_id, forward_id, progress_msg, offset_skip=None, engine_choice="auto"):
    sts = STS(forward_id)
    if not sts.verify(): return
    temp.CANCEL[user_id] = False

    bots = await db.get_all_bots(user_id)
    userbot = await db.get_userbot(user_id)
    valid_bots = [b for b in bots if b.get('is_bot', True)]

    if not valid_bots and not userbot:
        return await msg_edit(progress_msg, "<code>You need to add a bot or userbot via /settings!</code>", wait=True)

    if engine_choice == "bots":
        if not valid_bots:
            return await msg_edit(progress_msg, "<code>No bots found. Please add a bot via /settings!</code>", wait=True)
        engine_to_use = "ROUND_ROBIN"
    elif engine_choice == "userbot":
        if not userbot:
            return await msg_edit(progress_msg, "<code>No userbot found. Please add a userbot via /settings!</code>", wait=True)
        engine_to_use = "SINGLE_USERBOT"
    else:
        # auto: prefer bots, fall back to userbot
        engine_to_use = "ROUND_ROBIN" if valid_bots else "SINGLE_USERBOT"

    if engine_to_use == "ROUND_ROBIN":
        await msg_edit(progress_msg, f"<code>Starting Multi-Bot Engine ({len(valid_bots)} bots)...</code>")
        await run_round_robin_task(bot, user_id, forward_id, progress_msg, valid_bots, offset_skip)
    elif engine_to_use == "SINGLE_USERBOT":
        await msg_edit(progress_msg, "<code>Starting Userbot Engine...</code>")
        await run_single_client_task(bot, user_id, forward_id, progress_msg, userbot, offset_skip)

@Client.on_callback_query(filters.regex(r'^start_public'))
async def pub_(bot, message):
    user_id = message.from_user.id

    # parse callback: start_public_{forward_id}_{engine}
    # forward_id contains a dash: "userid-msgid"
    after_prefix = message.data[len("start_public_"):]
    if "_" in after_prefix:
        frwd_id, engine_choice = after_prefix.rsplit("_", 1)
        if engine_choice not in ("bots", "userbot", "auto"):
            frwd_id = after_prefix
            engine_choice = "auto"
    else:
        frwd_id = after_prefix
        engine_choice = "auto"

    if temp.lock.get(user_id) and str(temp.lock.get(user_id)) == "True":
        return await message.answer("Please wait until previous task completes", show_alert=True)

    sts = STS(frwd_id)
    if not sts.verify():
        await message.answer("You are clicking on an old button", show_alert=True)
        return await message.message.delete()

    if sts.get("TO") in temp.IS_FRWD_CHAT:
        return await message.answer("Target chat is busy. Please wait.", show_alert=True)

    m = await msg_edit(message.message, "<code>Analyzing channels...</code>")
    temp.forwardings += 1
    await db.add_frwd(user_id)
    sts.add(time=True)

    await start_task_router(bot, user_id, frwd_id, m, engine_choice=engine_choice)

async def restart_pending_forwads(bot, user):
    user_id = int(user.get('user_id', user.get('_id', user.get('id')))) if isinstance(user, dict) else int(user)
    settings = await db.get_forward_details(user_id)
    if not settings: return

    try:
        await asyncio.sleep(random.randint(5, 15)) 
        skiping = settings['offset']
        fetch = settings['fetched'] - settings['skip']
        forward_id = await store_vars(user_id)
        sts = STS(forward_id)

        if settings['chat_id'] is None or not sts.verify():
            return await db.rmve_frwd(user_id)

        temp.forwardings += 1
        sts.add('fetched', value=fetch)
        sts.add('duplicate', value=settings.get('duplicate', 0))
        sts.add('filtered', value=settings.get('filtered', 0))
        sts.add('deleted', value=settings.get('deleted', 0))
        sts.add('total_files', value=settings.get('total', 0))
        sts.add(time=True, start_time=settings.get('start_time'))

        try:
            m = await bot.get_messages(user_id, settings['msg_id'])
            if getattr(m, 'empty', True): raise Exception()
        except Exception:
            m = await bot.send_message(user_id, "<code>🔄 Analyzing channels to resume task...</code>")
            settings['msg_id'] = m.id
            await db.update_forward(user_id, settings)

        await start_task_router(bot, user_id, forward_id, m, offset_skip=skiping)
    except Exception as e:
        logger.error(f"Failed to resume task for {user_id}: {e}")

async def restart_forwards(client):
    users = await db.get_all_frwd()
    tasks = []
    async for user in users:
        tasks.append(restart_pending_forwads(client, user))
    if tasks: await asyncio.gather(*tasks)

# ==========================================
# BATCH FORWARD HELPERS (AUTO-HANDLING)
# ==========================================
async def copy_single(bot, user, msg, m, sts, to_chat=None):
   """Copy a single message using a specific bot client, with optional to_chat override."""
   target = to_chat if to_chat is not None else sts.get('TO')
   try:
      if msg.get("media") and msg.get("caption"):
         await bot.send_cached_media(chat_id=target, file_id=msg.get("media"), caption=msg.get("caption"), reply_markup=msg.get('button'), protect_content=msg.get("protect"))
      else:
         await bot.copy_message(chat_id=target, from_chat_id=sts.get('FROM'), caption=msg.get("caption"), message_id=msg.get("msg_id"), reply_markup=msg.get('button'), protect_content=msg.get("protect"))
   except FloodWait as e:
      await asyncio.sleep(e.value)
      await copy_single(bot, user, msg, m, sts, to_chat=target)
   except Exception as e:
      raise

async def process_queue_multi(bot_pool, user, message_queue, m, sts):
    """Strict alternating round-robin for ANY number of bots. Automatically caps at 20 msgs/min per bot."""
    msg_idx = 0
    total_msgs = len(message_queue)
    to_chat = sts.get('TO')

    while msg_idx < total_msgs:
        # 1. Grab the very next bot in line
        bot_entry = await bot_pool.get_next_bot()
        
        # If all bots are blocked/inactive, break out
        if not bot_entry:
            break

        msg_details = message_queue[msg_idx]
        
        try:
            await copy_single(bot_entry['client'], user, msg_details, m, sts, to_chat=to_chat)
        except FloodWait as e:
            logger.warning(f"FloodWait on {bot_entry['info']['username']}: {e.value}s")
            await asyncio.sleep(e.value)
            # Retry once after sleeping
            try:
                await copy_single(bot_entry['client'], user, msg_details, m, sts, to_chat=to_chat)
            except FloodWait:
                logger.error(f"Bot {bot_entry['info']['username']} FloodWait again, skipping...")
                await bot_pool.mark_inactive(bot_entry['info'])
                sts.add('deleted')
                msg_idx += 1
                continue
        except Exception as e:
            logger.error(f"Copy error on {bot_entry['info']['username']}: {e}")
            sts.add('deleted')

        msg_idx += 1
        
        # 2. AUTO HANDLING MATH FOR ANY BOT COUNT
        # Counts exactly how many bots are alive right now (2, 5, 80, etc.)
        active_bots = sum(1 for b in bot_pool.clients if b['active'])
        
        # base_sleep / active_bots maintains rate limit per bot
        dynamic_sleep = 3.0 / active_bots if active_bots > 0 else 3.0
            
        await asyncio.sleep(dynamic_sleep)

# ==========================================
# STANDARD ACTIONS & UI
# ==========================================
async def copy(user, bot, msg, m, sts):
   try:                               
     if msg.get("media") and msg.get("caption"):
        await bot.send_cached_media(chat_id=sts.get('TO'), file_id=msg.get("media"), caption=msg.get("caption"), reply_markup=msg.get('button'), protect_content=msg.get("protect"))
     else:
        await bot.copy_message(chat_id=sts.get('TO'), from_chat_id=sts.get('FROM'), caption=msg.get("caption"), message_id=msg.get("msg_id"), reply_markup=msg.get('button'), protect_content=msg.get("protect"))
   except FloodWait as e:
     await edit(user, m, 'ᴘʀᴏɢʀᴇssɪɴɢ', e.value, sts)
     await asyncio.sleep(e.value)
     await edit(user, m, 'ᴘʀᴏɢʀᴇssɪɴɢ', 5, sts)
     await copy(user, bot, msg, m, sts)
   except Exception: sts.add('deleted')

async def forward(user, bot, msg, m, sts, protect):
   try: await bot.forward_messages(chat_id=sts.get('TO'), from_chat_id=sts.get('FROM'), protect_content=protect, message_ids=msg)
   except FloodWait as e:
     await edit(user, m, 'ᴘʀᴏɢʀᴇssɪɴɢ', e.value, sts)
     await asyncio.sleep(e.value)
     await edit(user, m, 'ᴘʀᴏɢʀᴇssɪɴɢ', 5, sts)
     await forward(user, bot, msg, m, sts, protect)

async def msg_edit(msg, text, button=None, wait=None):
    try: return await msg.edit(text, reply_markup=button)
    except MessageNotModified: pass 
    except FloodWait as e:
        if wait:
           await asyncio.sleep(e.value)
           return await msg_edit(msg, text, button, wait)

async def edit(user, msg, title, status, sts):
   i = sts.get(full=True)
   status = 'Forwarding' if status == 5 else f"sleeping {status} s" if str(status).isnumeric() else status
   percentage = "{:.0f}".format(float(i.fetched)*100/float(i.total)) if i.total > 0 else "0"
   text = TEXT.format(i.fetched, i.total_files, i.duplicate, i.deleted, i.skip, i.filtered, status, percentage, title)
   
   await update_forward(user_id=user, last_id=None, start_time=i.start, limit=i.limit, chat_id=i.FROM, toid=i.TO, forward_id=None, msg_id=msg.id, fetched=i.fetched, deleted=i.deleted, total=i.total_files, duplicate=i.duplicate, skip=i.skip, filterd=i.filtered)
   
   now = time.time()
   diff = int(now - i.start)
   speed = sts.divide(i.fetched, diff) if diff > 0 else 0
   elapsed_time = round(diff) * 1000
   time_to_completion = round(sts.divide(i.total - i.fetched, int(speed))) * 1000 if speed > 0 else 0
   estimated_total_time = elapsed_time + time_to_completion  
   
   progress = "●{0}{1}".format(''.join(["●" for i in range(math.floor(int(percentage) / 4))]), ''.join(["○" for i in range(24 - math.floor(int(percentage) / 4))]))
   button =  [[InlineKeyboardButton(progress, f'fwrdstatus#{status}#{estimated_total_time}#{percentage}#{i.id}')]]
   estimated_total_time = TimeFormatter(milliseconds=estimated_total_time)
   estimated_total_time = estimated_total_time if estimated_total_time != '' else '0 s'
   
   if status in ["cancelled", "completed"]: button.append([InlineKeyboardButton('• ᴄᴏᴍᴘʟᴇᴛᴇᴅ ​•', url='https://t.me/VJ_BOTZ')])
   else: button.append([InlineKeyboardButton('• ᴄᴀɴᴄᴇʟ', 'terminate_frwd')])
   await msg_edit(msg, text, InlineKeyboardMarkup(button))

async def send_multi(bot_pool, user, text):
   for bot_entry in bot_pool.clients:
       try:
          await bot_entry['client'].send_message(user, text=text)
          return
       except: pass 

async def is_cancelled(client, user, msg, sts):
   if temp.CANCEL.get(user)==True:
      i = sts.get(full=True)
      if i.TO in temp.IS_FRWD_CHAT: temp.IS_FRWD_CHAT.remove(i.TO)
      await edit(user, msg, 'ᴄᴀɴᴄᴇʟʟᴇᴅ', "cancelled", sts)
      if isinstance(client, Client): await send(client, user, "<b>❌ ғᴏʀᴡᴀᴅɪɴɢ ᴄᴀɴᴄᴇʟʟᴇᴅ</b>")
      await stop(client, user)
      return True 
   return False 

async def stop(client, user):
   try: await client.stop()
   except: pass 
   await db.rmve_frwd(user)
   temp.forwardings -= 1
   temp.lock[user] = False 

async def send(bot, user, text):
   try: await bot.send_message(user, text=text)
   except: pass 

def custom_caption(msg, caption):
  if msg.media:
    if (msg.video or msg.document or msg.audio or msg.photo):
      media = getattr(msg, msg.media.value, None)
      if media:
        file_name = getattr(media, 'file_name', '')
        file_size = getattr(media, 'file_size', '')
        fcaption = getattr(msg, 'caption', '')
        if fcaption: fcaption = fcaption.html
        if caption: return caption.format(filename=file_name, size=get_size(file_size), caption=fcaption)
        return fcaption
  return None

def get_size(size):
  units = ["Bytes", "KB", "MB", "GB", "TB", "PB", "EB"]
  size = float(size)
  i = 0
  while size >= 1024.0 and i < len(units):
     i += 1
     size /= 1024.0
  return "%.2f %s" % (size, units[i]) 

async def keyword_filter(keywords, file_name):
    if keywords is None: return False
    if re.search(keywords, file_name): return False
    return True

async def extension_filter(extensions, file_name):
    if extensions is None: return False
    if not re.search(extensions, file_name): return False
    return True

async def size_filter(max_size, min_size, file_size):
    file_size = file_size / 1024 / 1024
    if max_size and min_size == 0: return False
    if max_size == 0: return file_size < min_size
    if min_size == 0: return file_size > max_size
    if not min_size <= file_size <= max_size: return True
    return False

def media(msg):
  if msg.media:
     media_obj = getattr(msg, msg.media.value, None)
     if media_obj: return getattr(media_obj, 'file_id', None)
  return None 

def TimeFormatter(milliseconds: int) -> str:
    seconds, milliseconds = divmod(int(milliseconds), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    tmp = ((str(days) + "d, ") if days else "") + ((str(hours) + "h, ") if hours else "") + ((str(minutes) + "m, ") if minutes else "") + ((str(seconds) + "s, ") if seconds else "") + ((str(milliseconds) + "ms, ") if milliseconds else "")
    return tmp[:-2] if len(tmp) > 2 else "0s"

def retry_btn(id): return InlineKeyboardMarkup([[InlineKeyboardButton('♻️ RETRY ♻️', f"start_public_{id}")]])

@Client.on_callback_query(filters.regex(r'^terminate_frwd$'))
async def terminate_frwding(bot, m):
    temp.lock[m.from_user.id] = False
    temp.CANCEL[m.from_user.id] = True 
    await m.answer("Forwarding cancelled !", show_alert=True)

@Client.on_callback_query(filters.regex(r'^fwrdstatus'))
async def status_msg(bot, msg):
    _, status, est_time, percentage, frwd_id = msg.data.split("#")
    sts = STS(frwd_id)
    if not sts.verify(): fetched, forwarded, remaining = 0, 0, 0
    else:
       fetched, limit, forwarded = sts.get('fetched'), sts.get('limit'), sts.get('total_files')
       remaining = limit - fetched 
    est_time = TimeFormatter(milliseconds=est_time)
    start_time = sts.get('start')
    uptime = await get_bot_uptime(start_time)
    total = sts.get('limit') - sts.get('fetched')
    time_to_comple = await complete_time(total)
    est_time = est_time if (est_time != '' or status not in ['completed', 'cancelled']) else '0 s'
    return await msg.answer(PROGRESS.format(percentage, fetched, forwarded, remaining, status, time_to_comple, uptime), show_alert=True)

@Client.on_callback_query(filters.regex(r'^close_btn$'))
async def close(bot, update):
    await update.answer()
    await update.message.delete()

@Client.on_message(filters.private & filters.command(['stop']))
async def stop_forward(client, message):
    user_id = message.from_user.id
    sts = await message.reply('<code>Stoping...</code>')
    await asyncio.sleep(0.5)
    if not await db.is_forwad_exit(message.from_user.id): return await sts.edit('**No Ongoing Forwards To Cancel**')
    temp.lock[user_id] = False
    temp.CANCEL[user_id] = True
    await sts.edit(f"<b>Successfully Canceled </b>", disable_web_page_preview=True)

async def store_vars(user_id):
    settings = await db.get_forward_details(user_id)
    fetch = settings['fetched']
    forward_id = f'{user_id}-{fetch}'
    STS(id=forward_id).store(settings['chat_id'], settings['toid'], settings['skip'], settings['limit'])
    return forward_id

async def update_forward(user_id, chat_id, start_time, toid, last_id, limit, forward_id, msg_id, fetched, total, duplicate, deleted, skip, filterd):
    details = {
        'chat_id': chat_id, 'toid': toid, 'forward_id': forward_id, 'last_id': last_id,
        'limit': limit, 'msg_id': msg_id, 'start_time': start_time, 'fetched': fetched,
        'offset': fetched, 'deleted': deleted, 'total': total, 'duplicate': duplicate,
        'skip': skip, 'filtered':filterd
    }
    await db.update_forward(user_id, details)

async def get_bot_uptime(start_time):
    uptime_seconds = int(time.time() - start_time)
    uptime_minutes = uptime_seconds // 60
    uptime_hours = uptime_minutes // 60
    uptime_days = uptime_hours // 24
    uptime_weeks = uptime_days // 7
    uptime_string = ""
    if uptime_weeks != 0: uptime_string += f"{uptime_weeks % 7}w, "
    if uptime_days != 0: uptime_string += f"{uptime_days % 24}d, "
    if uptime_hours != 0: uptime_string += f"{uptime_hours % 24}h, "
    if uptime_minutes != 0: uptime_string += f"{uptime_minutes % 60}m, "
    uptime_string += f"{uptime_seconds % 60}s"
    return uptime_string  

async def complete_time(total_files, files_per_minute=30):
    minutes_required = total_files / files_per_minute
    seconds_required = minutes_required * 60
    weeks = seconds_required // (7 * 24 * 60 * 60)
    days = (seconds_required % (7 * 24 * 60 * 60)) // (24 * 60 * 60)
    hours = (seconds_required % (24 * 60 * 60)) // (60 * 60)
    minutes = (seconds_required % (60 * 60)) // 60
    seconds = seconds_required % 60
    time_format = ""
    if weeks > 0: time_format += f"{int(weeks)}w, "
    if days > 0: time_format += f"{int(days)}d, "
    if hours > 0: time_format += f"{int(hours)}h, "
    if minutes > 0: time_format += f"{int(minutes)}m, "
    if seconds > 0: time_format += f"{int(seconds)}s"
    return time_format