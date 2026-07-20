# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

import asyncio 
from database import Db, db
from script import Script
from pyrogram import Client, filters
from .test import get_configs, update_configs, CLIENT, parse_buttons
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from .db import connect_user_db

CLIENT = CLIENT()

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

@Client.on_message(filters.command('settings'))
async def settings(client, message):
   await message.reply_text(
     "<b>Hᴇʀᴇ Is Tʜᴇ Sᴇᴛᴛɪɴɢs Pᴀɴᴇʟ⚙\n\nᴄʜᴀɴɢᴇ ʏᴏᴜʀ sᴇᴛᴛɪɴɢs ᴀs ʏᴏᴜʀ ᴡɪsʜ 👇</b>",
     reply_markup=main_buttons()
   )

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

@Client.on_callback_query(filters.regex(r'^settings'))
async def settings_query(bot, query):
  user_id = query.from_user.id
  i, type = query.data.split("#")
  buttons = [[InlineKeyboardButton('back', callback_data="settings#main")]]

  if type == "main":
     await query.message.edit_text(
       "<b>Hᴇʀᴇ Is Tʜᴇ Sᴇᴛᴛɪɴɢs Pᴀɴᴇʟ⚙\n\nᴄʜᴀɴɢᴇ ʏᴏᴜʀ sᴇᴛᴛɪɴɢs ᴀs ʏᴏᴜʀ ᴡɪsʜ 👇</b>",
       reply_markup=main_buttons())

  elif type == "extra":
     await query.message.edit_text(
       "<b>Hᴇʀᴇ Is Tʜᴇ Exᴛʀᴀ Sᴇᴛᴛɪɴɢs Pᴀɴᴇʟ⚙</b>",
       reply_markup=extra_buttons())

  elif type == "bots":
     buttons = []
     # FIX: use get_all_bots for multi-bot support
     bots = await db.get_all_bots(user_id)
     usr_bot = await db.get_userbot(user_id)
     if bots:
        for idx, _bot in enumerate(bots):
           buttons.append([InlineKeyboardButton(
              f"🤖 {_bot['name']} (@{_bot['username']})",
              callback_data=f"settings#editbot_{idx}")])
        buttons.append([InlineKeyboardButton('✚ Add Another Bot ✚',
                         callback_data="settings#addbot")])
     else:
        buttons.append([InlineKeyboardButton('✚ Add bot ✚',
                         callback_data="settings#addbot")])
     if usr_bot is not None:
        buttons.append([InlineKeyboardButton(
           f"👤 {usr_bot['name']} (UserBot)",
           callback_data="settings#edituserbot")])
     else:
        buttons.append([InlineKeyboardButton('✚ Add User bot ✚',
                         callback_data="settings#adduserbot")])
     buttons.append([InlineKeyboardButton('back', callback_data="settings#main")])
     bot_count = len(bots)
     speed_text = f"\n<b>⚡ Speed:</b> <code>{bot_count * 20} msgs/min</code>" if bot_count > 0 else ""
     await query.message.edit_text(
       f"<b><u>My Bots</u></b>\n\n<b>You can manage your bots here</b>\n<b>Active Bots:</b> <code>{bot_count}</code>{speed_text}",
       reply_markup=InlineKeyboardMarkup(buttons))

  elif type == "addbot":
     await query.message.delete()
     result = await CLIENT.add_bot(bot, query)
     if result != True:
        return
     await bot.send_message(
        query.from_user.id,
        "<b>✅ Bot token successfully added!</b>\n\n<i>Add more bots for faster forwarding!</i>",
        reply_markup=InlineKeyboardMarkup(buttons))

  elif type == "adduserbot":
     await query.message.delete()
     user = await CLIENT.add_session(bot, query)
     if user != True:
        return
     await bot.send_message(
        query.from_user.id,
        "<b>✅ Session successfully added!</b>",
        reply_markup=InlineKeyboardMarkup(buttons))

  elif type == "channels":
     buttons = []
     channels = await db.get_user_channels(user_id)
     for channel in channels:
        buttons.append([InlineKeyboardButton(
           f"{channel['title']}",
           callback_data=f"settings#editchannels_{channel['chat_id']}")])
     buttons.append([InlineKeyboardButton('✚ Add Channel ✚',
                      callback_data="settings#addchannel")])
     buttons.append([InlineKeyboardButton('back',
                      callback_data="settings#main")])
     await query.message.edit_text(
       "<b><u>My Channels</u></b>\n\n<b>you can manage your target chats in here</b>",
       reply_markup=InlineKeyboardMarkup(buttons))

  elif type == "addchannel":
     await query.message.delete()
     chat_ids = await bot.ask(
        chat_id=query.from_user.id,
        text="<b>❪ SET TARGET CHAT ❫\n\nForward a message from Your target chat\n/cancel - cancel this process</b>")
     if chat_ids.text == "/cancel":
        return await chat_ids.reply_text(
           "<b>process canceled</b>",
           reply_markup=InlineKeyboardMarkup(buttons))
     elif not chat_ids.forward_date:
        return await chat_ids.reply("<b>This is not a forward message</b>")
     else:
        chat_id = chat_ids.forward_from_chat.id
        title = chat_ids.forward_from_chat.title
        username = chat_ids.forward_from_chat.username
        username = "@" + username if username else "private"
     chat = await db.add_channel(user_id, chat_id, title, username)
     await chat_ids.reply_text(
        "<b>Successfully updated</b>" if chat else "<b>This channel already added</b>",
        reply_markup=InlineKeyboardMarkup(buttons))

  # FIX: editbot now supports index for multi-bot
  elif type.startswith("editbot"):
     idx = int(type.split('_')[1]) if '_' in type else 0
     bots = await db.get_all_bots(user_id)
     if not bots or idx >= len(bots):
        return await query.answer("Bot not found", show_alert=True)
     bot_data = bots[idx]
     TEXT = Script.BOT_DETAILS
     buttons = [
        [InlineKeyboardButton('❌ Remove ❌', callback_data=f"settings#removebot_{idx}")],
        [InlineKeyboardButton('back', callback_data="settings#bots")]
     ]
     await query.message.edit_text(
        TEXT.format(bot_data['name'], bot_data['id'], bot_data['username']),
        reply_markup=InlineKeyboardMarkup(buttons))

  elif type == "edituserbot":
     bot_data = await db.get_userbot(user_id)
     TEXT = Script.USER_DETAILS
     buttons = [
        [InlineKeyboardButton('❌ Remove ❌', callback_data="settings#removeuserbot")],
        [InlineKeyboardButton('back', callback_data="settings#bots")]
     ]
     await query.message.edit_text(
        TEXT.format(bot_data['name'], bot_data['id'], bot_data['username']),
        reply_markup=InlineKeyboardMarkup(buttons))

  # FIX: removebot now supports index
  elif type.startswith("removebot"):
     idx = int(type.split('_')[1]) if '_' in type else 0
     await db.remove_bot_by_index(user_id, idx)
     await query.message.edit_text(
        "<b>✅ Bot removed successfully</b>",
        reply_markup=InlineKeyboardMarkup(buttons))

  elif type == "removeuserbot":
     await db.remove_userbot(user_id)
     await query.message.edit_text(
        "<b>successfully updated</b>",
        reply_markup=InlineKeyboardMarkup(buttons))

  elif type.startswith("editchannels"):
     chat_id = type.split('_')[1]
     chat = await db.get_channel_details(user_id, chat_id)
     buttons = [
        [InlineKeyboardButton('❌ Remove ❌', callback_data=f"settings#removechannel_{chat_id}")],
        [InlineKeyboardButton('back', callback_data="settings#channels")]
     ]
     await query.message.edit_text(
        f"<b><u>📄 CHANNEL DETAILS</u></b>\n\n<b>- TITLE:</b> <code>{chat['title']}</code>\n<b>- CHANNEL ID:</b> <code>{chat['chat_id']}</code>\n<b>- USERNAME:</b> {chat['username']}",
        reply_markup=InlineKeyboardMarkup(buttons))

  elif type.startswith("removechannel"):
     chat_id = type.split('_')[1]
     await db.remove_channel(user_id, chat_id)
     await query.message.edit_text(
        "<b>successfully updated</b>",
        reply_markup=InlineKeyboardMarkup(buttons))

  elif type == "caption":
     buttons = []
     data = await get_configs(user_id)
     caption = data['caption']
     if caption is None:
        buttons.append([InlineKeyboardButton('✚ Add Caption ✚',
                      callback_data="settings#addcaption")])
     else:
        buttons.append([InlineKeyboardButton('See Caption',
                      callback_data="settings#seecaption")])
        buttons[-1].append(InlineKeyboardButton('🗑️ Delete Caption',
                      callback_data="settings#deletecaption"))
     buttons.append([InlineKeyboardButton('back', callback_data="settings#main")])
     await query.message.edit_text(
        "<b><u>CUSTOM CAPTION</u></b>\n\n<b>You can set a custom caption to videos and documents. Normally uses default caption</b>\n\n<b><u>AVAILABLE FILLINGS:</u></b>\n- <code>{filename}</code> : Filename\n- <code>{size}</code> : File size\n- <code>{caption}</code> : default caption",
        reply_markup=InlineKeyboardMarkup(buttons))

  elif type == "seecaption":
     data = await get_configs(user_id)
     buttons = [
        [InlineKeyboardButton('🖋️ Edit Caption', callback_data="settings#addcaption")],
        [InlineKeyboardButton('back', callback_data="settings#caption")]
     ]
     await query.message.edit_text(
        f"<b><u>YOUR CUSTOM CAPTION</u></b>\n\n<code>{data['caption']}</code>",
        reply_markup=InlineKeyboardMarkup(buttons))

  elif type == "deletecaption":
     await update_configs(user_id, 'caption', None)
     await query.message.edit_text(
        "<b>successfully updated</b>",
        reply_markup=InlineKeyboardMarkup(buttons))

  elif type == "addcaption":
     await query.message.delete()
     caption = await bot.ask(query.from_user.id, "Send your custom caption\n/cancel - <code>cancel this process</code>")
     if caption.text == "/cancel":
        return await caption.reply_text(
           "<b>process canceled !</b>",
           reply_markup=InlineKeyboardMarkup(buttons))
     try:
        caption.text.format(filename='', size='', caption='')
     except KeyError as e:
        return await caption.reply_text(
           f"<b>wrong filling {e} used in your caption. change it</b>",
           reply_markup=InlineKeyboardMarkup(buttons))
     await update_configs(user_id, 'caption', caption.text)
     await caption.reply_text(
        "<b>successfully updated</b>",
        reply_markup=InlineKeyboardMarkup(buttons))

  elif type == "button":
     buttons = []
     button = (await get_configs(user_id))['button']
     if button is None:
        buttons.append([InlineKeyboardButton('✚ Add Button ✚',
                      callback_data="settings#addbutton")])
     else:
        buttons.append([InlineKeyboardButton('👀 See Button',
                      callback_data="settings#seebutton")])
        buttons[-1].append(InlineKeyboardButton('🗑️ Remove Button',
                      callback_data="settings#deletebutton"))
     buttons.append([InlineKeyboardButton('back', callback_data="settings#main")])
     await query.message.edit_text(
        "<b><u>CUSTOM BUTTON</u></b>\n\n<b>You can set a inline button to messages.</b>\n\n<b><u>FORMAT:</u></b>\n`[Forward bot][buttonurl:https://t.me/mychannelurl]`\n",
        reply_markup=InlineKeyboardMarkup(buttons))

  elif type == "addbutton":
     await query.message.delete()
     ask = await bot.ask(user_id, text="**Send your custom button.\n\nFORMAT:**\n`[forward bot][buttonurl:https://t.me/url]`\n")
     button = parse_buttons(ask.text.html)
     if not button:
        return await ask.reply("<b>INVALID BUTTON</b>")
     await update_configs(user_id, 'button', ask.text.html)
     await ask.reply("<b>Successfully button added</b>",
             reply_markup=InlineKeyboardMarkup(buttons))

  elif type == "seebutton":
     button = (await get_configs(user_id))['button']
     button = parse_buttons(button, markup=False)
     if not button:
        return await query.answer("No button set", show_alert=True)
     button.append([InlineKeyboardButton("back", callback_data="settings#button")])
     await query.message.edit_text(
        "<b>YOUR CUSTOM BUTTON</b>",
        reply_markup=InlineKeyboardMarkup(button))

  elif type == "deletebutton":
     await update_configs(user_id, 'button', None)
     await query.message.edit_text(
        "<b>Successfully button deleted</b>",
        reply_markup=InlineKeyboardMarkup(buttons))

  elif type == "database":
     buttons = []
     db_uri = (await get_configs(user_id))['db_uri']
     if db_uri is None:
        buttons.append([InlineKeyboardButton('✚ Add Mongo Url',
                      callback_data="settings#addurl")])
     else:
        buttons.append([InlineKeyboardButton('👀 See Url',
                      callback_data="settings#seeurl")])
        buttons[-1].append(InlineKeyboardButton('❌ Remove Url',
                      callback_data="settings#deleteurl"))
     buttons.append([InlineKeyboardButton('back', callback_data="settings#main")])
     await query.message.edit_text(
        "<b><u>DATABASE</u>\n\nDatabase is required to store duplicate messages permanently. Otherwise stored duplicate media may disappear after bot restart.</b>",
        reply_markup=InlineKeyboardMarkup(buttons))

  elif type == "addurl":
     await query.message.delete()
     uri = await bot.ask(user_id, "<b>please send your mongodb url.</b>\n\n<i>get your Mongodb url from <a href='https://mongodb.com'>MongoDB</a></i>", disable_web_page_preview=True)
     if uri.text == "/cancel":
        return await uri.reply_text(
           "<b>process canceled !</b>",
           reply_markup=InlineKeyboardMarkup(buttons))
     if not uri.text.startswith("mongodb"):
        return await uri.reply("<b>Invalid Mongodb Url</b>",
                   reply_markup=InlineKeyboardMarkup(buttons))
     connect, udb = await connect_user_db(user_id, uri.text, "test")
     if connect:
        await udb.drop_all()
        await udb.close()
     else:
        return await uri.reply("<b>Invalid Mongodb Url — Cannot connect with this URI</b>",
                  reply_markup=InlineKeyboardMarkup(buttons))
     await update_configs(user_id, 'db_uri', uri.text)
     await uri.reply("<b>Successfully database url added</b>",
             reply_markup=InlineKeyboardMarkup(buttons))

  elif type == "seeurl":
     db_uri = (await get_configs(user_id))['db_uri']
     await query.answer(f"DATABASE URL: {db_uri}", show_alert=True)

  elif type == "deleteurl":
     await update_configs(user_id, 'db_uri', None)
     await query.message.edit_text(
        "<b>Successfully your database url deleted</b>",
        reply_markup=InlineKeyboardMarkup(buttons))

  elif type == "filters":
     await query.message.edit_text(
        "<b><u>💠 CUSTOM FILTERS 💠</u></b>\n\n<b>Configure the type of messages which you want to forward</b>",
        reply_markup=await filters_buttons(user_id))

  elif type == "nextfilters":
     await query.edit_message_reply_markup(
        reply_markup=await next_filters_buttons(user_id))

  elif type.startswith("updatefilter"):
     i, key, value = type.split('-')
     if value == "True":
        await update_configs(user_id, key, False)
     else:
        await update_configs(user_id, key, True)
     if key in ['poll', 'protect', 'voice', 'animation', 'sticker', 'duplicate']:
        return await query.edit_message_reply_markup(
           reply_markup=await next_filters_buttons(user_id))
     await query.edit_message_reply_markup(
        reply_markup=await filters_buttons(user_id))

  elif type.startswith("file_size"):
     settings = await get_configs(user_id)
     size = settings.get('min_size', 0)
     await query.message.edit_text(
        f'<b><u>SIZE LIMIT</u></b>\n\n<b>You can set a minimum file size to forward\n\nFiles larger than <code>{size} MB</code> will be forwarded</b>',
        reply_markup=size_button(size))

  # FIX: removed trailing space from maxfile_size
  elif type.startswith("maxfile_size"):
     settings = await get_configs(user_id)
     size = settings.get('max_size', 0)
     await query.message.edit_text(
        f'<b><u>Max SIZE LIMIT</u></b>\n\n<b>You can set a maximum file size to forward\n\nFiles smaller than <code>{size} MB</code> will be forwarded</b>',
        reply_markup=maxsize_button(size))

  # FIX: removed dead size_limit call; decrement callback_data fixed in size_button()
  elif type.startswith("update_size"):
     size = int(query.data.split('-')[1])
     if size < 0:
        size = 0
     if size > 4000:
        return await query.answer("size limit exceeded", show_alert=True)
     await update_configs(user_id, 'min_size', size)
     await query.message.edit_text(
        f'<b><u>SIZE LIMIT</u></b>\n\n<b>Files larger than <code>{size} MB</code> will be forwarded</b>',
        reply_markup=size_button(size))

  elif type.startswith("maxupdate_size"):
     size = int(query.data.split('-')[1])
     if size < 0:
        size = 0
     if size > 4000:
        return await query.answer("size limit exceeded", show_alert=True)
     await update_configs(user_id, 'max_size', size)
     await query.message.edit_text(
        f'<b><u>Max SIZE LIMIT</u></b>\n\n<b>Files smaller than <code>{size} MB</code> will be forwarded</b>',
        reply_markup=maxsize_button(size))

  elif type == "add_extension":
     await query.message.delete()
     ext = await bot.ask(user_id, text="<b>Please send your extensions (separate by space)\nExample: <code>.mp4 .mkv .zip</code></b>")
     if ext.text == '/cancel':
        return await ext.reply_text(
           "<b>process canceled</b>",
           reply_markup=InlineKeyboardMarkup(buttons))
     extensions = ext.text.split(" ")
     extension = (await get_configs(user_id))['extension']
     if extension:
        for extn in extensions:
           extension.append(extn)
     else:
        extension = extensions
     await update_configs(user_id, 'extension', extension)
     back_btn = [[InlineKeyboardButton('back', callback_data="settings#get_extension")]]
     await ext.reply_text("<b>successfully updated</b>", reply_markup=InlineKeyboardMarkup(back_btn))

  elif type == "get_extension":
     extensions = (await get_configs(user_id))['extension']
     btn = []
     text = ""
     if extensions:
        text += "<b>🕹 Extensions:</b>"
        for ext in extensions:
           text += f"\n<code>- {ext}</code>"
     else:
        text += "<b>No Extensions set</b>"
     btn.append([InlineKeyboardButton('✚ Add', callback_data='settings#add_extension')])
     btn.append([InlineKeyboardButton('Remove All', callback_data='settings#rmve_all_extension')])
     btn.append([InlineKeyboardButton('back', callback_data='settings#extra')])
     await query.message.edit_text(
        text=f"<b><u>EXTENSIONS</u></b>\n\n<b>Files with these extensions will NOT be forwarded</b>\n\n{text}",
        reply_markup=InlineKeyboardMarkup(btn))

  elif type == "rmve_all_extension":
     await update_configs(user_id, 'extension', None)
     back_btn = [[InlineKeyboardButton('back', callback_data="settings#get_extension")]]
     await query.message.edit_text(
        "<b>successfully deleted all extensions</b>",
        reply_markup=InlineKeyboardMarkup(back_btn))

  elif type == "add_keyword":
     await query.message.delete()
     ask = await bot.ask(user_id, text="<b>Please send the keywords (separate by space)\nExample: <code>English 1080p Hdrip</code></b>")
     if ask.text == '/cancel':
        return await ask.reply_text(
           "<b>process canceled</b>",
           reply_markup=InlineKeyboardMarkup(buttons))
     keywords = ask.text.split(" ")
     keyword = (await get_configs(user_id))['keywords']
     if keyword:
        for word in keywords:
           keyword.append(word)
     else:
        keyword = keywords
     await update_configs(user_id, 'keywords', keyword)
     back_btn = [[InlineKeyboardButton('back', callback_data="settings#get_keyword")]]
     await ask.reply_text("<b>successfully updated</b>", reply_markup=InlineKeyboardMarkup(back_btn))

  elif type == "get_keyword":
     keywords = (await get_configs(user_id))['keywords']
     btn = []
     text = ""
     if keywords:
        text += "<b>🔖 Keywords:</b>"
        for key in keywords:
           text += f"\n<code>- {key}</code>"
     else:
        text += "<b>No keywords set</b>"
     btn.append([InlineKeyboardButton('✚ Add', callback_data='settings#add_keyword')])
     btn.append([InlineKeyboardButton('Remove all', callback_data='settings#rmve_all_keyword')])
     btn.append([InlineKeyboardButton('Back', callback_data='settings#extra')])
     await query.message.edit_text(
        text=f"<b><u>Keywords</u></b>\n\n<b>Only files with these keywords in filename will be forwarded</b>\n\n{text}",
        reply_markup=InlineKeyboardMarkup(btn))

  elif type == "rmve_all_keyword":
     await update_configs(user_id, 'keywords', None)
     back_btn = [[InlineKeyboardButton('back', callback_data="settings#get_keyword")]]
     await query.message.edit_text(
        "<b>successfully deleted all keywords</b>",
        reply_markup=InlineKeyboardMarkup(back_btn))

  elif type == "speed":
     bs = await db.get_batch_settings(user_id)
     await query.message.edit_text(
        _speed_text(bs),
        reply_markup=_speed_markup(bs),
        disable_web_page_preview=True)

  elif type.startswith("speed_set"):
     # speed_set_batch_size, speed_set_base_sleep, speed_set_stagger_delay
     _, _, key, raw = type.split('_', 3)
     key = key + '_' + raw.rsplit('_', 1)[0] if key == 'base' or key == 'stagger' else key
     # Re-parse: format is speed_set_{key}-{value}  e.g. speed_set_batch_size-25
     parts = type[len("speed_set_"):]          # e.g. batch_size-25
     key, val = parts.rsplit('-', 1)
     if key == 'batch_size':
        value = int(val)
        if not (5 <= value <= 100):
           return await query.answer("Range: 5 – 100", show_alert=True)
     else:
        value = float(val)
        if key == 'base_sleep' and not (0.5 <= value <= 10.0):
           return await query.answer("Range: 0.5 – 10.0 s", show_alert=True)
        if key == 'stagger_delay' and not (0.0 <= value <= 2.0):
           return await query.answer("Range: 0.0 – 2.0 s", show_alert=True)
     await db.update_batch_settings(user_id, key, value)
     bs = await db.get_batch_settings(user_id)
     await query.message.edit_text(
        _speed_text(bs),
        reply_markup=_speed_markup(bs),
        disable_web_page_preview=True)

  elif type.startswith("alert"):
     alert = type.split('_', 1)[1]
     await query.answer(alert, show_alert=True)

