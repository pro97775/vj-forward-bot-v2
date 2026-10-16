# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

import re
from .utils import STS
from .test import compute_pool_delay
from database import db
from script import Script
from pyrogram import Client, filters, enums
from pyrogram.errors.exceptions.not_acceptable_406 import ChannelPrivate as PrivateChat
from pyrogram.errors.exceptions.bad_request_400 import (
    ChannelInvalid,
    UsernameInvalid,
    UsernameNotModified,
    ChannelPrivate,
)
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)


def _build_confirm_card(sts_id: str, bots: list, userbot: dict, mode: str, from_title: str, to_title: str, skip: int, limit: int):
    has_bots = len(bots) > 0
    has_userbot = userbot is not None

    if mode == "userbot" and has_userbot:
        mode_title = f"👤 Userbot Session (@{userbot.get('username', 'userbot')})"
        rate_info = "20 msgs/min • 3.0s base delay"
    else:
        mode = "pool"
        n = len(bots)
        delay = compute_pool_delay(n)
        mode_title = f"🤖 Multi-Bot Round-Robin Pool ({n} Bot{'s' if n != 1 else ''})"
        rate_info = f"{n * 20} msgs/min capacity • {delay}s auto-delay"

    text = Script.DOUBLE_CHECK.format(
        mode_title=mode_title,
        rate_info=rate_info,
        from_chat=from_title,
        to_chat=to_title,
        skip=skip,
        limit=limit,
    )

    buttons = [
        [
            InlineKeyboardButton("🚀 Start Forwarding", callback_data=f"start_public_{sts_id}"),
        ]
    ]
    if has_bots and has_userbot:
        toggle_label = (
            "🔄 Switch to 👤 Userbot Mode"
            if mode == "pool"
            else f"🔄 Switch to 🤖 Multi-Bot Pool ({len(bots)} Bots)"
        )
        buttons.append(
            [InlineKeyboardButton(toggle_label, callback_data=f"toggle_mode_{sts_id}")]
        )
    buttons.append([InlineKeyboardButton("✖️ Cancel", callback_data="close_btn")])
    return text, InlineKeyboardMarkup(buttons), mode


