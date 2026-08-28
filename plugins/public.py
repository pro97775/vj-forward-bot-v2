"""The /forward conversation.

Collects source, target(s), and range, then hands off to the engines in
regix.py. Compared with the previous version this validates every branch
before use (``last_msg_id`` could previously be referenced unbound), supports
fan-out to several target channels, and accepts an explicit id range so the
progress percentage is computed against a real total.
"""

import re

from pyrogram import Client, enums, filters
from pyrogram.errors.exceptions.bad_request_400 import (
    ChannelInvalid,
    ChannelPrivate,
    UsernameInvalid,
    UsernameNotModified,
)
from pyrogram.errors.exceptions.not_acceptable_406 import ChannelPrivate as PrivateChat
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from config import temp
from database import db
from script import Script

from .test import get_configs
from .utils import STS

LINK_RE = re.compile(
    r"(https://)?(t\.me/|telegram\.me/|telegram\.dog/)(c/)?(\d+|[a-zA-Z_0-9]+)/(\d+)$"
)
RANGE_RE = re.compile(r"^(\d+)\s*[-:]\s*(\d+)$")

DOUBLE_CHECK = """<b><u>DOUBLE CHECKING ⚠️</u></b>
<code>Check the details below, then pick an engine.</code>

<b>★ YOUR BOT(S):</b>
{bots_display}{speed_text}
<b>★ FROM CHANNEL:</b> <code>{from_chat}</code>
<b>★ TO CHANNEL(S):</b> <code>{to_chat}</code>
<b>★ MESSAGE RANGE:</b> <code>{start_id} → {last_id}</code>
<b>★ SKIPPING:</b> <code>{skip}</code>{dry}

<i>° Every bot must be admin in each target chat</i>
<i>° If the source is private, your userbot must be a member of it</i>

<b>Choose your forwarding engine 👇</b>"""


async def _resolve_source(bot, fromid):
    """Return (chat_id, last_msg_id, title) or (None, None, error_text)."""
    chat_id = last_msg_id = None

    if fromid.text and not fromid.forward_date:
        match = LINK_RE.match(fromid.text.strip().replace("?single", ""))
        if not match:
            return None, None, "Invalid link. Send the **last message link** of the source chat."
        chat_id = match.group(4)
        last_msg_id = int(match.group(5))
        if chat_id.isnumeric():
            chat_id = int("-100" + chat_id)

    elif fromid.forward_date and fromid.forward_from_chat:
        chat_type = fromid.forward_from_chat.type
        if chat_type not in (enums.ChatType.CHANNEL, enums.ChatType.SUPERGROUP):
            return None, None, "**Forward from a channel or supergroup, not a private chat.**"
        last_msg_id = fromid.forward_from_message_id
        chat_id = fromid.forward_from_chat.username or fromid.forward_from_chat.id
        if last_msg_id is None:
            return None, None, (
                "**That looks like an anonymous-admin forward. Send the last "
                "message *link* from the source chat instead.**"
            )
    else:
        return None, None, "**Invalid input. Send a forwarded message or a message link.**"

    # Resolve a readable title, tolerating private sources.
    try:
        title = (await bot.get_chat(chat_id)).title
    except (PrivateChat, ChannelPrivate, ChannelInvalid):
        title = (
            fromid.forward_from_chat.title
            if fromid.forward_from_chat
            else "private"
        )
    except (UsernameInvalid, UsernameNotModified):
        return None, None, "Invalid link specified."
    except Exception as exc:
        return None, None, f"Error resolving source: {exc}"

    return chat_id, last_msg_id, title


