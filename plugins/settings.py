"""The /settings panel."""

import re

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from database import db
from script import Script

from .db import connect_user_db
from .test import CLIENT, get_configs, parse_buttons, update_configs

CLIENT = CLIENT()

SETTINGS_TXT = (
    "<b>Hᴇʀᴇ Is Tʜᴇ Sᴇᴛᴛɪɴɢs Pᴀɴᴇʟ⚙\n\n"
    "ᴄʜᴀɴɢᴇ ʏᴏᴜʀ sᴇᴛᴛɪɴɢs ᴀs ʏᴏᴜʀ ᴡɪsʜ 👇</b>"
)


def _mask_uri(uri):
    """Hide credentials in a Mongo URI before showing it back to the user."""
    if not uri:
        return "not set"
    return re.sub(r"://([^:@/]+)(:[^@/]*)?@", "://***:***@", uri)


class _FakeQuery:
    """Re-dispatch the settings handler to another panel.

    Wraps the real callback query but reports different ``data``, so a handler
    can redraw a different panel without duplicating its rendering code.
    """

    __slots__ = ("_query", "data")

    def __init__(self, query, data):
        self._query = query
        self.data = data

    def __getattr__(self, item):
        return getattr(self._query, item)


@Client.on_message(filters.command("settings") & filters.private)
async def settings(client, message):
    await message.reply_text(SETTINGS_TXT, reply_markup=main_buttons())


@Client.on_callback_query(filters.regex(r"^noth$"))
async def noop(bot, query):
    await query.answer()


