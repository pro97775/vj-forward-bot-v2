"""/watch — continuous mode.

Registers a source channel so new posts are copied to the user's targets as
they arrive, instead of walking history once. Watches live in MongoDB so they
survive restarts, and the in-memory registry is rebuilt at startup.
"""

import asyncio
import logging
import re

from pyrogram import Client, filters
from pyrogram.errors import FloodWait
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from database import db

from .regix import (
    _compile_extensions,
    _compile_list,
    _file_meta,
    custom_caption,
    extension_skip,
    keyword_skip,
    size_skip,
)
from .test import parse_buttons

logger = logging.getLogger(__name__)

LINK_RE = re.compile(r"(?:https?://)?t\.me/(?:c/)?([a-zA-Z0-9_]+)")

# source chat id -> list of watch documents. Rebuilt on boot.
WATCHERS = {}


async def load_watchers():
    """Populate the in-memory registry from MongoDB."""
    WATCHERS.clear()
    cursor = db.db.watches.find({"active": True})
    count = 0
    async for doc in cursor:
        WATCHERS.setdefault(int(doc["source"]), []).append(doc)
        count += 1
    logger.info("Loaded %s active watch(es)", count)
    return count


async def _save_watch(user_id, source, targets):
    await db.db.watches.update_one(
        {"user_id": int(user_id), "source": int(source)},
        {"$set": {"targets": targets, "active": True}},
        upsert=True,
    )
    await load_watchers()


@Client.on_message(filters.private & filters.command(["watch"]))
async def watch_cmd(client, message):
    user_id = message.from_user.id

    channels = await db.get_user_channels(user_id)
    if not channels:
        return await message.reply(
            "<b>Add a target channel in /settings first.</b>"
        )

    ask = await client.ask(
        user_id,
        "<b>❪ WATCH A SOURCE ❫</b>\n\n"
        "Forward any message from the channel you want to watch, or send its "
        "link / ID.\n\n<i>New posts there will be copied to your targets "
        "automatically.</i>\n\n/cancel - cancel",
    )
    if ask.text and ask.text.startswith("/"):
        return await message.reply("<b>Cancelled.</b>")

    source = None
    if ask.forward_date and ask.forward_from_chat:
        source = ask.forward_from_chat.id
    elif ask.text:
        text = ask.text.strip()
        link = LINK_RE.match(text)
        try:
            resolved = await client.get_chat(link.group(1) if link else text)
            source = resolved.id
        except Exception as exc:
            return await message.reply(
                f"<b>Could not resolve that chat: <code>{exc}</code></b>"
            )
    if source is None:
        return await message.reply("<b>Invalid input.</b>")

    targets = [c["chat_id"] for c in channels]
    await _save_watch(user_id, source, targets)
    await message.reply(
        f"<b>👁 Watching <code>{source}</code></b>\n\n"
        f"New posts will be copied to <code>{len(targets)}</code> target(s).\n\n"
        "<i>This bot must be a member of the source and admin in the targets.</i>",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("🛑 Stop watching", callback_data=f"unwatch_{source}")]]
        ),
    )


@Client.on_message(filters.private & filters.command(["watches"]))
async def list_watches(client, message):
    cursor = db.db.watches.find({"user_id": int(message.from_user.id), "active": True})
    docs = [doc async for doc in cursor]
    if not docs:
        return await message.reply("<b>You have no active watches.</b>")

    lines = ["<b>👁 Active watches</b>", ""]
    buttons = []
    for doc in docs:
        lines.append(
            f"• <code>{doc['source']}</code> → {len(doc.get('targets', []))} target(s)"
        )
        buttons.append([
            InlineKeyboardButton(
                f"🛑 Stop {doc['source']}", callback_data=f"unwatch_{doc['source']}"
            )
        ])
    await message.reply("\n".join(lines), reply_markup=InlineKeyboardMarkup(buttons))


@Client.on_callback_query(filters.regex(r"^unwatch_"))
async def unwatch(bot, query):
    source = int(query.data.split("_", 1)[1])
    await db.db.watches.delete_many(
        {"user_id": int(query.from_user.id), "source": source}
    )
    await load_watchers()
    await query.answer("Stopped watching.", show_alert=True)
    await query.message.edit_text(f"<b>🛑 Stopped watching <code>{source}</code></b>")


@Client.on_message(filters.channel, group=3)
async def on_new_post(client, message):
    """Copy a new channel post to every watcher's targets."""
    watches = WATCHERS.get(message.chat.id)
    if not watches:
        return

    for watch in watches:
        user_id = watch["user_id"]
        try:
            configs = await db.get_configs(user_id)
            if configs.get("dry_run"):
                continue

            # Respect the same type filters as a normal forward.
            skip_types = [k for k, v in configs["filters"].items() if v is False]
            if skip_types and any(getattr(message, t, None) for t in skip_types):
                continue

            # …and the same name / extension / size filters, which continuous
            # mode previously ignored entirely.
            file_name, file_size = _file_meta(message)
            extensions = _compile_extensions(configs.get("extension"))
            ext_mode = configs.get("extension_mode") or "block"
            if extension_skip(extensions, file_name, ext_mode):
                continue
            if keyword_skip(_compile_list(configs.get("keywords")), file_name):
                continue
            if size_skip(configs.get("min_size", 0), configs.get("max_size", 0), file_size):
                continue

            caption = custom_caption(message, configs.get("caption"))
            button = parse_buttons(configs.get("button") or "")

            for target in watch.get("targets", []):
                for attempt in range(3):
                    try:
                        await message.copy(
                            chat_id=target,
                            caption=caption,
                            reply_markup=button,
                            protect_content=configs.get("protect"),
                        )
                        break
                    except FloodWait as exc:
                        if exc.value > 300 or attempt == 2:
                            logger.info("watch: giving up on %s (wait %ss)", target, exc.value)
                            break
                        await asyncio.sleep(exc.value + 1)
                    except Exception as exc:
                        logger.debug("watch copy to %s failed: %s", target, exc)
                        break
        except Exception as exc:
            logger.warning("watch handling failed for %s: %s", user_id, exc)
