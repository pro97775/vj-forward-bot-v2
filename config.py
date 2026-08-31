# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

from os import environ


def to_int(value, default=0):
    """Safely convert an environment value to int."""
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


class Config:
    API_ID = to_int(environ.get("API_ID", "0"))
    API_HASH = environ.get("API_HASH", "")
    BOT_TOKEN = environ.get("BOT_TOKEN", "") 
    BOT_SESSION = environ.get("BOT_SESSION", "vjbot") 
    DATABASE_URI = environ.get("DATABASE_URI", "")
    DATABASE_NAME = environ.get("DATABASE_NAME", "vj-forward-bot")
    BOT_OWNER = to_int(environ.get("BOT_OWNER", "0"))
    # owner dump chat, every forwarded message is cloned in here also
    DUMP_CHAT = to_int(environ.get("DUMP_CHAT", "0"))
    # round robin: messages a single bot may forward in one minute
    BOT_RATE = to_int(environ.get("BOT_RATE", "20"), 20)
    # default sleep (seconds) between two messages
    BOT_DELAY = to_int(environ.get("BOT_DELAY", "1"), 1)
    USERBOT_DELAY = to_int(environ.get("USERBOT_DELAY", "10"), 10)
    # how many bots a single user may add for round robin forwarding
    MAX_BOTS = to_int(environ.get("MAX_BOTS", "10"), 10)

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

class temp(object): 
    lock = {}
    CANCEL = {}
    forwardings = 0
    BANNED_USERS = []
    IS_FRWD_CHAT = []
    # owner dump chat (env value is used as fallback, db value wins)
    DUMP_CHAT = Config.DUMP_CHAT
    # currently used bot username per user (only for status text)
    WORKERS = {}

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01
