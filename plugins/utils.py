"""In-memory task state and the database-backed duplicate store.

Both containers here used to grow without limit and were the main source of
the slow RAM climb during long forwards:

* ``STATUS`` kept one entry per ``/forward`` forever.
* the duplicate list grew one entry per file and was scanned linearly.

``STS`` entries are now released when a task ends and swept on a TTL.
Duplicate tracking holds **nothing** in RAM: every lookup is a single atomic
upsert against MongoDB — the user's own database when they added one under
/settings → 🗃 MongoDB, otherwise the bot's own database with a TTL so the
records clean themselves up.
"""

import time as tm

from config import Config
from database import db

from .test import parse_buttons

# forward_id -> {"data": {...}, "touched": epoch}
STATUS = {}


def sweep_status(ttl=None):
    """Drop task states nobody has touched for at least ``ttl`` seconds.

    ``ttl=0`` drops everything, which is what the owner's /sweep uses.
    """
    ttl = Config.STATUS_TTL if ttl is None else ttl
    now = tm.time()
    stale = [k for k, v in STATUS.items() if now - v.get("touched", now) >= ttl]
    for key in stale:
        STATUS.pop(key, None)
    return len(stale)


def status_size():
    return len(STATUS)


class DupStore:
    """Duplicate tracker with no unbounded RAM growth.

    ``check_and_add`` performs one atomic upsert and returns True when the
    file was already known. Memory is O(1) per task regardless of how many
    files are processed — the previous implementation kept up to
    ``DUP_CACHE_LIMIT`` ids per running task in a set.

    ``user_db`` is the user's own MongoDB (``plugins.db.MongoDB``). When it is
    absent the bot's own database is used, scoped by ``key`` and expired by a
    TTL index so nothing accumulates forever.
    """

    __slots__ = ("_db", "_key", "_hot", "_hot_limit", "_checked", "_hits", "own_db")

    def __init__(self, key, user_db=None, hot_limit=None):
        self._db = user_db
        self._key = str(key)
        self.own_db = user_db is not None
        # Optional tiny write-through cache. Off by default (limit 0) so RAM
        # stays flat; raise DUP_HOT_CACHE to trade a little memory for fewer
        # database round trips.
        self._hot_limit = Config.DUP_HOT_CACHE if hot_limit is None else hot_limit
        self._hot = set() if self._hot_limit > 0 else None
        self._checked = 0
        self._hits = 0

    def __len__(self):
        """Ids currently held in RAM — 0 unless a hot cache is enabled."""
        return len(self._hot) if self._hot is not None else 0

    @property
    def checked(self):
        return self._checked

    @property
    def hits(self):
        return self._hits

    @property
    def backend(self):
        return "user-db" if self.own_db else "bot-db"

    async def check_and_add(self, file_id) -> bool:
        """True when ``file_id`` has been seen before."""
        if not file_id:
            return False
        self._checked += 1

        if self._hot is not None and file_id in self._hot:
            self._hits += 1
            return True

        try:
            if self._db is not None:
                existed = await self._db.mark(file_id)
            else:
                existed = await db.dupe_seen(self._key, file_id)
        except Exception:
            # A database hiccup must never drop a message; treat as unseen.
            return False

        if existed:
            self._hits += 1
        elif self._hot is not None and len(self._hot) < self._hot_limit:
            self._hot.add(file_id)
        return existed

    async def count(self):
        """How many ids are recorded for this task, in the database."""
        try:
            if self._db is not None:
                return await self._db.count()
            return await db.dupe_count(self._key)
        except Exception:
            return 0

    async def reset(self):
        """Forget everything recorded for this task."""
        if self._hot is not None:
            self._hot.clear()
        if self._db is None:
            await db.dupe_clear(self._key)

    def clear(self):
        if self._hot is not None:
            self._hot.clear()
        self._db = None


