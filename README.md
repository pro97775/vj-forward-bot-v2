# VJ Forward Bot

<b>Auto Restart All User Forwarding After Bot Restarted.</b>

![Typing SVG](https://readme-typing-svg.herokuapp.com/?lines=Welcome+To+VJ+Forward+Bot+!)

## How To Deploy [Video Tutorial](https://youtu.be/A-iIh_5WAlk)

## Features

- [x] Public Forward (Bot)
- [x] Private Forward (User Bot)
- [x] **Multiple bots round robin forwarding** - add up to `MAX_BOTS` bots, every bot forwards only `20` messages per minute (configurable) and the next bot continues, so the speed is `rate x bots` messages per minute
- [x] **Add bots by pasting the token directly** (no BotFather forward needed, several tokens at once are supported)
- [x] **Add a userbot by pasting the session string directly** (or login with a phone number)
- [x] **Add target chats by pasting the chat id / username / message link** (or by forwarding a message)
- [x] **Owner dump chat** - every message forwarded by any user is cloned in to the owner dump chat
- [x] **Forwarding delay control from the bot** (bot delay, userbot delay, per bot rate)
- [x] **Stats button** in settings (your bots, speed, delays, running task) and global bot stats
- [x] Custom Caption
- [x] Custom Button
- [x] Skip Messages Based On Extensions & Keywords & Size
- [x] Filter Type Of Messages
- [x] Duplicate cleaning with `/unequify` (uses telegram file hashes, documents + videos + audios + photos)
- [x] All settings through inline buttons
- [x] All commands are registered in telegram automatically when the bot starts
- [x] Auto Restart Pending Task After Bot Restart

> Duplicate checking was removed from the forwarding flow (it made forwarding slow and needed an extra database). Use `/unequify` on the target chat to delete duplicates by file hash instead.

<b>To Know About All Features, Join My <a href='https://t.me/VJ_Botz'>Update Channel</a>.</b>

## Commands

```
start - check I'm alive 
forward - forward messages
settings - configure your settings
stats - your forwarding stats
unequify - delete duplicate media messages in chats
stop - stop your ongoing tasks
reset - reset your settings
help - how to use me
dump - set the owner dump chat (owner only)
restart - restart server (owner only)
resetall - reset all users settings (owner only)
broadcast - broadcast a message to all your users (owner only)
```

## Variables

### Required

* `API_ID` API Id from my.telegram.org
* `API_HASH` API Hash from my.telegram.org
* `BOT_TOKEN` Bot token from @BotFather
* `BOT_OWNER` Telegram Account Id of Owner.
* `DATABASE_URI` Database uri from [MongoDB](https://mongodb.com) Watch [Video Tutorial](https://youtu.be/DAHRmFdw99o)

### Optional

* `DATABASE_NAME` Database name. Default `vj-forward-bot`
* `DUMP_CHAT` Chat id of the owner dump chat. Can also be set from the bot with `/dump`. Default `0` (off)
* `BOT_RATE` Messages a single bot forwards in one minute. Default `20`
* `BOT_DELAY` Seconds between two messages when bots are used. Default `1`
* `USERBOT_DELAY` Seconds between two messages when a userbot is used. Default `10`
* `MAX_BOTS` How many bots a single user can add. Default `10`

## Tests

Offline tests for the round robin scheduler, filters and link parsing:

```
pip install pytest
python -m pytest tests -q
```

## Credits

* <b>[Tech VJ](https://youtube.com/@Tech_VJ)</b>