def _speed_text(bs):
    batch  = bs.get('batch_size',    20)
    sleep  = bs.get('base_sleep',    3.0)
    stagger= bs.get('stagger_delay', 0.2)
    msgs_per_min = round(60 / sleep) if sleep > 0 else 0
    return (
        "<b><u>⚡ Speed / Batch Settings</u></b>\n\n"
        f"<b>📦 Batch Size:</b> <code>{batch}</code>  <i>(msgs per bot per turn)</i>\n"
        f"<b>⏱ Delay:</b> <code>{sleep}s</code>  <i>({msgs_per_min} msgs/min per bot)</i>\n"
        f"<b>🔀 Stagger:</b> <code>{stagger}s</code>  <i>(pause between bots)</i>\n\n"
        "<i>Tap a value to adjust it.</i>"
    )

def _speed_markup(bs):
    batch  = int(bs.get('batch_size',    20))
    sleep  = float(bs.get('base_sleep',    3.0))
    stagger= float(bs.get('stagger_delay', 0.2))
    s = round(sleep * 10) / 10    # keep 1 decimal
    st= round(stagger * 10) / 10
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"📦 Batch: {batch}", callback_data='noth')],
        [
            InlineKeyboardButton("-5",  callback_data=f"settings#speed_set_batch_size-{max(5,  batch-5)}"),
            InlineKeyboardButton("-1",  callback_data=f"settings#speed_set_batch_size-{max(5,  batch-1)}"),
            InlineKeyboardButton("+1",  callback_data=f"settings#speed_set_batch_size-{min(100,batch+1)}"),
            InlineKeyboardButton("+5",  callback_data=f"settings#speed_set_batch_size-{min(100,batch+5)}"),
        ],
        [InlineKeyboardButton(f"⏱ Delay: {s}s", callback_data='noth')],
        [
            InlineKeyboardButton("-0.5", callback_data=f"settings#speed_set_base_sleep-{max(0.5, round(s-0.5,1))}"),
            InlineKeyboardButton("-0.1", callback_data=f"settings#speed_set_base_sleep-{max(0.5, round(s-0.1,1))}"),
            InlineKeyboardButton("+0.1", callback_data=f"settings#speed_set_base_sleep-{min(10.0,round(s+0.1,1))}"),
            InlineKeyboardButton("+0.5", callback_data=f"settings#speed_set_base_sleep-{min(10.0,round(s+0.5,1))}"),
        ],
        [InlineKeyboardButton(f"🔀 Stagger: {st}s", callback_data='noth')],
        [
            InlineKeyboardButton("-0.1", callback_data=f"settings#speed_set_stagger_delay-{max(0.0, round(st-0.1,1))}"),
            InlineKeyboardButton("+0.1", callback_data=f"settings#speed_set_stagger_delay-{min(2.0, round(st+0.1,1))}"),
        ],
        [InlineKeyboardButton("⫷ Back", callback_data="settings#main")],
    ])

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