class STS:
    def __init__(self, id):
        self.id = str(id)

    # ── storage ─────────────────────────────────────────────────────

    @property
    def _entry(self):
        return STATUS.get(self.id)

    @property
    def data(self):
        entry = self._entry
        return entry["data"] if entry else None

    def verify(self):
        return self._entry is not None

    def _touch(self):
        entry = self._entry
        if entry:
            entry["touched"] = tm.time()

    def store(self, From, to, skip, limit, total=None, engine="auto", dry_run=False,
              extra_targets=None, start_id=None):
        """Create the task state.

        ``limit`` is the highest source message id to walk to. ``total`` is the
        real expected message count when known; it defaults to the id span so
        percentages stay meaningful for sparse channels.
        """
        skip = int(skip or 0)
        limit = int(limit or 0)
        start = int(start_id) if start_id else skip
        STATUS[self.id] = {
            "touched": tm.time(),
            "data": {
                "FROM": From,
                "TO": to,
                "TARGETS": list(extra_targets or []),
                "total_files": 0,
                "skip": skip,
                "start_id": start,
                "limit": limit,
                "fetched": 0,
                "filtered": 0,
                "deleted": 0,
                "duplicate": 0,
                "total": int(total) if total else max(limit - start, 0),
                "start": 0,
                "engine": engine,
                "dry_run": bool(dry_run),
                "cursor": start,
                "last_db_write": 0.0,
            },
        }
        return self

    def release(self):
        """Free this task's state. Call exactly once when a task finishes."""
        STATUS.pop(self.id, None)

    # ── access ──────────────────────────────────────────────────────

    def get(self, value=None, full=False, default=None):
        values = self.data
        if values is None:
            if full:
                raise KeyError(f"unknown task {self.id}")
            return default
        self._touch()
        if not full:
            return values.get(value, default)
        for k, v in values.items():
            setattr(self, k, v)
        return self

    def set(self, key, value):
        values = self.data
        if values is None:
            return
        values[key] = value
        self._touch()

    def add(self, key=None, value=1, time=False, start_time=None):
        values = self.data
        if values is None:
            return
        self._touch()
        if time:
            values["start"] = tm.time() if start_time is None else start_time
            return
        values[key] = values.get(key, 0) + value

    def divide(self, no, by):
        by = 1 if int(by) == 0 else by
        return int(no) / by

    def all_targets(self):
        """Primary target first, then any fan-out targets."""
        values = self.data or {}
        targets = [values.get("TO")]
        for extra in values.get("TARGETS") or []:
            if extra not in targets:
                targets.append(extra)
        return [t for t in targets if t is not None]

    def should_write_db(self, interval=None):
        """Rate-limit MongoDB progress writes to keep the loop cheap."""
        interval = Config.PROGRESS_DB_INTERVAL if interval is None else interval
        values = self.data
        if values is None:
            return False
        now = tm.time()
        if now - values.get("last_db_write", 0.0) < interval:
            return False
        values["last_db_write"] = now
        return True

    def snapshot(self):
        """Plain dict copy, for history records."""
        values = self.data
        return dict(values) if values else {}

    # ── config ──────────────────────────────────────────────────────

    async def get_data(self, user_id):
        bots = await db.get_all_bots(user_id)
        bot = bots[0] if bots else await db.get_userbot(user_id)
        message_filters = await db.get_filters(user_id)
        configs = await db.get_configs(user_id)
        button = parse_buttons(configs.get("button") or "")
        return (
            bot,
            configs.get("caption"),
            configs.get("forward_tag"),
            {
                "filters": message_filters,
                "keywords": configs.get("keywords"),
                "min_size": configs.get("min_size", 0),
                "max_size": configs.get("max_size", 0),
                "extensions": configs.get("extension"),
                # "block" = skip these extensions, "allow" = forward only these.
                "extension_mode": configs.get("extension_mode") or "block",
                "skip_duplicate": bool(configs.get("duplicate", True)),
                "db_uri": configs.get("db_uri"),
                "dry_run": bool(configs.get("dry_run", False)),
            },
            configs.get("protect"),
            button,
        )
