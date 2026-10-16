# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

import asyncio
import logging
from config import Config
from pyrogram import Client as VJ, idle
from plugins.regix import restart_forwards

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s - %(levelname)s] - %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


if __name__ == "__main__":
    VJBot = VJ(
        "VJ-Forward-Bot",
        bot_token=Config.BOT_TOKEN,
        api_id=Config.API_ID,
        api_hash=Config.API_HASH,
        sleep_threshold=120,
        plugins=dict(root="plugins"),
    )

    async def main():
        await VJBot.start()
        bot_info = await VJBot.get_me()
        logger.info(f"Bot @{bot_info.username} started successfully.")
        await restart_forwards(VJBot)
        await idle()

    asyncio.get_event_loop().run_until_complete(main())