# 🤖 VJ Forward Bot

<p align="center">
  <b>An advanced Telegram message-forwarding bot built with Pyrogram</b><br>
  Forward messages between channels with multi-bot round-robin, duplicate detection, smart filters, and more.
</p>

<p align="center">
  <a href="https://t.me/VJForwardBot"><img src="https://img.shields.io/badge/Bot-@VJForwardBot-blue?logo=telegram" alt="Bot"/></a>
  <a href="https://t.me/vj_botz"><img src="https://img.shields.io/badge/Updates-@vj__botz-blue?logo=telegram" alt="Updates"/></a>
  <a href="https://t.me/vj_bot_disscussion"><img src="https://img.shields.io/badge/Support-Group-green?logo=telegram" alt="Support"/></a>
  <a href="https://youtube.com/@Tech_VJ"><img src="https://img.shields.io/badge/YouTube-Tech__VJ-red?logo=youtube" alt="YouTube"/></a>
  <img src="https://img.shields.io/badge/Python-3.10+-yellow?logo=python" alt="Python"/>
</p>

<p align="center">
  <b>Auto Restart All User Forwarding After Bot Restarted.</b><br><br>
  <img src="https://readme-typing-svg.herokuapp.com/?lines=Welcome+To+VJ+Forward+Bot+!" alt="Typing SVG"/>
</p>

---

## ✨ Features

- **Multi-Bot Round-Robin** — Add multiple bots to share the forwarding workload; speed scales linearly (20 msgs/min per bot)
- **Userbot Support** — Forward from private channels using a Pyrogram session string or phone-number OTP login
- **Smart Auto-Router** — Optionally let the bot pick the fastest available engine automatically
- **Duplicate Detection** — Skip already-forwarded files using file-ID tracking (optional per-user MongoDB URI)
- **Custom Caption** — Override captions with dynamic placeholders: `{filename}`, `{size}`, `{caption}`
- **Custom Inline Buttons** — Attach URL buttons to forwarded messages using a simple syntax
- **Media Filters** — Toggle forwarding per type: documents, videos, photos, audio, voice, animations, stickers, polls, text
- **File Size Filters** — Set minimum and/or maximum file size limits (MB)
- **Extension Filters** — Allow or block specific file extensions with regex
- **Keyword Filters** — Forward only files whose names match a keyword/regex pattern
- **Secure Forward** — Protect forwarded messages from being re-forwarded
- **Forward Tag Toggle** — Strip or preserve the original "Forwarded from" tag
- **Duplicate Removal (/unequify)** — Scan a channel and delete duplicate documents
- **Broadcast** — Send a message to all bot users (owner only)
- **Live Progress** — Real-time status bar with percentage, ETA, and cancel button
- **Auto-Restart on Boot** — Resumes interrupted forwards after bot restart
- **Configurable Speed** — Tune batch size, sleep delay, and stagger per user
- **Flask Health Endpoint** — `/` returns `Hello from Koyeb` for uptime monitors

