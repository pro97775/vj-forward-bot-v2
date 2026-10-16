import asyncio
import copy
import types

# Python 3.11+ compatibility shim in case an older motor version is installed
if not hasattr(asyncio, "coroutine"):
    asyncio.coroutine = types.coroutine

import motor.motor_asyncio
from config import Config


DEFAULT_CONFIGS = {
    'caption': None,
    'prefix': None,
    'suffix': None,
    'duplicate': True,
    'forward_tag': False,
    'min_size': 0,
    'max_size': 0,
    'size_limit': None,
    'extension': None,
    'keywords': None,
    'protect': False,
    'button': None,
    'db_uri': None,
    'forward_mode': 'pool',  # 'pool' (Multi-Bot Pool) or 'userbot' (Userbot Session)
    'cleaners': {
        'username': False,
        'tme': False,
        'url': False,
        'html_links': False,
    },
    'replacements': {},
    'filters': {
        'poll': True,
        'text': True,
        'audio': True,
        'voice': True,
        'video': True,
        'photo': True,
        'document': True,
        'animation': True,
        'sticker': True,
    }
}


DEFAULT_FORWARD_DETAILS = {
    'chat_id': None,
    'forward_id': None,
    'toid': None,
    'last_id': None,
    'limit': None,
    'msg_id': None,
    'start_time': None,
    'fetched': 0,
    'offset': 0,
    'deleted': 0,
    'total': 0,
    'duplicate': 0,
    'skip': 0,
    'filtered': 0,
    'mode': 'pool',
    'status': 'idle',  # 'running', 'paused', 'idle'
}


