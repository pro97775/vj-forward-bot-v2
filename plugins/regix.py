# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

import asyncio
import logging
import math
import re
import time

from .utils import STS, Robin
from database import db
from .test import get_client, iter_messages
from config import temp
from script import Script
from pyrogram import Client, filters
from pyrogram.errors import FloodWait, MessageNotModified
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
TEXT = Script.TEXT
PROGRESS = Script.PROGRESS

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

async def msg_edit(msg, text, button=None, wait=None):
    """Edit a message, ignoring the errors which don't matter here."""
    try:
        return await msg.edit(text, reply_markup=button)
    except MessageNotModified:
        return msg
    except FloodWait as e:
        if wait:
            await asyncio.sleep(e.value)
            return await msg_edit(msg, text, button, wait)
        return msg
    except Exception as e:
        logger.warning(f"msg_edit: {e}")
        return msg

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

async def send(bot, user, text):
    try:
        await bot.send_message(user, text=text)
    except Exception:
        pass

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

async def stop_clients(workers):
    """Stop every started client of a task."""
    for worker in workers or []:
        try:
            await worker['client'].stop()
        except Exception:
            pass

async def finish(user, workers=None, chat=None, counted=True):
    """Clean up a task (clients, locks, db entry)."""
    await stop_clients(workers)
    try:
        await db.rmve_frwd(user)
    except Exception as e:
        logger.warning(f"rmve_frwd: {e}")
    if chat is not None and chat in temp.IS_FRWD_CHAT:
        temp.IS_FRWD_CHAT.remove(chat)
    if counted:
        temp.forwardings = max(0, temp.forwardings - 1)
    temp.lock[user] = False
    temp.WORKERS.pop(user, None)

# kept for backward compatibility with older callers
async def stop(client, user):
    await finish(user, [{'client': client}] if client else None)

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

async def check_client(client, source, last_id, target):
    """Check whether a client can read the source and post in the target."""
    can_read = can_send = False
    try:
        await client.get_messages(source, last_id)
        can_read = True
    except FloodWait as e:
        await asyncio.sleep(min(e.value, 10))
        try:
            await client.get_messages(source, last_id)
            can_read = True
        except Exception:
            pass
    except Exception:
        pass
    try:
        k = await client.send_message(target, "Testing")
        await k.delete()
        can_send = True
    except FloodWait as e:
        await asyncio.sleep(min(e.value, 10))
        try:
            k = await client.send_message(target, "Testing")
            await k.delete()
            can_send = True
        except Exception:
            pass
    except Exception:
        pass
    return can_read, can_send

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

async def setup_workers(user, data, source, last_id, target, sts):
    """Start every client used by a task.

    Bots are preferred (round robin). When no bot can be used the userbot
    is used alone. Returns (workers, robin, errors).
    """
    workers, errors = [], []
    for bot in data['bots']:
        client = await get_client(bot['token'], is_bot=True, name=f"bot{bot['id']}")
        try:
            await client.start()
        except Exception as e:
            errors.append(f"@{bot.get('username')} - <code>{e}</code>")
            continue
        can_read, can_send = await check_client(client, source, last_id, target)
        if not can_send:
            errors.append(f"@{bot.get('username')} - not admin in target chat")
        elif not can_read:
            errors.append(f"@{bot.get('username')} - can't read source chat")
        if can_read and can_send:
            workers.append({'client': client, 'name': bot['name'],
                            'username': bot.get('username'), 'is_bot': True})
            continue
        try:
            await client.stop()
        except Exception:
            pass
    if workers:
        robin = Robin(workers, rate=data['bot_rate'], delay=data['bot_delay'])
        sts.set('bots', len(workers))
        return workers, robin, errors
    userbot = data['userbot']
    if userbot:
        client = await get_client(userbot['session'], is_bot=False, name=f"user{userbot['id']}")
        try:
            await client.start()
        except Exception as e:
            errors.append(f"userbot - <code>{e}</code>")
            return [], None, errors
        can_read, can_send = await check_client(client, source, last_id, target)
        if can_read and can_send:
            workers.append({'client': client, 'name': userbot['name'],
                            'username': userbot.get('username'), 'is_bot': False})
            # userbots have no per minute limit, only the delay
            robin = Robin(workers, rate=None, delay=data['userbot_delay'])
            sts.set('bots', 1)
            return workers, robin, errors
        errors.append("userbot - " + ("not admin in target chat" if not can_send else "can't read source chat"))
        try:
            await client.stop()
        except Exception:
            pass
    return [], None, errors

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

