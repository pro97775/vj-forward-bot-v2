# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

from database import db
from script import Script
from config import Config, temp
from pyrogram import Client, filters, enums
from pyrogram.errors import ListenerTimeout
from .test import get_configs, update_configs, CLIENT, parse_buttons
from .public import parse_chat
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

CLIENT = CLIENT()
MAIN_TXT = "<b>Hᴇʀᴇ Is Tʜᴇ Sᴇᴛᴛɪɴɢs Pᴀɴᴇʟ⚙\n\nᴄʜᴀɴɢᴇ ʏᴏᴜʀ sᴇᴛᴛɪɴɢs ᴀs ʏᴏᴜʀ ᴡɪsʜ 👇</b>"

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

def main_buttons(is_owner=False):
   buttons = [[
        InlineKeyboardButton('🤖 Bᴏᴛs', callback_data='settings#bots'),
        InlineKeyboardButton('🏷 Cʜᴀɴɴᴇʟs', callback_data='settings#channels')
        ],[
        InlineKeyboardButton('🖍️ Cᴀᴘᴛɪᴏɴ', callback_data='settings#caption'),
        InlineKeyboardButton('⏹ Bᴜᴛᴛᴏɴ', callback_data='settings#button')
        ],[
        InlineKeyboardButton('🕵️ Fɪʟᴛᴇʀs', callback_data='settings#filters'),
        InlineKeyboardButton('⏱ Sᴘᴇᴇᴅ & Dᴇʟᴀʏ', callback_data='settings#speed')
        ],[
        InlineKeyboardButton('📊 Sᴛᴀᴛs', callback_data='settings#stats'),
        InlineKeyboardButton('🧪 Exᴛʀᴀ Sᴇᴛᴛɪɴɢs', callback_data='settings#extra')
        ]]
   if is_owner:
      buttons.append([InlineKeyboardButton('🗃 Dᴜᴍᴘ Cʜᴀᴛ', callback_data='settings#dump')])
   buttons.append([InlineKeyboardButton('⫷ Bᴀᴄᴋ', callback_data='help')])
   return InlineKeyboardMarkup(buttons)

def back_button(to="settings#main"):
   return InlineKeyboardMarkup([[InlineKeyboardButton('⫷ Bᴀᴄᴋ', callback_data=to)]])

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

@Client.on_message(filters.private & filters.command('settings'))
async def settings(client, message):
   await message.reply_text(
     MAIN_TXT,
     reply_markup=main_buttons(message.from_user.id == Config.BOT_OWNER)
     )

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

def extra_buttons():
   buttons = [[
        InlineKeyboardButton('💾 Mɪɴ Sɪᴢᴇ Lɪᴍɪᴛ', callback_data='settings#file_size'),
        InlineKeyboardButton('💾 Mᴀx Sɪᴢᴇ Lɪᴍɪᴛ', callback_data='settings#maxfile_size')
        ],[
        InlineKeyboardButton('🚥 Kᴇʏᴡᴏʀᴅs', callback_data='settings#get_keyword'),
        InlineKeyboardButton('🕹 Exᴛᴇɴsɪᴏɴs', callback_data='settings#get_extension')
        ],[
        InlineKeyboardButton('⫷ Bᴀᴄᴋ', callback_data='settings#main')
        ]]
   return InlineKeyboardMarkup(buttons)

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

async def filters_buttons(user_id):
  config = await get_configs(user_id)
  filter = config['filters']
  def row(label, key, value):
     # both buttons toggle the setting, so any tap works
     data = f'settings#updatefilter-{key}-{value}'
     return [InlineKeyboardButton(label, callback_data=data),
             InlineKeyboardButton('✅' if value else '❌', callback_data=data)]
  buttons = [
       row('🏷️ Forward tag', 'forward_tag', config['forward_tag']),
       row('🖍️ Texts', 'text', filter['text']),
       row('📁 Documents', 'document', filter['document']),
       row('🎞️ Videos', 'video', filter['video']),
       row('📷 Photos', 'photo', filter['photo']),
       row('🎧 Audios', 'audio', filter['audio']),
       [InlineKeyboardButton('⫷ Bᴀᴄᴋ', callback_data="settings#main"),
        InlineKeyboardButton('Nᴇxᴛ ⫸', callback_data="settings#nextfilters")]
       ]
  return InlineKeyboardMarkup(buttons) 