def extra_buttons():
   buttons = [[
       InlineKeyboardButton('💾 Mɪɴ Sɪᴢᴇ Lɪᴍɪᴛ',
                    callback_data='settings#file_size')
       ],[
       # FIX: removed trailing space from maxfile_size
       InlineKeyboardButton('💾 Mᴀx Sɪᴢᴇ Lɪᴍɪᴛ',
                    callback_data='settings#maxfile_size')
       ],[
       InlineKeyboardButton('🚥 Keywords',
                    callback_data='settings#get_keyword'),
       InlineKeyboardButton('🕹 Extensions',
                    callback_data='settings#get_extension')
       ],[
       InlineKeyboardButton('⫷ Bᴀᴄᴋ',
                    callback_data='settings#main')
       ]]
   return InlineKeyboardMarkup(buttons)

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

def main_buttons():
  buttons = [[
       InlineKeyboardButton('🤖 Bᴏᴛs',
                    callback_data='settings#bots'),
       InlineKeyboardButton('🏷 Cʜᴀɴɴᴇʟs',
                    callback_data='settings#channels')
       ],[
       InlineKeyboardButton('🖋️ Cᴀᴘᴛɪᴏɴ',
                    callback_data='settings#caption'),
       InlineKeyboardButton('⏹ Bᴜᴛᴛᴏɴ',
                    callback_data='settings#button')
       ],[
       InlineKeyboardButton('🕵‍♀ Fɪʟᴛᴇʀs 🕵‍♀',
                    callback_data='settings#filters'),
       InlineKeyboardButton('🗃 MᴏɴɢᴏDB',
                    callback_data='settings#database')
       ],[
       InlineKeyboardButton('Exᴛʀᴀ Sᴇᴛᴛɪɴɢs 🧪',
                    callback_data='settings#extra'),
       InlineKeyboardButton('⚡ Sᴘᴇᴇᴅ',
                    callback_data='settings#speed')
       ],[
       InlineKeyboardButton('⫷ Bᴀᴄᴋ',
                    callback_data='help')
       ]]
  return InlineKeyboardMarkup(buttons)

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