@Client.on_callback_query(filters.regex(r"^settings"))
async def settings_query(bot, query):
    user_id = query.from_user.id
    _, type = query.data.split("#", 1)
    buttons = [[InlineKeyboardButton("back", callback_data="settings#main")]]

    if type == "main":
        await query.message.edit_text(SETTINGS_TXT, reply_markup=main_buttons())

    elif type == "extra":
        await query.message.edit_text(
            "<b>Hᴇʀᴇ Is Tʜᴇ Exᴛʀᴀ Sᴇᴛᴛɪɴɢs Pᴀɴᴇʟ⚙</b>",
            reply_markup=extra_buttons(),
        )

    # ── bots ────────────────────────────────────────────────────────
    elif type == "bots":
        buttons = []
        bots = await db.get_all_bots(user_id)
        usr_bot = await db.get_userbot(user_id)
        for idx, _bot in enumerate(bots):
            buttons.append([
                InlineKeyboardButton(
                    f"🤖 {_bot['name']} (@{_bot['username']})",
                    callback_data=f"settings#editbot_{idx}",
                )
            ])
        buttons.append([
            InlineKeyboardButton(
                "✚ Add Another Bot ✚" if bots else "✚ Add bot ✚",
                callback_data="settings#addbot",
            )
        ])
        if usr_bot is not None:
            buttons.append([
                InlineKeyboardButton(
                    f"👤 {usr_bot['name']} (UserBot)",
                    callback_data="settings#edituserbot",
                )
            ])
        else:
            buttons.append([
                InlineKeyboardButton("✚ Add User bot ✚", callback_data="settings#adduserbot")
            ])
        buttons.append([InlineKeyboardButton("back", callback_data="settings#main")])
        speed_text = (
            f"\n<b>⚡ Speed:</b> <code>~{len(bots) * 20} msgs/min</code>" if bots else ""
        )
        await query.message.edit_text(
            f"<b><u>My Bots</u></b>\n\n<b>Manage your bots here.</b>\n"
            f"<b>Active Bots:</b> <code>{len(bots)}</code>{speed_text}",
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    elif type == "addbot":
        await query.message.delete()
        if await CLIENT.add_bot(bot, query) is not True:
            return
        await bot.send_message(
            user_id,
            "<b>✅ Bot token successfully added!</b>\n\n"
            "<i>Add more bots for faster forwarding.</i>",
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    elif type == "adduserbot":
        await query.message.delete()
        if await CLIENT.add_session(bot, query) is not True:
            return
        await bot.send_message(
            user_id,
            "<b>✅ Session successfully added!</b>",
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    elif type.startswith("editbot"):
        idx = int(type.split("_")[1]) if "_" in type else 0
        bots = await db.get_all_bots(user_id)
        if not bots or idx >= len(bots):
            return await query.answer("Bot not found", show_alert=True)
        bot_data = bots[idx]
        await query.message.edit_text(
            Script.BOT_DETAILS.format(
                bot_data["name"], bot_data["id"], bot_data["username"]
            ),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Remove ❌", callback_data=f"settings#removebot_{idx}")],
                [InlineKeyboardButton("back", callback_data="settings#bots")],
            ]),
        )

    elif type == "edituserbot":
        bot_data = await db.get_userbot(user_id)
        if not bot_data:
            return await query.answer("No userbot found", show_alert=True)
        await query.message.edit_text(
            Script.USER_DETAILS.format(
                bot_data["name"], bot_data["id"], bot_data["username"]
            ),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Remove ❌", callback_data="settings#removeuserbot")],
                [InlineKeyboardButton("back", callback_data="settings#bots")],
            ]),
        )

    elif type.startswith("removebot"):
        idx = int(type.split("_")[1]) if "_" in type else 0
        await db.remove_bot_by_index(user_id, idx)
        await query.message.edit_text(
            "<b>✅ Bot removed successfully</b>",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("back", callback_data="settings#bots")]]
            ),
        )

    elif type == "removeuserbot":
        await db.remove_userbot(user_id)
        await query.message.edit_text(
            "<b>✅ Userbot removed</b>",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("back", callback_data="settings#bots")]]
            ),
        )

    # ── channels ────────────────────────────────────────────────────
    elif type == "channels":
        buttons = []
        channels = await db.get_user_channels(user_id)
        for channel in channels:
            buttons.append([
                InlineKeyboardButton(
                    channel["title"],
                    callback_data=f"settings#editchannels_{channel['chat_id']}",
                )
            ])
        buttons.append([
            InlineKeyboardButton("✚ Add Channel ✚", callback_data="settings#addchannel")
        ])
        buttons.append([InlineKeyboardButton("back", callback_data="settings#main")])
        await query.message.edit_text(
            "<b><u>My Channels</u></b>\n\n<b>Manage your target chats here.</b>\n\n"
            "<i>With more than one channel, /forward lets you pick one or fan out "
            "to all of them.</i>",
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    elif type == "addchannel":
        await query.message.delete()
        chat_ids = await bot.ask(
            chat_id=user_id,
            text="<b>❪ SET TARGET CHAT ❫\n\nAdd a target chat in 3 ways:\n\n"
            "1️⃣ Forward any message from it\n"
            "2️⃣ Send its link (https://t.me/mychannel)\n"
            "3️⃣ Send its ID (-1001234567890)\n\n/cancel - cancel this process</b>",
        )
        if not chat_ids.text and not chat_ids.forward_date:
            return await chat_ids.reply_text(
                "<b>❌ Invalid input.</b>", reply_markup=InlineKeyboardMarkup(buttons)
            )
        if chat_ids.text == "/cancel":
            return await chat_ids.reply_text(
                "<b>process canceled</b>", reply_markup=InlineKeyboardMarkup(buttons)
            )

        chat_id = title = username = None
        if chat_ids.forward_date and chat_ids.forward_from_chat:
            chat_id = chat_ids.forward_from_chat.id
            title = chat_ids.forward_from_chat.title
            username = chat_ids.forward_from_chat.username
            username = "@" + username if username else "private"
        elif chat_ids.text:
            text = chat_ids.text.strip()
            link_match = re.match(r"(?:https?://)?t\.me/([a-zA-Z0-9_]+)$", text)
            if link_match:
                text = "@" + link_match.group(1)
            try:
                chat_obj = await bot.get_chat(text)
                chat_id = chat_obj.id
                title = chat_obj.title or chat_obj.first_name or str(chat_obj.id)
                username = "@" + chat_obj.username if chat_obj.username else "private"
            except Exception as exc:
                return await chat_ids.reply_text(
                    "<b>❌ Could not find that chat. Make sure the bot is an admin "
                    f"there first.\n\nError: <code>{exc}</code></b>",
                    reply_markup=InlineKeyboardMarkup(buttons),
                )

        chat = await db.add_channel(user_id, chat_id, title, username)
        await chat_ids.reply_text(
            "<b>✅ Successfully added!</b>" if chat else "<b>This channel is already added</b>",
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    elif type.startswith("editchannels"):
        chat_id = int(type.split("_")[1])
        chat = await db.get_channel_details(user_id, chat_id)
        if not chat:
            return await query.answer("Channel not found", show_alert=True)
        await query.message.edit_text(
            f"<b><u>📄 CHANNEL DETAILS</u></b>\n\n"
            f"<b>- TITLE:</b> <code>{chat['title']}</code>\n"
            f"<b>- CHANNEL ID:</b> <code>{chat['chat_id']}</code>\n"
            f"<b>- USERNAME:</b> {chat['username']}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Remove ❌", callback_data=f"settings#removechannel_{chat_id}")],
                [InlineKeyboardButton("back", callback_data="settings#channels")],
            ]),
        )

    elif type.startswith("removechannel"):
        chat_id = int(type.split("_")[1])
        await db.remove_channel(user_id, chat_id)
        await query.message.edit_text(
            "<b>✅ Channel removed</b>",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("back", callback_data="settings#channels")]]
            ),
        )

    # ── caption ─────────────────────────────────────────────────────
    elif type == "caption":
        buttons = []
        caption = (await get_configs(user_id))["caption"]
        if caption is None:
            buttons.append([
                InlineKeyboardButton("✚ Add Caption ✚", callback_data="settings#addcaption")
            ])
        else:
            buttons.append([
                InlineKeyboardButton("See Caption", callback_data="settings#seecaption"),
                InlineKeyboardButton("🗑️ Delete", callback_data="settings#deletecaption"),
            ])
        buttons.append([InlineKeyboardButton("back", callback_data="settings#main")])
        await query.message.edit_text(
            "<b><u>CUSTOM CAPTION</u></b>\n\n<b>Set a custom caption for videos and "
            "documents.</b>\n\n<b><u>AVAILABLE FILLINGS:</u></b>\n"
            "- <code>{filename}</code> : Filename\n"
            "- <code>{size}</code> : File size\n"
            "- <code>{caption}</code> : original caption",
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    elif type == "seecaption":
        data = await get_configs(user_id)
        await query.message.edit_text(
            f"<b><u>YOUR CUSTOM CAPTION</u></b>\n\n<code>{data['caption']}</code>",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🖋️ Edit", callback_data="settings#addcaption")],
                [InlineKeyboardButton("back", callback_data="settings#caption")],
            ]),
        )

    elif type == "deletecaption":
        await update_configs(user_id, "caption", None)
        await query.message.edit_text(
            "<b>✅ Caption deleted</b>",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("back", callback_data="settings#caption")]]
            ),
        )

    elif type == "addcaption":
        await query.message.delete()
        caption = await bot.ask(
            user_id,
            "Send your custom caption\n/cancel - <code>cancel this process</code>",
        )
        if not caption.text or caption.text == "/cancel":
            return await caption.reply_text(
                "<b>process canceled !</b>", reply_markup=InlineKeyboardMarkup(buttons)
            )
        try:
            caption.text.format(filename="", size="", caption="")
        except (KeyError, IndexError) as exc:
            return await caption.reply_text(
                f"<b>Wrong filling {exc} used in your caption. Fix it and try again.</b>",
                reply_markup=InlineKeyboardMarkup(buttons),
            )
        await update_configs(user_id, "caption", caption.text)
        await caption.reply_text(
            "<b>✅ Caption updated</b>", reply_markup=InlineKeyboardMarkup(buttons)
        )

    # ── button ──────────────────────────────────────────────────────
    elif type == "button":
        buttons = []
        button = (await get_configs(user_id))["button"]
        if button is None:
            buttons.append([
                InlineKeyboardButton("✚ Add Button ✚", callback_data="settings#addbutton")
            ])
        else:
            buttons.append([
                InlineKeyboardButton("👀 See Button", callback_data="settings#seebutton"),
                InlineKeyboardButton("🗑️ Remove", callback_data="settings#deletebutton"),
            ])
        buttons.append([InlineKeyboardButton("back", callback_data="settings#main")])
        await query.message.edit_text(
            "<b><u>CUSTOM BUTTON</u></b>\n\n<b>Attach an inline button to every "
            "message.</b>\n\n<b><u>FORMAT:</u></b>\n"
            "<code>[Forward bot][buttonurl:https://t.me/yourchannel]</code>",
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    elif type == "addbutton":
        await query.message.delete()
        ask = await bot.ask(
            user_id,
            "<b>Send your custom button.\n\nFORMAT:</b>\n"
            "<code>[forward bot][buttonurl:https://t.me/yourchannel]</code>",
        )
        if not ask.text or ask.text == "/cancel":
            return await ask.reply(
                "<b>process canceled !</b>", reply_markup=InlineKeyboardMarkup(buttons)
            )
        if not parse_buttons(ask.text.html):
            return await ask.reply("<b>INVALID BUTTON</b>")
        await update_configs(user_id, "button", ask.text.html)
        await ask.reply(
            "<b>✅ Button added</b>", reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif type == "seebutton":
        button = parse_buttons((await get_configs(user_id))["button"], markup=False)
        if not button:
            return await query.answer("No button set", show_alert=True)
        button.append([InlineKeyboardButton("back", callback_data="settings#button")])
        await query.message.edit_text(
            "<b>YOUR CUSTOM BUTTON</b>", reply_markup=InlineKeyboardMarkup(button)
        )

    elif type == "deletebutton":
        await update_configs(user_id, "button", None)
        await query.message.edit_text(
            "<b>✅ Button deleted</b>",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("back", callback_data="settings#button")]]
            ),
        )

    # ── database ────────────────────────────────────────────────────
    elif type == "database":
        buttons = []
        db_uri = (await get_configs(user_id))["db_uri"]
        if db_uri is None:
            buttons.append([
                InlineKeyboardButton("✚ Add Mongo Url", callback_data="settings#addurl")
            ])
        else:
            buttons.append([
                InlineKeyboardButton("👀 See Url", callback_data="settings#seeurl"),
                InlineKeyboardButton("❌ Remove Url", callback_data="settings#deleteurl"),
            ])
        buttons.append([InlineKeyboardButton("back", callback_data="settings#main")])
        await query.message.edit_text(
            "<b><u>DATABASE</u>\n\nA database stores duplicate file ids permanently, "
            "so skip-duplicate keeps working across restarts and across very large "
            "channels.</b>",
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    elif type == "addurl":
        await query.message.delete()
        uri = await bot.ask(
            user_id,
            "<b>Send your MongoDB URL.</b>\n\n"
            "<i>Get one free at <a href='https://mongodb.com'>mongodb.com</a></i>",
            disable_web_page_preview=True,
        )
        if not uri.text or uri.text == "/cancel":
            return await uri.reply_text(
                "<b>process canceled !</b>", reply_markup=InlineKeyboardMarkup(buttons)
            )
        if not uri.text.strip().startswith("mongodb"):
            return await uri.reply(
                "<b>Invalid MongoDB URL</b>", reply_markup=InlineKeyboardMarkup(buttons)
            )
        connect, udb = await connect_user_db(user_id, uri.text.strip(), "test")
        if not connect:
            return await uri.reply(
                "<b>Cannot connect with this URI. Check the URL, password, and that "
                "your IP is allowed.</b>",
                reply_markup=InlineKeyboardMarkup(buttons),
            )
        await udb.drop_all()
        await udb.close()
        await update_configs(user_id, "db_uri", uri.text.strip())
        # Delete the message so the plaintext URI does not linger in the chat.
        try:
            await uri.delete()
        except Exception:
            pass
        await bot.send_message(
            user_id,
            "<b>✅ Database URL added</b>\n<i>Your message was deleted so the "
            "credentials are not left in this chat.</i>",
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    elif type == "seeurl":
        db_uri = (await get_configs(user_id))["db_uri"]
        # Credentials are masked — the old version showed the full URI.
        await query.answer(f"DATABASE URL: {_mask_uri(db_uri)}", show_alert=True)

    elif type == "deleteurl":
        await update_configs(user_id, "db_uri", None)
        await query.message.edit_text(
            "<b>✅ Database URL deleted</b>",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("back", callback_data="settings#database")]]
            ),
        )

    # ── filters ─────────────────────────────────────────────────────
    elif type == "filters":
        await query.message.edit_text(
            "<b><u>💠 CUSTOM FILTERS 💠</u></b>\n\n"
            "<b>Pick which message types get forwarded.</b>",
            reply_markup=await filters_buttons(user_id),
        )

    elif type == "nextfilters":
        await query.edit_message_reply_markup(
            reply_markup=await next_filters_buttons(user_id)
        )

    elif type.startswith("updatefilter"):
        _, key, value = type.split("-")
        await update_configs(user_id, key, value != "True")
        if key in ("poll", "protect", "voice", "animation", "sticker", "duplicate"):
            return await query.edit_message_reply_markup(
                reply_markup=await next_filters_buttons(user_id)
            )
        await query.edit_message_reply_markup(
            reply_markup=await filters_buttons(user_id)
        )

    # ── dry run ─────────────────────────────────────────────────────
    elif type == "dryrun":
        configs = await get_configs(user_id)
        await query.message.edit_text(
            "<b><u>🧪 DRY RUN</u></b>\n\n"
            "<b>When enabled, /forward walks the source and applies all your "
            "filters but sends nothing.</b>\n\n"
            "<i>Use it to preview how many messages would actually be forwarded "
            "before committing to a large task.</i>\n\n"
            f"<b>Status:</b> <code>{'ON' if configs.get('dry_run') else 'OFF'}</code>",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "🔴 Turn OFF" if configs.get("dry_run") else "🟢 Turn ON",
                    callback_data=f"settings#toggledry-{configs.get('dry_run')}",
                )],
                [InlineKeyboardButton("back", callback_data="settings#extra")],
            ]),
        )

    elif type.startswith("toggledry"):
        current = type.split("-")[1] == "True"
        await update_configs(user_id, "dry_run", not current)
        configs = await get_configs(user_id)
        await query.message.edit_text(
            "<b><u>🧪 DRY RUN</u></b>\n\n"
            f"<b>Status:</b> <code>{'ON' if configs.get('dry_run') else 'OFF'}</code>",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "🔴 Turn OFF" if configs.get("dry_run") else "🟢 Turn ON",
                    callback_data=f"settings#toggledry-{configs.get('dry_run')}",
                )],
                [InlineKeyboardButton("back", callback_data="settings#extra")],
            ]),
        )

    # ── size limits ─────────────────────────────────────────────────
    elif type.startswith("file_size"):
        size = (await get_configs(user_id)).get("min_size", 0)
        await query.message.edit_text(_min_size_text(size), reply_markup=size_button(size))

    elif type.startswith("maxfile_size"):
        size = (await get_configs(user_id)).get("max_size", 0)
        await query.message.edit_text(_max_size_text(size), reply_markup=maxsize_button(size))

    elif type.startswith("maxupdate_size"):
        size = max(0, int(type.split("-")[1]))
        if size > 4000:
            return await query.answer("Size limit exceeded", show_alert=True)
        await update_configs(user_id, "max_size", size)
        await query.message.edit_text(_max_size_text(size), reply_markup=maxsize_button(size))

    elif type.startswith("update_size"):
        size = max(0, int(type.split("-")[1]))
        if size > 4000:
            return await query.answer("Size limit exceeded", show_alert=True)
        await update_configs(user_id, "min_size", size)
        await query.message.edit_text(_min_size_text(size), reply_markup=size_button(size))

    # ── extensions ──────────────────────────────────────────────────
    elif type == "add_extension":
        await query.message.delete()
        ext = await bot.ask(
            user_id,
            "<b>Send the file extensions, separated by spaces.</b>\n\n"
            "Example: <code>.mp4 .mkv .zip</code>\n"
            "<i>The leading dot is optional — <code>mp4 mkv</code> works too.</i>",
        )
        if not ext.text or ext.text == "/cancel":
            return await ext.reply_text(
                "<b>process canceled</b>", reply_markup=InlineKeyboardMarkup(buttons)
            )
        # Normalise to a bare, lower-case extension so ".MP4", "mp4" and
        # "*.mp4" all end up as the same entry.
        extensions = []
        for raw in ext.text.split():
            cleaned = raw.strip().lstrip("*").lstrip(".").lower()
            if cleaned:
                extensions.append(cleaned)
        if not extensions:
            return await ext.reply_text(
                "<b>No valid extension found in that message.</b>",
                reply_markup=InlineKeyboardMarkup(buttons),
            )
        current = (await get_configs(user_id))["extension"] or []
        merged = list(dict.fromkeys(current + extensions))
        await update_configs(user_id, "extension", merged)
        await ext.reply_text(
            f"<b>✅ Added:</b> <code>{', '.join('.' + e for e in extensions)}</code>",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("back", callback_data="settings#get_extension")]]
            ),
        )

    elif type == "get_extension":
        configs = await get_configs(user_id)
        extensions = configs["extension"]
        mode = configs.get("extension_mode") or "block"
        listing = (
            "<b>🕹 Extensions:</b>"
            + "".join(f"\n<code>- .{str(e).lstrip('.')}</code>" for e in extensions)
            if extensions
            else "<b>No extensions set</b>"
        )
        explain = (
            "<b>Mode: 🚫 BLOCK</b> — files with these extensions are <u>skipped</u>."
            if mode == "block"
            else "<b>Mode: ✅ ALLOW ONLY</b> — <u>only</u> files with these "
            "extensions are forwarded, everything else is skipped."
        )
        rows = [
            [InlineKeyboardButton(
                "🚫 Block these" if mode == "block" else "✅ Allow only these",
                callback_data="settings#toggle_extension_mode",
            )],
            [InlineKeyboardButton("✚ Add", callback_data="settings#add_extension")],
        ]
        if extensions:
            rows.append([
                InlineKeyboardButton("➖ Remove one", callback_data="settings#rmve_extension")
            ])
        rows.append([
            InlineKeyboardButton("Remove All", callback_data="settings#rmve_all_extension")
        ])
        rows.append([InlineKeyboardButton("back", callback_data="settings#extra")])
        await query.message.edit_text(
            f"<b><u>EXTENSIONS</u></b>\n\n{explain}\n\n{listing}",
            reply_markup=InlineKeyboardMarkup(rows),
        )

    elif type == "toggle_extension_mode":
        current = (await get_configs(user_id)).get("extension_mode") or "block"
        await update_configs(
            user_id, "extension_mode", "allow" if current == "block" else "block"
        )
        return await settings_query(
            bot, _FakeQuery(query, "settings#get_extension")
        )

    elif type == "rmve_extension":
        extensions = (await get_configs(user_id))["extension"] or []
        if not extensions:
            return await query.answer("Nothing to remove", show_alert=True)
        rows = [
            [InlineKeyboardButton(
                f"🗑 .{str(e).lstrip('.')}", callback_data=f"settings#delext_{i}"
            )]
            for i, e in enumerate(extensions)
        ]
        rows.append([InlineKeyboardButton("back", callback_data="settings#get_extension")])
        await query.message.edit_text(
            "<b>Tap an extension to remove it</b>",
            reply_markup=InlineKeyboardMarkup(rows),
        )

    elif type.startswith("delext_"):
        try:
            index = int(type.split("_", 1)[1])
        except ValueError:
            return await query.answer("Bad button", show_alert=True)
        extensions = (await get_configs(user_id))["extension"] or []
        if not 0 <= index < len(extensions):
            return await query.answer("Already removed", show_alert=True)
        removed = extensions.pop(index)
        await update_configs(user_id, "extension", extensions or None)
        await query.answer(f"Removed .{str(removed).lstrip('.')}")
        return await settings_query(bot, _FakeQuery(query, "settings#get_extension"))

    elif type == "rmve_all_extension":
        await update_configs(user_id, "extension", None)
        await query.message.edit_text(
            "<b>✅ All extensions deleted</b>",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("back", callback_data="settings#get_extension")]]
            ),
        )

    # ── keywords ────────────────────────────────────────────────────
    elif type == "add_keyword":
        await query.message.delete()
        ask = await bot.ask(
            user_id,
            "<b>Send the keywords (separated by spaces)\n"
            "Example: <code>English 1080p Hdrip</code></b>",
        )
        if not ask.text or ask.text == "/cancel":
            return await ask.reply_text(
                "<b>process canceled</b>", reply_markup=InlineKeyboardMarkup(buttons)
            )
        keywords = [k for k in ask.text.split() if k]
        current = (await get_configs(user_id))["keywords"] or []
        merged = list(dict.fromkeys(current + keywords))
        await update_configs(user_id, "keywords", merged)
        await ask.reply_text(
            "<b>✅ Updated</b>",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("back", callback_data="settings#get_keyword")]]
            ),
        )

    elif type == "get_keyword":
        keywords = (await get_configs(user_id))["keywords"]
        listing = (
            "<b>🔖 Keywords:</b>" + "".join(f"\n<code>- {k}</code>" for k in keywords)
            if keywords
            else "<b>No keywords set</b>"
        )
        await query.message.edit_text(
            f"<b><u>KEYWORDS</u></b>\n\n<b>Only files whose name matches one of these "
            f"will be forwarded</b>\n\n{listing}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✚ Add", callback_data="settings#add_keyword")],
                [InlineKeyboardButton("Remove all", callback_data="settings#rmve_all_keyword")],
                [InlineKeyboardButton("back", callback_data="settings#extra")],
            ]),
        )

    elif type == "rmve_all_keyword":
        await update_configs(user_id, "keywords", None)
        await query.message.edit_text(
            "<b>✅ All keywords deleted</b>",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("back", callback_data="settings#get_keyword")]]
            ),
        )

    # ── speed ───────────────────────────────────────────────────────
    elif type == "speed":
        bs = await db.get_batch_settings(user_id)
        await query.message.edit_text(
            _speed_text(bs), reply_markup=_speed_markup(bs), disable_web_page_preview=True
        )

    elif type.startswith("speed_set"):
        # Format: speed_set_{key}-{value}, e.g. speed_set_batch_size-25
        try:
            key, val = type[len("speed_set_"):].rsplit("-", 1)
        except ValueError:
            return await query.answer("Bad speed button", show_alert=True)

        if key == "batch_size":
            value = int(val)
            if not 5 <= value <= 100:
                return await query.answer("Range: 5 – 100", show_alert=True)
        elif key == "base_sleep":
            value = float(val)
            if not 0.5 <= value <= 10.0:
                return await query.answer("Range: 0.5 – 10.0 s", show_alert=True)
        elif key == "stagger_delay":
            value = float(val)
            if not 0.0 <= value <= 2.0:
                return await query.answer("Range: 0.0 – 2.0 s", show_alert=True)
        else:
            return await query.answer("Unknown setting", show_alert=True)

        await db.update_batch_settings(user_id, key, value)
        bs = await db.get_batch_settings(user_id)
        await query.message.edit_text(
            _speed_text(bs), reply_markup=_speed_markup(bs), disable_web_page_preview=True
        )

    elif type.startswith("alert"):
        await query.answer(type.split("_", 1)[1], show_alert=True)


