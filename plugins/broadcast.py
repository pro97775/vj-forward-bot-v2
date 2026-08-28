"""/broadcast — owner-only message fan-out to every user."""

import asyncio
import datetime
import logging
import time

from pyrogram import Client, filters
from pyrogram.errors import (
    FloodWait,
    InputUserDeactivated,
    PeerIdInvalid,
    UserIsBlocked,
)

from config import Config
from database import db

logger = logging.getLogger(__name__)

# Pause between sends so a large broadcast does not trip global limits.
SEND_DELAY = 0.15
UI_EVERY = 25


async def broadcast_messages(user_id, message):
    """Send one copy. Returns (ok, outcome) where outcome is a short reason."""
    for _ in range(3):
        try:
            await message.copy(chat_id=user_id)
            return True, "Success"
        except FloodWait as exc:
            if exc.value > 300:
                return False, "Error"
            await asyncio.sleep(exc.value + 1)
        except InputUserDeactivated:
            await db.delete_user(int(user_id))
            logger.info("%s removed — account deleted", user_id)
            return False, "Deleted"
        except UserIsBlocked:
            logger.info("%s has blocked the bot", user_id)
            return False, "Blocked"
        except PeerIdInvalid:
            await db.delete_user(int(user_id))
            return False, "Error"
        except Exception as exc:
            logger.debug("broadcast to %s failed: %s", user_id, exc)
            return False, "Error"
    return False, "Error"


@Client.on_message(
    filters.command("broadcast") & filters.user(Config.BOT_OWNER) & filters.reply
)
async def broadcast(bot, message):
    users = await db.get_all_users()
    b_msg = message.reply_to_message
    sts = await message.reply_text("Broadcasting your message…")
    start_time = time.time()
    total_users = await db.total_users_count()

    done = blocked = deleted = failed = success = 0
    template = (
        "<b>Broadcast in progress</b>\n\n"
        "Total: <code>{total}</code>\n"
        "Completed: <code>{done} / {total}</code>\n"
        "Success: <code>{success}</code>\n"
        "Blocked: <code>{blocked}</code>\n"
        "Deleted: <code>{deleted}</code>\n"
        "Failed: <code>{failed}</code>"
    )

    async for user in users:
        user_id = user.get("id")
        if user_id is None:
            failed += 1
        else:
            ok, outcome = await broadcast_messages(int(user_id), b_msg)
            if ok:
                success += 1
            elif outcome == "Blocked":
                blocked += 1
            elif outcome == "Deleted":
                deleted += 1
            else:
                failed += 1
        done += 1

        if done % UI_EVERY == 0:
            try:
                await sts.edit(
                    template.format(
                        total=total_users, done=done, success=success,
                        blocked=blocked, deleted=deleted, failed=failed,
                    )
                )
            except Exception:
                pass
        await asyncio.sleep(SEND_DELAY)

    elapsed = datetime.timedelta(seconds=int(time.time() - start_time))
    await sts.edit(
        f"<b>Broadcast completed in {elapsed}</b>\n\n"
        + template.format(
            total=total_users, done=done, success=success,
            blocked=blocked, deleted=deleted, failed=failed,
        ).split("\n\n", 1)[1]
    )