def size_limit(limit):
   if str(limit) == "None":
      return None, ""
   elif str(limit) == "True":
      return True, "more than"
   else:
      return False, "less than"

def extract_btn(datas):
    i = 0
    btn = []
    if datas:
       for data in datas:
         if i >= 3:
            i = 0
         if i == 0:
            btn.append([InlineKeyboardButton(data, callback_data=f'settings#alert_{data}')])
            i += 1
            continue
         elif i > 0:
            btn[-1].append(InlineKeyboardButton(data, callback_data=f'settings#alert_{data}'))
            i += 1
    return btn

# FIX: all decrement buttons now use correct format (no extra underscore)
def maxsize_button(size):
  buttons = [[
       InlineKeyboardButton('💾 Max Size Limit', callback_data='noth')
       ],[
       InlineKeyboardButton('+1',  callback_data=f'settings#maxupdate_size-{size + 1}'),
       InlineKeyboardButton('-1',  callback_data=f'settings#maxupdate_size-{max(0, size - 1)}')
       ],[
       InlineKeyboardButton('+5',  callback_data=f'settings#maxupdate_size-{size + 5}'),
       InlineKeyboardButton('-5',  callback_data=f'settings#maxupdate_size-{max(0, size - 5)}')
       ],[
       InlineKeyboardButton('+10', callback_data=f'settings#maxupdate_size-{size + 10}'),
       InlineKeyboardButton('-10', callback_data=f'settings#maxupdate_size-{max(0, size - 10)}')
       ],[
       InlineKeyboardButton('+50', callback_data=f'settings#maxupdate_size-{size + 50}'),
       InlineKeyboardButton('-50', callback_data=f'settings#maxupdate_size-{max(0, size - 50)}')
       ],[
       InlineKeyboardButton('+100', callback_data=f'settings#maxupdate_size-{size + 100}'),
       InlineKeyboardButton('-100', callback_data=f'settings#maxupdate_size-{max(0, size - 100)}')
       ],[
       InlineKeyboardButton('back', callback_data="settings#extra")
     ]]
  return InlineKeyboardMarkup(buttons)

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

