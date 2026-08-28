"""Per-user MongoDB used to persist duplicate file ids across restarts."""

import logging

import motor.motor_asyncio
from pymongo.errors import PyMongoError

logger = logging.getLogger(__name__)


class MongoDB:
    def __init__(self, uri, db_name, collection):
        self.uri = uri
        self.db_name = db_name
        self.collection = collection
        self.client = None
        self.db = None
        self.files = None

    async def connect(self):
        self.client = motor.motor_asyncio.AsyncIOMotorClient(
            self.uri, serverSelectionTimeoutMS=8000
        )
        # Fail fast on a bad URI instead of at first query.
        await self.client.admin.command("ping")
        self.db = self.client[self.db_name]
        self.files = self.db[self.collection]
        try:
            await self.files.create_index("file_id", unique=True)
        except PyMongoError as exc:
            logger.debug("index creation skipped: %s", exc)

    async def close(self):
        if self.client is not None:
            self.client.close()
            self.client = None
            self.db = None
            self.files = None

    async def add_file(self, file_id):
        if self.files is None:
            return None
        try:
            return await self.files.update_one(
                {"file_id": file_id},
                {"$setOnInsert": {"file_id": file_id}},
                upsert=True,
            )
        except PyMongoError as exc:
            logger.debug("add_file failed: %s", exc)
            return None

    async def is_file_exit(self, file_id):
        if self.files is None:
            return False
        try:
            return bool(await self.files.find_one({"file_id": file_id}, {"_id": 1}))
        except PyMongoError as exc:
            logger.debug("is_file_exit failed: %s", exc)
            return False

    async def mark(self, file_id):
        """Atomically record ``file_id``. Returns True if it already existed.

        One round trip instead of a find followed by an insert, so nothing
        needs to be held in RAM between the two steps.
        """
        if self.files is None:
            return False
        try:
            result = await self.files.update_one(
                {"file_id": file_id},
                {"$setOnInsert": {"file_id": file_id}},
                upsert=True,
            )
            return result.upserted_id is None
        except PyMongoError as exc:
            logger.debug("mark failed: %s", exc)
            return False

    async def count(self):
        if self.files is None:
            return 0
        try:
            return await self.files.count_documents({})
        except PyMongoError:
            return 0

    async def get_all_files(self):
        if self.files is None:
            return None
        return self.files.find({}, {"file_id": 1})

    async def drop_all(self):
        if self.files is None:
            return None
        try:
            return await self.files.drop()
        except PyMongoError as exc:
            logger.debug("drop_all failed: %s", exc)
            return None


async def connect_user_db(user_id, uri, chat):
    """Open a user's duplicate store. Returns (connected, db)."""
    collection = f"{user_id}{chat}"
    dbname = f"{user_id}-Forward-Bot"
    user_db = MongoDB(uri, dbname, collection)
    try:
        await user_db.connect()
    except Exception as exc:
        logger.warning("user db connect failed for %s: %s", user_id, exc)
        await user_db.close()
        return False, user_db
    return True, user_db