async def next_filters_buttons(user_id):
  config = await get_configs(user_id)
  filter = config['filters']
  def row(label, key, value):
     data = f'settings#updatefilter-{key}-{value}'
     return [InlineKeyboardButton(label, callback_data=data),
             InlineKeyboardButton('✅' if value else '❌', callback_data=data)]
  buttons = [
       row('🎤 Voices', 'voice', filter['voice']),
       row('🎭 Animations', 'animation', filter['animation']),
       row('🃏 Stickers', 'sticker', filter['sticker']),
       row('📊 Poll', 'poll', filter['poll']),
       row('🔒 Secure message', 'protect', config['protect']),
       [InlineKeyboardButton('⫷ Bᴀᴄᴋ', callback_data="settings#filters"),
        InlineKeyboardButton('Eɴᴅ ⫸', callback_data="settings#main")]
       ]
  return InlineKeyboardMarkup(buttons) 

def counter_buttons(label, key, value, back, step=(1, 5, 10, 50, 100), unit=""):
   """Build a +/- keyboard for a numeric setting."""
   buttons = [[InlineKeyboardButton(f'{label}: {value}{unit}', callback_data='noth')]]
   for s in step:
      buttons.append([
         InlineKeyboardButton(f'+{s}', callback_data=f'settings#{key}-{value + s}'),
         InlineKeyboardButton(f'-{s}', callback_data=f'settings#{key}-{max(0, value - s)}')
      ])
   buttons.append([InlineKeyboardButton('⫷ Bᴀᴄᴋ', callback_data=back)])
   return InlineKeyboardMarkup(buttons)

def size_button(size):
   return counter_buttons('💾 Mɪɴ Sɪᴢᴇ', 'update_size', size, 'settings#extra', unit=' MB')

def maxsize_button(size):
   return counter_buttons('💾 Mᴀx Sɪᴢᴇ', 'maxupdate_size', size, 'settings#extra', unit=' MB')

def speed_buttons(configs):
   """Delay + per bot rate controls."""
   buttons = [[
        InlineKeyboardButton(f"⏱ Bᴏᴛ Dᴇʟᴀʏ: {configs['bot_delay']} s", callback_data='noth')
        ],[
        InlineKeyboardButton('+1', callback_data=f"settings#botdelay-{configs['bot_delay'] + 1}"),
        InlineKeyboardButton('-1', callback_data=f"settings#botdelay-{max(0, configs['bot_delay'] - 1)}"),
        InlineKeyboardButton('+5', callback_data=f"settings#botdelay-{configs['bot_delay'] + 5}"),
        InlineKeyboardButton('-5', callback_data=f"settings#botdelay-{max(0, configs['bot_delay'] - 5)}")
        ],[
        InlineKeyboardButton(f"⏱ Uꜱᴇʀʙᴏᴛ Dᴇʟᴀʏ: {configs['userbot_delay']} s", callback_data='noth')
        ],[
        InlineKeyboardButton('+1', callback_data=f"settings#userdelay-{configs['userbot_delay'] + 1}"),
        InlineKeyboardButton('-1', callback_data=f"settings#userdelay-{max(0, configs['userbot_delay'] - 1)}"),
        InlineKeyboardButton('+5', callback_data=f"settings#userdelay-{configs['userbot_delay'] + 5}"),
        InlineKeyboardButton('-5', callback_data=f"settings#userdelay-{max(0, configs['userbot_delay'] - 5)}")
        ],[
        InlineKeyboardButton(f"📨 Pᴇʀ Bᴏᴛ Rᴀᴛᴇ: {configs['bot_rate']} / ᴍɪɴ", callback_data='noth')
        ],[
        InlineKeyboardButton('+5', callback_data=f"settings#botrate-{configs['bot_rate'] + 5}"),
        InlineKeyboardButton('-5', callback_data=f"settings#botrate-{max(1, configs['bot_rate'] - 5)}"),
        InlineKeyboardButton('+20', callback_data=f"settings#botrate-{configs['bot_rate'] + 20}"),
        InlineKeyboardButton('-20', callback_data=f"settings#botrate-{max(1, configs['bot_rate'] - 20)}")
        ],[
        InlineKeyboardButton('♻️ Rᴇsᴇᴛ Dᴇғᴀᴜʟᴛ', callback_data='settings#resetspeed')
        ],[
        InlineKeyboardButton('⫷ Bᴀᴄᴋ', callback_data='settings#main')
        ]]
   return InlineKeyboardMarkup(buttons)

def extract_btn(datas):
    """Show a list of keywords / extensions as alert buttons, 3 per row."""
    btn = []
    for i, data in enumerate(datas or []):
       if i % 3 == 0:
          btn.append([InlineKeyboardButton(data, f'settings#alert_{data}')])
       else:
          btn[-1].append(InlineKeyboardButton(data, f'settings#alert_{data}'))
    return btn

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

