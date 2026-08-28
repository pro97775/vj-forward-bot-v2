import logging
import time
from datetime import datetime, timedelta, timezone

import motor.motor_asyncio
from pymongo.errors import PyMongoError

from config import Config

logger = logging.getLogger(__name__)


class Db:
    def __init__(self, uri, database_name):
        self._client = motor.motor_asyncio.AsyncIOMotorClient(
            uri,
            serverSelectionTimeoutMS=10000,
            maxPoolSize=50,
        )
        self.db = self._client[database_name]
        self.bot = self.db.bots
        self.userbot = self.db.userbot
        self.col = self.db.users
        self.nfy = self.db.notify
        self.chl = self.db.channels
        self.hist = self.db.history
        # Fallback duplicate store for users who did not add their own MongoDB.
        # Entries expire on their own so an abandoned task cannot leave junk.
        self.dupes = self.db.dupes
        self._indexes_ready = False

    # ── Indexes ─────────────────────────────────────────────────────

    async def ensure_indexes(self):
        """Create the indexes every hot query relies on. Idempotent."""
        if self._indexes_ready:
            return
        try:
            await self.col.create_index("id", unique=True)
            await self.userbot.create_index("user_id")
            await self.nfy.create_index("user_id", unique=True)
            await self.chl.create_index([("user_id", 1), ("chat_id", 1)], unique=True)
            await self.hist.create_index([("user_id", 1), ("finished_at", -1)])
            # One document per (task, file). ``expires_at`` lets MongoDB reclaim
            # the space by itself if a task dies without cleaning up.
            await self.dupes.create_index([("key", 1), ("file_id", 1)], unique=True)
            await self.dupes.create_index("expires_at", expireAfterSeconds=0)
            self._indexes_ready = True
            logger.info("MongoDB indexes ready")
        except PyMongoError as exc:
            logger.warning("Could not create indexes: %s", exc)

    async def ping(self):
        await self._client.admin.command("ping")

    def close(self):
        self._client.close()

    # ── Users ───────────────────────────────────────────────────────

    def new_user(self, id, name):
        return dict(
            id=id,
            name=name,
            ban_status=dict(is_banned=False, ban_reason=""),
        )

    async def add_user(self, id, name):
        await self.col.update_one(
            {"id": int(id)},
            {"$setOnInsert": self.new_user(int(id), name)},
            upsert=True,
        )

    async def is_user_exist(self, id):
        user = await self.col.find_one({"id": int(id)}, {"_id": 1})
        return bool(user)

    async def total_users_count(self):
        return await self.col.count_documents({})

    async def total_users_bots_count(self):
        count = await self.col.count_documents({})
        bcount = await self.col.count_documents({"bots": {"$exists": True, "$ne": []}})
        return count, bcount

    async def remove_ban(self, id):
        await self.col.update_one(
            {"id": int(id)},
            {"$set": {"ban_status": dict(is_banned=False, ban_reason="")}},
        )

    async def ban_user(self, user_id, ban_reason="No Reason"):
        await self.col.update_one(
            {"id": int(user_id)},
            {"$set": {"ban_status": dict(is_banned=True, ban_reason=ban_reason)}},
        )

    async def get_ban_status(self, id):
        default = dict(is_banned=False, ban_reason="")
        user = await self.col.find_one({"id": int(id)})
        if not user:
            return default
        return user.get("ban_status", default)

    async def get_all_users(self):
        return self.col.find({})

    async def delete_user(self, user_id):
        await self.col.delete_many({"id": int(user_id)})

    async def get_banned(self):
        users = self.col.find({"ban_status.is_banned": True}, {"id": 1})
        return [user["id"] async for user in users]

    # ── Configs ─────────────────────────────────────────────────────

    @staticmethod
    def default_configs():
        return {
            "caption": None,
            "duplicate": True,
            "forward_tag": False,
            "min_size": 0,
            "max_size": 0,
            "extension": None,
            # "block" — skip the listed extensions (default)
            # "allow"  — forward *only* the listed extensions
            "extension_mode": "block",
            "keywords": None,
            "protect": None,
            "button": None,
            "db_uri": None,
            "dry_run": False,
            "filters": {
                "poll": True,
                "text": True,
                "audio": True,
                "voice": True,
                "video": True,
                "photo": True,
                "document": True,
                "animation": True,
                "sticker": True,
            },
        }

    async def update_configs(self, id, configs):
        await self.col.update_one(
            {"id": int(id)}, {"$set": {"configs": configs}}, upsert=True
        )

    async def get_configs(self, id):
        default = self.default_configs()
        user = await self.col.find_one({"id": int(id)}, {"configs": 1})
        if not user or "configs" not in user:
            return default
        stored = user["configs"]
        # Merge so configs added in later versions always have a value.
        merged = {**default, **stored}
        merged["filters"] = {**default["filters"], **(stored.get("filters") or {})}
        return merged

    # ── Multi-bot support ───────────────────────────────────────────

    async def add_bot_to_list(self, user_id, bot_details):
        """Add a bot to the user's bot list. Returns False if already present."""
        user_data = await self.col.find_one({"id": int(user_id)}, {"bots": 1})
        bots = (user_data or {}).get("bots", []) or []
        for b in bots:
            if b.get("id") == bot_details.get("id"):
                return False
        bots.append(bot_details)
        await self.col.update_one(
            {"id": int(user_id)}, {"$set": {"bots": bots}}, upsert=True
        )
        return True

    async def get_all_bots(self, user_id):
        user_data = await self.col.find_one({"id": int(user_id)}, {"bots": 1})
        if user_data and user_data.get("bots"):
            return user_data["bots"]
        # One-time migration from the legacy single-bot collection.
        old_bot = await self.bot.find_one({"user_id": int(user_id)})
        if old_bot:
            old_bot.pop("_id", None)
            await self.add_bot_to_list(user_id, old_bot)
            return [old_bot]
        return []

    async def remove_bot_by_index(self, user_id, index):
        user_data = await self.col.find_one({"id": int(user_id)}, {"bots": 1})
        bots = (user_data or {}).get("bots") or []
        if 0 <= index < len(bots):
            bots.pop(index)
            await self.col.update_one({"id": int(user_id)}, {"$set": {"bots": bots}})
            return True
        return False

    async def remove_bot_by_id(self, user_id, bot_id):
        user_data = await self.col.find_one({"id": int(user_id)}, {"bots": 1})
        bots = (user_data or {}).get("bots") or []
        remaining = [b for b in bots if b.get("id") != bot_id]
        await self.col.update_one({"id": int(user_id)}, {"$set": {"bots": remaining}})
        return len(remaining) != len(bots)

    async def add_bot(self, datas):
        return await self.add_bot_to_list(datas["user_id"], datas)

    async def remove_bot(self, user_id):
        await self.col.update_one({"id": int(user_id)}, {"$unset": {"bots": ""}})
        await self.bot.delete_many({"user_id": int(user_id)})

    async def get_bot(self, user_id: int):
        bots = await self.get_all_bots(user_id)
        return bots[0] if bots else None

    async def is_bot_exist(self, user_id):
        return bool(await self.get_all_bots(user_id))

    # ── Userbot ─────────────────────────────────────────────────────

    async def add_userbot(self, datas):
        await self.userbot.update_one(
            {"user_id": int(datas["user_id"])}, {"$set": datas}, upsert=True
        )

    async def remove_userbot(self, user_id):
        await self.userbot.delete_many({"user_id": int(user_id)})

    async def get_userbot(self, user_id: int):
        return await self.userbot.find_one({"user_id": int(user_id)})

    async def is_userbot_exist(self, user_id):
        return bool(await self.userbot.find_one({"user_id": int(user_id)}, {"_id": 1}))

    # ── Channels ────────────────────────────────────────────────────

    async def in_channel(self, user_id: int, chat_id: int) -> bool:
        channel = await self.chl.find_one(
            {"user_id": int(user_id), "chat_id": int(chat_id)}, {"_id": 1}
        )
        return bool(channel)

    async def add_channel(self, user_id: int, chat_id: int, title, username):
        if await self.in_channel(user_id, chat_id):
            return False
        return await self.chl.insert_one(
            {
                "user_id": int(user_id),
                "chat_id": int(chat_id),
                "title": title,
                "username": username,
            }
        )

    async def remove_channel(self, user_id: int, chat_id: int):
        if not await self.in_channel(user_id, chat_id):
            return False
        return await self.chl.delete_many(
            {"user_id": int(user_id), "chat_id": int(chat_id)}
        )

    async def get_channel_details(self, user_id: int, chat_id: int):
        return await self.chl.find_one(
            {"user_id": int(user_id), "chat_id": int(chat_id)}
        )

    async def get_user_channels(self, user_id: int):
        channels = self.chl.find({"user_id": int(user_id)})
        return [channel async for channel in channels]

    async def get_filters(self, user_id):
        configs = await self.get_configs(user_id)
        return [str(k) for k, v in configs["filters"].items() if v is False]

    # ── Forward tracking ────────────────────────────────────────────

    async def add_frwd(self, user_id):
        return await self.nfy.update_one(
            {"user_id": int(user_id)},
            {"$setOnInsert": {"user_id": int(user_id)}},
            upsert=True,
        )

    async def rmve_frwd(self, user_id=0, all=False):
        data = {} if all else {"user_id": int(user_id)}
        return await self.nfy.delete_many(data)

    async def get_all_frwd(self):
        return self.nfy.find({})

    async def forwad_count(self):
        return await self.nfy.count_documents({})

    async def is_forwad_exit(self, user):
        return bool(await self.nfy.find_one({"user_id": int(user)}, {"_id": 1}))

    async def get_forward_details(self, user_id):
        default = {
            "chat_id": None,
            "forward_id": None,
            "toid": None,
            "last_id": None,
            "limit": None,
            "msg_id": None,
            "start_time": None,
            "fetched": 0,
            "offset": 0,
            "deleted": 0,
            "total": 0,
            "expected_total": 0,
            "duplicate": 0,
            "skip": 0,
            "filtered": 0,
            "targets": [],
            "engine_choice": "auto",
        }
        user = await self.nfy.find_one({"user_id": int(user_id)})
        if user:
            return {**default, **(user.get("details") or {})}
        return default

    async def update_forward(self, user_id, details):
        await self.nfy.update_one(
            {"user_id": int(user_id)}, {"$set": {"details": details}}, upsert=True
        )

    # ── Task history ────────────────────────────────────────────────

    async def add_history(self, user_id, entry):
        entry = {**entry, "user_id": int(user_id), "finished_at": time.time()}
        await self.hist.insert_one(entry)
        # Keep only the 20 most recent entries per user.
        old = self.hist.find(
            {"user_id": int(user_id)}, {"_id": 1}
        ).sort("finished_at", -1).skip(20)
        stale = [doc["_id"] async for doc in old]
        if stale:
            await self.hist.delete_many({"_id": {"$in": stale}})

    async def get_history(self, user_id, limit=10):
        cursor = (
            self.hist.find({"user_id": int(user_id)})
            .sort("finished_at", -1)
            .limit(limit)
        )
        return [doc async for doc in cursor]

    # ── Duplicate store (fallback, when the user has no own MongoDB) ──

    async def dupe_seen(self, key, file_id):
        """True if ``file_id`` was already recorded under ``key``.

        Uses an atomic upsert so the check and the insert are one round trip:
        if the document already existed, this is a duplicate.
        """
        try:
            result = await self.dupes.update_one(
                {"key": str(key), "file_id": str(file_id)},
                {
                    "$setOnInsert": {
                        "key": str(key),
                        "file_id": str(file_id),
                        "expires_at": datetime.now(timezone.utc)
                        + timedelta(hours=Config.DUP_TTL_HOURS),
                    }
                },
                upsert=True,
            )
            return result.upserted_id is None
        except PyMongoError as exc:
            logger.debug("dupe_seen failed: %s", exc)
            return False

    async def dupe_count(self, key):
        try:
            return await self.dupes.count_documents({"key": str(key)})
        except PyMongoError:
            return 0

    async def dupe_clear(self, key):
        try:
            await self.dupes.delete_many({"key": str(key)})
        except PyMongoError as exc:
            logger.debug("dupe_clear failed: %s", exc)

    # ── Batch speed settings ────────────────────────────────────────

    @staticmethod
    def default_batch_settings():
        return {"batch_size": 20, "base_sleep": 3.0, "stagger_delay": 0.2}

    async def get_batch_settings(self, user_id):
        default = self.default_batch_settings()
        user = await self.col.find_one({"id": int(user_id)}, {"batch_settings": 1})
        if user and user.get("batch_settings"):
            return {**default, **user["batch_settings"]}
        return default

    async def update_batch_settings(self, user_id, key, value):
        await self.col.update_one(
            {"id": int(user_id)},
            {"$set": {f"batch_settings.{key}": value}},
            upsert=True,
        )


db = Db(Config.DATABASE_URI, Config.DATABASE_NAME)