async def acquire(robin, cost, user, m, sts):
    """Wait until a worker is allowed to send `cost` messages."""
    while True:
        worker, wait = robin.pick(cost)
        if worker:
            return worker
        if temp.CANCEL.get(user) == True:
            return None
        # every bot reached its per minute limit, show the countdown
        await edit(user, m, 'ᴡᴀɪᴛɪɴɢ', wait, sts)
        await asyncio.sleep(max(1, min(int(wait), 30)))

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

async def dump_messages(main_bot, clients, dump_chat, source, msg_ids):
    """Clone forwarded messages into the owner dump chat.

    The main bot is tried first (it is the one which is admin in the dump
    chat), then every worker of the task. Failures are ignored so a missing
    permission never stops the forwarding.
    """
    if not dump_chat or not msg_ids:
        return 0
    order = ([main_bot] if main_bot else []) + list(clients)
    for client in order:
        try:
            await client.forward_messages(chat_id=dump_chat, from_chat_id=source,
                                          message_ids=msg_ids)
            return len(msg_ids)
        except FloodWait as e:
            await asyncio.sleep(min(e.value, 30))
        except Exception:
            continue
    # forwarding failed (protected source), try a plain copy
    for client in order:
        try:
            for msg_id in msg_ids:
                await client.copy_message(chat_id=dump_chat, from_chat_id=source,
                                          message_id=msg_id)
            return len(msg_ids)
        except FloodWait as e:
            await asyncio.sleep(min(e.value, 30))
        except Exception:
            continue
    return 0

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

async def copy_message(worker, msg, sts, user, m):
    """Copy a single message to the target chat.

    `copy_message` is used (not `send_cached_media`) because a file_id read
    by one client can not be reused by another client of the round robin.
    """
    try:
        await worker['client'].copy_message(
            chat_id=sts.get('TO'),
            from_chat_id=sts.get('FROM'),
            caption=msg.get("caption"),
            message_id=msg.get("msg_id"),
            reply_markup=msg.get('button'),
            protect_content=msg.get("protect"))
        return True
    except FloodWait as e:
        await edit(user, m, 'ᴘʀᴏɢʀᴇssɪɴɢ', e.value, sts)
        await asyncio.sleep(e.value)
        return await copy_message(worker, msg, sts, user, m)
    except Exception as e:
        logger.warning(f"copy: {e}")
        sts.add('deleted')
        return False

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

async def forward_batch(worker, msg_ids, sts, user, m, protect):
    """Forward a batch of messages (forward tag on) to the target chat."""
    try:
        await worker['client'].forward_messages(
            chat_id=sts.get('TO'),
            from_chat_id=sts.get('FROM'),
            protect_content=protect,
            message_ids=msg_ids)
        return True
    except FloodWait as e:
        await edit(user, m, 'ᴘʀᴏɢʀᴇssɪɴɢ', e.value, sts)
        await asyncio.sleep(e.value)
        return await forward_batch(worker, msg_ids, sts, user, m, protect)
    except Exception as e:
        logger.warning(f"forward: {e}")
        sts.add('deleted', value=len(msg_ids))
        return False

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

