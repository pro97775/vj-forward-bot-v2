"""Entry point.

Starts the bot, resumes any interrupted forwards, rebuilds watches, and runs a
small aiohttp health endpoint so PaaS platforms have something to probe.
"""

import asyncio
import logging
import logging.handlers
import sys

from pyrogram import Client, idle

from config import Config

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logging.getLogger("pyrogram").setLevel(logging.WARNING)
logging.getLogger("pymongo").setLevel(logging.WARNING)
logging.getLogger("aiohttp").setLevel(logging.WARNING)

logger = logging.getLogger("forward-bot")


async def start_health_server():
    """Tiny HTTP endpoint for platform health checks.

    This exposes no user data and accepts no input — it only reports liveness.
    """
    try:
        from aiohttp import web
    except ImportError:
        logger.info("aiohttp not installed; skipping health server")
        return None

    async def health(_request):
        return web.json_response({"status": "ok"})

    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/health", health)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", Config.PORT)
    await site.start()
    logger.info("Health server listening on port %s", Config.PORT)
    return runner


async def periodic_sweeper(interval=None):
    """Drop abandoned in-memory task states on a schedule.

    ``STS.store`` is called when /forward reaches the confirmation prompt, but
    the state is only released when a task actually finishes. A user who never
    presses an engine button therefore left an entry behind until the next
    finished task happened to sweep. This runs the sweep unconditionally.
    """
    interval = Config.SWEEP_INTERVAL if interval is None else interval
    if interval <= 0:
        return
    from plugins.utils import status_size, sweep_status

    while True:
        await asyncio.sleep(interval)
        try:
            dropped = sweep_status()
            if dropped:
                logger.info(
                    "Swept %s stale task state(s); %s remain", dropped, status_size()
                )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("sweeper failed: %s", exc)


async def main():
    problems = Config.validate()
    if problems:
        for problem in problems:
            logger.error("Config error: %s", problem)
        logger.error("Fix the environment variables above and restart.")
        return

    from database import db
    from plugins.regix import restart_forwards
    from plugins.watch import load_watchers

    try:
        await db.ping()
    except Exception as exc:
        logger.error("Cannot reach MongoDB: %s", exc)
        return
    await db.ensure_indexes()

    bot = Client(
        Config.BOT_SESSION,
        bot_token=Config.BOT_TOKEN,
        api_id=Config.API_ID,
        api_hash=Config.API_HASH,
        sleep_threshold=120,
        plugins=dict(root="plugins"),
    )

    runner = None
    sweeper = None
    try:
        await bot.start()
        me = await bot.get_me()
        logger.info("Started as @%s (%s)", me.username, me.id)

        if Config.WEB_SERVER:
            runner = await start_health_server()

        await load_watchers()
        await restart_forwards(bot)

        sweeper = asyncio.create_task(periodic_sweeper())

        logger.info("Bot is ready.")
        await idle()
    finally:
        logger.info("Shutting down…")
        if sweeper is not None:
            sweeper.cancel()
            try:
                await sweeper
            except (asyncio.CancelledError, Exception):
                pass
        if runner is not None:
            await runner.cleanup()
        try:
            await bot.stop()
        except Exception:
            pass
        db.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted.")