@Client.on_message(filters.private & filters.command(["forward"]))
async def run(bot, message):
    buttons = []
    btn_data = {}
    user_id = message.from_user.id

    bots = await db.get_bots(user_id)
    userbot = await db.get_userbot(user_id)
    if not bots and not userbot:
        return await message.reply(
            "<blockquote><b>⚠️ No Worker Bots or Userbot Found!</b>\n\n"
            "Go to <code>/settings</code> ➔ <b>🤖 Bot Manager</b> to add your bot token(s) or Userbot session first.</blockquote>"
        )

    channels = await db.get_user_channels(user_id)
    if not channels:
        return await message.reply_text(
            "<blockquote><b>⚠️ No Target Channels Configured!</b>\n\n"
            "Please add at least one Target Channel in <code>/settings</code> ➔ <b>📢 Target Channels</b> before forwarding.</blockquote>"
        )

    if len(channels) > 1:
        for channel in channels:
            buttons.append([KeyboardButton(f"{channel['title']}")])
            btn_data[channel["title"]] = channel["chat_id"]
        buttons.append([KeyboardButton("cancel")])
        _toid = await bot.ask(
            message.chat.id,
            Script.TO_MSG,
            reply_markup=ReplyKeyboardMarkup(buttons, one_time_keyboard=True, resize_keyboard=True),
        )
        if not _toid.text or _toid.text.lower().startswith(("/", "cancel")):
            return await message.reply_text(Script.CANCEL, reply_markup=ReplyKeyboardRemove())
        to_title = _toid.text
        toid = btn_data.get(to_title)
        if not toid:
            return await message.reply_text(
                "<blockquote><b>❌ Unknown target channel selected!</b></blockquote>",
                reply_markup=ReplyKeyboardRemove(),
            )
    else:
        toid = channels[0]["chat_id"]
        to_title = channels[0]["title"]

    fromid = await bot.ask(message.chat.id, Script.FROM_MSG, reply_markup=ReplyKeyboardRemove())
    if fromid.text and fromid.text.startswith("/"):
        return await message.reply(Script.CANCEL)

    if fromid.text and not fromid.forward_date:
        regex = re.compile(r"(https://)?(t\.me/|telegram\.me/|telegram\.dog/)(c/)?(\d+|[a-zA-Z_0-9]+)/(\d+)$")
        match = regex.match(fromid.text.replace("?single", "").strip())
        if not match:
            return await message.reply("<blockquote><b>❌ Invalid Telegram message link.</b></blockquote>")
        chat_id = match.group(4)
        last_msg_id = int(match.group(5))
        if chat_id.isnumeric():
            chat_id = int("-100" + chat_id)
    elif fromid.forward_from_chat and fromid.forward_from_chat.type in [
        enums.ChatType.CHANNEL,
        enums.ChatType.SUPERGROUP,
        "supergroup",
    ]:
        last_msg_id = fromid.forward_from_message_id
        chat_id = fromid.forward_from_chat.username or fromid.forward_from_chat.id
        if last_msg_id is None:
            return await message.reply_text(
                "<blockquote><b>⚠️ Anonymous Admin Forward Detected</b>\n\n"
                "Please copy and send the direct message link from the source chat instead.</blockquote>"
            )
    else:
        return await message.reply_text("<blockquote><b>❌ Invalid source message or link!</b></blockquote>")

    try:
        title = (await bot.get_chat(chat_id)).title
    except (PrivateChat, ChannelPrivate, ChannelInvalid):
        title = "Private Chat" if fromid.text else fromid.forward_from_chat.title
    except (UsernameInvalid, UsernameNotModified):
        return await message.reply("<blockquote><b>❌ Invalid chat username or link specified.</b></blockquote>")
    except Exception as e:
        return await message.reply(f"<blockquote><b>❌ Error resolving source chat:</b> <code>{e}</code></blockquote>")

    skipno = await bot.ask(message.chat.id, Script.SKIP_MSG)
    if not skipno.text or skipno.text.startswith("/"):
        return await message.reply(Script.CANCEL)
    if not skipno.text.strip().isdigit():
        return await message.reply("<blockquote><b>❌ Invalid skip number. Please enter a non-negative integer (e.g. 0).</b></blockquote>")

    skip_val = int(skipno.text.strip())
    forward_id = f"{user_id}-{skipno.id}"

    configs = await db.get_configs(user_id)
    preferred_mode = configs.get("forward_mode", "pool")
    if preferred_mode == "pool" and not bots:
        preferred_mode = "userbot"
    elif preferred_mode == "userbot" and not userbot:
        preferred_mode = "pool"

    sts = STS(forward_id).store(chat_id, toid, skip_val, int(last_msg_id), mode=preferred_mode)
    sts.set_val("from_title", title)
    sts.set_val("to_title", to_title)

    text, reply_markup, final_mode = _build_confirm_card(
        forward_id, bots, userbot, preferred_mode, title, to_title, skip_val, int(last_msg_id)
    )
    sts.set_val("mode", final_mode)

    await message.reply_text(
        text=text,
        disable_web_page_preview=True,
        reply_markup=reply_markup,
    )


@Client.on_callback_query(filters.regex(r"^toggle_mode_"))
async def toggle_forward_mode(bot, query):
    user_id = query.from_user.id
    forward_id = query.data.split("toggle_mode_")[1]
    sts = STS(forward_id)
    if not sts.verify():
        return await query.answer("This confirmation card has expired.", show_alert=True)

    bots = await db.get_bots(user_id)
    userbot = await db.get_userbot(user_id)
    current_mode = sts.get("mode") or "pool"
    new_mode = "userbot" if current_mode == "pool" else "pool"

    text, reply_markup, final_mode = _build_confirm_card(
        forward_id,
        bots,
        userbot,
        new_mode,
        sts.get("from_title") or str(sts.get("FROM")),
        sts.get("to_title") or str(sts.get("TO")),
        sts.get("skip"),
        sts.get("limit"),
    )
    sts.set_val("mode", final_mode)
    await query.message.edit_text(
        text=text,
        disable_web_page_preview=True,
        reply_markup=reply_markup,
    )
    await query.answer(f"Switched mode to {'Userbot' if final_mode == 'userbot' else 'Multi-Bot Pool'}!")