# FIX: all decrement buttons now use correct format (no extra underscore)
def size_button(size):
  buttons = [[
       InlineKeyboardButton('💾 Min Size Limit', callback_data='noth')
       ],[
       InlineKeyboardButton('+1',  callback_data=f'settings#update_size-{size + 1}'),
       InlineKeyboardButton('-1',  callback_data=f'settings#update_size-{max(0, size - 1)}')
       ],[
       InlineKeyboardButton('+5',  callback_data=f'settings#update_size-{size + 5}'),
       InlineKeyboardButton('-5',  callback_data=f'settings#update_size-{max(0, size - 5)}')
       ],[
       InlineKeyboardButton('+10', callback_data=f'settings#update_size-{size + 10}'),
       InlineKeyboardButton('-10', callback_data=f'settings#update_size-{max(0, size - 10)}')
       ],[
       InlineKeyboardButton('+50', callback_data=f'settings#update_size-{size + 50}'),
       InlineKeyboardButton('-50', callback_data=f'settings#update_size-{max(0, size - 50)}')
       ],[
       InlineKeyboardButton('+100', callback_data=f'settings#update_size-{size + 100}'),
       InlineKeyboardButton('-100', callback_data=f'settings#update_size-{max(0, size - 100)}')
       ],[
       InlineKeyboardButton('back', callback_data="settings#extra")
     ]]
  return InlineKeyboardMarkup(buttons)

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