> To know about all features, join the [Update Channel](https://t.me/VJ_Botz).

---

## 🛠️ Tech Stack

| Component | Library |
|-----------|---------|
| Telegram MTProto | [Pyrofork](https://github.com/Mayuri-Chan/pyrofork) (Pyrogram fork) |
| Async MongoDB | [Motor](https://motor.readthedocs.io/) + [PyMongo](https://pymongo.readthedocs.io/) |
| Web server | Flask + Gunicorn |
| Crypto | TgCrypto |
| System stats | psutil |

---

## ⚙️ Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `API_ID` | ✅ | Telegram API ID from [my.telegram.org](https://my.telegram.org) |
| `API_HASH` | ✅ | Telegram API Hash from [my.telegram.org](https://my.telegram.org) |
| `BOT_TOKEN` | ✅ | Bot token from [@BotFather](https://t.me/BotFather) |
| `DATABASE_URI` | ✅ | MongoDB connection string — [Video Tutorial](https://youtu.be/DAHRmFdw99o) |
| `BOT_OWNER` | ✅ | Your Telegram user ID |
| `DATABASE_NAME` | ❌ | MongoDB database name (default: `vj-forward-bot`) |
| `BOT_SESSION` | ❌ | Pyrogram session string (optional, for userbot mode) |

---

## 🚀 Deployment

### How To Deploy — [Video Tutorial](https://youtu.be/A-iIh_5WAlk)

### Run Locally

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/vj-forward-bot.git
cd vj-forward-bot

# 2. Install dependencies
pip3 install -r requirements.txt

# 3. Set environment variables (or create a .env file)
export API_ID=your_api_id
export API_HASH=your_api_hash
export BOT_TOKEN=your_bot_token
export DATABASE_URI=your_mongo_uri
export BOT_OWNER=your_telegram_id

# 4. Start the bot
python3 main.py
```

### Deploy on Koyeb / Railway / Heroku

1. Fork this repository.
2. Create a new app and link your fork.
3. Set all required environment variables from the table above.
4. Set the start command to `python3 main.py`.
5. (Optional) Run Gunicorn alongside for the health endpoint: `gunicorn app:app`.

### Deploy with Docker

```bash
docker build -t vj-forward-bot .
docker run -d \
  -e API_ID=your_api_id \
  -e API_HASH=your_api_hash \
  -e BOT_TOKEN=your_bot_token \
  -e DATABASE_URI=your_mongo_uri \
  -e BOT_OWNER=your_telegram_id \
  vj-forward-bot
```

---

## 📖 Usage

### Before Forwarding

1. Start the bot and send `/settings`.
2. **Add a Bot** — Create a bot via [@BotFather](https://t.me/BotFather), then paste the token.
3. **Add a Target Channel** — Forward any message from your target channel to register it.
4. Make sure your added bot (or userbot) is **admin** in the target channel.

### Commands

```
start      - check I'm alive
forward    - forward messages
unequify   - delete duplicate media messages in chats
settings   - configure your settings
stop       - stop your ongoing tasks
reset      - reset your settings
restart    - restart server (owner only)
resetall   - reset all users settings (owner only)
broadcast  - broadcast a message to all your users (owner only)
```

### Forwarding Engines

When you run `/forward`, you choose an engine:

| Engine | Speed | Requirement |
|--------|-------|-------------|
| 🤖 **Bots (N)** | N × 20 msgs/min | N bots added in settings |
| 👤 **Userbot** | ~20 msgs/min | Session string or phone login |
| ⚡ **Auto (Smart Router)** | Best available | At least one bot + userbot |

---

## 🗂️ Project Structure

```
├── main.py              # Entry point — starts the Pyrogram client
├── config.py            # Config and temp state classes
├── database.py          # Db class — all MongoDB operations
├── script.py            # All bot text/templates
├── app.py               # Flask health-check endpoint
├── requirements.txt     # Python dependencies
└── plugins/
    ├── regix.py         # Core forwarding engine (round-robin, userbot, auto)
    ├── public.py        # /forward command handler
    ├── commands.py      # /start, /help, /about, status callbacks
    ├── settings.py      # /settings panel and all sub-menus
    ├── broadcast.py     # /broadcast command
    ├── test.py          # CLIENT class, session handling, helpers
    ├── unequeify.py     # /unequify duplicate-removal command
    ├── utils.py         # STS (status tracker) class
    └── db.py            # Per-user MongoDB helper (for duplicate tracking)
```

---

## 🔧 Settings Panel

All settings are per-user and persisted in MongoDB.

| Setting | Description |
|---------|-------------|
| **Bots** | Add / remove forwarding bots; view speed estimate |
| **Userbot** | Add / remove a userbot session |
| **Channels** | Add / remove target channels |
| **Filters** | Toggle each media type on/off |
| **Caption** | Set a custom caption template |
| **Button** | Attach inline URL buttons |
| **Extensions** | Block/allow file extensions |
| **Keywords** | Forward only matching filenames |
| **Min/Max Size** | File size limits in MB |
| **Database** | Personal MongoDB URI for duplicate tracking |
| **Speed** | Tune batch size and sleep delay |
| **Extra** | Forward tag, protect content, duplicate skip |

---

## 📺 Tutorial

- 🎬 [How to Deploy](https://youtu.be/A-iIh_5WAlk)
- 🎬 [How to Use VJ Forward Bot](https://youtu.be/wO1FE-lf35I)
- 🎬 [MongoDB Setup](https://youtu.be/DAHRmFdw99o)

---

## 🙏 Credits

- **Developer:** [King VJ](https://t.me/kingvj01)
- **Updates Channel:** [@vj_botz](https://t.me/vj_botz)
- **Support Group:** [@vj_bot_disscussion](https://t.me/vj_bot_disscussion)
- **YouTube:** [Tech_VJ](https://youtube.com/@Tech_VJ)

> ⚠️ **Please do not remove credits.** This project is shared for educational and personal use. Respect the developer's work.

---

## 📄 License

This project is provided as-is for personal use. Redistribution without credit to the original developer ([@VJ_Botz](https://t.me/VJ_Botz)) is not permitted.
