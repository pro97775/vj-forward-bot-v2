import time
import motor.motor_asyncio
from config import Config

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

DEFAULT_CONFIGS = {
    'caption': None,
    'forward_tag': False,
    'min_size': 0,
    'max_size': 0,
    'size_limit': None,
    'extension': None,
    'keywords': None,
    'protect': None,
    'button': None,
    # forwarding speed controls (editable from the bot ui)
    'bot_delay': Config.BOT_DELAY,
    'userbot_delay': Config.USERBOT_DELAY,
    'bot_rate': Config.BOT_RATE,
    'filters': {
        'poll': True,
        'text': True,
        'audio': True,
        'voice': True,
        'video': True,
        'photo': True,
        'document': True,
        'animation': True,
        'sticker': True
    }
}

DEFAULT_FORWARD = {
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
    'skip': 0,
    'filtered': 0,
    'dumped': 0
}


def _merge(default, current):
    """Return a copy of default updated with the values found in current."""
    data = {}
    for key, value in default.items():
        if isinstance(value, dict):
            sub = current.get(key) if isinstance(current, dict) else None
            data[key] = _merge(value, sub if isinstance(sub, dict) else {})
        elif isinstance(current, dict) and key in current:
            data[key] = current[key]
        else:
            data[key] = value
    return data

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01