async def filters_buttons(user_id):
  filter = await get_configs(user_id)
  filters = filter['filters']
  buttons = [[
       InlineKeyboardButton('🏷️ Forward tag',
                    callback_data=f'settings_#updatefilter-forward_tag-{filter["forward_tag"]}'),
       InlineKeyboardButton('✅' if filter['forward_tag'] else '❌',
                    callback_data=f'settings#updatefilter-forward_tag-{filter["forward_tag"]}')
       ],[
       InlineKeyboardButton('🖍️ Texts',
                    callback_data=f'settings_#updatefilter-text-{filters["text"]}'),
       InlineKeyboardButton('✅' if filters['text'] else '❌',
                    callback_data=f'settings#updatefilter-text-{filters["text"]}')
       ],[
       InlineKeyboardButton('📁 Documents',
                    callback_data=f'settings_#updatefilter-document-{filters["document"]}'),
       InlineKeyboardButton('✅' if filters['document'] else '❌',
                    callback_data=f'settings#updatefilter-document-{filters["document"]}')
       ],[
       InlineKeyboardButton('🎞️ Videos',
                    callback_data=f'settings_#updatefilter-video-{filters["video"]}'),
       InlineKeyboardButton('✅' if filters['video'] else '❌',
                    callback_data=f'settings#updatefilter-video-{filters["video"]}')
       ],[
       InlineKeyboardButton('📷 Photos',
                    callback_data=f'settings_#updatefilter-photo-{filters["photo"]}'),
       InlineKeyboardButton('✅' if filters['photo'] else '❌',
                    callback_data=f'settings#updatefilter-photo-{filters["photo"]}')
       ],[
       InlineKeyboardButton('🎧 Audios',
                    callback_data=f'settings_#updatefilter-audio-{filters["audio"]}'),
       InlineKeyboardButton('✅' if filters['audio'] else '❌',
                    callback_data=f'settings#updatefilter-audio-{filters["audio"]}')
       ],[
       InlineKeyboardButton('⫷ back', callback_data="settings#main"),
       InlineKeyboardButton('next ⫸', callback_data="settings#nextfilters")
       ]]
  return InlineKeyboardMarkup(buttons)

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