async def edit(user, msg, title, status, sts):
    """Refresh the status message of a task."""
    i = sts.get(full=True)
    if status == 5:
        status = 'Forwarding'
    elif str(status).isnumeric():
        status = f"sleeping {status} s"
    total = float(i.total) if i.total else 1.0
    percentage = "{:.0f}".format(float(i.fetched) * 100 / total)
    text = TEXT.format(i.fetched, i.total_files, i.dumped, i.deleted, i.skip,
                       i.filtered, i.bots, status, percentage, title)
    await update_forward(user_id=user, last_id=None, start_time=i.start, limit=i.limit,
                        chat_id=i.FROM, toid=i.TO, forward_id=None, msg_id=msg.id,
                        fetched=i.fetched, deleted=i.deleted, total=i.total_files,
                        skip=i.skip, filterd=i.filtered, dumped=i.dumped)
    now = time.time()
    diff = int(now - i.start) or 1
    speed = sts.divide(i.fetched, diff)
    elapsed_time = round(diff) * 1000
    time_to_completion = round(sts.divide(i.total - i.fetched, int(speed))) * 1000
    estimated_total_time = elapsed_time + time_to_completion
    done = max(0, min(24, math.floor(int(percentage) / 4)))
    progress = "●{0}{1}".format("●" * done, "○" * (24 - done))
    sts.set('status', status)
    sts.set('eta', TimeFormatter(estimated_total_time) or '0 s')
    sts.set('percentage', percentage)
    # keep the callback data short (telegram allows only 64 bytes)
    button = [[InlineKeyboardButton(progress, f'fwrdstatus#{i.id}')]]
    if title in ["ᴄᴀɴᴄᴇʟʟᴇᴅ", "ᴄᴏᴍᴘʟᴇᴛᴇᴅ"] or status in ["cancelled", "completed"]:
        button.append([InlineKeyboardButton('• ᴄᴏᴍᴘʟᴇᴛᴇᴅ •', url='https://t.me/VJ_BOTZ')])
    else:
        button.append([InlineKeyboardButton('• ᴄᴀɴᴄᴇʟ', 'terminate_frwd')])
    await msg_edit(msg, text, InlineKeyboardMarkup(button))

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

async def is_cancelled(bot, user, msg, sts, workers):
    """Stop a task when the user pressed cancel."""
    if temp.CANCEL.get(user) == True:
        await edit(user, msg, 'ᴄᴀɴᴄᴇʟʟᴇᴅ', "cancelled", sts)
        await send(bot, user, "<b>❌ ғᴏʀᴡᴀʀᴅɪɴɢ ᴄᴀɴᴄᴇʟʟᴇᴅ</b>")
        await finish(user, workers, sts.get('TO'))
        return True
    return False

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

