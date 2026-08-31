# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

import asyncio, logging
from config import Config, temp
from pyrogram import Client as VJ, idle
from database import db
from plugins.regix import restart_forwards
from plugins.commands import set_commands

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s - %(levelname)s] - %(name)s - %(message)s",
    datefmt='%d-%b-%y %H:%M:%S')
logging.getLogger("pyrogram").setLevel(logging.WARNING)

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01


def check_config():
    """Stop early with a clear message when a variable is missing."""
    missing = []
    if not Config.API_ID:
        missing.append("API_ID")
    if not Config.API_HASH:
        missing.append("API_HASH")
    if not Config.BOT_TOKEN:
        missing.append("BOT_TOKEN")
    if not Config.DATABASE_URI:
        missing.append("DATABASE_URI")
    if not Config.BOT_OWNER:
        missing.append("BOT_OWNER")
    if missing:
        raise SystemExit(f"Please fill these variables: {', '.join(missing)}")


if __name__ == "__main__":
    check_config()
    VJBot = VJ(
        "VJ-Forward-Bot",
        bot_token=Config.BOT_TOKEN,
        api_id=Config.API_ID,
        api_hash=Config.API_HASH,
        sleep_threshold=120,
        plugins=dict(root="plugins")
    )  

    async def main():
        await VJBot.start()
        bot_info = await VJBot.get_me()
        # register every command in telegram so users see them in the menu
        await set_commands(VJBot)
        try:
            temp.DUMP_CHAT = await db.get_dump_chat()
        except Exception as e:
            logging.warning(f"can't read the dump chat: {e}")
        # continue the tasks which were running before the restart
        await restart_forwards(VJBot)
        print(f"@{bot_info.username} Started.")
        await idle()
        await VJBot.stop()

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    loop.run_until_complete(main())

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01