class Db:
    def __init__(self, uri, database_name):
        self._client = motor.motor_asyncio.AsyncIOMotorClient(uri) if uri else None
        self.db = self._client[database_name] if self._client is not None else None
        self.bot = self.db.bots if self.db is not None else None
        self.userbot = self.db.userbot if self.db is not None else None
        self.col = self.db.users if self.db is not None else None
        self.nfy = self.db.notify if self.db is not None else None
        self.chl = self.db.channels if self.db is not None else None
        self.dup = self.db.dup_files if self.db is not None else None

    def new_user(self, id, name):
        return dict(
            id=int(id),
            name=name,
            ban_status=dict(
                is_banned=False,
                ban_reason="",
            ),
            configs=copy.deepcopy(DEFAULT_CONFIGS),
        )

    async def add_user(self, id, name):
        if not await self.is_user_exist(id):
            user = self.new_user(id, name)
            await self.col.insert_one(user)

    async def is_user_exist(self, id):
        user = await self.col.find_one({'id': int(id)})
        return bool(user)

    async def total_users_count(self):
        return await self.col.count_documents({})

    async def total_users_bots_count(self):
        bcount = await self.bot.count_documents({})
        ucount = await self.userbot.count_documents({})
        count = await self.col.count_documents({})
        return count, bcount + ucount

    async def remove_ban(self, id):
        ban_status = dict(is_banned=False, ban_reason='')
        await self.col.update_one({'id': int(id)}, {'$set': {'ban_status': ban_status}})

    async def ban_user(self, user_id, ban_reason="No Reason"):
        ban_status = dict(is_banned=True, ban_reason=ban_reason)
        await self.col.update_one({'id': int(user_id)}, {'$set': {'ban_status': ban_status}})

    async def get_ban_status(self, id):
        default = dict(is_banned=False, ban_reason='')
        user = await self.col.find_one({'id': int(id)})
        if not user:
            return default
        return user.get('ban_status', default)

    async def get_all_users(self):
        return self.col.find({})

    async def delete_user(self, user_id):
        await self.col.delete_many({'id': int(user_id)})

    async def get_banned(self):
        users = self.col.find({'ban_status.is_banned': True})
        return [user['id'] async for user in users]

    async def update_configs(self, id, configs):
        await self.col.update_one(
            {'id': int(id)},
            {'$set': {'configs': configs}},
            upsert=True
        )

    async def get_configs(self, id):
        merged = copy.deepcopy(DEFAULT_CONFIGS)
        user = await self.col.find_one({'id': int(id)})
        if user and 'configs' in user and isinstance(user['configs'], dict):
            saved = user['configs']
            for k, v in saved.items():
                if k in ('filters', 'cleaners') and isinstance(v, dict):
                    merged[k].update(v)
                elif k == 'replacements' and isinstance(v, dict):
                    merged['replacements'] = dict(v)
                else:
                    merged[k] = v
        return merged

    # ------------------------------------------------------------------
    # Multi-Bot Pool Management (Multiple Worker Bots per User)
    # ------------------------------------------------------------------
    async def add_bot(self, datas: dict) -> str:
        user_id = int(datas['user_id'])
        bot_id = int(datas['id'])
        datas['user_id'] = user_id
        datas['id'] = bot_id
        datas['is_bot'] = True
        existing = await self.bot.find_one({'user_id': user_id, 'id': bot_id})
        if existing:
            await self.bot.update_one(
                {'user_id': user_id, 'id': bot_id},
                {'$set': datas}
            )
            return "updated"
        await self.bot.insert_one(datas)
        return "added"

    async def get_bots(self, user_id: int) -> list:
        cursor = self.bot.find({'user_id': int(user_id)})
        bots = [b async for b in cursor]
        return bots

    async def get_bot(self, user_id: int, bot_id: int = None):
        query = {'user_id': int(user_id)}
        if bot_id is not None:
            query['id'] = int(bot_id)
        bot = await self.bot.find_one(query)
        return bot if bot else None

    async def remove_bot(self, user_id: int, bot_id: int = None):
        query = {'user_id': int(user_id)}
        if bot_id is not None:
            query['id'] = int(bot_id)
        await self.bot.delete_many(query)

    async def is_bot_exist(self, user_id: int, bot_id: int = None) -> bool:
        query = {'user_id': int(user_id)}
        if bot_id is not None:
            query['id'] = int(bot_id)
        bot = await self.bot.find_one(query)
        return bool(bot)

    # ------------------------------------------------------------------
    # Userbot Management (For Private / Restricted Source Chats)
    # ------------------------------------------------------------------
    async def add_userbot(self, datas: dict):
        user_id = int(datas['user_id'])
        datas['user_id'] = user_id
        datas['is_bot'] = False
        await self.userbot.update_one(
            {'user_id': user_id},
            {'$set': datas},
            upsert=True
        )

    async def remove_userbot(self, user_id: int):
        await self.userbot.delete_many({'user_id': int(user_id)})

    async def get_userbot(self, user_id: int):
        bot = await self.userbot.find_one({'user_id': int(user_id)})
        return bot if bot else None

    async def is_userbot_exist(self, user_id: int) -> bool:
        bot = await self.userbot.find_one({'user_id': int(user_id)})
        return bool(bot)

    # ------------------------------------------------------------------
    # Target Channels Management
    # ------------------------------------------------------------------
    async def in_channel(self, user_id: int, chat_id: int) -> bool:
        channel = await self.chl.find_one({"user_id": int(user_id), "chat_id": int(chat_id)})
        return bool(channel)

    async def add_channel(self, user_id: int, chat_id: int, title, username):
        if await self.in_channel(user_id, chat_id):
            return False
        return await self.chl.insert_one({
            "user_id": int(user_id),
            "chat_id": int(chat_id),
            "title": title,
            "username": username
        })

    async def remove_channel(self, user_id: int, chat_id: int):
        if not await self.in_channel(user_id, chat_id):
            return False
        return await self.chl.delete_many({"user_id": int(user_id), "chat_id": int(chat_id)})

    async def get_channel_details(self, user_id: int, chat_id: int):
        return await self.chl.find_one({"user_id": int(user_id), "chat_id": int(chat_id)})

    async def get_user_channels(self, user_id: int):
        channels = self.chl.find({"user_id": int(user_id)})
        return [channel async for channel in channels]

    # ------------------------------------------------------------------
    # Filters & Forward State Persistence (Pause / Resume / Recovery)
    # ------------------------------------------------------------------
    async def get_filters(self, user_id: int):
        disabled_filters = []
        filters_cfg = (await self.get_configs(user_id))['filters']
        for k, v in filters_cfg.items():
            if v is False:
                disabled_filters.append(str(k))
        return disabled_filters

    async def add_frwd(self, user_id: int):
        await self.nfy.update_one(
            {'user_id': int(user_id)},
            {'$setOnInsert': {'user_id': int(user_id), 'details': copy.deepcopy(DEFAULT_FORWARD_DETAILS)}},
            upsert=True
        )

    async def rmve_frwd(self, user_id: int = 0, all: bool = False):
        data = {} if all else {'user_id': int(user_id)}
        return await self.nfy.delete_many(data)

    async def get_all_frwd(self):
        return self.nfy.find({})

    async def forwad_count(self):
        return await self.nfy.count_documents({})

    async def is_forwad_exit(self, user_id: int):
        u = await self.nfy.find_one({'user_id': int(user_id)})
        return bool(u and u.get('details', {}).get('chat_id') is not None)

    async def get_forward_details(self, user_id: int):
        merged = copy.deepcopy(DEFAULT_FORWARD_DETAILS)
        user = await self.nfy.find_one({'user_id': int(user_id)})
        if user and isinstance(user.get('details'), dict):
            merged.update(user['details'])
        return merged

    async def update_forward(self, user_id: int, details: dict):
        await self.nfy.update_one(
            {'user_id': int(user_id)},
            {'$set': {'user_id': int(user_id), 'details': details}},
            upsert=True
        )

    # ------------------------------------------------------------------
    # Built-in Persistent Deduplication Storage (Unpacked File IDs)
    # ------------------------------------------------------------------
    async def add_dup_file(self, user_id: int, chat_id: int, file_id: str):
        await self.dup.update_one(
            {'user_id': int(user_id), 'chat_id': int(chat_id), 'file_id': file_id},
            {'$set': {'user_id': int(user_id), 'chat_id': int(chat_id), 'file_id': file_id}},
            upsert=True
        )

    async def get_dup_files(self, user_id: int, chat_id: int) -> set:
        cursor = self.dup.find({'user_id': int(user_id), 'chat_id': int(chat_id)}, {'file_id': 1})
        return {doc['file_id'] async for doc in cursor if 'file_id' in doc}

    async def clear_dup_files(self, user_id: int, chat_id: int = None):
        query = {'user_id': int(user_id)}
        if chat_id is not None:
            query['chat_id'] = int(chat_id)
        await self.dup.delete_many(query)


db = Db(Config.DATABASE_URI, Config.DATABASE_NAME)