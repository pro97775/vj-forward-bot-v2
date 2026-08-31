# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

import math
import time as tm
from collections import deque
from database import db
from .test import parse_buttons

STATUS = {}

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

class STS:
    def __init__(self, id):
        self.id = id
        self.data = STATUS

    def verify(self):
        return self.data.get(self.id)

    def store(self, From, to,  skip, limit):
        self.data[self.id] = {"FROM": From, 'TO': to, 'total_files': 0, 'skip': skip, 'limit': limit,
                      'fetched': skip, 'filtered': 0, 'deleted': 0, 'dumped': 0, 'total': limit,
                      'start': 0, 'bots': 0, 'status': 'starting', 'percentage': 0, 'eta': 0}
        self.get(full=True)
        return STS(self.id)

    def get(self, value=None, full=False):
        values = self.data.get(self.id)
        if values is None:
            return None if not full else self
        if not full:
           return values.get(value)
        for k, v in values.items():
            setattr(self, k, v)
        return self

    def set(self, key, value):
        if self.data.get(self.id) is None:
            return
        self.data[self.id].update({key: value})

    def add(self, key=None, value=1, time=False, start_time=None):
        if self.data.get(self.id) is None:
            return
        if time:
          return self.data[self.id].update({'start': tm.time() if start_time is None else start_time})
        self.data[self.id].update({key: (self.get(key) or 0) + (value or 0)})

    def divide(self, no, by):
       by = 1 if int(by) == 0 else by 
       return int(no) / by 

    async def get_data(self, user_id):
        """Return every setting needed for a forwarding task."""
        configs = await db.get_configs(user_id)
        bots = await db.get_bots(user_id)
        userbot = await db.get_userbot(user_id)
        keywords = "|".join(configs['keywords']) if configs['keywords'] else None
        extensions = "|".join(configs['extension']) if configs['extension'] else None
        return {
            'bots': bots,
            'userbot': userbot,
            'caption': configs['caption'],
            'forward_tag': configs['forward_tag'],
            'protect': configs['protect'],
            'button': parse_buttons(configs['button'] if configs['button'] else ''),
            'filters': await db.get_filters(user_id),
            'keywords': keywords,
            'extensions': extensions,
            'min_size': configs['min_size'] or 0,
            'max_size': configs['max_size'] or 0,
            'bot_delay': configs['bot_delay'],
            'userbot_delay': configs['userbot_delay'],
            'bot_rate': configs['bot_rate']
        }

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

class Robin:
    """Round robin scheduler.

    Every worker (bot) is allowed to send only `rate` messages per minute.
    Workers are used one after another so the total speed is
    `rate x number of bots` messages per minute.
    Userbots are used alone with rate=None (no per minute limit, only delay).
    """

    def __init__(self, workers, rate=20, delay=1):
        self.workers = list(workers)
        self.rate = int(rate) if rate and int(rate) > 0 else None
        self.delay = float(delay) if delay and float(delay) > 0 else 0
        self.index = 0
        self.used = {n: deque() for n in range(len(self.workers))}

    def __len__(self):
        return len(self.workers)

    @property
    def batch(self):
        """How many messages can be sent by one worker in a single call."""
        if self.rate is None:
            return 100
        return max(1, min(100, self.rate))

    def _wait_for(self, n, cost=1):
        """Seconds to wait before worker `n` can send `cost` messages."""
        if self.rate is None:
            return 0
        used = self.used[n]
        now = tm.time()
        while used and now - used[0] >= 60:
            used.popleft()
        if len(used) + cost <= self.rate:
            return 0
        # wait until enough old messages fall out of the 60s window
        need = len(used) + cost - self.rate
        need = min(need, len(used))
        return max(0, 60 - (now - used[need - 1]))

    def pick(self, cost=1):
        """Return (worker, 0) when a worker is free else (None, seconds)."""
        total = len(self.workers)
        if total == 0:
            return None, 0
        waits = []
        for step in range(total):
            n = (self.index + step) % total
            wait = self._wait_for(n, cost)
            if wait <= 0:
                self.index = (n + 1) % total
                if self.rate is not None:
                    now = tm.time()
                    for _ in range(cost):
                        self.used[n].append(now)
                return self.workers[n], 0
            waits.append(wait)
        return None, math.ceil(min(waits)) if waits else 0

    def names(self):
        return ", ".join(w['name'] for w in self.workers)

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