# ── text helpers ───────────────────────────────────────────────────


def _min_size_text(size):
    return (
        "<b><u>MIN SIZE LIMIT</u></b>\n\n"
        f"<b>Only files larger than <code>{size} MB</code> are forwarded.</b>\n\n"
        "<i>Set to 0 to disable.</i>"
    )


def _max_size_text(size):
    return (
        "<b><u>MAX SIZE LIMIT</u></b>\n\n"
        f"<b>Only files smaller than <code>{size} MB</code> are forwarded.</b>\n\n"
        "<i>Set to 0 to disable.</i>"
    )


def _speed_text(bs):
    batch = bs.get("batch_size", 20)
    sleep = bs.get("base_sleep", 3.0)
    stagger = bs.get("stagger_delay", 0.2)
    per_bot = round(60 / sleep) if sleep > 0 else 0
    return (
        "<b><u>⚡ Speed / Batch Settings</u></b>\n\n"
        f"<b>📦 Queue Size:</b> <code>{batch}</code>  <i>(messages buffered before dispatch)</i>\n"
        f"<b>⏱ Delay:</b> <code>{sleep}s</code>  <i>(~{per_bot} msgs/min per bot)</i>\n"
        f"<b>🔀 Stagger:</b> <code>{stagger}s</code>  <i>(offset between bot workers)</i>\n\n"
        "<i>Bots send in parallel, so total speed ≈ per-bot rate × bot count.\n"
        "Lower the delay for speed; raise it if you hit FloodWait.</i>"
    )


