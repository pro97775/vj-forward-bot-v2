# 🤖 VJ Forward Bot

> **Advanced Telegram Message Forwarding Bot with Multi-Bot Support, Auto-Restart, and Smart Filtering**

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Pyrogram](https://img.shields.io/badge/Pyrogram-2.x-green)
![MongoDB](https://img.shields.io/badge/MongoDB-Atlas%2FSelf--Hosted-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## 📋 Table of Contents

- [Features](#-features)
- [Screenshots](#-screenshots)
- [Deployment](#-deployment)
  - [Video Tutorial](#-video-tutorial)
  - [Heroku](#-heroku)
  - [Koyeb](#-koyeb)
  - [VPS](#-vps)
- [Environment Variables](#-environment-variables)
- [Bot Commands](#-bot-commands)
- [Settings Guide](#-settings-guide)
- [How to Use](#-how-to-use)
- [Multi-Bot System](#-multi-bot-system)
- [Speed / Batch Settings](#-speed--batch-settings)
- [Architecture](#-architecture)
- [Credits](#-credits)
- [Disclaimer](#-disclaimer)

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🔄 **Public Forward** | Forward messages from public channels without admin permission |
| 🔒 **Private Forward** | Forward from private channels using UserBot (session-based) |
| 🤖 **Multi-Bot Support** | Add multiple bots to increase forwarding speed (round-robin) |
| ⚡ **Smart Router** | Auto-select best engine (Bots / UserBot / Combined) |
| 📝 **Custom Caption** | Set custom captions with dynamic placeholders `{filename}`, `{size}`, `{caption}` |
| 🔘 **Custom Button** | Add inline buttons to forwarded messages |
| 🗑️ **Skip Duplicates** | Automatically skip duplicate media files |
| 🔍 **Keyword Filter** | Forward only files matching specific keywords |
| 🎬 **Extension Filter** | Block/allow specific file extensions |
| 📊 **Size Filter** | Set min/max file size limits |
| 🏷️ **Message Type Filters** | Toggle forwarding for text, photo, video, audio, document, sticker, etc. |
| 🔄 **Auto Restart** | Automatically resumes pending forwards after bot restart |
| 📢 **Broadcast** | Owner-only broadcast to all users |
| 📈 **Live Progress** | Real-time forwarding status with percentage, ETA, and stats |
| ⚙️ **Speed Control** | Adjustable batch size, delay, and stagger settings |
| 🗃️ **MongoDB Support** | Persistent duplicate tracking across restarts |
| 🧹 **Duplicate Cleaner** | `/unequify` command to remove duplicate files from chats |

---

## 📸 Screenshots

*Add screenshots of the bot in action here*

---

## 🚀 Deployment

### 🎥 Video Tutorial

[![Watch Tutorial](https://img.shields.io/badge/YouTube-Watch%20Tutorial-red)](https://youtu.be/A-iIh_5WAlk)

---

### 🔷 Heroku

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=YOUR_REPO_URL)

1. Click the **Deploy** button above
2. Fill in the required environment variables
3. Click **Deploy app**

---

### 🔶 Koyeb

1. Fork this repository
2. Go to [Koyeb](https://app.koyeb.com) and create a new app
3. Connect your GitHub repository
4. Set the **Build Command**: `pip install -r requirements.txt`
5. Set the **Run Command**: `gunicorn app:app & python3 main.py`
6. Add environment variables
7. Deploy!

---

### 🖥️ VPS (Ubuntu/Debian)

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/vj-forward-bot.git
cd vj-forward-bot

# 2. Install Python 3.10+ if not already installed
sudo apt update && sudo apt install python3 python3-pip -y

# 3. Install dependencies
pip3 install -r requirements.txt

# 4. Set environment variables (or create .env file)
export API_ID=your_api_id
export API_HASH=your_api_hash
export BOT_TOKEN=your_bot_token
export BOT_OWNER=your_telegram_id
export DATABASE_URI=your_mongodb_uri

# 5. Run the bot
python3 main.py
```

**For background execution:**
```bash
# Using screen
screen -S forwardbot
python3 main.py
# Press Ctrl+A then D to detach

# Using systemd (recommended for production)
sudo nano /etc/systemd/system/forwardbot.service
```

Add the following:
```ini
[Unit]
Description=VJ Forward Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/vj-forward-bot
ExecStart=/usr/bin/python3 main.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable forwardbot
sudo systemctl start forwardbot
sudo systemctl status forwardbot
```

---

## 🔐 Environment Variables

| Variable | Required | Description | How to Get |
|----------|----------|-------------|------------|
| `API_ID` | ✅ Yes | Telegram API ID | [my.telegram.org](https://my.telegram.org) |
| `API_HASH` | ✅ Yes | Telegram API Hash | [my.telegram.org](https://my.telegram.org) |
| `BOT_TOKEN` | ✅ Yes | Bot Token from @BotFather | [@BotFather](https://t.me/BotFather) |
| `BOT_OWNER` | ✅ Yes | Your Telegram Numeric ID | [@userinfobot](https://t.me/userinfobot) |
| `DATABASE_URI` | ✅ Yes | MongoDB Connection URI | [MongoDB Atlas](https://mongodb.com) or self-hosted |
| `DATABASE_NAME` | ❌ No | Database name (default: `vj-forward-bot`) | — |
| `BOT_SESSION` | ❌ No | Custom session name | — |

### 🎬 MongoDB Setup Video

[![MongoDB Tutorial](https://img.shields.io/badge/YouTube-MongoDB%20Setup-blue)](https://youtu.be/DAHRmFdw99o)

---

## 🛠️ Bot Commands

| Command | Access | Description |
|---------|--------|-------------|
| `/start` | Everyone | Start the bot and see welcome message |
| `/forward` | Everyone | Begin message forwarding process |
| `/settings` | Everyone | Configure bot settings |
| `/stop` | Everyone | Cancel ongoing forwarding task |
| `/reset` | Everyone | Reset personal settings to default |
| `/unequify` | Everyone | Remove duplicate media from a chat |
| `/restart` | Owner Only | Restart the bot server |
| `/resetall` | Owner Only | Reset ALL users' settings |
| `/broadcast` | Owner Only | Broadcast message to all users (reply to a message) |

---

## Commands

```
start - check I'm alive 
forward - forward messages
unequify - delete duplicate media messages in chats
settings - configure your settings
stop - stop your ongoing tasks
reset - reset your settings
restart - restart server (owner only)
resetall - reset all users settings (owner only)
broadcast - broadcast a message to all your users (owner only)
```

## ⚙️ Settings Guide

Access settings via `/settings` or the **⚙ Settings** button.

### 🤖 Bots
- Add multiple Telegram bots for faster forwarding
- Add a UserBot (via session string or phone login) for private channels
- View and remove added bots

### 🏷️ Channels
- Add target channels where messages will be forwarded
- Forward a message from the target channel to add it

### 🖋️ Custom Caption
Set dynamic captions using placeholders:
- `{filename}` — Original file name
- `{size}` — Human-readable file size
- `{caption}` — Original caption

Example: `📁 {filename}\n💾 Size: {size}\n📝 {caption}`

### ⏹️ Custom Button
Add inline buttons in format:
```
[Button Text][buttonurl:https://t.me/yourchannel]
```

### 🕵️‍♀️ Filters
Toggle message types to forward:
- Text, Photo, Video, Audio, Document, Voice, Animation, Sticker, Poll
- Forward Tag (show original sender)
- Skip Duplicate
- Secure Message (protect content)

### 🗃️ MongoDB
Add a custom MongoDB URL for **permanent duplicate tracking** across bot restarts.

### 🧪 Extra Settings
- **Min/Max Size Limit** — Filter by file size (MB)
- **Keywords** — Only forward files containing these words
- **Extensions** — Block specific file extensions

### ⚡ Speed / Batch Settings
- **Batch Size**: Messages per bot per turn (5–100)
- **Base Delay**: Seconds between messages per bot (0.5–10.0s)
- **Stagger Delay**: Pause between bot switches (0.0–2.0s)

---

## 📖 How to Use

### Forwarding Messages

1. **Add a Bot or UserBot**
   - Go to `/settings` → **🤖 Bots** → **✚ Add Bot**
   - Send the bot token from [@BotFather](https://t.me/BotFather)
   - (Optional) Add a UserBot for private channels

2. **Add Target Channel**
   - Go to `/settings` → **🏷️ Channels** → **✚ Add Channel**
   - Forward any message from your target channel

3. **Start Forwarding**
   - Send `/forward`
   - Select target channel (if multiple)
   - Send the **last message** or **last message link** from source channel
   - Enter skip number (how many messages to skip from start)
   - Choose forwarding engine: **Bots**, **UserBot**, or **Auto**
   - Click **Yes** to confirm

4. **Monitor Progress**
   - Live status updates with:
     - Fetched messages
     - Successfully forwarded
     - Duplicates skipped
     - Deleted/Filtered messages
     - Percentage and ETA

5. **Cancel Anytime**
   - Send `/stop` or click **Cancel** button

### Removing Duplicates

1. Send `/unequify`
2. Forward last message or send link of target chat
3. Send `/yes` to confirm
4. Bot will scan and delete duplicate media files

---

## 🤖 Multi-Bot System

The bot supports **multiple bot accounts** to dramatically increase forwarding speed:

| Bots Added | Estimated Speed |
|------------|-----------------|
| 1 Bot | ~20 msgs/min |
| 2 Bots | ~40 msgs/min |
| 3 Bots | ~60 msgs/min |
| 5 Bots | ~100 msgs/min |

### How it works:
- **Round-Robin**: Messages are distributed across all active bots
- **Auto-handling**: If one bot hits a FloodWait, others continue
- **Smart Sleep**: Dynamic delay calculation based on active bot count

### Adding More Bots:
1. Create additional bots via [@BotFather](https://t.me/BotFather)
2. Add each bot token in `/settings` → **🤖 Bots**
3. Make **ALL** bots admin in the target channel

---

## ⚡ Speed / Batch Settings

Fine-tune forwarding speed to balance between **speed** and **FloodWait safety**:

| Setting | Default | Range | Effect |
|---------|---------|-------|--------|
| Batch Size | 20 | 5–100 | Messages processed per bot per turn |
| Base Delay | 3.0s | 0.5–10.0s | Sleep time between messages per bot |
| Stagger Delay | 0.2s | 0.0–2.0s | Pause when switching between bots |

> ⚠️ **Warning**: Lower delays increase speed but risk **FloodWait** penalties from Telegram.

---

## 🏗️ Architecture

```
vj-forward-bot/
├── app.py              # Flask app (for Koyeb/Heroku health checks)
├── main.py             # Main entry point (Pyrogram client)
├── config.py           # Configuration and environment variables
├── database.py         # MongoDB database operations (Db class)
├── db.py               # User-specific MongoDB connection helper
├── db_helpers.py       # Multi-bot database helper methods
├── script.py           # All bot text messages and UI strings
├── utils.py            # STS class for forward status tracking
├── broadcast.py        # Owner broadcast functionality
├── commands.py         # Main bot commands (/start, /restart, etc.)
├── settings.py         # Settings menu and configuration UI
├── public.py           # /forward command and engine selection
├── regix.py            # Core forwarding engines (round-robin, userbot)
├── test.py             # Bot/UserBot client creation and session handling
├── test_manual_bot_or_string.py  # Alternative manual bot/string handler
├── unequeify.py        # Duplicate message removal (/unequify)
├── requirements.txt    # Python dependencies
├── runtime.txt         # Python runtime version
└── run cmd.txt         # Production run command
```

### Core Components

| File | Purpose |
|------|---------|
| `regix.py` | **Engine A**: Multi-bot round-robin forwarding<br>**Engine B**: Single-client userbot forwarding<br>**Smart Router**: Auto-selects best engine |
| `database.py` | All MongoDB operations: users, bots, channels, forwards, configs, batch settings |
| `utils.py` | `STS` class — tracks forward progress, stats, and state |
| `test.py` | `CLIENT` class — handles bot token validation and userbot session creation |
| `public.py` | `/forward` command flow — from channel selection to engine choice |
| `settings.py` | Interactive settings menu with inline keyboards |

---

## 🧪 Requirements

```
pyrofork
tgcrypto
pyropatch
humanize
motor==2.5.1
TgCrypto
dnspython==2.2.1
pymongo[srv]==3.13.0
umongo==3.0.1
psutil
pytz
Flask==2.0.2
gunicorn==20.1.0
Jinja2==3.0.3
werkzeug==2.0.2
itsdangerous==2.0.1
```

**Python Version:** `3.10.8` or higher

---

## 🙏 Credits

- **Developer**: [King VJ 👑](https://t.me/kingvj01)
- **Channel**: [VJ Botz](https://t.me/vj_botz)
- **Support**: [VJ Bot Discussion](https://t.me/vj_bot_disscussion)
- **YouTube**: [Tech VJ](https://youtube.com/@Tech_VJ)

---

## ⚠️ Disclaimer

> This bot is provided for educational purposes only. The developer is not responsible for any misuse or account bans that may occur from using this bot. 
>
> **UserBot Warning**: Using a userbot (real Telegram account session) carries a risk of account ban. Use a fake/secondary account if possible.
>
> Always ensure you have proper permissions before forwarding content from any channel.

---

## 📜 License

This project is licensed under the MIT License.

---

## 💝 Support

If you find this project helpful, consider:

- ⭐ Starring the repository
- 📢 Sharing with friends
- 💬 Joining our [Support Group](https://t.me/vj_bot_disscussion)
- 📺 Subscribing to [YouTube](https://youtube.com/@Tech_VJ)

---

<p align="center">
  <b>Made with ❤️ by <a href="https://t.me/kingvj01">King VJ</a></b>
</p>

<p align="center">
  <a href="https://t.me/vj_botz">Update Channel</a> •
  <a href="https://t.me/vj_bot_disscussion">Support Group</a> •
  <a href="https://youtube.com/@Tech_VJ">YouTube</a>
</p>
