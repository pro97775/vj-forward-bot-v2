class  Script(object):
  START_TXT = """<b>ʜɪ {}
  
ɪ'ᴍ ᴀ ᴀᴅᴠᴀɴᴄᴇᴅ ꜰᴏʀᴡᴀʀᴅ ʙᴏᴛ
ɪ ᴄᴀɴ ꜰᴏʀᴡᴀʀᴅ ᴀʟʟ ᴍᴇssᴀɢᴇ ꜰʀᴏᴍ ᴏɴᴇ ᴄʜᴀɴɴᴇʟ ᴛᴏ ᴀɴᴏᴛʜᴇʀ ᴄʜᴀɴɴᴇʟ</b>

**ᴄʟɪᴄᴋ ʜᴇʟᴘ ʙᴜᴛᴛᴏɴ ᴛᴏ ᴋɴᴏᴡ ᴍᴏʀᴇ ᴀʙᴏᴜᴛ ᴍᴇ**"""
  HELP_TXT = """<b><u>🔆 Help</b></u>

<u><b>📚 Commands</b></u>
<b>⏣ /start — check I'm alive
⏣ /forward — forward messages (also /fwd)
⏣ /settings — configure everything
⏣ /watch — auto-forward new posts from a channel
⏣ /watches — list & stop your watches
⏣ /tasks — history of your finished forwards
⏣ /unequify — delete duplicate media in a chat
⏣ /stop — stop your ongoing task
⏣ /reset — reset your settings</b>

<u><b>💢 Features</b></u>
<b>► Forward from public channels with no admin rights needed
► <u>Multi-bot parallel engine</u> — add N bots, get ~N× the speed
► Fan-out: send to several target channels in one task
► Message-ID ranges (e.g. <code>500-1500</code>) as well as plain skip
► 🧪 Dry run — preview what would be forwarded, send nothing
► Skip duplicates — fully database-backed, zero RAM growth
► Custom caption & inline button
► Per-type filters (video, doc, photo, audio, text, …)
► Min/max file size, keyword, and extension filters (block or allow-only)
► Auto-resume after a restart</b>

<i>Private sources need a userbot member, or your bots as admins.</i>
"""
  
  HOW_USE_TXT = """<b><u>⚠️ Before Forwarding</b></u>
<b>1. Add one or more bots via /settings → Bots
   <i>Each extra bot multiplies your speed — they work in parallel.</i>
2. Add at least one target channel via /settings → Channels
   <i>Every bot must be an admin there.</i>
3. If the source is private, add a userbot (or make your bots admins there).
4. Run /forward and pick an engine.</b>

<b><u>💡 Tips</b></u>
<b>► At the skip prompt you can send a <u>range</u> like <code>500-1500</code>
► Turn on 🧪 Dry Run (Extra Settings) to preview a big task first
► Add a MongoDB URL so skip-duplicate survives restarts
► Hitting FloodWait? Raise the delay in ⚡ Speed
► Use /watch to keep mirroring a channel continuously</b>

<b>► ʜᴏᴡ ᴛᴏ ᴜsᴇ ᴍᴇ [ᴛᴜᴛᴏʀɪᴀʟ ᴠɪᴅᴇᴏ](https://youtu.be/wO1FE-lf35I)</b>"""
  
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
║┣⪼**🔃 Fᴏʀᴡᴀʀᴅɪɴɢs:** `{}`
║┃
║╰━━━━━━━━━━━━━━━➣
╚══════════════════❍⊱❁۪۪
"""
  FROM_MSG = "<b>❪ SET SOURCE CHAT ❫\n\nForward the last message or last message link of source chat.\n/cancel - cancel this process</b>"
  TO_MSG = "<b>❪ CHOOSE TARGET CHAT ❫\n\nChoose a target chat from the buttons below, or pick <code>ALL CHANNELS</code> to forward to every one of them at once.\n/cancel - Cancel this process</b>"
  SKIP_MSG = """<b>❪ SET RANGE OR SKIP COUNT ❫</b>

<b>Send a number to skip that many messages from the start:</b>
<code>0</code> — forward everything
<code>500</code> — start from message 500

<b>Or send an explicit ID range:</b>
<code>500-1500</code> — only messages 500 to 1500

<i>A range also makes the progress percentage accurate.</i>

/cancel <b>- cancel this process</b>"""
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
║┣⪼<b>👥 ᴅᴜᴘʟɪᴄᴀᴛᴇ Msɢ :</b> <code>{}</code>
║┃
║┣⪼<b>🗑 ᴅᴇʟᴇᴛᴇᴅ Msɢ :</b> <code>{}</code>
║┃
║┣⪼<b>🪆 Sᴋɪᴘᴘᴇᴅ Msɢ :</b> <code>{}</code>
║┃
║┣⪼<b>🔁 Fɪʟᴛᴇʀᴇᴅ Msɢ :</b> <code>{}</code>
║┃
║┣⪼<b>📊 Cᴜʀʀᴇɴᴛ Sᴛᴀᴛᴜs:</b> <code>{}</code>
║┃
║┣⪼<b>𖨠 Pᴇʀᴄᴇɴᴛᴀɢᴇ:</b> <code>{}</code> %
║╰━━━━━━━━━━━━━━━➣ 
╚════❰ {} ❱══❍⊱❁۪۪
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

<b>★ YOUR BOT:</b> [{botname}](t.me/{botuname})
<b>★ FROM CHANNEL:</b> `{from_chat}`
<b>★ TO CHANNEL:</b> `{to_chat}`
<b>★ SKIP MESSAGES:</b> `{skip}`

<i>° [{botname}](t.me/{botuname}) must be admin in **TARGET CHAT**</i> (`{to_chat}`)
<i>° If the **SOURCE CHAT** is private your userbot must be member or your bot must be admin in there also</b></i>

<b>If the above is checked then the yes button can be clicked</b>"""
  
SETTINGS_TXT = """<b>change your settings as your wish</b>"""