def _speed_markup(bs):
    batch = int(bs.get("batch_size", 20))
    s = round(float(bs.get("base_sleep", 3.0)) * 10) / 10
    st = round(float(bs.get("stagger_delay", 0.2)) * 10) / 10
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"📦 Queue: {batch}", callback_data="noth")],
        [
            InlineKeyboardButton("-5", callback_data=f"settings#speed_set_batch_size-{max(5, batch - 5)}"),
            InlineKeyboardButton("-1", callback_data=f"settings#speed_set_batch_size-{max(5, batch - 1)}"),
            InlineKeyboardButton("+1", callback_data=f"settings#speed_set_batch_size-{min(100, batch + 1)}"),
            InlineKeyboardButton("+5", callback_data=f"settings#speed_set_batch_size-{min(100, batch + 5)}"),
        ],
        [InlineKeyboardButton(f"⏱ Delay: {s}s", callback_data="noth")],
        [
            InlineKeyboardButton("-0.5", callback_data=f"settings#speed_set_base_sleep-{max(0.5, round(s - 0.5, 1))}"),
            InlineKeyboardButton("-0.1", callback_data=f"settings#speed_set_base_sleep-{max(0.5, round(s - 0.1, 1))}"),
            InlineKeyboardButton("+0.1", callback_data=f"settings#speed_set_base_sleep-{min(10.0, round(s + 0.1, 1))}"),
            InlineKeyboardButton("+0.5", callback_data=f"settings#speed_set_base_sleep-{min(10.0, round(s + 0.5, 1))}"),
        ],
        [InlineKeyboardButton(f"🔀 Stagger: {st}s", callback_data="noth")],
        [
            InlineKeyboardButton("-0.1", callback_data=f"settings#speed_set_stagger_delay-{max(0.0, round(st - 0.1, 1))}"),
            InlineKeyboardButton("+0.1", callback_data=f"settings#speed_set_stagger_delay-{min(2.0, round(st + 0.1, 1))}"),
        ],
        [InlineKeyboardButton("⫷ Back", callback_data="settings#main")],
    ])


