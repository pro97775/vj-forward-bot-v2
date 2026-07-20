
# ============================================
# DATABASE METHODS TO ADD FOR MULTI-BOT SUPPORT
# ============================================
# Add these methods to your database/Db class
# (in database/__init__.py or wherever Db is defined)

async def add_bot_to_list(self, user_id, bot_details):
    """Add a bot to user's bot list (supports multiple bots)"""
    user_data = await self.col.find_one({'_id': user_id})
    bots = user_data.get('bots', []) if user_data else []

    # Check if bot already exists
    for bot in bots:
        if bot['id'] == bot_details['id']:
            return False  # Bot already added

    # Add new bot
    bots.append(bot_details)

    # Update user document
    await self.col.update_one(
        {'_id': user_id},
        {'$set': {'bots': bots}},
        upsert=True
    )
    return True

async def get_all_bots(self, user_id):
    """Get all bots for a user"""
    user_data = await self.col.find_one({'_id': user_id})
    if user_data and 'bots' in user_data:
        return user_data['bots']

    # Fallback: check old single-bot format
    old_bot = await self.get_bot(user_id)
    if old_bot:
        # Migrate to new format
        await self.add_bot_to_list(user_id, old_bot)
        return [old_bot]
    return []

async def remove_bot_by_index(self, user_id, index):
    """Remove a bot by its index in the list"""
    user_data = await self.col.find_one({'_id': user_id})
    if not user_data or 'bots' not in user_data:
        return False

    bots = user_data['bots']
    if 0 <= index < len(bots):
        bots.pop(index)
        await self.col.update_one(
            {'_id': user_id},
            {'$set': {'bots': bots}}
        )
        return True
    return False

async def remove_bot_by_id(self, user_id, bot_id):
    """Remove a bot by its ID"""
    user_data = await self.col.find_one({'_id': user_id})
    if not user_data or 'bots' not in user_data:
        return False

    bots = [b for b in user_data['bots'] if b['id'] != bot_id]
    await self.col.update_one(
        {'_id': user_id},
        {'$set': {'bots': bots}}
    )
    return True

# Keep backward compatibility - modify existing methods:
async def get_bot(self, user_id):
    """Get first bot (backward compatible)"""
    bots = await self.get_all_bots(user_id)
    return bots[0] if bots else None

async def add_bot(self, bot_details):
    """Add single bot (backward compatible)"""
    return await self.add_bot_to_list(bot_details['user_id'], bot_details)

async def remove_bot(self, user_id):
    """Remove all bots for user"""
    await self.col.update_one(
        {'_id': user_id},
        {'$unset': {'bots': ''}}
    )