async def run_forward(bot, user, m, sts, data, offset=None):
    """The forwarding engine.

    Used by both /forward and the auto restart. Messages are distributed
    over every working bot with the round robin scheduler.
    """
    source, target, last_id = sts.get('FROM'), sts.get('TO'), sts.get('limit')
    workers, robin, errors = await setup_workers(user, data, source, last_id, target, sts)
    if not workers:
        text = "<b>No usable bot found for this task.</b>"
        if errors:
            text += "\n\n" + "\n".join(errors[:10])
        text += "\n\n<i>Add a bot / userbot using /settings and make it admin in the target chat.</i>"
        await msg_edit(m, text, retry_btn(sts.id), True)
        await finish(user, None, counted=False)
        return
    if errors:
        await send(bot, user, "<b>Skipped bots:</b>\n" + "\n".join(errors[:10]))
    dump_chat = await db.get_dump_chat()
    temp.WORKERS[user] = robin.names()
    temp.IS_FRWD_CHAT.append(target)
    temp.lock[user] = True
    temp.forwardings += 1
    await db.add_frwd(user)
    await send(bot, user, "<b>Fᴏʀᴡᴀʀᴅɪɴɢ sᴛᴀʀᴛᴇᴅ🔥</b>")
    clients = [w['client'] for w in workers]
    forward_tag = data['forward_tag']
    protect = data['protect']
    caption = data['caption']
    button = data['button']
    batch = min(100, robin.batch) if forward_tag else 1
    MSG = []
    pling = 0
    try:
        await edit(user, m, 'ᴘʀᴏɢʀᴇssɪɴɢ', 5, sts)
        async for message in iter_messages(clients[0], chat_id=source, limit=last_id,
                                           offset=offset if offset is not None else sts.get('skip'),
                                           filters=data['filters']):
            if await is_cancelled(bot, user, m, sts, workers):
                return
            if pling % 20 == 0:
                await edit(user, m, 'ᴘʀᴏɢʀᴇssɪɴɢ', 5, sts)
            pling += 1
            sts.add('fetched')
            if message == "FILTERED":
                sts.add('filtered')
                continue
            if message is None or message.empty or message.service:
                sts.add('deleted')
                continue
            if message.document:
                name = message.document.file_name or ""
                if await extension_filter(data['extensions'], name):
                    sts.add('filtered')
                    continue
                if await keyword_filter(data['keywords'], name):
                    sts.add('filtered')
                    continue
                if await size_filter(data['max_size'], data['min_size'], message.document.file_size):
                    sts.add('filtered')
                    continue
            if forward_tag:
                MSG.append(message.id)
                remaining = sts.get('total') - sts.get('fetched')
                if len(MSG) >= batch or remaining <= 0:
                    worker = await acquire(robin, len(MSG), user, m, sts)
                    if worker is None:
                        await is_cancelled(bot, user, m, sts, workers)
                        return
                    if await forward_batch(worker, MSG, sts, user, m, protect):
                        sts.add('total_files', len(MSG))
                        sts.add('dumped', await dump_messages(bot, clients, dump_chat, source, MSG))
                    MSG = []
                    if robin.delay:
                        await asyncio.sleep(robin.delay)
            else:
                worker = await acquire(robin, 1, user, m, sts)
                if worker is None:
                    await is_cancelled(bot, user, m, sts, workers)
                    return
                details = {"msg_id": message.id,
                           "caption": custom_caption(message, caption),
                           'button': button, "protect": protect}
                if await copy_message(worker, details, sts, user, m):
                    sts.add('total_files')
                    sts.add('dumped', await dump_messages(bot, clients, dump_chat, source,
                                                          [message.id]))
                if robin.delay:
                    await asyncio.sleep(robin.delay)
        if forward_tag and MSG:
            worker = await acquire(robin, len(MSG), user, m, sts)
            if worker and await forward_batch(worker, MSG, sts, user, m, protect):
                sts.add('total_files', len(MSG))
                sts.add('dumped', await dump_messages(bot, clients, dump_chat, source, MSG))
    except Exception as e:
        logger.exception("forwarding failed")
        await msg_edit(m, f'<b>ERROR:</b>\n<code>{e}</code>', wait=True)
        await finish(user, workers, target)
        return
    await send(bot, user, "<b>🎉 ғᴏʀᴡᴀᴅɪɴɢ ᴄᴏᴍᴘʟᴇᴛᴇᴅ</b>")
    await edit(user, m, 'ᴄᴏᴍᴘʟᴇᴛᴇᴅ', "completed", sts)
    await finish(user, workers, target)

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

@Client.on_callback_query(filters.regex(r'^start_public'))
async def pub_(bot, message):
    """Start a forwarding task after the double check message."""
    user = message.from_user.id
    temp.CANCEL[user] = False
    frwd_id = message.data.split("_", 2)[2]
    if temp.lock.get(user) and str(temp.lock.get(user)) == "True":
        return await message.answer("please wait until previous task complete", show_alert=True)
    sts = STS(frwd_id)
    if not sts.verify():
        await message.answer("your are clicking on my old button", show_alert=True)
        return await message.message.delete()
    i = sts.get(full=True)
    if i.TO in temp.IS_FRWD_CHAT:
        return await message.answer("In Target chat a task is progressing. please wait until task complete", show_alert=True)
    m = await msg_edit(message.message, "<code>verifying your data's, please wait.</code>")
    data = await sts.get_data(user)
    if not data['bots'] and not data['userbot']:
        return await msg_edit(m, "<code>You didn't added any bot. Please add a bot using /settings !</code>", wait=True)
    await msg_edit(m, "<code>starting your bots, please wait..</code>")
    await run_forward(bot, user, m, sts, data)

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

@Client.on_callback_query(filters.regex(r'^terminate_frwd$'))
async def terminate_frwding(bot, m):
    user_id = m.from_user.id 
    temp.lock[user_id] = False
    temp.CANCEL[user_id] = True 
    await m.answer("Forwarding cancelled !", show_alert=True)

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