# ── keyboards ──────────────────────────────────────────────────────


def extra_buttons():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💾 Mɪɴ Sɪᴢᴇ Lɪᴍɪᴛ", callback_data="settings#file_size")],
        [InlineKeyboardButton("💾 Mᴀx Sɪᴢᴇ Lɪᴍɪᴛ", callback_data="settings#maxfile_size")],
        [
            InlineKeyboardButton("🚥 Keywords", callback_data="settings#get_keyword"),
            InlineKeyboardButton("🕹 Extensions", callback_data="settings#get_extension"),
        ],
        [InlineKeyboardButton("🧪 Dʀʏ Rᴜɴ", callback_data="settings#dryrun")],
        [InlineKeyboardButton("⫷ Bᴀᴄᴋ", callback_data="settings#main")],
    ])


def main_buttons():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🤖 Bᴏᴛs", callback_data="settings#bots"),
            InlineKeyboardButton("🏷 Cʜᴀɴɴᴇʟs", callback_data="settings#channels"),
        ],
        [
            InlineKeyboardButton("🖋️ Cᴀᴘᴛɪᴏɴ", callback_data="settings#caption"),
            InlineKeyboardButton("⏹ Bᴜᴛᴛᴏɴ", callback_data="settings#button"),
        ],
        [
            InlineKeyboardButton("🕵‍♀ Fɪʟᴛᴇʀs 🕵‍♀", callback_data="settings#filters"),
            InlineKeyboardButton("🗃 MᴏɴɢᴏDB", callback_data="settings#database"),
        ],
        [
            InlineKeyboardButton("Exᴛʀᴀ Sᴇᴛᴛɪɴɢs 🧪", callback_data="settings#extra"),
            InlineKeyboardButton("⚡ Sᴘᴇᴇᴅ", callback_data="settings#speed"),
        ],
        [InlineKeyboardButton("⫷ Bᴀᴄᴋ", callback_data="help")],
    ])


