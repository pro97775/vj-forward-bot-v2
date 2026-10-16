# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

from database import db
from script import Script
from pyrogram import Client, filters
from .test import get_configs, update_configs, CLIENT, parse_buttons, compute_pool_delay
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from .db import connect_user_db

CLIENT = CLIENT()


@Client.on_message(filters.command("settings") & filters.private)
async def settings(client, message):
    await message.reply_text(
        Script.SETTINGS_TXT,
        reply_markup=main_buttons(),
    )


@Client.on_callback_query(filters.regex(r"^settings"))
async def settings_query(bot, query):
    user_id = query.from_user.id
    parts = query.data.split("#", 1)
    type = parts[1].strip() if len(parts) > 1 else "main"
    back_main_btn = [[InlineKeyboardButton("⬅️ Back to Settings", callback_data="settings#main")]]

    # ------------------------------------------------------------------
    # MAIN & EXTRA MENUS
    # ------------------------------------------------------------------
    if type == "main":
        await query.message.edit_text(
            Script.SETTINGS_TXT,
            reply_markup=main_buttons(),
        )

    elif type == "extra":
        configs = await get_configs(user_id)
        min_s = configs.get("min_size", 0)
        max_s = configs.get("max_size", 0)
        kw_count = len(configs.get("keywords") or [])
        ext_count = len(configs.get("extension") or [])
        text = (
            "<blockquote><b>📏 SIZE, KEYWORDS & EXTENSION FILTERS</b></blockquote>\n\n"
            "<blockquote>"
            f"┌ <b>📉 Min File Size:</b> <code>{min_s} MB</code>\n"
            f"├ <b>📈 Max File Size:</b> <code>{max_s if max_s > 0 else 'Unlimited'}</code>\n"
            f"├ <b>🏷 Allowlist Keywords:</b> <code>{kw_count} active</code>\n"
            f"└ <b>🚫 Blocklist Extensions:</b> <code>{ext_count} active</code>"
            "</blockquote>\n\n"
            "<i>👇 Select a filter rule to configure:</i>"
        )
        await query.message.edit_text(text, reply_markup=extra_buttons())

    # ------------------------------------------------------------------
    # 🤖 MULTI-BOT ROUND-ROBIN POOL & USERBOT MANAGER
    # ------------------------------------------------------------------
    elif type == "bots":
        await render_bot_manager(query, user_id)

    elif type == "toggle_default_mode":
        configs = await get_configs(user_id)
        cur = configs.get("forward_mode", "pool")
        new_mode = "userbot" if cur == "pool" else "pool"
        await update_configs(user_id, "forward_mode", new_mode)
        await query.answer(
            f"Default mode set to {'Userbot Session' if new_mode == 'userbot' else 'Multi-Bot Pool'}!"
        )
        await render_bot_manager(query, user_id)

    elif type == "addbot":
        await query.message.delete()
        ok = await CLIENT.add_bot(bot, query)
        btns = [[InlineKeyboardButton("⬅️ Back to Bot Manager", callback_data="settings#bots")]]
        if ok:
            await bot.send_message(
                user_id,
                "<blockquote><b>✅ Worker bot(s) saved to your Multi-Bot Round-Robin Pool!</b></blockquote>",
                reply_markup=InlineKeyboardMarkup(btns),
            )
        else:
            await bot.send_message(
                user_id,
                "<blockquote><b>↩️ Return to Bot Manager:</b></blockquote>",
                reply_markup=InlineKeyboardMarkup(btns),
            )

    elif type == "adduserbot":
        await query.message.delete()
        ok = await CLIENT.add_session(bot, query)
        btns = [[InlineKeyboardButton("⬅️ Back to Bot Manager", callback_data="settings#bots")]]
        if ok:
            await bot.send_message(
                user_id,
                "<blockquote><b>✅ Userbot session successfully added to database!</b></blockquote>",
                reply_markup=InlineKeyboardMarkup(btns),
            )
        else:
            await bot.send_message(
                user_id,
                "<blockquote><b>↩️ Return to Bot Manager:</b></blockquote>",
                reply_markup=InlineKeyboardMarkup(btns),
            )

    elif type.startswith("editbot"):
        bot_id = int(type.split("_")[1]) if "_" in type else None
        _bot = await db.get_bot(user_id, bot_id)
        if not _bot:
            return await render_bot_manager(query, user_id)
        buttons = [
            [InlineKeyboardButton("🗑 Remove This Bot", callback_data=f"settings#removebot_{_bot['id']}")],
            [InlineKeyboardButton("⬅️ Back to Bot Manager", callback_data="settings#bots")],
        ]
        await query.message.edit_text(
            Script.BOT_DETAILS.format(_bot["name"], _bot["id"], _bot.get("username", "")),
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    elif type == "edituserbot":
        _ubot = await db.get_userbot(user_id)
        if not _ubot:
            return await render_bot_manager(query, user_id)
        buttons = [
            [InlineKeyboardButton("🗑 Remove Userbot", callback_data="settings#removeuserbot")],
            [InlineKeyboardButton("⬅️ Back to Bot Manager", callback_data="settings#bots")],
        ]
        await query.message.edit_text(
            Script.USER_DETAILS.format(_ubot["name"], _ubot["id"], _ubot.get("username", "")),
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    elif type.startswith("removebot"):
        bot_id = int(type.split("_")[1]) if "_" in type else None
        await db.remove_bot(user_id, bot_id)
        await query.answer("Worker bot removed from pool!")
        await render_bot_manager(query, user_id)

    elif type == "clearallbots":
        await db.remove_bot(user_id, None)
        await query.answer("All worker bots cleared from pool!")
        await render_bot_manager(query, user_id)

    elif type == "removeuserbot":
        await db.remove_userbot(user_id)
        await query.answer("Userbot session removed!")
        await render_bot_manager(query, user_id)

    # ------------------------------------------------------------------
    # 📢 TARGET CHANNELS MANAGER
    # ------------------------------------------------------------------
    elif type == "channels":
        await render_channels_menu(query, user_id)

    elif type == "addchannel":
        await query.message.delete()
        back_ch_btn = [[InlineKeyboardButton("⬅️ Back to Channels", callback_data="settings#channels")]]
        chat_ids = await bot.ask(
            chat_id=user_id,
            text=(
                "<blockquote><b>📢 ADD TARGET CHANNEL</b></blockquote>\n\n"
                "<blockquote>Forward any message from your target channel, OR send its <code>-100...</code> chat ID / <code>@username</code>.\n\n"
                "• Make sure your worker bot(s) or Userbot are <b>Admin</b> in that channel.</blockquote>\n\n"
                "<i>Send /cancel to abort.</i>"
            ),
        )
        if not chat_ids.text and not chat_ids.forward_from_chat:
            return await chat_ids.reply_text(
                "<blockquote><b>❌ Invalid input provided.</b></blockquote>",
                reply_markup=InlineKeyboardMarkup(back_ch_btn),
            )
        if chat_ids.text and chat_ids.text.strip().lower() == "/cancel":
            return await chat_ids.reply_text(
                "<blockquote><b>🚫 Process cancelled.</b></blockquote>",
                reply_markup=InlineKeyboardMarkup(back_ch_btn),
            )

        if chat_ids.forward_date and chat_ids.forward_from_chat:
            chat_id = chat_ids.forward_from_chat.id
            title = chat_ids.forward_from_chat.title
            username = "@" + chat_ids.forward_from_chat.username if chat_ids.forward_from_chat.username else "private"
        elif chat_ids.text:
            raw = chat_ids.text.strip()
            try:
                target_lookup = int(raw) if (raw.startswith("-") or raw.isdigit()) else raw
                chat_obj = await bot.get_chat(target_lookup)
                chat_id = chat_obj.id
                title = chat_obj.title or str(chat_id)
                username = "@" + chat_obj.username if chat_obj.username else "private"
            except Exception:
                return await chat_ids.reply_text(
                    "<blockquote><b>❌ Could not resolve chat. Please forward a message directly from the target channel.</b></blockquote>",
                    reply_markup=InlineKeyboardMarkup(back_ch_btn),
                )
        else:
            return await chat_ids.reply_text(
                "<blockquote><b>❌ Please forward a message from your target channel.</b></blockquote>",
                reply_markup=InlineKeyboardMarkup(back_ch_btn),
            )

        added = await db.add_channel(user_id, chat_id, title, username)
        await chat_ids.reply_text(
            f"<blockquote><b>✅ Channel <code>{title}</code> added successfully!</b></blockquote>"
            if added
            else "<blockquote><b>ℹ️ This channel is already in your target list.</b></blockquote>",
            reply_markup=InlineKeyboardMarkup(back_ch_btn),
        )

    elif type.startswith("editchannels"):
        chat_id = type.split("_")[1]
        chat = await db.get_channel_details(user_id, chat_id)
        if not chat:
            return await render_channels_menu(query, user_id)
        buttons = [
            [InlineKeyboardButton("🗑 Remove Channel", callback_data=f"settings#removechannel_{chat_id}")],
            [InlineKeyboardButton("⬅️ Back to Channels", callback_data="settings#channels")],
        ]
        await query.message.edit_text(
            "<blockquote><b>📢 TARGET CHANNEL DETAILS</b></blockquote>\n\n"
            "<blockquote>"
            f"┌ <b>🏷 Title:</b> <code>{chat['title']}</code>\n"
            f"├ <b>🆔 Chat ID:</b> <code>{chat['chat_id']}</code>\n"
            f"└ <b>🔗 Username:</b> {chat['username']}"
            "</blockquote>",
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    elif type.startswith("removechannel"):
        chat_id = type.split("_")[1]
        await db.remove_channel(user_id, chat_id)
        await query.answer("Target channel removed!")
        await render_channels_menu(query, user_id)

    # ------------------------------------------------------------------
    # 📝 SMART CAPTION ENGINE (Template + Prefix + Suffix)
    # ------------------------------------------------------------------
    elif type == "caption":
        await render_caption_menu(query, user_id)

    elif type == "seecaption":
        data = await get_configs(user_id)
        buttons = [
            [InlineKeyboardButton("✏️ Edit Template", callback_data="settings#addcaption")],
            [InlineKeyboardButton("⬅️ Back to Smart Caption", callback_data="settings#caption")],
        ]
        await query.message.edit_text(
            "<blockquote><b>📝 SMART CAPTION CONFIGURATION</b></blockquote>\n\n"
            f"<blockquote><b>🔼 Prefix Block:</b>\n<code>{data.get('prefix') or 'None'}</code></blockquote>\n"
            f"<blockquote><b>📄 Caption Template:</b>\n<code>{data.get('caption') or '{caption} (Default)'}</code></blockquote>\n"
            f"<blockquote><b>🔽 Suffix Block:</b>\n<code>{data.get('suffix') or 'None'}</code></blockquote>",
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    elif type == "deletecaption":
        await update_configs(user_id, "caption", None)
        await query.answer("Custom caption template removed!")
        await render_caption_menu(query, user_id)

    elif type == "addcaption":
        await query.message.delete()
        back_cap = [[InlineKeyboardButton("⬅️ Back to Smart Caption", callback_data="settings#caption")]]
        ask = await bot.ask(
            query.message.chat.id,
            "<blockquote><b>📝 SET SMART CAPTION TEMPLATE</b></blockquote>\n\n"
            "<blockquote>Send your custom caption template using any of these placeholders:\n"
            "• <code>{filename}</code> — Media file name\n"
            "• <code>{size}</code> — Formatted file size\n"
            "• <code>{caption}</code> — Original (cleaned) caption</blockquote>\n\n"
            "<blockquote><b>💡 Example:</b>\n"
            "<code>📁 {filename}\n💾 Size: {size}\n\n{caption}</code></blockquote>\n\n"
            "<i>Send /cancel to abort.</i>",
        )
        if not ask.text or ask.text.strip().lower() == "/cancel":
            return await ask.reply_text("<blockquote><b>🚫 Cancelled.</b></blockquote>", reply_markup=InlineKeyboardMarkup(back_cap))
        await update_configs(user_id, "caption", ask.text.html)
        await ask.reply_text(
            "<blockquote><b>✅ Smart caption template saved!</b></blockquote>",
            reply_markup=InlineKeyboardMarkup(back_cap),
        )

    elif type == "addprefix":
        await query.message.delete()
        back_cap = [[InlineKeyboardButton("⬅️ Back to Smart Caption", callback_data="settings#caption")]]
        ask = await bot.ask(
            query.message.chat.id,
            "<blockquote><b>🔼 SET CUSTOM PREFIX BLOCK</b></blockquote>\n\n"
            "<blockquote>Send the text/HTML block you want prepended to the top of every forwarded message or caption.</blockquote>\n\n"
            "<i>Send /cancel to abort.</i>",
        )
        if not ask.text or ask.text.strip().lower() == "/cancel":
            return await ask.reply_text("<blockquote><b>🚫 Cancelled.</b></blockquote>", reply_markup=InlineKeyboardMarkup(back_cap))
        await update_configs(user_id, "prefix", ask.text.html)
        await ask.reply_text("<blockquote><b>✅ Custom Prefix saved!</b></blockquote>", reply_markup=InlineKeyboardMarkup(back_cap))

    elif type == "delprefix":
        await update_configs(user_id, "prefix", None)
        await query.answer("Prefix cleared!")
        await render_caption_menu(query, user_id)

    elif type == "addsuffix":
        await query.message.delete()
        back_cap = [[InlineKeyboardButton("⬅️ Back to Smart Caption", callback_data="settings#caption")]]
        ask = await bot.ask(
            query.message.chat.id,
            "<blockquote><b>🔽 SET CUSTOM SUFFIX BLOCK</b></blockquote>\n\n"
            "<blockquote>Send the text/HTML block you want appended to the bottom of every forwarded message or caption.</blockquote>\n\n"
            "<i>Send /cancel to abort.</i>",
        )
        if not ask.text or ask.text.strip().lower() == "/cancel":
            return await ask.reply_text("<blockquote><b>🚫 Cancelled.</b></blockquote>", reply_markup=InlineKeyboardMarkup(back_cap))
        await update_configs(user_id, "suffix", ask.text.html)
        await ask.reply_text("<blockquote><b>✅ Custom Suffix saved!</b></blockquote>", reply_markup=InlineKeyboardMarkup(back_cap))

    elif type == "delsuffix":
        await update_configs(user_id, "suffix", None)
        await query.answer("Suffix cleared!")
        await render_caption_menu(query, user_id)

    # ------------------------------------------------------------------
    # 🧹 1-CLICK AUTO-CLEANERS & CUSTOM WORD REPLACER
    # ------------------------------------------------------------------
    elif type == "cleaners":
        await render_cleaners_menu(query, user_id)

    elif type.startswith("togglecleaner_"):
        ckey = type.split("togglecleaner_")[1]
        configs = await get_configs(user_id)
        cur_val = bool((configs.get("cleaners") or {}).get(ckey, False))
        await update_configs(user_id, ckey, not cur_val)
        await query.answer(f"Cleaner {ckey}: {'ENABLED ✅' if not cur_val else 'DISABLED ❌'}")
        await render_cleaners_menu(query, user_id)

    elif type == "words":
        await render_words_menu(query, user_id)

    elif type == "addwords":
        await query.message.delete()
        back_w = [[InlineKeyboardButton("⬅️ Back to Word Replacer", callback_data="settings#words")]]
        ask = await bot.ask(
            user_id,
            "<blockquote><b>🔤 ADD WORD REPLACE / REMOVE RULES</b></blockquote>\n\n"
            "<blockquote>Send one or more rules (one rule per line):\n"
            "• <b>Replace word:</b> <code>old_word : new_word</code> (or <code>old_word -> new_word</code>)\n"
            "• <b>Remove word:</b> just send <code>word_to_remove</code></blockquote>\n\n"
            "<blockquote><b>💡 Example:</b>\n"
            "<code>@OldChannel : @MyChannel\n"
            "Downloaded from XYZ\n"
            "1080p : 1080p Full HD</code></blockquote>\n\n"
            "<i>Send /cancel to abort.</i>",
        )
        if not ask.text or ask.text.strip().lower() == "/cancel":
            return await ask.reply_text("<blockquote><b>🚫 Cancelled.</b></blockquote>", reply_markup=InlineKeyboardMarkup(back_w))

        configs = await get_configs(user_id)
        replacements = dict(configs.get("replacements") or {})
        for line in ask.text.splitlines():
            line = line.strip()
            if not line:
                continue
            if "->" in line:
                old_w, new_w = line.split("->", 1)
                replacements[old_w.strip()] = new_w.strip()
            elif ":" in line:
                old_w, new_w = line.split(":", 1)
                replacements[old_w.strip()] = new_w.strip()
            else:
                replacements[line] = ""

        await update_configs(user_id, "replacements", replacements)
        await ask.reply_text(
            f"<blockquote><b>✅ Saved! ({len(replacements)} active word rule(s))</b></blockquote>",
            reply_markup=InlineKeyboardMarkup(back_w),
        )

    elif type == "clearwords":
        await update_configs(user_id, "replacements", {})
        await query.answer("All custom word rules cleared!")
        await render_words_menu(query, user_id)

    # ------------------------------------------------------------------
    # 🔘 CUSTOM INLINE BUTTONS
    # ------------------------------------------------------------------
    elif type == "button":
        buttons = []
        button = (await get_configs(user_id))["button"]
        if button is None:
            buttons.append([InlineKeyboardButton("➕ Add Custom Button", callback_data="settings#addbutton")])
        else:
            buttons.append(
                [
                    InlineKeyboardButton("👀 Preview Button", callback_data="settings#seebutton"),
                    InlineKeyboardButton("🗑 Remove Button", callback_data="settings#deletebutton"),
                ]
            )
        buttons.append([InlineKeyboardButton("⬅️ Back to Settings", callback_data="settings#main")])
        await query.message.edit_text(
            "<blockquote><b>🔘 CUSTOM INLINE BUTTON</b></blockquote>\n\n"
            "<blockquote>Attach custom URL buttons below every forwarded message.\n\n"
            "<b>Syntax:</b>\n"
            "<code>[Button Text][buttonurl:https://t.me/yourchannel]</code>\n"
            "• Append <code>:same</code> to place two buttons on the same row.</blockquote>",
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    elif type == "addbutton":
        await query.message.delete()
        back_b = [[InlineKeyboardButton("⬅️ Back to Buttons", callback_data="settings#button")]]
        ask = await bot.ask(
            user_id,
            text=(
                "<blockquote><b>🔘 SEND CUSTOM BUTTON MARKUP</b></blockquote>\n\n"
                "<blockquote><b>Example:</b>\n"
                "<code>[Join Channel][buttonurl:https://t.me/vj_botz]</code>\n"
                "<code>[Support][buttonurl:https://t.me/vj_bot_disscussion:same]</code></blockquote>\n\n"
                "<i>Send /cancel to abort.</i>"
            ),
        )
        if not ask.text or ask.text.strip().lower() == "/cancel":
            return await ask.reply("<blockquote><b>🚫 Cancelled.</b></blockquote>", reply_markup=InlineKeyboardMarkup(back_b))
        button = parse_buttons(ask.text.html)
        if not button:
            return await ask.reply(
                "<blockquote><b>❌ Invalid button format! Please follow the example syntax.</b></blockquote>",
                reply_markup=InlineKeyboardMarkup(back_b),
            )
        await update_configs(user_id, "button", ask.text.html)
        await ask.reply(
            "<blockquote><b>✅ Custom inline button saved!</b></blockquote>",
            reply_markup=InlineKeyboardMarkup(back_b),
        )

    elif type == "seebutton":
        button = (await get_configs(user_id))["button"]
        button = parse_buttons(button, markup=False) or []
        button.append([InlineKeyboardButton("⬅️ Back", callback_data="settings#button")])
        await query.message.edit_text(
            "<blockquote><b>👀 YOUR CUSTOM INLINE BUTTON PREVIEW</b></blockquote>",
            reply_markup=InlineKeyboardMarkup(button),
        )

    elif type == "deletebutton":
        await update_configs(user_id, "button", None)
        await query.message.edit_text(
            "<blockquote><b>✅ Custom button removed.</b></blockquote>",
            reply_markup=InlineKeyboardMarkup(back_main_btn),
        )

    # ------------------------------------------------------------------
    # 🗄 MONGODB PERSISTENT DEDUPLICATION
    # ------------------------------------------------------------------
    elif type == "database":
        buttons = []
        db_uri = (await get_configs(user_id))["db_uri"]
        if db_uri is None:
            buttons.append([InlineKeyboardButton("➕ Add External MongoDB URI", callback_data="settings#addurl")])
        else:
            buttons.append(
                [
                    InlineKeyboardButton("👀 View URI", callback_data="settings#seeurl"),
                    InlineKeyboardButton("🗑 Remove URI", callback_data="settings#deleteurl"),
                ]
            )
        buttons.append([InlineKeyboardButton("🧹 Clear Deduplication Cache", callback_data="settings#cleardupcache")])
        buttons.append([InlineKeyboardButton("⬅️ Back to Settings", callback_data="settings#main")])
        await query.message.edit_text(
            "<blockquote><b>🗄 PERSISTENT DEDUPLICATION DATABASE</b></blockquote>\n\n"
            "<blockquote>• Unpacked media file IDs are automatically deduplicated in memory and in the bot's built-in MongoDB store.\n"
            "• You can also link a custom <b>MongoDB URI</b> or clear your saved deduplication history below.</blockquote>",
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    elif type == "cleardupcache":
        await db.clear_dup_files(user_id)
        await query.answer("✅ Persistent deduplication cache cleared!", show_alert=True)

    elif type == "addurl":
        await query.message.delete()
        uri = await bot.ask(
            user_id,
            "<blockquote><b>🗄 ADD EXTERNAL MONGODB URI</b></blockquote>\n\n"
            "<blockquote>Send your MongoDB connection string (<code>mongodb+srv://...</code>).\n"
            "• Get a free cluster at <a href='https://mongodb.com'>mongodb.com</a>.</blockquote>\n\n"
            "<i>Send /cancel to abort.</i>",
            disable_web_page_preview=True,
        )
        if not uri.text or uri.text.strip().lower() == "/cancel":
            return await uri.reply_text("<blockquote><b>🚫 Cancelled.</b></blockquote>", reply_markup=InlineKeyboardMarkup(back_main_btn))
        if not uri.text.startswith(("mongodb+srv://", "mongodb://")):
            return await uri.reply("<blockquote><b>❌ Invalid MongoDB URI format.</b></blockquote>", reply_markup=InlineKeyboardMarkup(back_main_btn))
        connect, udb = await connect_user_db(user_id, uri.text.strip(), "test")
        if connect:
            await udb.drop_all()
            await udb.close()
        else:
            return await uri.reply(
                "<blockquote><b>❌ Could not connect to this MongoDB URI. Check your credentials & IP allowlist.</b></blockquote>",
                reply_markup=InlineKeyboardMarkup(back_main_btn),
            )
        await update_configs(user_id, "db_uri", uri.text.strip())
        await uri.reply("<blockquote><b>✅ MongoDB URI verified and saved!</b></blockquote>", reply_markup=InlineKeyboardMarkup(back_main_btn))

    elif type == "seeurl":
        db_uri = (await get_configs(user_id))["db_uri"]
        await query.answer(f"MongoDB URI:\n{db_uri}", show_alert=True)

    elif type == "deleteurl":
        await update_configs(user_id, "db_uri", None)
        await query.message.edit_text(
            "<blockquote><b>✅ External MongoDB URI removed.</b></blockquote>",
            reply_markup=InlineKeyboardMarkup(back_main_btn),
        )

    # ------------------------------------------------------------------
    # 🔍 GRANULAR MEDIA & MESSAGE TYPE FILTERS
    # ------------------------------------------------------------------
    elif type == "filters":
        await query.message.edit_text(
            "<blockquote><b>🔍 GRANULAR MEDIA & MESSAGE FILTERS (1/2)</b></blockquote>\n\n"
            "<blockquote>Toggle which message types and forwarding options should be forwarded (✅) or skipped (❌):</blockquote>",
            reply_markup=await filters_buttons(user_id),
        )

    elif type == "nextfilters":
        await query.message.edit_text(
            "<blockquote><b>🔍 GRANULAR MEDIA & MESSAGE FILTERS (2/2)</b></blockquote>\n\n"
            "<blockquote>Toggle voice notes, animations, stickers, polls, duplicate skipping, and content protection:</blockquote>",
            reply_markup=await next_filters_buttons(user_id),
        )

    elif type.startswith("updatefilter"):
        _, key, value = type.split("-")
        new_val = False if value == "True" else True
        await update_configs(user_id, key, new_val)
        if key in ["poll", "protect", "voice", "animation", "sticker", "duplicate"]:
            return await query.edit_message_reply_markup(reply_markup=await next_filters_buttons(user_id))
        await query.edit_message_reply_markup(reply_markup=await filters_buttons(user_id))

    # ------------------------------------------------------------------
    # 📏 MIN / MAX FILE SIZE LIMITS (MB)
    # ------------------------------------------------------------------
    elif type.startswith("file_size"):
        settings_cfg = await get_configs(user_id)
        size = settings_cfg.get("min_size", 0)
        await query.message.edit_text(
            "<blockquote><b>📉 MINIMUM FILE SIZE LIMIT</b></blockquote>\n\n"
            f"<blockquote>• <b>Current Minimum:</b> <code>{size} MB</code>\n"
            f"• Media files smaller than <code>{size} MB</code> will be skipped.</blockquote>",
            reply_markup=size_button(size),
        )

    elif type.startswith("maxfile_size"):
        settings_cfg = await get_configs(user_id)
        size = settings_cfg.get("max_size", 0)
        await query.message.edit_text(
            "<blockquote><b>📈 MAXIMUM FILE SIZE LIMIT</b></blockquote>\n\n"
            f"<blockquote>• <b>Current Maximum:</b> <code>{size if size > 0 else '0 (Unlimited)'} MB</code>\n"
            f"• Media files larger than <code>{size} MB</code> will be skipped (0 = no max limit).</blockquote>",
            reply_markup=maxsize_button(size),
        )

    elif type.startswith("update_size"):
        size = int(type.split("_size_")[1])
        size = max(0, min(4000, size))
        await update_configs(user_id, "min_size", size)
        await query.message.edit_text(
            "<blockquote><b>📉 MINIMUM FILE SIZE LIMIT</b></blockquote>\n\n"
            f"<blockquote>• <b>Current Minimum:</b> <code>{size} MB</code>\n"
            f"• Media files smaller than <code>{size} MB</code> will be skipped.</blockquote>",
            reply_markup=size_button(size),
        )

    elif type.startswith("maxupdate_size"):
        size = int(type.split("_size_")[1])
        size = max(0, min(4000, size))
        await update_configs(user_id, "max_size", size)
        await query.message.edit_text(
            "<blockquote><b>📈 MAXIMUM FILE SIZE LIMIT</b></blockquote>\n\n"
            f"<blockquote>• <b>Current Maximum:</b> <code>{size if size > 0 else '0 (Unlimited)'} MB</code>\n"
            f"• Media files larger than <code>{size} MB</code> will be skipped (0 = no max limit).</blockquote>",
            reply_markup=maxsize_button(size),
        )

    elif type in ("custom_min_size", "custom_max_size"):
        is_min = type == "custom_min_size"
        await query.message.delete()
        back_sz = [[InlineKeyboardButton("⬅️ Back", callback_data="settings#file_size" if is_min else "settings#maxfile_size")]]
        ask = await bot.ask(
            user_id,
            f"<blockquote><b>✏️ SET {'MINIMUM' if is_min else 'MAXIMUM'} FILE SIZE (MB)</b></blockquote>\n\n"
            "<blockquote>Enter a number between <code>0</code> and <code>4000</code> MB (0 disables the limit).</blockquote>\n\n"
            "<i>Send /cancel to abort.</i>",
        )
        if not ask.text or ask.text.strip().lower() == "/cancel":
            return await ask.reply("<blockquote><b>🚫 Cancelled.</b></blockquote>", reply_markup=InlineKeyboardMarkup(back_sz))
        if not ask.text.strip().isdigit():
            return await ask.reply("<blockquote><b>❌ Please enter a valid integer in MB.</b></blockquote>", reply_markup=InlineKeyboardMarkup(back_sz))
        val = max(0, min(4000, int(ask.text.strip())))
        await update_configs(user_id, "min_size" if is_min else "max_size", val)
        await ask.reply(
            f"<blockquote><b>✅ {'Minimum' if is_min else 'Maximum'} file size set to <code>{val} MB</code>!</b></blockquote>",
            reply_markup=InlineKeyboardMarkup(back_sz),
        )

    # ------------------------------------------------------------------
    # 🚫 EXTENSION BLOCKLIST & 🏷 KEYWORD ALLOWLIST
    # ------------------------------------------------------------------
    elif type == "add_extension":
        await query.message.delete()
        back_ext = [[InlineKeyboardButton("⬅️ Back to Extensions", callback_data="settings#get_extension")]]
        ext = await bot.ask(
            user_id,
            text=(
                "<blockquote><b>🚫 ADD BLOCKLIST FILE EXTENSIONS</b></blockquote>\n\n"
                "<blockquote>Send extensions separated by spaces or commas (e.g. <code>apk exe zip rar</code>).\n"
                "• Any file matching these extensions will be skipped.</blockquote>\n\n"
                "<i>Send /cancel to abort.</i>"
            ),
        )
        if not ext.text or ext.text.strip().lower() == "/cancel":
            return await ext.reply_text("<blockquote><b>🚫 Cancelled.</b></blockquote>", reply_markup=InlineKeyboardMarkup(back_ext))

        raw_tokens = [t.strip().lstrip(".").lower() for t in ext.text.replace(",", " ").split() if t.strip()]
        existing = (await get_configs(user_id)).get("extension") or []
        merged = list(dict.fromkeys(existing + raw_tokens))
        await update_configs(user_id, "extension", merged)
        await ext.reply_text(
            f"<blockquote><b>✅ Blocklist updated ({len(merged)} extension(s) blocked).</b></blockquote>",
            reply_markup=InlineKeyboardMarkup(back_ext),
        )

    elif type == "get_extension":
        extensions = (await get_configs(user_id)).get("extension")
        if extensions:
            ext_list = ", ".join(f"<code>.{e.lstrip('.')}</code>" for e in extensions)
            body = f"<b>🚫 Blocked Extensions:</b>\n{ext_list}"
        else:
            body = "<i>No extensions are currently blocked.</i>"
        btn = [
            [
                InlineKeyboardButton("➕ Add Extensions", callback_data="settings#add_extension"),
                InlineKeyboardButton("🗑 Clear All", callback_data="settings#rmve_all_extension"),
            ],
            [InlineKeyboardButton("⬅️ Back", callback_data="settings#extra")],
        ]
        await query.message.edit_text(
            text=(
                "<blockquote><b>🚫 EXTENSION BLOCKLIST</b></blockquote>\n\n"
                f"<blockquote>Files with these extensions will NOT be forwarded:\n\n{body}</blockquote>"
            ),
            reply_markup=InlineKeyboardMarkup(btn),
        )

    elif type == "rmve_all_extension":
        await update_configs(user_id, "extension", None)
        await query.answer("Cleared all blocked extensions!")
        await settings_query(bot, type_override(query, "settings#get_extension"))

    elif type == "add_keyword":
        await query.message.delete()
        back_kw = [[InlineKeyboardButton("⬅️ Back to Keywords", callback_data="settings#get_keyword")]]
        ask = await bot.ask(
            user_id,
            text=(
                "<blockquote><b>🏷 ADD ALLOWLIST KEYWORDS</b></blockquote>\n\n"
                "<blockquote>Send keywords separated by spaces or commas (e.g. <code>1080p HEVC Dual</code>).\n"
                "• When active, ONLY messages/files containing at least one keyword will be forwarded.</blockquote>\n\n"
                "<i>Send /cancel to abort.</i>"
            ),
        )
        if not ask.text or ask.text.strip().lower() == "/cancel":
            return await ask.reply_text("<blockquote><b>🚫 Cancelled.</b></blockquote>", reply_markup=InlineKeyboardMarkup(back_kw))

        new_kws = [k.strip() for k in ask.text.replace(",", " ").split() if k.strip()]
        existing = (await get_configs(user_id)).get("keywords") or []
        merged = list(dict.fromkeys(existing + new_kws))
        await update_configs(user_id, "keywords", merged)
        await ask.reply_text(
            f"<blockquote><b>✅ Keyword allowlist updated ({len(merged)} keyword(s) active).</b></blockquote>",
            reply_markup=InlineKeyboardMarkup(back_kw),
        )

    elif type == "get_keyword":
        keywords = (await get_configs(user_id)).get("keywords")
        if keywords:
            kw_list = ", ".join(f"<code>{k}</code>" for k in keywords)
            body = f"<b>🏷 Active Keywords:</b>\n{kw_list}"
        else:
            body = "<i>No keyword filter active (all files allowed).</i>"
        btn = [
            [
                InlineKeyboardButton("➕ Add Keywords", callback_data="settings#add_keyword"),
                InlineKeyboardButton("🗑 Clear All", callback_data="settings#rmve_all_keyword"),
            ],
            [InlineKeyboardButton("⬅️ Back", callback_data="settings#extra")],
        ]
        await query.message.edit_text(
            text=(
                "<blockquote><b>🏷 KEYWORD ALLOWLIST</b></blockquote>\n\n"
                f"<blockquote>Only files/messages matching these keywords will be forwarded:\n\n{body}</blockquote>"
            ),
            reply_markup=InlineKeyboardMarkup(btn),
        )

    elif type == "rmve_all_keyword":
        await update_configs(user_id, "keywords", None)
        await query.answer("Cleared all allowlist keywords!")
        await settings_query(bot, type_override(query, "settings#get_keyword"))

    elif type.startswith("alert"):
        alert = type.split("_", 1)[1]
        await query.answer(alert, show_alert=True)


def type_override(query, new_data: str):
    query.data = new_data
    return query


# ------------------------------------------------------------------
# SUB-MENU RENDERERS
# ------------------------------------------------------------------
async def render_bot_manager(query, user_id: int):
    bots = await db.get_bots(user_id)
    usr_bot = await db.get_userbot(user_id)
    configs = await get_configs(user_id)
    mode = configs.get("forward_mode", "pool")

    n_bots = len(bots)
    delay = compute_pool_delay(n_bots)
    capacity = n_bots * 20

    buttons = []
    row = []
    for idx, b in enumerate(bots, start=1):
        row.append(
            InlineKeyboardButton(
                f"🤖 #{idx} {b['name']}",
                callback_data=f"settings#editbot_{b['id']}",
            )
        )
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    action_row = [InlineKeyboardButton("➕ Add Worker Bot(s)", callback_data="settings#addbot")]
    if n_bots > 0:
        action_row.append(InlineKeyboardButton("🗑 Clear Pool", callback_data="settings#clearallbots"))
    buttons.append(action_row)

    if usr_bot is not None:
        buttons.append(
            [InlineKeyboardButton(f"👤 Userbot: {usr_bot['name']}", callback_data="settings#edituserbot")]
        )
    else:
        buttons.append([InlineKeyboardButton("➕ Add Userbot Session", callback_data="settings#adduserbot")])

    mode_text = "🤖 Multi-Bot Pool" if mode == "pool" else "👤 Userbot Session"
    buttons.append(
        [InlineKeyboardButton(f"🔄 Default Mode: {mode_text}", callback_data="settings#toggle_default_mode")]
    )
    buttons.append([InlineKeyboardButton("⬅️ Back to Settings", callback_data="settings#main")])

    text = (
        "<blockquote><b>🤖 BOT MANAGER & ROUND-ROBIN POOL</b></blockquote>\n\n"
        "<blockquote>"
        f"┌ <b>🤖 Worker Bots in Pool:</b> <code>{n_bots} Bot(s)</code>\n"
        f"├ <b>⚡ Pool Rate Capacity:</b> <code>{capacity} msgs/min</code> (20/min each)\n"
        f"├ <b>⏱ Auto-Adjusted Delay:</b> <code>{delay}s</code> <i>(1=3.0s, 2=1.5s, 3=1.0s, 6=0.5s)</i>\n"
        f"├ <b>👤 Userbot Session:</b> <code>{'Connected (@' + str(usr_bot.get('username')) + ')' if usr_bot else 'Not Connected'}</code>\n"
        f"└ <b>🎯 Default Mode:</b> <code>{mode_text}</code>"
        "</blockquote>\n\n"
        "<i>💡 Tip: Tap <b>➕ Add Worker Bot(s)</b> to paste multiple bot tokens at once!</i>"
    )
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))


async def render_channels_menu(query, user_id: int):
    buttons = []
    channels = await db.get_user_channels(user_id)
    for channel in channels:
        buttons.append(
            [
                InlineKeyboardButton(
                    f"📢 {channel['title']}",
                    callback_data=f"settings#editchannels_{channel['chat_id']}",
                )
            ]
        )
    buttons.append([InlineKeyboardButton("➕ Add Target Channel", callback_data="settings#addchannel")])
    buttons.append([InlineKeyboardButton("⬅️ Back to Settings", callback_data="settings#main")])
    await query.message.edit_text(
        f"<blockquote><b>📢 TARGET CHANNELS ({len(channels)})</b></blockquote>\n\n"
        "<blockquote>Manage destination channels where messages will be forwarded. Make sure your bots/userbot are Admin in each channel.</blockquote>",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def render_caption_menu(query, user_id: int):
    data = await get_configs(user_id)
    caption = data.get("caption")
    prefix = data.get("prefix")
    suffix = data.get("suffix")

    buttons = []
    if caption is None:
        buttons.append([InlineKeyboardButton("➕ Set Caption Template", callback_data="settings#addcaption")])
    else:
        buttons.append(
            [
                InlineKeyboardButton("👀 View / Edit Template", callback_data="settings#seecaption"),
                InlineKeyboardButton("🗑 Clear Template", callback_data="settings#deletecaption"),
            ]
        )

    pref_row = [
        InlineKeyboardButton("🔼 Set Prefix" if not prefix else "🔼 Edit Prefix", callback_data="settings#addprefix")
    ]
    if prefix:
        pref_row.append(InlineKeyboardButton("🗑 Clear Prefix", callback_data="settings#delprefix"))
    buttons.append(pref_row)

    suff_row = [
        InlineKeyboardButton("🔽 Set Suffix" if not suffix else "🔽 Edit Suffix", callback_data="settings#addsuffix")
    ]
    if suffix:
        suff_row.append(InlineKeyboardButton("🗑 Clear Suffix", callback_data="settings#delsuffix"))
    buttons.append(suff_row)

    buttons.append([InlineKeyboardButton("⬅️ Back to Settings", callback_data="settings#main")])

    await query.message.edit_text(
        "<blockquote><b>📝 SMART CAPTION ENGINE</b></blockquote>\n\n"
        "<blockquote><b>Available Placeholders:</b>\n"
        "• <code>{filename}</code> — File Name\n"
        "• <code>{size}</code> — File Size\n"
        "• <code>{caption}</code> — Original (Cleaned) Caption</blockquote>\n\n"
        "<blockquote>"
        f"┌ <b>📄 Template:</b> <code>{'Custom Set ✅' if caption else 'Default'}</code>\n"
        f"├ <b>🔼 Prefix Block:</b> <code>{'Active ✅' if prefix else 'None'}</code>\n"
        f"└ <b>🔽 Suffix Block:</b> <code>{'Active ✅' if suffix else 'None'}</code>"
        "</blockquote>",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def render_cleaners_menu(query, user_id: int):
    configs = await get_configs(user_id)
    cleaners = configs.get("cleaners") or {}
    replacements = configs.get("replacements") or {}

    u_on = cleaners.get("username", False)
    t_on = cleaners.get("tme", False)
    w_on = cleaners.get("url", False)
    h_on = cleaners.get("html_links", False)

    buttons = [
        [
            InlineKeyboardButton("🏷 Strip @Usernames", callback_data="settings#togglecleaner_username"),
            InlineKeyboardButton("✅ ON" if u_on else "❌ OFF", callback_data="settings#togglecleaner_username"),
        ],
        [
            InlineKeyboardButton("🔗 Strip t.me Links", callback_data="settings#togglecleaner_tme"),
            InlineKeyboardButton("✅ ON" if t_on else "❌ OFF", callback_data="settings#togglecleaner_tme"),
        ],
        [
            InlineKeyboardButton("🌐 Strip Web URLs", callback_data="settings#togglecleaner_url"),
            InlineKeyboardButton("✅ ON" if w_on else "❌ OFF", callback_data="settings#togglecleaner_url"),
        ],
        [
            InlineKeyboardButton("⚓ Strip HTML <a> Tags", callback_data="settings#togglecleaner_html_links"),
            InlineKeyboardButton("✅ ON" if h_on else "❌ OFF", callback_data="settings#togglecleaner_html_links"),
        ],
        [
            InlineKeyboardButton(
                f"🔤 Word Replacer / Remover ({len(replacements)} rules)",
                callback_data="settings#words",
            )
        ],
        [InlineKeyboardButton("⬅️ Back to Settings", callback_data="settings#main")],
    ]
    await query.message.edit_text(
        "<blockquote><b>🧹 1-CLICK AUTO-CLEANERS & WORD REPLACER</b></blockquote>\n\n"
        "<blockquote>Automatically strip unwanted mentions, promotional links, HTML anchor tags, "
        "or replace/remove custom words from captions and filenames:</blockquote>",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def render_words_menu(query, user_id: int):
    configs = await get_configs(user_id)
    replacements = configs.get("replacements") or {}
    if replacements:
        lines = []
        for idx, (k, v) in enumerate(list(replacements.items())[:25], start=1):
            if v:
                lines.append(f"{idx}. <code>{k}</code> ➔ <code>{v}</code>")
            else:
                lines.append(f"{idx}. <code>{k}</code> ➔ <i>(Removed)</i>")
        rules_txt = "\n".join(lines)
    else:
        rules_txt = "<i>No custom word replacement or removal rules configured yet.</i>"

    buttons = [
        [
            InlineKeyboardButton("➕ Add Word Rules", callback_data="settings#addwords"),
            InlineKeyboardButton("🗑 Clear All", callback_data="settings#clearwords"),
        ],
        [InlineKeyboardButton("⬅️ Back to Auto-Cleaners", callback_data="settings#cleaners")],
    ]
    await query.message.edit_text(
        f"<blockquote><b>🔤 CUSTOM WORD REPLACER & REMOVER</b></blockquote>\n\n<blockquote>{rules_txt}</blockquote>",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


def main_buttons():
    buttons = [
        [
            InlineKeyboardButton("🤖 Bot Manager (Pool)", callback_data="settings#bots"),
            InlineKeyboardButton("📢 Target Channels", callback_data="settings#channels"),
        ],
        [
            InlineKeyboardButton("📝 Smart Caption", callback_data="settings#caption"),
            InlineKeyboardButton("🧹 Auto-Cleaners & Words", callback_data="settings#cleaners"),
        ],
        [
            InlineKeyboardButton("🔍 Media Filters", callback_data="settings#filters"),
            InlineKeyboardButton("📏 Size, Keywords & Ext", callback_data="settings#extra"),
        ],
        [
            InlineKeyboardButton("🔘 Custom Button", callback_data="settings#button"),
            InlineKeyboardButton("🗄 MongoDB Dedup", callback_data="settings#database"),
        ],
        [
            InlineKeyboardButton("⬅️ Back to Home", callback_data="back"),
        ],
    ]
    return InlineKeyboardMarkup(buttons)


def extra_buttons():
    buttons = [
        [
            InlineKeyboardButton("📉 Min Size Limit (MB)", callback_data="settings#file_size"),
            InlineKeyboardButton("📈 Max Size Limit (MB)", callback_data="settings#maxfile_size"),
        ],
        [
            InlineKeyboardButton("🏷 Keyword Allowlist", callback_data="settings#get_keyword"),
            InlineKeyboardButton("🚫 Extension Blocklist", callback_data="settings#get_extension"),
        ],
        [
            InlineKeyboardButton("⬅️ Back to Settings", callback_data="settings#main"),
        ],
    ]
    return InlineKeyboardMarkup(buttons)


def maxsize_button(size):
    size = int(size or 0)
    buttons = [
        [
            InlineKeyboardButton("-100", callback_data=f"settings#maxupdate_size_{max(0, size - 100)}"),
            InlineKeyboardButton("-50", callback_data=f"settings#maxupdate_size_{max(0, size - 50)}"),
            InlineKeyboardButton("-10", callback_data=f"settings#maxupdate_size_{max(0, size - 10)}"),
            InlineKeyboardButton("-1", callback_data=f"settings#maxupdate_size_{max(0, size - 1)}"),
        ],
        [
            InlineKeyboardButton("+1", callback_data=f"settings#maxupdate_size_{size + 1}"),
            InlineKeyboardButton("+10", callback_data=f"settings#maxupdate_size_{size + 10}"),
            InlineKeyboardButton("+50", callback_data=f"settings#maxupdate_size_{size + 50}"),
            InlineKeyboardButton("+100", callback_data=f"settings#maxupdate_size_{size + 100}"),
        ],
        [
            InlineKeyboardButton("✏️ Enter Custom MB", callback_data="settings#custom_max_size"),
            InlineKeyboardButton("🔄 Reset (0 MB)", callback_data="settings#maxupdate_size_0"),
        ],
        [InlineKeyboardButton("⬅️ Back", callback_data="settings#extra")],
    ]
    return InlineKeyboardMarkup(buttons)


def size_button(size):
    size = int(size or 0)
    buttons = [
        [
            InlineKeyboardButton("-100", callback_data=f"settings#update_size_{max(0, size - 100)}"),
            InlineKeyboardButton("-50", callback_data=f"settings#update_size_{max(0, size - 50)}"),
            InlineKeyboardButton("-10", callback_data=f"settings#update_size_{max(0, size - 10)}"),
            InlineKeyboardButton("-1", callback_data=f"settings#update_size_{max(0, size - 1)}"),
        ],
        [
            InlineKeyboardButton("+1", callback_data=f"settings#update_size_{size + 1}"),
            InlineKeyboardButton("+10", callback_data=f"settings#update_size_{size + 10}"),
            InlineKeyboardButton("+50", callback_data=f"settings#update_size_{size + 50}"),
            InlineKeyboardButton("+100", callback_data=f"settings#update_size_{size + 100}"),
        ],
        [
            InlineKeyboardButton("✏️ Enter Custom MB", callback_data="settings#custom_min_size"),
            InlineKeyboardButton("🔄 Reset (0 MB)", callback_data="settings#update_size_0"),
        ],
        [InlineKeyboardButton("⬅️ Back", callback_data="settings#extra")],
    ]
    return InlineKeyboardMarkup(buttons)


async def filters_buttons(user_id):
    cfg = await get_configs(user_id)
    f = cfg["filters"]
    buttons = [
        [
            InlineKeyboardButton("🏷️ Forward Tag", callback_data=f"settings#updatefilter-forward_tag-{cfg['forward_tag']}"),
            InlineKeyboardButton("✅ ON" if cfg["forward_tag"] else "❌ OFF", callback_data=f"settings#updatefilter-forward_tag-{cfg['forward_tag']}"),
        ],
        [
            InlineKeyboardButton("🖍️ Text Messages", callback_data=f"settings#updatefilter-text-{f['text']}"),
            InlineKeyboardButton("✅ ON" if f["text"] else "❌ OFF", callback_data=f"settings#updatefilter-text-{f['text']}"),
        ],
        [
            InlineKeyboardButton("📁 Documents", callback_data=f"settings#updatefilter-document-{f['document']}"),
            InlineKeyboardButton("✅ ON" if f["document"] else "❌ OFF", callback_data=f"settings#updatefilter-document-{f['document']}"),
        ],
        [
            InlineKeyboardButton("🎞️ Videos", callback_data=f"settings#updatefilter-video-{f['video']}"),
            InlineKeyboardButton("✅ ON" if f["video"] else "❌ OFF", callback_data=f"settings#updatefilter-video-{f['video']}"),
        ],
        [
            InlineKeyboardButton("📷 Photos", callback_data=f"settings#updatefilter-photo-{f['photo']}"),
            InlineKeyboardButton("✅ ON" if f["photo"] else "❌ OFF", callback_data=f"settings#updatefilter-photo-{f['photo']}"),
        ],
        [
            InlineKeyboardButton("🎧 Audio Files", callback_data=f"settings#updatefilter-audio-{f['audio']}"),
            InlineKeyboardButton("✅ ON" if f["audio"] else "❌ OFF", callback_data=f"settings#updatefilter-audio-{f['audio']}"),
        ],
        [
            InlineKeyboardButton("⬅️ Back", callback_data="settings#main"),
            InlineKeyboardButton("Page 2 ➡️", callback_data="settings#nextfilters"),
        ],
    ]
    return InlineKeyboardMarkup(buttons)


async def next_filters_buttons(user_id):
    cfg = await get_configs(user_id)
    f = cfg["filters"]
    buttons = [
        [
            InlineKeyboardButton("🎤 Voice Notes", callback_data=f"settings#updatefilter-voice-{f['voice']}"),
            InlineKeyboardButton("✅ ON" if f["voice"] else "❌ OFF", callback_data=f"settings#updatefilter-voice-{f['voice']}"),
        ],
        [
            InlineKeyboardButton("🎭 Animations / GIFs", callback_data=f"settings#updatefilter-animation-{f['animation']}"),
            InlineKeyboardButton("✅ ON" if f["animation"] else "❌ OFF", callback_data=f"settings#updatefilter-animation-{f['animation']}"),
        ],
        [
            InlineKeyboardButton("🃏 Stickers", callback_data=f"settings#updatefilter-sticker-{f['sticker']}"),
            InlineKeyboardButton("✅ ON" if f["sticker"] else "❌ OFF", callback_data=f"settings#updatefilter-sticker-{f['sticker']}"),
        ],
        [
            InlineKeyboardButton("📊 Polls", callback_data=f"settings#updatefilter-poll-{f['poll']}"),
            InlineKeyboardButton("✅ ON" if f["poll"] else "❌ OFF", callback_data=f"settings#updatefilter-poll-{f['poll']}"),
        ],
        [
            InlineKeyboardButton("♻️ Skip Duplicates", callback_data=f"settings#updatefilter-duplicate-{cfg['duplicate']}"),
            InlineKeyboardButton("✅ ON" if cfg["duplicate"] else "❌ OFF", callback_data=f"settings#updatefilter-duplicate-{cfg['duplicate']}"),
        ],
        [
            InlineKeyboardButton("🔒 Protect Content", callback_data=f"settings#updatefilter-protect-{cfg['protect']}"),
            InlineKeyboardButton("✅ ON" if cfg["protect"] else "❌ OFF", callback_data=f"settings#updatefilter-protect-{cfg['protect']}"),
        ],
        [
            InlineKeyboardButton("⬅️ Page 1", callback_data="settings#filters"),
            InlineKeyboardButton("Done ✅", callback_data="settings#main"),
        ],
    ]
    return InlineKeyboardMarkup(buttons)