async def stats_text(user_id):
   """Build the per user stats text."""
   configs = await get_configs(user_id)
   bots = await db.get_bots(user_id)
   userbot = await db.get_userbot(user_id)
   channels = await db.get_user_channels(user_id)
   speed = (configs['bot_rate'] * len(bots)) if bots else (
      int(60 / max(1, configs['userbot_delay'])) if userbot else 0)
   return Script.MY_STATS.format(
      bots=len(bots),
      userbot=f"@{userbot['username']}" if userbot else "not added",
      channels=len(channels),
      speed=speed,
      bot_delay=configs['bot_delay'],
      userbot_delay=configs['userbot_delay'],
      rate=configs['bot_rate'],
      tag="on" if configs['forward_tag'] else "off",
      running="yes" if await db.is_forwad_exit(user_id) else "no")

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

@Client.on_callback_query(filters.regex(r'^noth$'))
async def nothing(bot, query):
   await query.answer()

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

@Client.on_callback_query(filters.regex(r'^settings'))
async def settings_query(bot, query):
  user_id = query.from_user.id
  i, type = query.data.split("#", 1)
  if type == "main":
     await query.message.edit_text(
       MAIN_TXT,
       reply_markup=main_buttons(user_id == Config.BOT_OWNER))

  elif type == "extra":
     await query.message.edit_text(
       "<b>Hᴇʀᴇ Is Tʜᴇ Exᴛʀᴀ Sᴇᴛᴛɪɴɢs Pᴀɴᴇʟ⚙</b>",
       reply_markup=extra_buttons())

  elif type == "stats":
     await query.message.edit_text(
       await stats_text(user_id),
       reply_markup=InlineKeyboardMarkup([[
          InlineKeyboardButton('♻️ Rᴇғʀᴇsʜ', callback_data='settings#stats')
       ],[
          InlineKeyboardButton('🌐 Bᴏᴛ Sᴛᴀᴛs', callback_data='status'),
          InlineKeyboardButton('⫷ Bᴀᴄᴋ', callback_data='settings#main')
       ]]))

  elif type == "speed":
     configs = await get_configs(user_id)
     await query.message.edit_text(
       Script.DELAY_TXT.format(configs['bot_delay'], configs['userbot_delay'], configs['bot_rate']),
       reply_markup=speed_buttons(configs))

  elif type.startswith("botdelay-"):
     value = max(0, min(300, int(type.split('-')[1])))
     await update_configs(user_id, 'bot_delay', value)
     configs = await get_configs(user_id)
     await query.message.edit_text(
       Script.DELAY_TXT.format(configs['bot_delay'], configs['userbot_delay'], configs['bot_rate']),
       reply_markup=speed_buttons(configs))

  elif type.startswith("userdelay-"):
     value = max(0, min(300, int(type.split('-')[1])))
     await update_configs(user_id, 'userbot_delay', value)
     configs = await get_configs(user_id)
     await query.message.edit_text(
       Script.DELAY_TXT.format(configs['bot_delay'], configs['userbot_delay'], configs['bot_rate']),
       reply_markup=speed_buttons(configs))

  elif type.startswith("botrate-"):
     value = max(1, min(100, int(type.split('-')[1])))
     await update_configs(user_id, 'bot_rate', value)
     configs = await get_configs(user_id)
     await query.message.edit_text(
       Script.DELAY_TXT.format(configs['bot_delay'], configs['userbot_delay'], configs['bot_rate']),
       reply_markup=speed_buttons(configs))

  elif type == "resetspeed":
     await update_configs(user_id, 'bot_delay', Config.BOT_DELAY)
     await update_configs(user_id, 'userbot_delay', Config.USERBOT_DELAY)
     await update_configs(user_id, 'bot_rate', Config.BOT_RATE)
     configs = await get_configs(user_id)
     await query.answer("reset to default", show_alert=True)
     await query.message.edit_text(
       Script.DELAY_TXT.format(configs['bot_delay'], configs['userbot_delay'], configs['bot_rate']),
       reply_markup=speed_buttons(configs))

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01
  elif type == "bots":
     btn = []
     bots = await db.get_bots(user_id)
     usr_bot = await db.get_userbot(user_id)
     for _bot in bots:
        btn.append([InlineKeyboardButton(f"🤖 {_bot['name']}",
                         callback_data=f"settings#editbot_{_bot['id']}")])
     if usr_bot is not None:
        btn.append([InlineKeyboardButton(f"👤 {usr_bot['name']}",
                         callback_data="settings#edituserbot")])
     btn.append([InlineKeyboardButton('✚ Aᴅᴅ Bᴏᴛ', callback_data="settings#addbot"),
                 InlineKeyboardButton('✚ Aᴅᴅ Uꜱᴇʀʙᴏᴛ', callback_data="settings#adduserbot")])
     if len(bots) > 1:
        btn.append([InlineKeyboardButton('🗑 Rᴇᴍᴏᴠᴇ Aʟʟ Bᴏᴛs', callback_data="settings#removeallbots")])
     btn.append([InlineKeyboardButton('⫷ Bᴀᴄᴋ', callback_data="settings#main")])
     rate = (await get_configs(user_id))['bot_rate']
     await query.message.edit_text(
       f"<b><u>My Bots</b></u>\n\n<b>You can add up to {Config.MAX_BOTS} bots. Messages are shared between all of them "
       f"(round robin), every bot forwards only {rate} messages per minute.</b>\n\n"
       f"<b>➣ Bots added:</b> <code>{len(bots)}</code>",
       reply_markup=InlineKeyboardMarkup(btn))

  elif type == "addbot":
     await query.answer()
     await query.message.delete()
     added = await CLIENT.add_bot(bot, query)
     if added is not True:
        return
     await bot.send_message(user_id,
        "<b>bot token successfully added to db</b>",
        reply_markup=back_button("settings#bots"))

  elif type == "adduserbot":
     await query.answer()
     await query.message.delete()
     user = await CLIENT.add_session(bot, query)
     if user is not True:
        return
     await bot.send_message(user_id,
        "<b>session successfully added to db</b>",
        reply_markup=back_button("settings#bots"))

  elif type.startswith("editbot"):
     bot_id = int(type.split('_')[1])
     bots = await db.get_bots(user_id)
     _bot = next((b for b in bots if int(b['id']) == bot_id), None)
     if not _bot:
        return await query.answer("this bot was removed already", show_alert=True)
     btn = [[InlineKeyboardButton('❌ Rᴇᴍᴏᴠᴇ', callback_data=f"settings#removebot_{bot_id}")],
            [InlineKeyboardButton('⫷ Bᴀᴄᴋ', callback_data="settings#bots")]]
     await query.message.edit_text(
        Script.BOT_DETAILS.format(_bot['name'], _bot['id'], _bot['username']),
        reply_markup=InlineKeyboardMarkup(btn))

  elif type == "edituserbot":
     _bot = await db.get_userbot(user_id)
     if not _bot:
        return await query.answer("this userbot was removed already", show_alert=True)
     btn = [[InlineKeyboardButton('❌ Rᴇᴍᴏᴠᴇ', callback_data="settings#removeuserbot")],
            [InlineKeyboardButton('⫷ Bᴀᴄᴋ', callback_data="settings#bots")]]
     await query.message.edit_text(
        Script.USER_DETAILS.format(_bot['name'], _bot['id'], _bot['username']),
        reply_markup=InlineKeyboardMarkup(btn))

  elif type.startswith("removebot"):
     bot_id = int(type.split('_')[1])
     await db.remove_bot(user_id, bot_id)
     await query.message.edit_text(
        "<b>successfully updated</b>",
        reply_markup=back_button("settings#bots"))

  elif type == "removeallbots":
     await db.remove_bot(user_id)
     await query.message.edit_text(
        "<b>successfully removed all your bots</b>",
        reply_markup=back_button("settings#bots"))

  elif type == "removeuserbot":
     await db.remove_userbot(user_id)
     await query.message.edit_text(
        "<b>successfully updated</b>",
        reply_markup=back_button("settings#bots"))

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01
  elif type == "channels":
     btn = []
     channels = await db.get_user_channels(user_id)
     for channel in channels:
        btn.append([InlineKeyboardButton(f"🏷 {channel['title']}",
                         callback_data=f"settings#editchannels_{channel['chat_id']}")])
     btn.append([InlineKeyboardButton('✚ Aᴅᴅ Cʜᴀɴɴᴇʟ', callback_data="settings#addchannel")])
     btn.append([InlineKeyboardButton('⫷ Bᴀᴄᴋ', callback_data="settings#main")])
     await query.message.edit_text(
       "<b><u>My Channels</b></u>\n\n<b>you can manage your target chats in here</b>",
       reply_markup=InlineKeyboardMarkup(btn))

  elif type == "addchannel":
     await query.answer()
     await query.message.delete()
     try:
        ask = await bot.ask(chat_id=user_id, timeout=300, text=
           "<b>❪ SET TARGET CHAT ❫</b>\n\n"
           "<b>Send any of these:</b>\n"
           "<b>➣ forward a message from your target chat</b>\n"
           "<b>➣ paste the chat id</b> <code>(-1001234567890)</code>\n"
           "<b>➣ paste the chat username</b> <code>(@mychannel)</code>\n"
           "<b>➣ paste a message link of the chat</b>\n\n"
           "/cancel - <code>cancel this process</code>")
     except ListenerTimeout:
        return await bot.send_message(user_id, "<b>time out ! process cancelled.</b>")
     if ask.text and ask.text.strip().startswith('/'):
        return await ask.reply_text("<b>process canceled</b>", reply_markup=back_button("settings#channels"))
     chat_id = None
     if ask.forward_from_chat:
        chat_id = ask.forward_from_chat.id
     elif ask.text:
        chat_id, _ = parse_chat(ask.text)
     if chat_id is None:
        return await ask.reply("<b>Invalid chat id / username / link</b>",
                               reply_markup=back_button("settings#channels"))
     try:
        chat = await bot.get_chat(chat_id)
     except Exception as e:
        return await ask.reply(f"<b>I can't read that chat:</b> <code>{e}</code>\n\n"
                               "<i>add your main bot in that chat first.</i>",
                               reply_markup=back_button("settings#channels"))
     if chat.type not in [enums.ChatType.CHANNEL, enums.ChatType.SUPERGROUP, enums.ChatType.GROUP]:
        return await ask.reply("<b>Only channels / groups can be a target chat</b>",
                               reply_markup=back_button("settings#channels"))
     username = "@" + chat.username if chat.username else "private"
     added = await db.add_channel(user_id, chat.id, chat.title, username)
     await ask.reply_text(
        "<b>Successfully updated</b>" if added else "<b>This channel already added</b>",
        reply_markup=back_button("settings#channels"))

  elif type.startswith("editchannels"):
     chat_id = int(type.split('_')[1])
     chat = await db.get_channel_details(user_id, chat_id)
     if not chat:
        return await query.answer("this channel was removed already", show_alert=True)
     btn = [[InlineKeyboardButton('❌ Rᴇᴍᴏᴠᴇ', callback_data=f"settings#removechannel_{chat_id}")],
            [InlineKeyboardButton('⫷ Bᴀᴄᴋ', callback_data="settings#channels")]]
     await query.message.edit_text(
        f"<b><u>📄 CHANNEL DETAILS</b></u>\n\n<b>- TITLE:</b> <code>{chat['title']}</code>\n"
        f"<b>- CHANNEL ID: </b> <code>{chat['chat_id']}</code>\n<b>- USERNAME:</b> {chat['username']}",
        reply_markup=InlineKeyboardMarkup(btn))

  elif type.startswith("removechannel"):
     chat_id = int(type.split('_')[1])
     await db.remove_channel(user_id, chat_id)
     await query.message.edit_text(
        "<b>successfully updated</b>",
        reply_markup=back_button("settings#channels"))

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01
  elif type == "caption":
     btn = []
     caption = (await get_configs(user_id))['caption']
     if caption is None:
        btn.append([InlineKeyboardButton('✚ Aᴅᴅ Cᴀᴘᴛɪᴏɴ', callback_data="settings#addcaption")])
     else:
        btn.append([InlineKeyboardButton('👀 Sᴇᴇ Cᴀᴘᴛɪᴏɴ', callback_data="settings#seecaption"),
                    InlineKeyboardButton('🗑️ Dᴇʟᴇᴛᴇ', callback_data="settings#deletecaption")])
     btn.append([InlineKeyboardButton('⫷ Bᴀᴄᴋ', callback_data="settings#main")])
     await query.message.edit_text(
        "<b><u>CUSTOM CAPTION</b></u>\n\n<b>You can set a custom caption to videos and documents. Normaly use its default caption</b>\n\n<b><u>AVAILABLE FILLINGS:</b></u>\n- <code>{filename}</code> : Filename\n- <code>{size}</code> : File size\n- <code>{caption}</code> : default caption",
        reply_markup=InlineKeyboardMarkup(btn))

  elif type == "seecaption":
     data = await get_configs(user_id)
     btn = [[InlineKeyboardButton('🖋️ Eᴅɪᴛ Cᴀᴘᴛɪᴏɴ', callback_data="settings#addcaption")],
            [InlineKeyboardButton('⫷ Bᴀᴄᴋ', callback_data="settings#caption")]]
     await query.message.edit_text(
        f"<b><u>YOUR CUSTOM CAPTION</b></u>\n\n<code>{data['caption']}</code>",
        reply_markup=InlineKeyboardMarkup(btn))

  elif type == "deletecaption":
     await update_configs(user_id, 'caption', None)
     await query.message.edit_text(
        "<b>successfully updated</b>",
        reply_markup=back_button("settings#caption"))

  elif type == "addcaption":
     await query.answer()
     await query.message.delete()
     try:
        caption = await bot.ask(user_id, "Send your custom caption\n/cancel - <code>cancel this process</code>", timeout=300)
     except ListenerTimeout:
        return await bot.send_message(user_id, "<b>time out ! process cancelled.</b>")
     if not caption.text or caption.text.strip().startswith('/'):
        return await bot.send_message(user_id, "<b>process canceled !</b>",
                   reply_markup=back_button("settings#caption"))
     try:
         caption.text.format(filename='', size='', caption='')
     except KeyError as e:
         return await caption.reply_text(
            f"<b>wrong filling {e} used in your caption. change it</b>",
            reply_markup=back_button("settings#caption"))
     await update_configs(user_id, 'caption', caption.text.html)
     await caption.reply_text(
        "<b>successfully updated</b>",
        reply_markup=back_button("settings#caption"))

  elif type == "button":
     btn = []
     button = (await get_configs(user_id))['button']
     if button is None:
        btn.append([InlineKeyboardButton('✚ Aᴅᴅ Bᴜᴛᴛᴏɴ', callback_data="settings#addbutton")])
     else:
        btn.append([InlineKeyboardButton('👀 Sᴇᴇ Bᴜᴛᴛᴏɴ', callback_data="settings#seebutton"),
                    InlineKeyboardButton('🗑️ Rᴇᴍᴏᴠᴇ', callback_data="settings#deletebutton")])
     btn.append([InlineKeyboardButton('⫷ Bᴀᴄᴋ', callback_data="settings#main")])
     await query.message.edit_text(
        "<b><u>CUSTOM BUTTON</b></u>\n\n<b>You can set a inline button to messages.</b>\n\n<b><u>FORMAT:</b></u>\n`[Forward bot][buttonurl:https://t.me/mychannelurl]`\n",
        reply_markup=InlineKeyboardMarkup(btn))

  elif type == "addbutton":
     await query.answer()
     await query.message.delete()
     try:
        ask = await bot.ask(user_id, timeout=300, text="**Send your custom button.\n\nFORMAT:**\n`[forward bot][buttonurl:https://t.me/url]`\n")
     except ListenerTimeout:
        return await bot.send_message(user_id, "<b>time out ! process cancelled.</b>")
     if not ask.text or ask.text.strip().startswith('/'):
        return await bot.send_message(user_id, "<b>process canceled !</b>",
                   reply_markup=back_button("settings#button"))
     button = parse_buttons(ask.text.html)
     if not button:
        return await ask.reply("**INVALID BUTTON**", reply_markup=back_button("settings#button"))
     await update_configs(user_id, 'button', ask.text.html)
     await ask.reply("**Successfully button added**",
              reply_markup=back_button("settings#button"))

  elif type == "seebutton":
     button = (await get_configs(user_id))['button']
     button = parse_buttons(button or '', markup=False) or []
     button.append([InlineKeyboardButton("⫷ Bᴀᴄᴋ", "settings#button")])
     await query.message.edit_text(
        "**YOUR CUSTOM BUTTON**",
        reply_markup=InlineKeyboardMarkup(button))

  elif type == "deletebutton":
     await update_configs(user_id, 'button', None)
     await query.message.edit_text(
        "**Successfully button deleted**",
        reply_markup=back_button("settings#button"))

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

  elif type == "filters":
     await query.message.edit_text(
        "<b><u>💠 CUSTOM FILTERS 💠</b></u>\n\n**configure the type of messages which you want forward**",
        reply_markup=await filters_buttons(user_id))

  elif type == "nextfilters":
     await query.edit_message_reply_markup(
        reply_markup=await next_filters_buttons(user_id))

  elif type.startswith("updatefilter"):
     i, key, value = type.split('-')
     await update_configs(user_id, key, value != "True")
     if key in ['poll', 'protect', 'voice', 'animation', 'sticker']:
        return await query.edit_message_reply_markup(
           reply_markup=await next_filters_buttons(user_id))
     await query.edit_message_reply_markup(
        reply_markup=await filters_buttons(user_id))

  elif type == "file_size":
     size = (await get_configs(user_id))['min_size'] or 0
     await query.message.edit_text(
        f'<b><u>SIZE LIMIT</b></u><b>\n\nyou can set file Minimum size limit to forward\n\nfiles with greater than `{size} MB` will forward</b>',
        reply_markup=size_button(size))

  elif type == "maxfile_size":
     size = (await get_configs(user_id))['max_size'] or 0
     await query.message.edit_text(
        f'<b><u>Max SIZE LIMIT</b></u><b>\n\nyou can set file Maximum size limit to forward\n\nfiles with less than `{size} MB` will forward</b>',
        reply_markup=maxsize_button(size))

  elif type.startswith("update_size"):
     size = int(type.split('-')[1])
     if size > 4000:
        return await query.answer("size limit exceeded", show_alert=True)
     await update_configs(user_id, 'min_size', size)
     await query.message.edit_text(
        f'<b><u>SIZE LIMIT</b></u><b>\n\nyou can set file Minimum size limit to forward\n\nfiles with greater than `{size} MB` will forward</b>',
        reply_markup=size_button(size))

  elif type.startswith("maxupdate_size"):
     size = int(type.split('-')[1])
     if size > 4000:
        return await query.answer("size limit exceeded", show_alert=True)
     await update_configs(user_id, 'max_size', size)
     await query.message.edit_text(
        f'<b><u>Max SIZE LIMIT</b></u><b>\n\nyou can set file Maximum size limit to forward\n\nfiles with less than `{size} MB` will forward</b>',
        reply_markup=maxsize_button(size))

  elif type == "add_extension":
     await query.answer()
     await query.message.delete()
     try:
        ext = await bot.ask(user_id, text="**please send your extensions (seperete by space)**", timeout=300)
     except ListenerTimeout:
        return await bot.send_message(user_id, "<b>time out ! process cancelled.</b>")
     if not ext.text or ext.text.strip().startswith('/'):
        return await bot.send_message(user_id, "<b>process canceled</b>",
                   reply_markup=back_button("settings#get_extension"))
     extensions = [e for e in ext.text.split() if e]
     extension = (await get_configs(user_id))['extension'] or []
     extension = list(dict.fromkeys(extension + extensions))
     await update_configs(user_id, 'extension', extension)
     await ext.reply_text("**successfully updated**",
         reply_markup=back_button("settings#get_extension"))

  elif type == "get_extension":
     extensions = (await get_configs(user_id))['extension']
     btn = extract_btn(extensions)
     text = "**🕹 Extensions**" if extensions else "**No Extensions Here**"
     btn.append([InlineKeyboardButton('✚ Aᴅᴅ', 'settings#add_extension')])
     if extensions:
        btn.append([InlineKeyboardButton('🗑 Rᴇᴍᴏᴠᴇ Aʟʟ', 'settings#rmve_all_extension')])
     btn.append([InlineKeyboardButton('⫷ Bᴀᴄᴋ', 'settings#extra')])
     await query.message.edit_text(
         text=f"<b><u>EXTENSIONS</u></b>\n\n**Files with these extentions will not forward**\n\n{text}",
         reply_markup=InlineKeyboardMarkup(btn))

  elif type == "rmve_all_extension":
     await update_configs(user_id, 'extension', None)
     await query.message.edit_text(text="**successfully deleted**",
                                   reply_markup=back_button("settings#get_extension"))

  elif type == "add_keyword":
     await query.answer()
     await query.message.delete()
     try:
        ask = await bot.ask(user_id, text="**please send the keywords (seperete by space Like:- English 1080p Hdrip)**", timeout=300)
     except ListenerTimeout:
        return await bot.send_message(user_id, "<b>time out ! process cancelled.</b>")
     if not ask.text or ask.text.strip().startswith('/'):
        return await bot.send_message(user_id, "<b>process canceled</b>",
                   reply_markup=back_button("settings#get_keyword"))
     keywords = [k for k in ask.text.split() if k]
     keyword = (await get_configs(user_id))['keywords'] or []
     keyword = list(dict.fromkeys(keyword + keywords))
     await update_configs(user_id, 'keywords', keyword)
     await ask.reply_text("**successfully updated**",
         reply_markup=back_button("settings#get_keyword"))

  elif type == "get_keyword":
     keywords = (await get_configs(user_id))['keywords']
     btn = extract_btn(keywords)
     text = "**🔖 Keywords:**" if keywords else "**You didn't Added Any Keywords**"
     btn.append([InlineKeyboardButton('✚ Aᴅᴅ', 'settings#add_keyword')])
     if keywords:
        btn.append([InlineKeyboardButton('🗑 Rᴇᴍᴏᴠᴇ Aʟʟ', 'settings#rmve_all_keyword')])
     btn.append([InlineKeyboardButton('⫷ Bᴀᴄᴋ', 'settings#extra')])
     await query.message.edit_text(
         text=f"<b><u>Keywords</u></b>\n\n**Only files with these keywords in file name will forward**\n\n{text}",
         reply_markup=InlineKeyboardMarkup(btn))

  elif type == "rmve_all_keyword":
     await update_configs(user_id, 'keywords', None)
     await query.message.edit_text(text="**successfully deleted All Keywords**",
                                   reply_markup=back_button("settings#get_keyword"))

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01
  elif type == "dump":
     if user_id != Config.BOT_OWNER:
        return await query.answer("this is only for my owner", show_alert=True)
     dump = await db.get_dump_chat()
     btn = [[InlineKeyboardButton('✚ Sᴇᴛ Dᴜᴍᴘ Cʜᴀᴛ', callback_data="settings#setdump")]]
     if dump:
        btn.append([InlineKeyboardButton('❌ Rᴇᴍᴏᴠᴇ Dᴜᴍᴘ', callback_data="settings#rmvedump")])
     btn.append([InlineKeyboardButton('⫷ Bᴀᴄᴋ', callback_data="settings#main")])
     await query.message.edit_text(
        Script.DUMP_TXT.format(dump if dump else "not set"),
        reply_markup=InlineKeyboardMarkup(btn))

  elif type == "setdump":
     if user_id != Config.BOT_OWNER:
        return await query.answer("this is only for my owner", show_alert=True)
     await query.answer()
     await query.message.delete()
     try:
        ask = await bot.ask(user_id, timeout=300, text=
           "<b>❪ SET DUMP CHAT ❫</b>\n\n"
           "<b>Forward a message from the dump chat, or paste the chat id / username / message link.</b>\n\n"
           "/cancel - <code>cancel this process</code>")
     except ListenerTimeout:
        return await bot.send_message(user_id, "<b>time out ! process cancelled.</b>")
     if ask.text and ask.text.strip().startswith('/'):
        return await ask.reply_text("<b>process canceled</b>", reply_markup=back_button("settings#dump"))
     chat_id = None
     if ask.forward_from_chat:
        chat_id = ask.forward_from_chat.id
     elif ask.text:
        chat_id, _ = parse_chat(ask.text)
     if chat_id is None:
        return await ask.reply("<b>Invalid chat id / username / link</b>",
                               reply_markup=back_button("settings#dump"))
     try:
        chat = await bot.get_chat(chat_id)
        k = await bot.send_message(chat.id, "<code>dump chat connected ✅</code>")
        await k.delete()
     except Exception as e:
        return await ask.reply(f"<b>I can't post in that chat:</b> <code>{e}</code>\n\n"
                               "<i>make me admin in the dump chat first.</i>",
                               reply_markup=back_button("settings#dump"))
     await db.set_dump_chat(chat.id)
     temp.DUMP_CHAT = chat.id
     await ask.reply(f"<b>Successfully dump chat set to</b> <code>{chat.id}</code>",
                     reply_markup=back_button("settings#dump"))

  elif type == "rmvedump":
     if user_id != Config.BOT_OWNER:
        return await query.answer("this is only for my owner", show_alert=True)
     await db.set_dump_chat(0)
     temp.DUMP_CHAT = 0
     await query.message.edit_text("<b>successfully removed your dump chat</b>",
                                   reply_markup=back_button("settings#main"))

  elif type.startswith("alert"):
     alert = type.split('_', 1)[1]
     await query.answer(alert, show_alert=True)

  else:
     await query.answer()

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

@Client.on_message(filters.private & filters.command('dump') & filters.user(Config.BOT_OWNER))
async def dump_cmd(client, message):
   """Owner shortcut for the dump chat panel."""
   dump = await db.get_dump_chat()
   btn = [[InlineKeyboardButton('✚ Sᴇᴛ Dᴜᴍᴘ Cʜᴀᴛ', callback_data="settings#setdump")]]
   if dump:
      btn.append([InlineKeyboardButton('❌ Rᴇᴍᴏᴠᴇ Dᴜᴍᴘ', callback_data="settings#rmvedump")])
   btn.append([InlineKeyboardButton('⫷ Bᴀᴄᴋ', callback_data="settings#main")])
   await message.reply_text(
      Script.DUMP_TXT.format(dump if dump else "not set"),
      reply_markup=InlineKeyboardMarkup(btn))

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01


# Ask Doubt on telegram @KingVJ01