async def next_filters_buttons(user_id):
  filter = await get_configs(user_id)
  filters = filter['filters']
  buttons = [[
       InlineKeyboardButton('🎤 Voices',
                    callback_data=f'settings_#updatefilter-voice-{filters["voice"]}'),
       InlineKeyboardButton('✅' if filters['voice'] else '❌',
                    callback_data=f'settings#updatefilter-voice-{filters["voice"]}')
       ],[
       InlineKeyboardButton('🎭 Animations',
                    callback_data=f'settings_#updatefilter-animation-{filters["animation"]}'),
       InlineKeyboardButton('✅' if filters['animation'] else '❌',
                    callback_data=f'settings#updatefilter-animation-{filters["animation"]}')
       ],[
       InlineKeyboardButton('🃏 Stickers',
                    callback_data=f'settings_#updatefilter-sticker-{filters["sticker"]}'),
       InlineKeyboardButton('✅' if filters['sticker'] else '❌',
                    callback_data=f'settings#updatefilter-sticker-{filters["sticker"]}')
       ],[
       InlineKeyboardButton('▶️ Skip duplicate',
                    callback_data=f'settings_#updatefilter-duplicate-{filter["duplicate"]}'),
       InlineKeyboardButton('✅' if filter['duplicate'] else '❌',
                    callback_data=f'settings#updatefilter-duplicate-{filter["duplicate"]}')
       ],[
       InlineKeyboardButton('📊 Poll',
                    callback_data=f'settings_#updatefilter-poll-{filters["poll"]}'),
       InlineKeyboardButton('✅' if filters['poll'] else '❌',
                    callback_data=f'settings#updatefilter-poll-{filters["poll"]}')
       ],[
       InlineKeyboardButton('🔒 Secure message',
                    callback_data=f'settings_#updatefilter-protect-{filter["protect"]}'),
       InlineKeyboardButton('✅' if filter['protect'] else '❌',
                    callback_data=f'settings#updatefilter-protect-{filter["protect"]}')
       ],[
       InlineKeyboardButton('⫷ back', callback_data="settings#filters"),
       InlineKeyboardButton('End ⫸', callback_data="settings#main")
       ]]
  return InlineKeyboardMarkup(buttons)

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01
