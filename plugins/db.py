# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

import asyncio
import types

if not hasattr(asyncio, "coroutine"):
    asyncio.coroutine = types.coroutine

import motor.motor_asyncio


class MongoDB:
    def __init__(self, uri, db_name, collection):
        self.uri = uri
        self.db_name = db_name
        self.collection = str(collection)
        self.client = None
        self.db = None
        self.files = None

    async def connect(self):
        self.client = motor.motor_asyncio.AsyncIOMotorClient(
            self.uri,
            serverSelectionTimeoutMS=5000
        )
        await self.client.admin.command("ping")
        self.db = self.client[self.db_name]
        self.files = self.db[self.collection]

    async def close(self):
        if self.client:
            self.client.close()

    async def add_file(self, file_id: str):
        return await self.files.update_one(
            {"file_id": file_id},
            {"$set": {"file_id": file_id}},
            upsert=True
        )

    async def is_file_exit(self, file_id: str) -> bool:
        f = await self.files.find_one({"file_id": file_id})
        return bool(f)

    async def get_all_files(self):
        return self.files.find({})

    async def drop_all(self):
        return await self.files.drop()


async def connect_user_db(user_id, uri, chat):
    chat_col = f"{user_id}_{chat}"
    dbname = f"{user_id}-Forward-Bot"
    user_db = MongoDB(uri, dbname, chat_col)
    try:
        await user_db.connect()
    except Exception as e:
        print(f"User DB Connection Error: {e}")
        return False, user_db
    return True, user_db