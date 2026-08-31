# VJ Forward Bot

A Telegram bot that copies messages from one channel to another. Point it at a
source, pick your targets, and it walks the history forwarding everything that
passes your filters — with multiple bots working in parallel for speed.

---

## Table of contents

- [What it does](#what-it-does)
- [Quick start](#quick-start)
- [Environment variables](#environment-variables)
- [Deploying](#deploying)
- [Command reference](#command-reference)
- [First forward, step by step](#first-forward-step-by-step)
- [The settings panel](#the-settings-panel)
- [Engines and speed](#engines-and-speed)
- [Duplicate skipping](#duplicate-skipping)
- [Continuous mode](#continuous-mode)
- [Owner tools](#owner-tools)
- [Troubleshooting](#troubleshooting)
- [Security notes](#security-notes)
- [Development](#development)
- [Project layout](#project-layout)

---

## What it does

- **Multi-bot parallel forwarding.** Add N bot tokens and they send
  concurrently. Throughput scales roughly linearly with bot count.
- **Userbot support** for private sources your bots cannot join.
- **Fan-out** to several target channels in a single task.
- **ID ranges** (`500-1500`) as well as plain skip counts.
- **Dry run** to preview exactly what a task would forward, sending nothing.
- **Duplicate skipping**, fully database-backed — nothing is held in RAM.
- **Custom captions and inline buttons** on every forwarded message.
- **Filters** by message type, filename keyword, extension, and file size.
- **Auto-resume** — an interrupted task picks up where it stopped after a
  restart.
- **Continuous watch mode** that mirrors new posts as they are published.
- **Task history** so you can see what previous runs actually did.

---

## Quick start

You need Python 3.10 or newer, a MongoDB database, and a Telegram API keypair.

```bash
git clone <your-fork-url>
cd vj-forward-bot

python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Set the five required variables and run:

```bash
export API_ID=1234567
export API_HASH=your_api_hash
export BOT_TOKEN=123456:ABC-your-bot-token
export DATABASE_URI="mongodb+srv://user:pass@cluster.mongodb.net"
export BOT_OWNER=your_numeric_telegram_id

python3 main.py
```

On boot the bot validates its config, pings MongoDB, creates indexes, restores
any watches, and resumes interrupted forwards. If something is missing it tells
you exactly which variable and exits instead of failing later with a confusing
traceback.

### Where to get the credentials

| Value | Where |
|---|---|
| `API_ID`, `API_HASH` | [my.telegram.org](https://my.telegram.org) → API development tools |
| `BOT_TOKEN` | [@BotFather](https://t.me/BotFather) → `/newbot` |
| `DATABASE_URI` | [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) free tier is fine |
| `BOT_OWNER` | [@userinfobot](https://t.me/userinfobot) will tell you your ID |

For Atlas, allow access from anywhere (`0.0.0.0/0`) unless you know your host's
egress IP, or connections will silently time out.

---

## Environment variables

### Required

| Variable | Description |
|---|---|
| `API_ID` | Telegram API ID (integer) |
| `API_HASH` | Telegram API hash |
| `BOT_TOKEN` | Token for the main controller bot |
| `DATABASE_URI` | MongoDB connection string |
| `BOT_OWNER` | Your numeric Telegram user ID |

### Optional

| Variable | Default | Description |
|---|---|---|
| `DATABASE_NAME` | `vj-forward-bot` | Mongo database name |
| `BOT_SESSION` | `VJ-Forward-Bot` | Pyrogram session name |
| `PORT` | `8080` | Port for the health endpoint |
| `WEB_SERVER` | `true` | Serve `GET /health`; disable for a pure worker |
| `DUP_HOT_CACHE` | `0` | File IDs cached in RAM per task (`0` = none) |
| `DUP_TTL_HOURS` | `72` | Hours before fallback duplicate records self-expire |
| `STATUS_TTL` | `86400` | Seconds before finished task state is swept |
| `SWEEP_INTERVAL` | `1800` | Seconds between background sweeps (`0` = off) |
| `PROGRESS_DB_INTERVAL` | `10` | Min seconds between progress writes to Mongo |
| `ALLOW_GIT_RESTART` | `false` | Let `/restart` run `git pull` + `pip install` |

Duplicate checking keeps **nothing** in RAM by default — every check is one
atomic upsert in MongoDB, so memory is flat no matter how many files a task
processes. `DUP_HOT_CACHE` trades a little memory for fewer database round
trips if you have RAM to spare; at `50000` it costs roughly 5–8 MB per task.

`ALLOW_GIT_RESTART` is off by default because it executes whatever is on your
remote branch. Only turn it on if you control the repository.

---

## Deploying

### Docker

```bash
docker build -t vj-forward-bot .
docker run -d --name forward-bot \
  -e API_ID=1234567 \
  -e API_HASH=your_hash \
  -e BOT_TOKEN=your_token \
  -e DATABASE_URI="mongodb+srv://..." \
  -e BOT_OWNER=123456789 \
  -p 8080:8080 \
  vj-forward-bot
```

The image runs a single process that serves the health endpoint and the bot
together. There is no separate web command to start.

### Koyeb / Render / Railway

Deploy from the repository, set the environment variables above, and expose the
port from `PORT`. The health check path is `/health`.

### Heroku-style workers

`Procfile` declares `worker: python3 main.py`. On a worker-only dyno set
`WEB_SERVER=false`, since there is no port to bind.

---

## Command reference

### Everyone

| Command | What it does |
|---|---|
| `/start` | Check the bot is alive |
| `/forward` (or `/fwd`) | Start a forwarding task |
| `/settings` | Open the configuration panel |
| `/stop` | Request cancellation of your running task |
| `/watch` | Mirror new posts from a channel continuously |
| `/watches` | List and stop your active watches |
| `/tasks` | History of your last 10 finished tasks |
| `/unequify` | Delete duplicate media in a chat (needs a userbot) |
| `/reset` | Reset your settings to defaults |

### Owner only

| Command | What it does |
|---|---|
| `/broadcast` | Reply to a message to send it to every user |
| `/memory` | RSS, thread and task counts, live cache sizes |
| `/sweep` | Force-drop retained in-memory task state |
| `/restart` | Restart the process |
| `/resetall` | Clear every user's saved MongoDB URI |

---

## First forward, step by step

1. **Add a bot.** `/settings` → 🤖 Bots → ✚ Add bot. Create a bot with
   [@BotFather](https://t.me/BotFather) and forward its token message here.
   Repeat for as many bots as you want; each one increases throughput.

2. **Add a target channel.** `/settings` → 🏷 Channels → ✚ Add Channel. You can
   forward a message from it, send its `t.me` link, or send its numeric ID.
   **Every bot you added must be an admin in that channel** with permission to
   post.

3. **Handle a private source, if needed.** Public channels work with just bots.
   For a private source either add your bots as admins there, or add a userbot
   under `/settings` → 🤖 Bots → ✚ Add User bot.

4. **Preview first (recommended for big jobs).** `/settings` → Extra Settings →
   🧪 Dry Run → Turn ON. The next task walks the source and applies every filter
   but sends nothing, so you can confirm the counts before committing.

5. **Run `/forward`.** Pick a target (or `ALL CHANNELS`), send the last message
   link from the source, then send `0` to forward everything — or a range like
   `500-1500`.

6. **Choose an engine** from the confirmation screen and watch the progress bar.
   Cancel any time with the button or `/stop`.

---

## The settings panel

### 🤖 Bots

Add and remove bot tokens and one userbot. The panel shows an estimated
aggregate speed. Removing a bot does not affect a task already running.

### 🏷 Channels

Your target chats. With more than one saved, `/forward` lets you pick a single
target or fan out to all of them at once.

### 🖋️ Caption

A custom caption for videos, documents, audio, and photos. Available
placeholders:

| Placeholder | Becomes |
|---|---|
| `{filename}` | The file's name |
| `{size}` | Human-readable size, e.g. `1.42 GB` |
| `{caption}` | The original caption |

```
{filename}

Size: {size}
Join @mychannel
```

An invalid placeholder is rejected when you set it, not silently at forward
time.

### ⏹ Button

An inline button attached to every forwarded message:

```
[Join Channel][buttonurl:https://t.me/mychannel]
```

Add `:same` before the closing bracket to place a button on the same row as the
previous one.

### 🕵️ Filters

Toggle which message types are forwarded — text, documents, videos, photos,
audio, voice, animations, stickers, polls. Also here:

- **Forward tag** — keep the "Forwarded from" header. Faster (messages go in
  batches of 100) but captions and buttons cannot be customised.
- **Skip duplicate** — do not forward a file you have already sent this run.
- **Secure message** — mark forwarded content as protected from saving.

### 🗃 MongoDB

An optional second database that stores duplicate file IDs permanently. See
[Duplicate skipping](#duplicate-skipping).

### 🧪 Extra Settings

- **Min / max size limit** in MB. Set either to `0` to disable it. Both work
  independently, and together they define a window.
- **Keywords** — only forward files whose name matches at least one keyword.
- **Extensions** — filter by file extension, in one of two modes:
  - 🚫 **Block** (default) — files with these extensions are skipped.
  - ✅ **Allow only** — *only* files with these extensions are forwarded.

  Tap the mode button in the panel to switch. The leading dot is optional
  (`mp4` and `.mp4` are the same entry), matching is case-insensitive, and only
  the real end of the filename counts — `mp4` no longer matches
  `movie.mp4.part`. Extensions can be removed one at a time or all at once.
- **Dry run** — walk and filter without sending.

### ⚡ Speed

| Setting | Range | Meaning |
|---|---|---|
| Queue size | 5–100 | Messages buffered *per bot* before a dispatch round |
| Delay | 0.5–10.0 s | Interval per bot between sends |
| Stagger | 0.0–2.0 s | Offset between bot workers starting |

Because bots send in parallel, total throughput is approximately
`(60 / delay) × bot count` messages per minute. The default 3 s delay gives
20/min per bot: 1 bot ≈ 20/min, 2 bots ≈ 40/min, 3 bots ≈ 60/min, and so on.
Lower it for speed; if you start seeing FloodWait in the logs, raise it back.

The delay is an *interval*, not a pause tacked on after each send — a worker
sleeps only the remainder of its slot, so the time a send itself takes does not
eat into the rate. Queue size is multiplied by the number of active bots when
building a dispatch round, so every bot gets a full share of work and the pool
actually reaches the aggregate rate instead of leaving one bot to finish alone.

---

## Engines and speed

At the confirmation screen you choose how the work gets done.

**🤖 Bots** — every bot you added runs as an independent worker pulling from a
shared queue. Each paces itself with your configured delay, so the aggregate
rate scales with the number of bots while each individual bot stays within its
own limits. This is the fastest option and the right default.

**👤 Userbot** — a single user session, sequential. Slower, but it can read
private channels it is a member of without any admin rights.

**⚡ Auto** — prefers the bot pool, falls back to the userbot if you have no
bots.

Before any task starts, every client posts and deletes a test message in every
target. If one bot is not an admin, the task aborts immediately with a message
naming that bot rather than failing partway through.

### Rough throughput

| Setup | Approximate rate |
|---|---|
| 1 bot | 20 msgs/min |
| 3 bots | 60 msgs/min |
| 5 bots | 100 msgs/min |
| 1 userbot | 20 msgs/min |

Real numbers vary with file sizes, whether the forward tag is on (batches of
100 are much faster), and how aggressively Telegram is rate-limiting you.

---

## Duplicate skipping

With **Skip duplicate** on, the bot tracks file IDs it has already forwarded
and skips repeats.

Nothing is kept in RAM. Each file is checked with a single atomic upsert:

- **You added your own MongoDB URL** (`/settings` → 🗃 MongoDB) — checks run
  against your database, in a collection scoped to the task's target chat.
- **You did not** — checks run against the bot's own database, scoped to the
  task, with a TTL index (`DUP_TTL_HOURS`) so records expire on their own even
  if a task is killed mid-run.

Either way memory stays flat whether you process 100 files or 10 million. Set
`DUP_HOT_CACHE` above `0` to cache recently seen IDs in RAM and cut the number
of database round trips.

If MongoDB is briefly unreachable, the check reports "not a duplicate" so a
file is forwarded rather than silently dropped.

Adding a URL deletes your message immediately so the credentials do not sit in
your chat history, and the panel only ever displays a masked version.

---

## Continuous mode

`/forward` walks a fixed range once. `/watch` keeps going:

```
/watch
→ forward any message from the source channel
```

From then on, every new post there is copied to your target channels, with your
caption, button, type filters, and your keyword / extension / size filters
applied. Watches are stored in MongoDB and restored automatically when the bot
restarts.

`/watches` lists what you are watching and gives you a stop button for each.

The bot must be a **member of the source channel** — Telegram only delivers
channel updates to members.

---

## Owner tools

`/memory` is the one to reach for if you suspect a leak:

```
🧠 Memory report

RSS: 142.3 MB
VMS: 388.1 MB
Open FDs: 24
Threads: 5
asyncio tasks: 12

Task states held: 1
Active forwards: 1
Locks / cancels: 1 / 1
Busy targets: 1

Duplicate stores (RAM cache 0):
   • 123456789: 8432 checked, 117 dup · backend user-db · in RAM 0
```

`backend` tells you which database is answering duplicate checks: `user-db` is
the user's own MongoDB, `bot-db` is the bot's own fallback store. `in RAM`
should be `0` unless you raised `DUP_HOT_CACHE`.

Healthy behaviour during a long forward is RSS climbing early and then
flattening. "Task states held" should return to 0 shortly after tasks finish;
if it does not, `/sweep` clears retained state and tells you how much it freed.

---

## Troubleshooting

**"Make @yourbot an admin in the target chat"** — exactly what it says. Every
bot in the pool needs admin rights with post permission in every target. Add
the missing one and press ♻️ RETRY.

**Nothing forwards, no error** — check your filters. If a message type is
toggled off, or a keyword filter excludes everything, messages are counted as
"Filtered" rather than forwarded. Turn on Dry Run and watch the counters to see
which stage is dropping them.

**Cannot read the source channel** — public channels need nothing special. A
private one needs either your bots as admins there or a userbot that is a
member. "CHANNEL_INVALID" or "CHANNEL_PRIVATE" means no client you have can see
it.

**Progress percentage looks wrong** — supply a range (`500-1500`) instead of a
skip count. Telegram message IDs are sparse, so without a real total the
percentage is estimated from the ID span.

**Task did not resume after a restart** — resume needs the `notify` record in
Mongo. If the bot was killed before its first progress write (within
`PROGRESS_DB_INTERVAL` seconds of starting), there is nothing to resume from.

**FloodWait spam in the logs** — raise the delay under ⚡ Speed. A single send
retries up to 3 times and tolerates waits up to 15 minutes before that message
is counted as failed; the task itself keeps going.

**Bot will not start** — the startup log names the exact problem. Missing
variables are listed individually; a MongoDB failure means the URI, the
password, or the IP allowlist.

---

## Security notes

Worth understanding before you run this for other people:

- **Userbot sessions are stored in plaintext** in your database. Anyone with
  database access can take over those accounts. Use throwaway accounts, and
  keep your MongoDB credentials tight.
- **Adding a userbot risks that account.** Telegram limits and bans accounts
  that forward at volume. This is inherent to userbots, not specific to this
  bot.
- **`/restart` with `ALLOW_GIT_RESTART=true` executes remote code.** It pulls
  from your git remote and installs dependencies. Leave it off unless you own
  the repository.
- **The health endpoint is unauthenticated** but exposes only
  `{"status": "ok"}` — no user data, no input accepted. If you extend it, add
  authentication before exposing anything real.
- **Database URLs are masked in the UI** and your message containing one is
  deleted on receipt.
- Owner-only commands are gated on `BOT_OWNER`. Set it correctly; if it is
  wrong, those commands answer to whoever holds that ID.

---

## Development

Run the tests:

```bash
python -m unittest discover -s tests -v
```

53 tests cover the filter logic, the database-backed duplicate store, and task
state lifecycle — the areas where bugs were previously found. They need no
network or database.

Lint:

```bash
pip install pyflakes
python -m pyflakes *.py plugins/
```

### Notes for contributors

- **One Telegram library only.** `pyrofork` and `pyrogram` install into the
  same `pyrogram` namespace; having both makes which one loads
  nondeterministic. Same for `tgcrypto` vs `TgCrypto-pyrofork`.
- **Release task state in `finally`.** Anything stored in `STATUS` or `temp`
  must be cleared on every exit path, including cancellation and errors. That
  was the source of the original memory growth.
- **Close every client you start.** Use the `temporary_client` context manager
  or `close_client` in a `finally`. A leaked client keeps a socket and its
  dispatcher tasks alive for the life of the process.
- **Keep per-message work bounded.** Anything that grows once per forwarded
  message needs a cap. Prefer sets over lists for membership tests.
- **Handle FloodWait iteratively, not recursively.** Recursion on a persistent
  rate limit eventually exhausts the stack.

---

## Project layout

```
main.py                 Entry point: startup, health server, shutdown
config.py               Environment config, validation, process-local state
database.py             Main MongoDB layer (users, bots, channels, history)
script.py               User-facing message templates

plugins/
  commands.py           /start, /help, /status, /reset, owner commands
  public.py             The /forward conversation
  regix.py              Forwarding engines, filters, progress UI
  settings.py           The /settings panel
  test.py               Client factories, message iterator, login flows
  utils.py              Task state (STS) and the database-backed duplicate store
  db.py                 Per-user duplicate database
  watch.py              Continuous mode
  unequeify.py          /unequify duplicate cleanup
  broadcast.py          Owner broadcast

tests/
  test_logic.py         Unit tests for filters, cache, and state lifecycle
```

---

## Credits

Built on [Pyrofork](https://github.com/Mayuri-Chan/pyrofork).

Original project by [Tech VJ](https://t.me/kingvj01) ·
[Update channel](https://t.me/vj_botz) ·
[Support group](https://t.me/VJ_Bot_Disscussion)

Licensed under the terms in [LICENCE](LICENCE).
