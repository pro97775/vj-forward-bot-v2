from os import environ


def _int(name: str, default: str = "0") -> int:
    raw = environ.get(name, default).strip()
    try:
        return int(raw)
    except ValueError:
        return int(default)


def _float(name: str, default: str) -> float:
    raw = environ.get(name, default).strip()
    try:
        return float(raw)
    except ValueError:
        return float(default)


def _bool(name: str, default: bool = False) -> bool:
    return environ.get(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


class Config:
    # ── Telegram ────────────────────────────────────────────────────
    API_ID = _int("API_ID", "")
    API_HASH = environ.get("API_HASH", "").strip()
    BOT_TOKEN = environ.get("BOT_TOKEN", "").strip()
    BOT_SESSION = environ.get("BOT_SESSION", "VJ-Forward-Bot").strip()

    # ── Database ────────────────────────────────────────────────────
    DATABASE_URI = environ.get("DATABASE_URI", "").strip()
    DATABASE_NAME = environ.get("DATABASE_NAME", "vj-forward-bot").strip()

    # ── Owner ───────────────────────────────────────────────────────
    BOT_OWNER = _int("BOT_OWNER", "")

    # ── Health web server (Koyeb / Render / Heroku) ─────────────────
    PORT = _int("PORT", "8080")
    WEB_SERVER = _bool("WEB_SERVER", True)

    # ── Memory guards ───────────────────────────────────────────────
    # Duplicate checking no longer keeps file ids in RAM at all — every
    # lookup goes to MongoDB (the user's own database when they added one,
    # otherwise the bot's). This is the only value left that bounds RAM.
    # Small write-through cache used purely to avoid re-querying the same
    # id twice in a row. 0 disables it entirely.
    DUP_HOT_CACHE = _int("DUP_HOT_CACHE", "0")
    # How long fallback duplicate records live before MongoDB expires them.
    DUP_TTL_HOURS = _int("DUP_TTL_HOURS", "72")
    # Age at which finished in-memory task states are swept, in seconds.
    STATUS_TTL = _int("STATUS_TTL", "86400")
    # How often the background sweeper runs, in seconds. 0 disables it.
    SWEEP_INTERVAL = _int("SWEEP_INTERVAL", "1800")
    # Minimum seconds between MongoDB progress writes for a running task.
    PROGRESS_DB_INTERVAL = _float("PROGRESS_DB_INTERVAL", "10")

    # ── Safety ──────────────────────────────────────────────────────
    # /restart runs `git pull` + `pip install` when enabled. Off by default
    # because it executes remote code on the host.
    ALLOW_GIT_RESTART = _bool("ALLOW_GIT_RESTART", False)

    @classmethod
    def validate(cls):
        """Return a list of human-readable configuration problems."""
        problems = []
        if not cls.API_ID:
            problems.append("API_ID is missing or not a number")
        if not cls.API_HASH:
            problems.append("API_HASH is missing")
        if not cls.BOT_TOKEN:
            problems.append("BOT_TOKEN is missing")
        if not cls.DATABASE_URI:
            problems.append("DATABASE_URI is missing")
        if not cls.BOT_OWNER:
            problems.append("BOT_OWNER is missing or not a number")
        return problems


class temp:
    """Process-local scratch state.

    Every mapping here is keyed by user id and MUST be cleared when a task
    ends, otherwise the process grows for every user that ever ran a task.
    Use the helpers below instead of touching the containers directly.
    """

    forwardings = 0
    BANNED_USERS = set()
    IS_FRWD_CHAT = set()
    lock = {}
    CANCEL = {}

    @classmethod
    def is_locked(cls, user_id) -> bool:
        return bool(cls.lock.get(int(user_id)))

    @classmethod
    def is_cancelled(cls, user_id) -> bool:
        return bool(cls.CANCEL.get(int(user_id)))

    @classmethod
    def begin_task(cls, user_id, to_chat=None):
        user_id = int(user_id)
        cls.lock[user_id] = True
        cls.CANCEL[user_id] = False
        if to_chat is not None:
            cls.IS_FRWD_CHAT.add(to_chat)

    @classmethod
    def end_task(cls, user_id, to_chat=None):
        """Release every trace of a task. Safe to call more than once."""
        user_id = int(user_id)
        cls.lock.pop(user_id, None)
        cls.CANCEL.pop(user_id, None)
        if to_chat is not None:
            cls.IS_FRWD_CHAT.discard(to_chat)

    @classmethod
    def request_cancel(cls, user_id, force=False):
        """Ask a running task to stop.

        Only records the flag when the user actually holds a task — otherwise a
        stray /stop or an old cancel button left an entry in ``CANCEL`` that was
        never popped, which is a small but permanent leak per user. ``force``
        is for callers that already verified a task exists in the database
        (e.g. a task resumed after a restart, before its lock is taken).
        """
        user_id = int(user_id)
        if not force and user_id not in cls.lock and user_id not in cls.CANCEL:
            return False
        cls.CANCEL[user_id] = True
        cls.lock.pop(user_id, None)
        return True