def _toggle_row(label, key, value, prefix="settings"):
    return [
        InlineKeyboardButton(label, callback_data=f"{prefix}_#updatefilter-{key}-{value}"),
        InlineKeyboardButton(
            "✅" if value else "❌", callback_data=f"{prefix}#updatefilter-{key}-{value}"
        ),
    ]


async def filters_buttons(user_id):
    configs = await get_configs(user_id)
    f = configs["filters"]
    return InlineKeyboardMarkup([
        _toggle_row("🏷️ Forward tag", "forward_tag", configs["forward_tag"]),
        _toggle_row("🖍️ Texts", "text", f["text"]),
        _toggle_row("📁 Documents", "document", f["document"]),
        _toggle_row("🎞️ Videos", "video", f["video"]),
        _toggle_row("📷 Photos", "photo", f["photo"]),
        _toggle_row("🎧 Audios", "audio", f["audio"]),
        [
            InlineKeyboardButton("⫷ back", callback_data="settings#main"),
            InlineKeyboardButton("next ⫸", callback_data="settings#nextfilters"),
        ],
    ])


async def next_filters_buttons(user_id):
    configs = await get_configs(user_id)
    f = configs["filters"]
    return InlineKeyboardMarkup([
        _toggle_row("🎤 Voices", "voice", f["voice"]),
        _toggle_row("🎭 Animations", "animation", f["animation"]),
        _toggle_row("🃏 Stickers", "sticker", f["sticker"]),
        _toggle_row("▶️ Skip duplicate", "duplicate", configs["duplicate"]),
        _toggle_row("📊 Poll", "poll", f["poll"]),
        _toggle_row("🔒 Secure message", "protect", configs["protect"]),
        [
            InlineKeyboardButton("⫷ back", callback_data="settings#filters"),
            InlineKeyboardButton("End ⫸", callback_data="settings#main"),
        ],
    ])


def size_button(size):
    rows = [[InlineKeyboardButton("💾 Min Size Limit", callback_data="noth")]]
    for step in (1, 5, 10, 50, 100):
        rows.append([
            InlineKeyboardButton(f"+{step}", callback_data=f"settings#update_size-{size + step}"),
            InlineKeyboardButton(f"-{step}", callback_data=f"settings#update_size-{max(0, size - step)}"),
        ])
    rows.append([InlineKeyboardButton("back", callback_data="settings#extra")])
    return InlineKeyboardMarkup(rows)


def maxsize_button(size):
    rows = [[InlineKeyboardButton("💾 Max Size Limit", callback_data="noth")]]
    for step in (1, 5, 10, 50, 100):
        rows.append([
            InlineKeyboardButton(f"+{step}", callback_data=f"settings#maxupdate_size-{size + step}"),
            InlineKeyboardButton(f"-{step}", callback_data=f"settings#maxupdate_size-{max(0, size - step)}"),
        ])
    rows.append([InlineKeyboardButton("back", callback_data="settings#extra")])
    return InlineKeyboardMarkup(rows)
