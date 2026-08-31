class  Script(object):
  START_TXT = """<b>ʜɪ {}
  
ɪ'ᴍ ᴀ ᴀᴅᴠᴀɴᴄᴇᴅ ꜰᴏʀᴡᴀʀᴅ ʙᴏᴛ
ɪ ᴄᴀɴ ꜰᴏʀᴡᴀʀᴅ ᴀʟʟ ᴍᴇssᴀɢᴇ ꜰʀᴏᴍ ᴏɴᴇ ᴄʜᴀɴɴᴇʟ ᴛᴏ ᴀɴᴏᴛʜᴇʀ ᴄʜᴀɴɴᴇʟ</b>

**ᴄʟɪᴄᴋ ʜᴇʟᴘ ʙᴜᴛᴛᴏɴ ᴛᴏ ᴋɴᴏᴡ ᴍᴏʀᴇ ᴀʙᴏᴜᴛ ᴍᴇ**"""
  HELP_TXT = """<b><u>🔆 Help</b></u>

<u>**📚 Available commands:**</u>
<b>⏣ __/start - check I'm alive__ 
⏣ __/forward - forward messages__
⏣ __/settings - configure your settings__
⏣ __/unequify - delete duplicate media messages in chats__
⏣ __/dump - set owner dump chat (owner only)__
⏣ __/stop - stop your ongoing tasks__
⏣ __/reset - reset your settings__</b>

<b><u>💢 Features:</b></u>
<b>► __Forward message from public channel to your channel without admin permission. if the channel is private need admin permission, if you can't give admin permission then use userbot, but in userbot there is a chance to get your account ban so use fake account__
► __Multiple bots round robin forwarding (each bot forwards only the configured messages per minute)__
► __custom caption__
► __custom button__
► __forwarding delay control from bot__
► __owner dump chat cloning__
► __duplicate cleaning with /unequify (telegram file hash)__
► __filter type of messages__</b>
"""
  
  HOW_USE_TXT = """<b><u>⚠️ Before Forwarding:</b></u>
<b>► __add a bot or userbot__
► __add atleast one to channel__ `(your bot/userbot must be admin in there)`
► __You can add chats or bots by using /settings__
► __if the **From Channel** is private your userbot must be member in there or your bot must need admin permission in there also__
► __Then use /forward to forward messages__

► ʜᴏᴡ ᴛᴏ ᴜsᴇ ᴍᴇ [ᴛᴜᴛᴏʀɪᴀʟ ᴠɪᴅᴇᴏ](https://youtu.be/wO1FE-lf35I)</b>"""
  
  ABOUT_TXT = """<b>
╔════❰ ғᴏʀᴡᴀʀᴅ ʙᴏᴛ ❱═❍⊱❁۪۪
║╭━━━━━━━━━━━━━━━➣
║┣⪼📃ʙᴏᴛ : [Fᴏʀᴡᴀᴅ Bᴏᴛ](https://t.me/VJForwardBot)
║┣⪼👦Cʀᴇᴀᴛᴏʀ : [Kɪɴɢ VJ 👑](https://t.me/kingvj01)
║┣⪼🤖Uᴘᴅᴀᴛᴇ : [VJ Bᴏᴛᴢ](https://t.me/vj_botz)
║┣⪼📡Hᴏsᴛᴇᴅ ᴏɴ : Sᴜᴘᴇʀ Fᴀsᴛ
║┣⪼🗣️Lᴀɴɢᴜᴀɢᴇ : Pʏᴛʜᴏɴ3
║┣⪼📚Lɪʙʀᴀʀʏ : Pʏʀᴏɢʀᴀᴍ Gᴀᴛʜᴇʀ 2.11.0 
║┣⪼🗒️Vᴇʀsɪᴏɴ : 0.18.3
║╰━━━━━━━━━━━━━━━➣
╚══════════════════❍⊱❁۪۪
</b>"""
  STATUS_TXT = """
╔════❰ ʙᴏᴛ sᴛᴀᴛᴜs  ❱═❍⊱❁۪۪
║╭━━━━━━━━━━━━━━━➣
║┣⪼**⏳ ʙᴏᴛ ᴜᴘᴛɪᴍᴇ:**`{}`
║┃
║┣⪼**👱 Tᴏᴛᴀʟ Usᴇʀs:** `{}`
║┃
║┣⪼**🤖 Tᴏᴛᴀʟ Bᴏᴛ:** `{}`
║┃
║┣⪼**🏷 Tᴏᴛᴀʟ Cʜᴀɴɴᴇʟs:** `{}`
║┃
║┣⪼**🔃 Fᴏʀᴡᴀʀᴅɪɴɢs:** `{}`
║┃
║┣⪼**⚡ Rᴜɴɴɪɴɢ Nᴏᴡ:** `{}`
║┃
║┣⪼**🗃 Dᴜᴍᴘ Cʜᴀᴛ:** `{}`
║┃
║╰━━━━━━━━━━━━━━━➣
╚══════════════════❍⊱❁۪۪
"""
  MY_STATS = """<b><u>📊 YOUR STATS</b></u>

<b>➣ 🤖 Yᴏᴜʀ Bᴏᴛs:</b> <code>{bots}</code>
<b>➣ 👤 Uꜱᴇʀʙᴏᴛ:</b> <code>{userbot}</code>
<b>➣ 🏷 Tᴀʀɢᴇᴛ Cʜᴀᴛs:</b> <code>{channels}</code>
<b>➣ ⚡ Sᴘᴇᴇᴅ:</b> <code>{speed} msg / minute</code>
<b>➣ ⏱ Bᴏᴛ Dᴇʟᴀʏ:</b> <code>{bot_delay} s</code>
<b>➣ ⏱ Uꜱᴇʀʙᴏᴛ Dᴇʟᴀʏ:</b> <code>{userbot_delay} s</code>
<b>➣ 📨 Pᴇʀ Bᴏᴛ Rᴀᴛᴇ:</b> <code>{rate} / minute</code>
<b>➣ 🏷 Fᴏʀᴡᴀʀᴅ Tᴀɢ:</b> <code>{tag}</code>
<b>➣ 🔃 Tᴀꜱᴋ Rᴜɴɴɪɴɢ:</b> <code>{running}</code>"""
  DUMP_TXT = """<b><u>🗃 DUMP CHAT</b></u>

<b>Every message forwarded by any user is cloned in to this chat also.</b>

<b>➣ Cᴜʀʀᴇɴᴛ:</b> <code>{}</code>

<i>Your main bot must be admin in the dump chat.</i>"""
  DELAY_TXT = """<b><u>⏱ FORWARDING DELAY</b></u>

<b>➣ Bᴏᴛ Dᴇʟᴀʏ:</b> <code>{} s</code>
<b>➣ Uꜱᴇʀʙᴏᴛ Dᴇʟᴀʏ:</b> <code>{} s</code>
<b>➣ Pᴇʀ Bᴏᴛ Rᴀᴛᴇ:</b> <code>{} messages / minute</code>

<i>Round robin: every bot forwards only the rate above in one minute, then the next bot is used. Userbot works alone with its own delay.</i>"""
  FROM_MSG = "<b>❪ SET SOURCE CHAT ❫\n\nForward the last message or last message link of source chat.\n/cancel - cancel this process</b>"
  TO_MSG = "<b>❪ CHOOSE TARGET CHAT ❫\n\nChoose your target chat from the given buttons.\n/cancel - Cancel this process</b>"
  SKIP_MSG = "<b>❪ SET MESSAGE SKIPING NUMBER ❫</b>\n\n<b>Skip the message as much as you enter the number and the rest of the message will be forwarded\nDefault Skip Number =</b> <code>0</code>\n<code>eg: You enter 0 = 0 message skiped\n You enter 5 = 5 message skiped</code>\n/cancel <b>- cancel this process</b>"
  CANCEL = "<b>Process Cancelled Succefully !</b>"
  BOT_DETAILS = "<b><u>📄 BOT DETAILS</b></u>\n\n<b>➣ NAME:</b> <code>{}</code>\n<b>➣ BOT ID:</b> <code>{}</code>\n<b>➣ USERNAME:</b> @{}"
  USER_DETAILS = "<b><u>📄 USERBOT DETAILS</b></u>\n\n<b>➣ NAME:</b> <code>{}</code>\n<b>➣ USER ID:</b> <code>{}</code>\n<b>➣ USERNAME:</b> @{}"  
         
  TEXT = """
╔════❰ ғᴏʀᴡᴀʀᴅ sᴛᴀᴛᴜs  ❱═❍⊱❁۪۪
║╭━━━━━━━━━━━━━━━➣
║┣⪼<b>🕵 ғᴇᴄʜᴇᴅ Msɢ :</b> <code>{}</code>
║┃
║┣⪼<b>✅ sᴜᴄᴄᴇғᴜʟʟʏ Fᴡᴅ :</b> <code>{}</code>
║┃
║┣⪼<b>🗃 Dᴜᴍᴘᴇᴅ Msɢ :</b> <code>{}</code>
║┃
║┣⪼<b>🗑 ᴅᴇʟᴇᴛᴇᴅ Msɢ :</b> <code>{}</code>
║┃
║┣⪼<b>🪆 Sᴋɪᴘᴘᴇᴅ Msɢ :</b> <code>{}</code>
║┃
║┣⪼<b>🔁 Fɪʟᴛᴇʀᴇᴅ Msɢ :</b> <code>{}</code>
║┃
║┣⪼<b>🤖 Wᴏʀᴋɪɴɢ Bᴏᴛs :</b> <code>{}</code>
║┃
║┣⪼<b>📊 Cᴜʀʀᴇɴᴛ Sᴛᴀᴛᴜs:</b> <code>{}</code>
║┃
║┣⪼<b>𖨠 Pᴇʀᴄᴇɴᴛᴀɢᴇ:</b> <code>{}</code> %
║╰━━━━━━━━━━━━━━━➣ 
╚════❰ {} ❱══❍⊱❁۪۪
"""
  PROGRESS = """
📊 Pᴇʀᴄᴇɴᴛᴀɢᴇ: {} %

🕵 Fᴇᴛᴄʜᴇᴅ: {}
✅ Fᴏʀᴡᴀʀᴅᴇᴅ: {}
🔄 Rᴇᴍᴀɪɴɪɴɢ: {}

📈 Sᴛᴀᴛᴜs: {}
⏳ Esᴛɪᴍᴀᴛᴇᴅ Tɪᴍᴇ: {}
⏱ Rᴜɴɴɪɴɢ Sɪɴᴄᴇ: {}
"""
  DUPLICATE_TEXT = """
╔════❰ ᴜɴᴇǫᴜɪғʏ sᴛᴀᴛᴜs ❱═❍⊱❁۪۪
║╭━━━━━━━━━━━━━━━➣
║┣⪼ <b>ғᴇᴛᴄʜᴇᴅ ғɪʟᴇs:</b> <code>{}</code>
║┃
║┣⪼ <b>ᴅᴜᴘʟɪᴄᴀᴛᴇ ᴅᴇʟᴇᴛᴇᴅ:</b> <code>{}</code> 
║╰━━━━━━━━━━━━━━━➣
╚════❰ {} ❱══❍⊱❁۪۪
"""
  DOUBLE_CHECK = """<b><u>DOUBLE CHECKING ⚠️</b></u>
<code>Before forwarding the messages Click the Yes button only after checking the following</code>

<b>★ YOUR BOTS:</b> {bots}
<b>★ FROM CHANNEL:</b> `{from_chat}`
<b>★ TO CHANNEL:</b> `{to_chat}`
<b>★ SKIP MESSAGES:</b> `{skip}`
<b>★ SPEED:</b> `{speed} messages / minute`

<i>° All the bots above must be admin in **TARGET CHAT**</i> (`{to_chat}`)
<i>° If the **SOURCE CHAT** is private your userbot must be member or your bots must be admin in there also</i>

<b>If the above is checked then the yes button can be clicked</b>"""
  
SETTINGS_TXT = """<b>change your settings as your wish</b>"""