class Db:

    def __init__(self, uri, database_name):
        self._client = motor.motor_asyncio.AsyncIOMotorClient(uri)
        self.db = self._client[database_name]
        self.bot = self.db.bots
        self.userbot = self.db.userbot 
        self.col = self.db.users
        self.nfy = self.db.notify
        self.chl = self.db.channels 
        self.misc = self.db.misc

    def new_user(self, id, name):
        return dict(
            id = id,
            name = name,
            ban_status=dict(
                is_banned=False,
                ban_reason="",
            ),
        )

    async def add_user(self, id, name):
        user = self.new_user(id, name)
        await self.col.insert_one(user)

    async def is_user_exist(self, id):
        user = await self.col.find_one({'id':int(id)})
        return bool(user)

    async def total_users_count(self):
        count = await self.col.count_documents({})
        return count

    async def total_users_bots_count(self):
        bcount = await self.bot.count_documents({})
        ucount = await self.userbot.count_documents({})
        count = await self.col.count_documents({})
        return count, bcount + ucount

    async def total_channels_count(self):
        return await self.chl.count_documents({})

    async def remove_ban(self, id):
        ban_status = dict(
            is_banned=False,
            ban_reason=''
        )
        await self.col.update_one({'id': id}, {'$set': {'ban_status': ban_status}})

    async def ban_user(self, user_id, ban_reason="No Reason"):
        ban_status = dict(
            is_banned=True,
            ban_reason=ban_reason
        )
        await self.col.update_one({'id': user_id}, {'$set': {'ban_status': ban_status}})

    async def get_ban_status(self, id):
        default = dict(
            is_banned=False,
            ban_reason=''
        )
        user = await self.col.find_one({'id':int(id)})
        if not user:
            return default
        return user.get('ban_status', default)

    async def get_all_users(self):
        return self.col.find({})

    async def delete_user(self, user_id):
        await self.col.delete_many({'id': int(user_id)})

    async def get_banned(self):
        users = self.col.find({'ban_status.is_banned': True})
        b_users = [user['id'] async for user in users]
        return b_users

    async def update_configs(self, id, configs):
        await self.col.update_one({'id': int(id)}, {'$set': {'configs': configs}}, upsert=True)

    async def get_configs(self, id):
        user = await self.col.find_one({'id': int(id)})
        current = user.get('configs', {}) if user else {}
        # merging keeps old users working when new settings are added
        return _merge(DEFAULT_CONFIGS, current if isinstance(current, dict) else {})

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

    async def add_bot(self, datas):
       """Add a bot for round robin forwarding. Returns False on duplicate."""
       if await self.is_bot_exist(datas['user_id'], datas['id']):
          return False
       datas['added_at'] = time.time()
       await self.bot.insert_one(datas)
       return True

    async def remove_bot(self, user_id, bot_id=None):
       data = {'user_id': int(user_id)}
       if bot_id is not None:
          data['id'] = int(bot_id)
       await self.bot.delete_many(data)

    async def get_bot(self, user_id: int):
       """First added bot of the user (single client fallback)."""
       bots = await self.get_bots(user_id)
       return bots[0] if bots else None

    async def get_bots(self, user_id: int):
       """All bots of a user in the order they were added."""
       bots = self.bot.find({'user_id': int(user_id)})
       bots = [bot async for bot in bots]
       bots.sort(key=lambda b: b.get('added_at', 0))
       return bots

    async def count_bots(self, user_id: int):
       return await self.bot.count_documents({'user_id': int(user_id)})

    async def is_bot_exist(self, user_id, bot_id=None):
       data = {'user_id': int(user_id)}
       if bot_id is not None:
          data['id'] = int(bot_id)
       bot = await self.bot.find_one(data)
       return bool(bot)
   
    async def add_userbot(self, datas):
       # only one userbot per user, a new session replaces the old one
       await self.userbot.delete_many({'user_id': int(datas['user_id'])})
       datas['added_at'] = time.time()
       await self.userbot.insert_one(datas)
       return True

    async def remove_userbot(self, user_id):
       await self.userbot.delete_many({'user_id': int(user_id)})

    async def get_userbot(self, user_id: int):
       bot = await self.userbot.find_one({'user_id': int(user_id)})
       return bot if bot else None

    async def is_userbot_exist(self, user_id):
       bot = await self.userbot.find_one({'user_id': int(user_id)})
       return bool(bot)
    
    async def in_channel(self, user_id: int, chat_id: int) -> bool:
       channel = await self.chl.find_one({"user_id": int(user_id), "chat_id": int(chat_id)})
       return bool(channel)

    async def add_channel(self, user_id: int, chat_id: int, title, username):
       channel = await self.in_channel(user_id, chat_id)
       if channel:
         return False
       return await self.chl.insert_one({"user_id": int(user_id), "chat_id": int(chat_id), "title": title, "username": username})

    async def remove_channel(self, user_id: int, chat_id: int):
       channel = await self.in_channel(user_id, chat_id )
       if not channel:
         return False
       return await self.chl.delete_many({"user_id": int(user_id), "chat_id": int(chat_id)})

    async def get_channel_details(self, user_id: int, chat_id: int):
       return await self.chl.find_one({"user_id": int(user_id), "chat_id": int(chat_id)})

    async def get_user_channels(self, user_id: int):
       channels = self.chl.find({"user_id": int(user_id)})
       return [channel async for channel in channels]

    async def get_filters(self, user_id):
       filters = []
       filter = (await self.get_configs(user_id))['filters']
       for k, v in filter.items():
          if v == False:
            filters.append(str(k))
       return filters

    async def add_frwd(self, user_id):
       if await self.is_forwad_exit(int(user_id)):
          return
       return await self.nfy.insert_one({'user_id': int(user_id)})

    async def rmve_frwd(self, user_id=0, all=False):
       data = {} if all else {'user_id': int(user_id)}
       return await self.nfy.delete_many(data)

    async def get_all_frwd(self):
       return self.nfy.find({})
  
    async def forwad_count(self):
        c = await self.nfy.count_documents({})
        return c
        
    async def is_forwad_exit(self, user):
        u = await self.nfy.find_one({'user_id': int(user)})
        return bool(u)
        
    async def get_forward_details(self, user_id):
        user = await self.nfy.find_one({'user_id': int(user_id)})
        details = user.get('details', {}) if user else {}
        return _merge(DEFAULT_FORWARD, details if isinstance(details, dict) else {})
   
    async def update_forward(self, user_id, details):
        await self.nfy.update_one({'user_id': int(user_id)}, {'$set': {'details': details}}, upsert=True)

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

    async def get_settings(self):
        """Global (owner) settings."""
        default = {'dump_chat': Config.DUMP_CHAT}
        data = await self.misc.find_one({'_id': 'settings'})
        if not data:
            return default
        return _merge(default, data)

    async def update_setting(self, key, value):
        await self.misc.update_one({'_id': 'settings'}, {'$set': {key: value}}, upsert=True)

    async def get_dump_chat(self):
        return (await self.get_settings())['dump_chat']

    async def set_dump_chat(self, chat_id):
        await self.update_setting('dump_chat', int(chat_id) if chat_id else 0)
        
db = Db(Config.DATABASE_URI, Config.DATABASE_NAME)

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

