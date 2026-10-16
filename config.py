# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

from os import environ


def _int_env(key: str, default: int = 0) -> int:
    val = environ.get(key, "").strip()
    if val and (val.isdigit() or (val.startswith("-") and val[1:].isdigit())):
        return int(val)
    return default


class Config:
    API_ID = _int_env("API_ID", 0)
    API_HASH = environ.get("API_HASH", "")
    BOT_TOKEN = environ.get("BOT_TOKEN", "")
    BOT_SESSION = environ.get("BOT_SESSION", "vjbot")
    DATABASE_URI = environ.get("DATABASE_URI", "")
    DATABASE_NAME = environ.get("DATABASE_NAME", "vj-forward-bot")
    BOT_OWNER = _int_env("BOT_OWNER", 0)

    # Rate-Limiting & Multi-Bot Pool Constants
    MAX_MSGS_PER_MINUTE_PER_BOT = 20
    RATE_LIMIT_WINDOW_SECONDS = 60.0
    SINGLE_BOT_BASE_DELAY = 3.0  # 1 bot = 3.0s, 2 = 1.5s, 3 = 1.0s, 6 = 0.5s
    MIN_POOL_DELAY = 0.2


class temp(object):
    lock = {}
    CANCEL = {}
    PAUSE = {}
    forwardings = 0
    BANNED_USERS = []
    IS_FRWD_CHAT = []
    ACTIVE_POOLS = {}