@Client.on_message(filters.private & filters.command(["forward", "fwd"]))
async def run(bot, message):
    user_id = message.from_user.id

    if temp.is_locked(user_id):
        return await message.reply(
            "<b>You already have a task running. Use /stop first.</b>"
        )

    bots = await db.get_all_bots(user_id)
    userbot = await db.get_userbot(user_id)
    if not bots and not userbot:
        return await message.reply(
            "<code>You haven't added any bot yet. Add one using /settings !</code>"
        )

    bot_names = [f"  • [{b['name']}](t.me/{b['username']})" for b in bots]
    if userbot:
        bot_names.append(f"  • [{userbot['name']}](t.me/{userbot['username']}) (UserBot)")
    bots_display = "\n".join(bot_names)

    active_count = len(bots) + (1 if userbot else 0)
    speed_text = (
        f"\n<b>⚡ Estimated Speed:</b> <code>~{active_count * 20} msgs/min</code>"
        if active_count > 1
        else ""
    )

    channels = await db.get_user_channels(user_id)
    if not channels:
        return await message.reply_text(
            "Please set a target channel in /settings before forwarding."
        )

    # ── target selection (supports fan-out) ─────────────────────────
    targets = []
    if len(channels) > 1:
        btn_data = {}
        buttons = []
        for channel in channels:
            buttons.append([KeyboardButton(channel["title"])])
            btn_data[channel["title"]] = channel["chat_id"]
        buttons.append([KeyboardButton("ALL CHANNELS")])
        buttons.append([KeyboardButton("cancel")])

        _toid = await bot.ask(
            message.chat.id,
            Script.TO_MSG,
            reply_markup=ReplyKeyboardMarkup(
                buttons, one_time_keyboard=True, resize_keyboard=True
            ),
        )
        if not _toid.text or _toid.text.startswith(("/", "cancel")):
            return await message.reply_text(
                Script.CANCEL, reply_markup=ReplyKeyboardRemove()
            )
        if _toid.text.strip() == "ALL CHANNELS":
            targets = [(c["chat_id"], c["title"]) for c in channels]
        else:
            chosen = btn_data.get(_toid.text.strip())
            if not chosen:
                return await message.reply_text(
                    "Wrong channel chosen!", reply_markup=ReplyKeyboardRemove()
                )
            targets = [(chosen, _toid.text.strip())]
    else:
        targets = [(channels[0]["chat_id"], channels[0]["title"])]

    # ── source ──────────────────────────────────────────────────────
    fromid = await bot.ask(
        message.chat.id, Script.FROM_MSG, reply_markup=ReplyKeyboardRemove()
    )
    if fromid.text and fromid.text.startswith("/"):
        return await message.reply(Script.CANCEL)

    chat_id, last_msg_id, title_or_error = await _resolve_source(bot, fromid)
    if chat_id is None:
        return await message.reply(title_or_error)
    title = title_or_error

    # ── range / skip ────────────────────────────────────────────────
    skipno = await bot.ask(message.chat.id, Script.SKIP_MSG)
    if not skipno.text or skipno.text.startswith("/"):
        return await message.reply(Script.CANCEL)

    raw = skipno.text.strip()
    range_match = RANGE_RE.match(raw)
    if range_match:
        start_id = int(range_match.group(1))
        end_id = int(range_match.group(2))
        if start_id > end_id:
            start_id, end_id = end_id, start_id
        skip = start_id
        last_msg_id = min(last_msg_id, end_id) if last_msg_id else end_id
    elif raw.isdigit():
        skip = int(raw)
        start_id = skip
    else:
        return await message.reply(
            "<b>Send a number to skip (e.g. <code>0</code>) or a range "
            "(e.g. <code>500-1500</code>).</b>"
        )

    if last_msg_id is None or last_msg_id <= start_id:
        return await message.reply(
            "<b>Nothing to forward — the start point is at or past the last message.</b>"
        )

    forward_id = f"{user_id}-{skipno.id}"
    primary_id, primary_title = targets[0]
    extra_targets = [t[0] for t in targets[1:]]
    to_display = ", ".join(t[1] for t in targets)

    configs = await get_configs(user_id)
    dry_run = bool(configs.get("dry_run"))

    # ── engine buttons ──────────────────────────────────────────────
    engine_buttons = []
    if bots:
        engine_buttons.append([
            InlineKeyboardButton(
                f"🤖 Bots ({len(bots)}) — ~{len(bots) * 20}/min",
                callback_data=f"start_public_{forward_id}_bots",
            )
        ])
    if userbot:
        engine_buttons.append([
            InlineKeyboardButton(
                "👤 Userbot — ~20/min",
                callback_data=f"start_public_{forward_id}_userbot",
            )
        ])
    if bots and userbot:
        engine_buttons.append([
            InlineKeyboardButton(
                "⚡ Auto (Smart Router)",
                callback_data=f"start_public_{forward_id}_auto",
            )
        ])
    engine_buttons.append([
        InlineKeyboardButton("❌ No / Cancel", callback_data="close_btn")
    ])

    await message.reply_text(
        text=DOUBLE_CHECK.format(
            bots_display=bots_display,
            speed_text=speed_text,
            from_chat=title,
            to_chat=to_display,
            start_id=start_id,
            last_id=last_msg_id,
            skip=skip,
            dry="\n<b>★ MODE:</b> <code>DRY RUN (nothing will be sent)</code>" if dry_run else "",
        ),
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup(engine_buttons),
    )

    STS(forward_id).store(
        chat_id,
        primary_id,
        skip,
        last_msg_id,
        total=max(0, last_msg_id - start_id),
        dry_run=dry_run,
        extra_targets=extra_targets,
        start_id=start_id,
    )
