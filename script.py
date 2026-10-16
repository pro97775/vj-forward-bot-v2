class Script(object):
    START_TXT = """<blockquote><b>👋 Hey {0}! Welcome to Advanced Multi-Bot Forwarder</b></blockquote>

<blockquote><b>⚡ High-Speed Telegram Forwarding Engine</b>
Forward messages across public & private channels with an automated <b>Multi-Bot Round-Robin Pool</b>, smart captioning, 1-click auto-cleaners, and persistent deduplication.</blockquote>

<blockquote><b>✨ Core Highlights</b>
• <b>🤖 Multi-Bot Pool:</b> Rotate multiple bots (20 msgs/min each) with auto-scaled delay & dynamic FloodWait recovery
• <b>🔓 Public & Private:</b> Bot Pool for public/admin chats • Userbot for restricted private chats
• <b>⏸ Pause & Resume:</b> Pause anytime with <code>/stop</code> and continue via <code>/resume</code>
• <b>📝 Smart Captions & Cleaners:</b> Dynamic <code>{{filename}}</code>, <code>{{size}}</code>, <code>{{caption}}</code>, Prefix/Suffix, link/username strippers & word replacer</blockquote>

<i>👇 Tap a button below to configure or start forwarding:</i>"""

    HELP_TXT = """<blockquote><b>📖 COMMANDS & FEATURE GUIDE</b></blockquote>

<blockquote><b>⌨️ Available Commands</b>
• <code>/start</code> — Open the main dashboard
• <code>/forward</code> — Launch a new forwarding task
• <code>/stop</code> — Safely pause your active task (saves exact offset)
• <code>/resume</code> — Resume a paused or interrupted task
• <code>/unequify</code> — Scan & delete duplicate media in a channel
• <code>/settings</code> — Configure bots, channels, captions, cleaners & filters
• <code>/reset</code> — Reset all settings & caches to default</blockquote>

<blockquote><b>🚀 Engine Capabilities</b>
• <b>Multi-Bot Round-Robin Pool:</b> Paste multiple bot tokens at once. Delay scales automatically (<code>1 bot = 3.0s</code>, <code>2 = 1.5s</code>, <code>3 = 1.0s</code>, <code>6 = 0.5s</code>).
• <b>Smart Caption Engine:</b> Customize captions with <code>{filename}</code>, <code>{size}</code>, <code>{caption}</code>, plus Prefix & Suffix blocks.
• <b>1-Click Auto-Cleaners:</b> Strip <code>@usernames</code>, <code>t.me</code> links, web URLs, HTML <code>&lt;a&gt;</code> tags, or replace/remove custom words.
• <b>Granular Filters & Dedup:</b> Toggle 9 media types, Min/Max MB size, keyword allowlist, extension blocklist & unpacked file ID deduplication.</blockquote>"""

    HOW_USE_TXT = """<blockquote><b>🚀 QUICK 4-STEP SETUP GUIDE</b></blockquote>

<blockquote><b>1️⃣ Build Your Worker Bot Pool (or Userbot)</b>
• Open <code>/settings</code> ➔ <b>🤖 Bot Manager</b>.
• Paste one or multiple bot tokens from @BotFather to build your <b>Round-Robin Pool</b>.
• <i>Optional:</i> Add a <b>Userbot Session</b> for private source chats where bots aren't admins.</blockquote>

<blockquote><b>2️⃣ Add Your Target Channel(s)</b>
• Open <code>/settings</code> ➔ <b>📢 Target Channels</b>.
• Promote all worker bots in your pool (or your Userbot) to <b>Admin</b> in the target channel.</blockquote>

<blockquote><b>3️⃣ Customize Captions, Cleaners & Filters</b>
• Configure Prefix/Suffix, 1-click link/username cleaners, word replacements, and media filters in <code>/settings</code>.</blockquote>

<blockquote><b>4️⃣ Start, Pause & Resume</b>
• Send <code>/forward</code>, pick your target chat, forward the last message (or link) from the source chat, and hit <b>🚀 Start Forwarding</b>!
• Use <code>/stop</code> to pause safely and <code>/resume</code> to continue anytime.</blockquote>

🎥 <a href="https://youtu.be/wO1FE-lf35I">Watch Video Tutorial</a>"""

    ABOUT_TXT = """<blockquote><b>ℹ️ ABOUT ADVANCED FORWARD BOT</b></blockquote>

<blockquote>┌ <b>🤖 Bot Name:</b> <a href="https://t.me/VJForwardBot">Advanced Forward Bot</a>
├ <b>👨‍💻 Developer:</b> <a href="https://t.me/kingvj01">King VJ 👑</a>
├ <b>📢 Updates:</b> <a href="https://t.me/vj_botz">VJ Botz</a>
├ <b>🐍 Runtime:</b> <code>Python 3.11 Async</code>
├ <b>📚 Framework:</b> <code>Pyrofork (MTProto)</code>
├ <b>⚙️ Engine:</b> <code>Multi-Bot Round-Robin v3.0</code>
└ <b>🗄 Database:</b> <code>MongoDB Motor Async</code></blockquote>"""

    STATUS_TXT = """<blockquote><b>📊 LIVE BOT STATISTICS</b></blockquote>

<blockquote>┌ <b>⏳ Bot Uptime:</b> <code>{}</code>
├ <b>👥 Total Users:</b> <code>{}</code>
├ <b>🤖 Pool Bots & Sessions:</b> <code>{}</code>
└ <b>🔄 Active / Saved Tasks:</b> <code>{}</code></blockquote>"""

    FROM_MSG = """<blockquote><b>📥 STEP 2 OF 3 — SET SOURCE CHAT</b></blockquote>

<blockquote>Forward the <b>last message</b> from the source chat, or send its <b>Telegram message link</b>:
• Example: <code>https://t.me/channel_name/1500</code>
• Private Link: <code>https://t.me/c/123456789/1500</code></blockquote>

<i>Send /cancel to abort this setup.</i>"""

    TO_MSG = """<blockquote><b>📤 STEP 1 OF 3 — CHOOSE TARGET CHAT</b></blockquote>

<blockquote>Select your destination channel from the reply keyboard below.</blockquote>

<i>Send /cancel to abort this setup.</i>"""

    SKIP_MSG = """<blockquote><b>⏭ STEP 3 OF 3 — STARTING MESSAGE OFFSET</b></blockquote>

<blockquote>Enter the starting message ID (number of initial messages to skip):
• Send <code>0</code> to start from the very first message
• Send <code>100</code> to skip the first 100 messages</blockquote>

<i>Send /cancel to abort this setup.</i>"""

    CANCEL = "<blockquote><b>🚫 Operation cancelled successfully.</b></blockquote>"

    BOT_DETAILS = """<blockquote><b>🤖 WORKER BOT PROFILE</b></blockquote>

<blockquote>┌ <b>🏷 Name:</b> <code>{}</code>
├ <b>🆔 Bot ID:</b> <code>{}</code>
├ <b>🔗 Username:</b> @{}
└ <b>⚡ Rate Limit:</b> <code>20 msgs / 60s sliding window</code></blockquote>"""

    USER_DETAILS = """<blockquote><b>👤 USERBOT SESSION PROFILE</b></blockquote>

<blockquote>┌ <b>🏷 Name:</b> <code>{}</code>
├ <b>🆔 User ID:</b> <code>{}</code>
├ <b>🔗 Username:</b> @{}
└ <b>🔓 Access:</b> <code>Public & Private Restricted Chats</code></blockquote>"""

    TEXT = """<blockquote><b>{title}</b>
<code>{progress_bar}</code> <b>{percentage}%</b></blockquote>

<blockquote>┌ <b>📥 Fetched:</b> <code>{fetched}</code> / <code>{total}</code>
├ <b>✅ Forwarded:</b> <code>{forwarded}</code>
├ <b>♻️ Duplicates Skipped:</b> <code>{duplicate}</code>
├ <b>🔍 Filtered Out:</b> <code>{filtered}</code>
├ <b>🗑 Deleted / Empty:</b> <code>{deleted}</code>
└ <b>⏭ Initial Offset:</b> <code>{skip}</code></blockquote>

<blockquote>┌ <b>🤖 Engine:</b> <code>{mode_label}</code>
├ <b>⏱ Auto Delay:</b> <code>{delay}s</code>
├ <b>📡 Status:</b> <code>{status}</code>
└ <b>⏳ Est. Remaining:</b> <code>{eta}</code></blockquote>"""

    PROGRESS_ALERT = (
        "📊 Progress: {percentage}%\n"
        "📥 Fetched: {fetched}\n"
        "✅ Forwarded: {forwarded}\n"
        "⏳ Remaining: {remaining}\n"
        "📡 Status: {status}\n"
        "⏱ Elapsed: {uptime}\n"
        "🏁 Est. Left: {eta}"
    )

    DUPLICATE_TEXT = """<blockquote><b>🧹 CHANNEL DEDUPLICATION (/unequify)</b></blockquote>

<blockquote>┌ <b>🔎 Media Scanned:</b> <code>{}</code>
├ <b>🗑 Duplicates Deleted:</b> <code>{}</code>
└ <b>📡 Status:</b> <code>{}</code></blockquote>"""

    DOUBLE_CHECK = """<blockquote><b>🔍 CONFIRM FORWARDING TASK</b></blockquote>

<blockquote>┌ <b>🤖 Forwarding Mode:</b> <code>{mode_title}</code>
├ <b>⚡ Pool Rate / Delay:</b> <code>{rate_info}</code>
├ <b>📥 Source Chat:</b> <code>{from_chat}</code>
├ <b>📤 Target Chat:</b> <code>{to_chat}</code>
├ <b>⏭ Start Offset:</b> <code>{skip}</code>
└ <b>📨 Last Message ID:</b> <code>{limit}</code></blockquote>

<blockquote><b>⚠️ Pre-Flight Checklist</b>
• Ensure your worker bot(s) or Userbot are <b>Admin</b> in <code>{to_chat}</code>.
• For private source chats, make your bot(s) Admin there or switch mode to <b>Userbot Session</b>.</blockquote>

<i>👇 Click <b>🚀 Start Forwarding</b> or switch mode below:</i>"""

    SETTINGS_TXT = """<blockquote><b>⚙️ CONTROL PANEL & SETTINGS</b></blockquote>

<blockquote>Manage your <b>Multi-Bot Round-Robin Pool</b>, <b>Target Channels</b>, <b>Smart Caption Engine</b>, <b>1-Click Auto-Cleaners</b>, and <b>Granular Media Filters</b> from the menu below:</blockquote>"""