@Client.on_callback_query(filters.regex(r'^fwrdstatus'))
async def status_msg(bot, msg):
    frwd_id = msg.data.split("#")[-1]
    sts = STS(frwd_id)
    if not sts.verify():
        return await msg.answer("this task is not running anymore", show_alert=True)
    fetched = sts.get('fetched') or 0
    limit = sts.get('limit') or 0
    forwarded = sts.get('total_files') or 0
    remaining = max(0, limit - fetched)
    status = sts.get('status') or 'Forwarding'
    percentage = sts.get('percentage') or 0
    eta = sts.get('eta') or '0 s'
    start_time = sts.get('start') or time.time()
    uptime = await get_bot_uptime(start_time)
    return await msg.answer(PROGRESS.format(percentage, fetched, forwarded, remaining,
                                            status, eta, uptime), show_alert=True)

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

@Client.on_callback_query(filters.regex(r'^close_btn$'))
async def close(bot, update):
    await update.answer()
    await update.message.delete()

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

@Client.on_message(filters.private & filters.command(['stop']))
async def stop_forward(client, message):
    user_id = message.from_user.id
    sts = await message.reply('<code>Stoping...</code>')
    await asyncio.sleep(0.5)
    if not await db.is_forwad_exit(user_id):
        return await sts.edit('**No Ongoing Forwards To Cancel**')
    temp.lock[user_id] = False
    temp.CANCEL[user_id] = True
    await sts.edit("<b>Successfully Canceled </b>", disable_web_page_preview=True)

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

async def restart_pending_forwads(bot, user):
    """Continue a task which was interrupted by a bot restart."""
    user = user['user_id']
    try:
        settings = await db.get_forward_details(user)
        if not settings['chat_id'] or not settings['msg_id']:
            return await db.rmve_frwd(user)
        forward_id = f"{user}-{settings['fetched']}"
        sts = STS(forward_id).store(settings['chat_id'], settings['toid'],
                                   settings['skip'], settings['limit'])
        sts.add('fetched', value=max(0, settings['fetched'] - settings['skip']))
        sts.add('filtered', value=settings['filtered'])
        sts.add('deleted', value=settings['deleted'])
        sts.add('dumped', value=settings['dumped'])
        sts.add('total_files', value=settings['total'])
        sts.add(time=True, start_time=settings['start_time'])
        m = await bot.get_messages(user, settings['msg_id'])
        data = await sts.get_data(user)
        if not data['bots'] and not data['userbot']:
            await msg_edit(m, "<code>You didn't added any bot. Please add a bot using /settings !</code>", wait=True)
            return await db.rmve_frwd(user)
        await msg_edit(m, "<code>resuming your task, please wait..</code>")
    except Exception as e:
        logger.warning(f"restart_pending_forwads: {e}")
        return await db.rmve_frwd(user)
    temp.CANCEL[user] = False
    await run_forward(bot, user, m, sts, data, offset=settings['offset'])

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

async def restart_forwards(client):
    """Restart every pending task after the bot started."""
    users = await db.get_all_frwd()
    tasks = []
    async for user in users:
        tasks.append(restart_pending_forwads(client, user))
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
    print('Done')

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

async def update_forward(user_id, chat_id, start_time, toid, last_id, limit, forward_id,
                         msg_id, fetched, total, deleted, skip, filterd, dumped=0):
    details = {
        'chat_id': chat_id,
        'toid': toid,
        'forward_id': forward_id,
        'last_id': last_id,
        'limit': limit,
        'msg_id': msg_id,
        'start_time': start_time,
        'fetched': fetched,
        'offset': fetched,
        'deleted': deleted,
        'total': total,
        'skip': skip,
        'filtered': filterd,
        'dumped': dumped
    }
    await db.update_forward(user_id, details)

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

def retry_btn(id):
    return InlineKeyboardMarkup([[InlineKeyboardButton('♻️ RETRY ♻️', f"start_public_{id}")]])

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

