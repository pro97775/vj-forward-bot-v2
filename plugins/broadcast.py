# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

import asyncio
import datetime
import time
import logging
from pyrogram.errors import (
    InputUserDeactivated,
    FloodWait,
    UserIsBlocked,
    PeerIdInvalid,
)
from database import db
from pyrogram import Client, filters
from config import Config

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


async def broadcast_messages(user_id, message):
    try:
        await message.copy(chat_id=user_id)
        return True, "Success"
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await broadcast_messages(user_id, message)
    except InputUserDeactivated:
        await db.delete_user(int(user_id))
        logger.info(f"{user_id} - Removed from Database (deleted account).")
        return False, "Deleted"
    except UserIsBlocked:
        logger.info(f"{user_id} - Blocked the bot.")
        return False, "Blocked"
    except PeerIdInvalid:
        await db.delete_user(int(user_id))
        logger.info(f"{user_id} - PeerIdInvalid")
        return False, "Error"
    except Exception:
        return False, "Error"


@Client.on_message(filters.command("broadcast") & filters.user(Config.BOT_OWNER) & filters.reply)
async def verupikkals(bot, message):
    users = await db.get_all_users()
    b_msg = message.reply_to_message
    sts = await message.reply_text(text="<blockquote><b>📡 Broadcasting your message...</b></blockquote>")
    start_time = time.time()
    total_users = await db.total_users_count()
    done = blocked = deleted = failed = success = 0

    async for user in users:
        if "id" in user:
            pti, sh = await broadcast_messages(int(user["id"]), b_msg)
            if pti:
                success += 1
            else:
                if sh == "Blocked":
                    blocked += 1
                elif sh == "Deleted":
                    deleted += 1
                else:
                    failed += 1
        else:
            failed += 1

        done += 1
        if done % 20 == 0:
            try:
                await sts.edit(
                    "<blockquote><b>📡 BROADCAST IN PROGRESS</b></blockquote>\n\n"
                    "<blockquote>"
                    f"┌ <b>👥 Total Users:</b> <code>{total_users}</code>\n"
                    f"├ <b>🔄 Completed:</b> <code>{done} / {total_users}</code>\n"
                    f"├ <b>✅ Success:</b> <code>{success}</code>\n"
                    f"├ <b>🚫 Blocked:</b> <code>{blocked}</code>\n"
                    f"└ <b>🗑 Deleted:</b> <code>{deleted}</code>"
                    "</blockquote>"
                )
            except Exception:
                pass

    time_taken = datetime.timedelta(seconds=int(time.time() - start_time))
    await sts.edit(
        f"<blockquote><b>✅ BROADCAST COMPLETED IN {time_taken}</b></blockquote>\n\n"
        "<blockquote>"
        f"┌ <b>👥 Total Users:</b> <code>{total_users}</code>\n"
        f"├ <b>🔄 Completed:</b> <code>{done} / {total_users}</code>\n"
        f"├ <b>✅ Success:</b> <code>{success}</code>\n"
        f"├ <b>🚫 Blocked:</b> <code>{blocked}</code>\n"
        f"└ <b>🗑 Deleted:</b> <code>{deleted}</code>"
        "</blockquote>"
    )