def custom_caption(msg, caption):
    """Build the caption of a copied message."""
    if not msg.media:
        return None
    if not (msg.video or msg.document or msg.audio or msg.photo):
        return None
    media = getattr(msg, msg.media.value, None)
    if not media:
        return None
    file_name = getattr(media, 'file_name', '') or ''
    file_size = getattr(media, 'file_size', 0) or 0
    fcaption = getattr(msg, 'caption', '')
    if fcaption:
        fcaption = fcaption.html
    if caption:
        return caption.format(filename=file_name, size=get_size(file_size), caption=fcaption or '')
    return fcaption or None

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

def media(msg):
    if msg.media:
        media = getattr(msg, msg.media.value, None)
        if media:
            return getattr(media, 'file_id', None)
    return None 

def get_size(size):
    units = ["Bytes", "KB", "MB", "GB", "TB", "PB", "EB"]
    size = float(size)
    i = 0
    while size >= 1024.0 and i < len(units) - 1:
        i += 1
        size /= 1024.0
    return "%.2f %s" % (size, units[i]) 

async def keyword_filter(keywords, file_name):
    """True when the file must be skipped (no keyword matched)."""
    if not keywords:
        return False
    try:
        return not re.search(keywords, file_name, re.IGNORECASE)
    except re.error:
        return False

async def extension_filter(extensions, file_name):
    """True when the file must be skipped (extension blocked)."""
    if not extensions:
        return False
    try:
        return bool(re.search(extensions, file_name, re.IGNORECASE))
    except re.error:
        return False

async def size_filter(max_size, min_size, file_size):
    """True when the file size is out of the configured range."""
    file_size = (file_size or 0) / 1024 / 1024
    if not max_size and not min_size:
        return False
    if not max_size:
        return file_size < min_size
    if not min_size:
        return file_size > max_size
    return not (min_size <= file_size <= max_size)

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

def TimeFormatter(milliseconds: int) -> str:
    seconds, milliseconds = divmod(int(milliseconds), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    tmp = ((str(days) + "d, ") if days else "") + \
        ((str(hours) + "h, ") if hours else "") + \
        ((str(minutes) + "m, ") if minutes else "") + \
        ((str(seconds) + "s, ") if seconds else "") + \
        ((str(milliseconds) + "ms, ") if milliseconds else "")
    return tmp[:-2]

async def get_bot_uptime(start_time):
    """Human readable time passed since `start_time`."""
    uptime_seconds = int(time.time() - (start_time or time.time()))
    uptime_minutes = uptime_seconds // 60
    uptime_hours = uptime_minutes // 60
    uptime_days = uptime_hours // 24
    uptime_weeks = uptime_days // 7
    uptime_string = ""
    if uptime_weeks != 0:
        uptime_string += f"{uptime_weeks % 7}w, "
    if uptime_days != 0:
        uptime_string += f"{uptime_days % 24}d, "
    if uptime_hours != 0:
        uptime_string += f"{uptime_hours % 24}h, "
    if uptime_minutes != 0:
        uptime_string += f"{uptime_minutes % 60}m, "
    uptime_string += f"{uptime_seconds % 60}s"
    return uptime_string  

async def complete_time(total_files, files_per_minute=30):
    """Rough eta for the remaining files."""
    files_per_minute = files_per_minute or 30
    seconds_required = (total_files / files_per_minute) * 60
    weeks = seconds_required // (7 * 24 * 60 * 60)
    days = (seconds_required % (7 * 24 * 60 * 60)) // (24 * 60 * 60)
    hours = (seconds_required % (24 * 60 * 60)) // (60 * 60)
    minutes = (seconds_required % (60 * 60)) // 60
    seconds = seconds_required % 60
    time_format = ""
    if weeks > 0:
        time_format += f"{int(weeks)}w, "
    if days > 0:
        time_format += f"{int(days)}d, "
    if hours > 0:
        time_format += f"{int(hours)}h, "
    if minutes > 0:
        time_format += f"{int(minutes)}m, "
    if seconds > 0:
        time_format += f"{int(seconds)}s"
    return time_format

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

# Ask Doubt on telegram @KingVJ01

# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01


# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01
