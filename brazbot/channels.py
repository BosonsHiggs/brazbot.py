import aiohttp
import json
import logging
import websockets
from datetime import datetime, timezone
from .voiceclient import VoiceClient

"""
SEE: 
    1. https://discord.com/developers/docs/resources/channel#get-channel
    2. https://discord.com/developers/docs/topics/voice-connections
    3. https://discord.com/developers/docs/topics/voice-connections#connecting-to-voice
"""
class Channel:
    def __init__(self, data, bot=None, guild_id=None, channel_id=None, user_id=None):
        self.bot = bot
        self.id = channel_id
        self.name = data.get('name')
        self.category = data.get('category')
        self.changed_roles = data.get('changed_roles', [])
        self.created_at = datetime.fromtimestamp(((int(self.id) >> 22) + 1420070400000) / 1000)
        self.guild = data.get('guild')
        self.guild_id = guild_id
        self.jump_url = data.get('jump_url')
        self.mention = data.get('mention')
        self.overwrites = data.get('overwrites', {})
        self.permissions_synced = data.get('permissions_synced', False)
        self.position = data.get('position')
        self.type = data.get('type')
        self.type_channel = "channel"
        self.user_id = user_id

        """
        ['__class__', '__delattr__', '__dict__', '__dir__', '__doc__', '__eq__', 
        '__format__', '__ge__', '__getattribute__', '__gt__', '__hash__', '__init__', 
        '__init_subclass__', '__le__', '__lt__', '__module__', '__ne__', '__new__', 
        '__reduce__', '__reduce_ex__', '__repr__', '__setattr__', '__sizeof__', '__str__', 
        '__subclasshook__', '__weakref__', 'bot', 'category', 'changed_roles', 'channel_type', 
        'clone', 'create_invite', 'created_at', 'delete', 'from_channel_id', 'guild', 'id', 
        'invites', 'jump_url', 'mention', 'move', 'name', 'overwrites', 'overwrites_for', 
        'permissions_for', 'permissions_synced', 'position', 'send_message', 'set_permissions', 'type']
        """

    @classmethod
    async def from_channel_id(cls, bot, guild_id, channel_id, user_id):
        cache_key = f"channel_{channel_id}"
        data = bot.get_cache_data(cache_key)

        if data:
            return cls(data, bot, guild_id, channel_id, user_id)

        url = f"https://discord.com/api/v10/channels/{channel_id}"
        headers = {
            "Authorization": f"Bot {bot.token}"
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    bot.set_cache_data(cache_key, data, seconds=120)
                    return cls(data, bot, guild_id, channel_id, user_id)
                else:
                    raise Exception(f"Failed to fetch channel data: {response.status}")

    def getChanelType(self):
        return self.type_channel

    def __str__(self):
        return self.name

    async def send_message(self, content=None, embed=None, embeds=None, files=None, components=None, ephemeral=False):
        url = f"{self.base_url}/channels/{self.id}/messages"
        data = {}
        if content:
            data["content"] = str(content)
        if embed:
            data["embeds"] = [embed]
        if embeds:
            data["embeds"] = embeds
        if components:
            data["components"] = components
        if ephemeral:
            data["flags"] = 64  # This flag makes the response ephemeral

        async with aiohttp.ClientSession() as session:
            if files:
                form = FormData()
                form.add_field('payload_json', json.dumps(data))
                for file in files:
                    form.add_field('file', file['data'], filename=file['filename'], content_type=file['content_type'])
                async with session.post(url, headers=self.headers, data=form) as response:
                    if response.status != 200:
                        logging.error(f"Failed to send message with file: {response.status} - {await response.text()}")
                        return None
                    else:
                        response_json = await response.json()
                        logging.info(f"Message sent with file: {response_json}")
                        return response_json
            else:
                async with session.post(url, headers=self.headers, json=data) as response:
                    if response.status != 200:
                        logging.error(f"Failed to send message: {response.status} - {await response.text()}")
                        return None
                    else:
                        response_json = await response.json()
                        logging.info(f"Message sent: {response_json}")
                        return response_json

    # Methods to interact with the Discord API
    async def clone(self, name=None, reason=None):
        url = f"https://discord.com/api/v10/channels/{self.id}/clone"
        headers = {
            "Authorization": f"Bot {self.bot.token}",
            "Content-Type": "application/json"
        }
        json_data = {
            "name": name or self.name,
            "reason": reason
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=json_data) as response:
                if response.status != 200:
                    raise Exception(f"Failed to clone channel {self.id}: {response.status}")

    async def create_invite(self, max_age=86400, max_uses=0, temporary=False, unique=True):
        url = f"https://discord.com/api/v10/channels/{self.id}/invites"
        headers = {
            "Authorization": f"Bot {self.bot.token}",
            "Content-Type": "application/json"
        }
        json_data = {
            "max_age": max_age,
            "max_uses": max_uses,
            "temporary": temporary,
            "unique": unique
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=json_data) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"Failed to create invite for channel {self.id}: {response.status}")

    async def delete(self, reason=None):
        url = f"https://discord.com/api/v10/channels/{self.id}"
        headers = {
            "Authorization": f"Bot {self.bot.token}",
            "Content-Type": "application/json"
        }
        async with aiohttp.ClientSession() as session:
            async with session.delete(url, headers=headers) as response:
                if response.status != 204:
                    raise Exception(f"Failed to delete channel {self.id}: {response.status}")

    async def invites(self):
        url = f"https://discord.com/api/v10/channels/{self.id}/invites"
        headers = {
            "Authorization": f"Bot {self.bot.token}"
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"Failed to fetch invites for channel {self.id}: {response.status}")

    async def move(self, position, parent_id=None, lock_permissions=False, reason=None):
        url = f"https://discord.com/api/v10/channels/{self.id}"
        headers = {
            "Authorization": f"Bot {self.bot.token}",
            "Content-Type": "application/json"
        }
        json_data = {
            "position": position,
            "parent_id": parent_id,
            "lock_permissions": lock_permissions,
            "reason": reason
        }
        async with aiohttp.ClientSession() as session:
            async with session.patch(url, headers=headers, json=json_data) as response:
                if response.status != 200:
                    raise Exception(f"Failed to move channel {self.id}: {response.status}")

    def overwrites_for(self, member_or_role):
        return self.overwrites.get(str(member_or_role.id))

    async def permissions_for(self, member_or_role):
        url = f"https://discord.com/api/v10/channels/{self.id}/permissions/{member_or_role.id}"
        headers = {
            "Authorization": f"Bot {self.bot.token}"
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"Failed to fetch permissions for {member_or_role.id} in channel {self.id}: {response.status}")

    async def set_permissions(self, member_or_role, allow, deny, reason=None):
        url = f"https://discord.com/api/v10/channels/{self.id}/permissions/{member_or_role.id}"
        headers = {
            "Authorization": f"Bot {self.bot.token}",
            "Content-Type": "application/json"
        }
        json_data = {
            "allow": allow,
            "deny": deny,
            "reason": reason
        }
        async with aiohttp.ClientSession() as session:
            async with session.put(url, headers=headers, json=json_data) as response:
                if response.status != 204:
                    raise Exception(f"Failed to set permissions for {member_or_role.id} in channel {self.id}: {response.status}")

    def channel_type(self):
        if self.type == 0:
            return "Text"
        elif self.type == 2:
            return "Voice"
        elif self.type == 4:
            return "Category"
        elif self.type == 5:
            return "Announcement"
        elif self.type == 10 or self.type == 11 or self.type == 12:
            return "Thread"
        elif self.type == 13:
            return "Stage"
        elif self.type == 14:
            return "Directory"
        elif self.type == 15:
            return "Forum"
        else:
            return "Unknown"

class TextChannel():
    def __init__(self, data, bot=None, guild_id=None, channel_id=None, user_id=None):
        self.bot = bot
        self.id = channel_id
        self.name = data.get('name')
        self.category = data.get('category')
        self.changed_roles = data.get('changed_roles', [])
        self.created_at = datetime.fromtimestamp(((int(self.id) >> 22) + 1420070400000) / 1000)
        self.guild = data.get('guild')
        self.guild_id = guild_id
        self.jump_url = data.get('jump_url')
        self.mention = data.get('mention')
        self.overwrites = data.get('overwrites', {})
        self.permissions_synced = data.get('permissions_synced', False)
        self.position = data.get('position')
        self.type = data.get('type')

        self.category_id = data.get('category_id')
        self.default_auto_archive_duration = data.get('default_auto_archive_duration')
        self.default_thread_slowmode_delay = data.get('default_thread_slowmode_delay')
        self.last_message_id = data.get('last_message_id')
        self.nsfw = data.get('nsfw')
        self.slowmode_delay = data.get('slowmode_delay')
        self.topic = data.get('topic')
        self.type = data.get('type')
        self.threads = data.get('threads', [])
        self.members = data.get('members', [])
        self.last_message = None
        self.bot = bot
        self.type_channel = "text"
        self.user_id = user_id

    @classmethod
    async def from_channel_id(cls, bot, guild_id, channel_id, user_id):
        cache_key = f"channel_{channel_id}"
        data = bot.get_cache_data(cache_key)

        if data:
            return cls(data, bot, guild_id, channel_id, user_id)

        url = f"https://discord.com/api/v10/channels/{channel_id}"
        headers = {
            "Authorization": f"Bot {self.bot.token}"
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    bot.set_cache_data(cache_key, data, seconds=120)
                    return cls(data, bot, guild_id, channel_id, user_id)
                else:
                    raise Exception(f"Failed to fetch channel data: {response.status}")

    def getChhanelType(self):
        return self.type_channel

    async def archived_threads(self, before=None, limit=50):
        url = f"https://discord.com/api/v10/channels/{self.id}/threads/archived/public"
        headers = {
            "Authorization": f"Bot {self.bot.token}"
        }
        params = {"before": before, "limit": limit}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"Failed to fetch archived threads: {response.status}")

    async def clone(self, name=None, reason=None):
        url = f"https://discord.com/api/v10/channels/{self.id}/clone"
        headers = {
            "Authorization": f"Bot {self.bot.token}",
            "Content-Type": "application/json"
        }
        json_data = {
            "name": name or self.name,
            "reason": reason
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=json_data) as response:
                if response.status != 200:
                    raise Exception(f"Failed to clone channel {self.id}: {response.status}")

    async def create_invite(self, max_age=86400, max_uses=0, temporary=False, unique=True):
        url = f"https://discord.com/api/v10/channels/{self.id}/invites"
        headers = {
            "Authorization": f"Bot {self.bot.token}",
            "Content-Type": "application/json"
        }
        json_data = {
            "max_age": max_age,
            "max_uses": max_uses,
            "temporary": temporary,
            "unique": unique
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=json_data) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"Failed to create invite for channel {self.id}: {response.status}")

    async def create_thread(self, name, auto_archive_duration=1440, type=11, reason=None):
        url = f"https://discord.com/api/v10/channels/{self.id}/threads"
        headers = {
            "Authorization": f"Bot {self.bot.token}",
            "Content-Type": "application/json"
        }
        json_data = {
            "name": name,
            "auto_archive_duration": auto_archive_duration,
            "type": type,
            "reason": reason
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=json_data) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"Failed to create thread: {response.status}")

    async def create_webhook(self, name, avatar=None, reason=None):
        url = f"https://discord.com/api/v10/channels/{self.id}/webhooks"
        headers = {
            "Authorization": f"Bot {self.bot.token}",
            "Content-Type": "application/json"
        }
        json_data = {
            "name": name,
            "avatar": avatar,
            "reason": reason
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=json_data) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"Failed to create webhook: {response.status}")

    async def delete(self, reason=None):
        url = f"https://discord.com/api/v10/channels/{self.id}"
        headers = {
            "Authorization": f"Bot {self.bot.token}",
            "Content-Type": "application/json"
        }
        async with aiohttp.ClientSession() as session:
            async with session.delete(url, headers=headers) as response:
                if response.status != 204:
                    raise Exception(f"Failed to delete channel {self.id}: {response.status}")

    async def delete_messages(self, message_ids, reason=None):
        url = f"https://discord.com/api/v10/channels/{self.id}/messages/bulk-delete"
        headers = {
            "Authorization": f"Bot {self.bot.token}",
            "Content-Type": "application/json"
        }
        json_data = {
            "messages": message_ids,
            "reason": reason
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=json_data) as response:
                if response.status != 204:
                    raise Exception(f"Failed to delete messages: {response.status}")

    async def edit(self, **fields):
        url = f"https://discord.com/api/v10/channels/{self.id}"
        headers = {
            "Authorization": f"Bot {self.bot.token}",
            "Content-Type": "application/json"
        }
        async with aiohttp.ClientSession() as session:
            async with session.patch(url, headers=headers, json=fields) as response:
                if response.status != 200:
                    raise Exception(f"Failed to edit channel {self.id}: {response.status}")

    async def fetch_message(self, message_id):
        url = f"https://discord.com/api/v10/channels/{self.id}/messages/{message_id}"
        headers = {
            "Authorization": f"Bot {self.bot.token}"
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"Failed to fetch message: {response.status}")

    async def follow(self, webhook_channel_id, reason=None):
        url = f"https://discord.com/api/v10/channels/{self.id}/followers"
        headers = {
            "Authorization": f"Bot {self.bot.token}",
            "Content-Type": "application/json"
        }
        json_data = {
            "webhook_channel_id": webhook_channel_id,
            "reason": reason
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=json_data) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"Failed to follow channel: {response.status}")

    def get_partial_message(self, message_id):
        return PartialMessage(channel=self, id=message_id)

    async def get_thread(self, thread_id):
        url = f"https://discord.com/api/v10/channels/{thread_id}"
        headers = {
            "Authorization": f"Bot {self.bot.token}"
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"Failed to fetch thread: {response.status}")

    async def history(self, limit=100, before=None, after=None, around=None):
        url = f"https://discord.com/api/v10/channels/{self.id}/messages"
        headers = {
            "Authorization": f"Bot {self.bot.token}"
        }
        params = {"limit": limit}
        if before:
            params["before"] = before
        if after:
            params["after"] = after
        if around:
            params["around"] = around

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"Failed to fetch message history: {response.status}")

    async def invites(self):
        url = f"https://discord.com/api/v10/channels/{self.id}/invites"
        headers = {
            "Authorization": f"Bot {self.bot.token}"
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"Failed to fetch invites: {response.status}")

    def is_news(self):
        return self.type == 5

    def is_nsfw(self):
        return self.nsfw

    async def move(self, position, parent_id=None, lock_permissions=False, reason=None):
        url = f"https://discord.com/api/v10/channels/{self.id}"
        headers = {
            "Authorization": f"Bot {self.bot.token}",
            "Content-Type": "application/json"
        }
        json_data = {
            "position": position,
            "parent_id": parent_id,
            "lock_permissions": lock_permissions,
            "reason": reason
        }
        async with aiohttp.ClientSession() as session:
            async with session.patch(url, headers=headers, json=json_data) as response:
                if response.status != 200:
                    raise Exception(f"Failed to move channel {self.id}: {response.status}")

    def overwrites_for(self, member_or_role):
        return self.overwrites.get(str(member_or_role.id))

    async def permissions_for(self, member_or_role):
        url = f"https://discord.com/api/v10/channels/{self.id}/permissions/{member_or_role.id}"
        headers = {
            "Authorization": f"Bot {self.bot.token}"
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"Failed to fetch permissions for {member_or_role.id} in channel {self.id}: {response.status}")

    async def set_permissions(self, member_or_role, allow, deny, reason=None):
        url = f"https://discord.com/api/v10/channels/{self.id}/permissions/{member_or_role.id}"
        headers = {
            "Authorization": f"Bot {self.bot.token}",
            "Content-Type": "application/json"
        }
        json_data = {
            "allow": allow,
            "deny": deny,
            "reason": reason
        }
        async with aiohttp.ClientSession() as session:
            async with session.put(url, headers=headers, json=json_data) as response:
                if response.status != 204:
                    raise Exception(f"Failed to set permissions for {member_or_role.id} in channel {self.id}: {response.status}")

    async def pins(self):
        url = f"https://discord.com/api/v10/channels/{self.id}/pins"
        headers = {
            "Authorization": f"Bot {self.bot.token}"
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"Failed to fetch pinned messages: {response.status}")

    async def purge(self, limit=100, check=None, before=None, after=None, around=None):
        messages = []
        async for message in self.history(limit=limit, before=before, after=after, around=around):
            if check is None or check(message):
                messages.append(message)
        if messages:
            await self.delete_messages([message['id'] for message in messages])

    async def send(self, content=None, embed=None, embeds=None, files=None, components=None, ephemeral=False):
        url = f"https://discord.com/api/v10/channels/{self.id}/messages"
        data = {}
        if content:
            data["content"] = str(content)
        if embed:
            data["embeds"] = [embed]
        if embeds:
            data["embeds"] = embeds
        if components:
            data["components"] = components
        if ephemeral:
            data["flags"] = 64  # This flag makes the response ephemeral

        async with aiohttp.ClientSession() as session:
            if files:
                form = aiohttp.FormData()
                form.add_field('payload_json', json.dumps(data))
                for file in files:
                    form.add_field('file', file['data'], filename=file['filename'], content_type=file['content_type'])
                async with session.post(url, headers=self.headers, data=form) as response:
                    if response.status != 200:
                        logging.error(f"Failed to send message with file: {response.status} - {await response.text()}")
                        return None
                    else:
                        response_json = await response.json()
                        logging.info(f"Message sent with file: {response_json}")
                        return response_json
            else:
                async with session.post(url, headers=self.headers, json=data) as response:
                    if response.status != 200:
                        logging.error(f"Failed to send message: {response.status} - {await response.text()}")
                        return None
                    else:
                        response_json = await response.json()
                        logging.info(f"Message sent: {response_json}")
                        return response_json

    async def typing(self):
        url = f"https://discord.com/api/v10/channels/{self.id}/typing"
        headers = {
            "Authorization": f"Bot {self.bot.token}"
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers) as response:
                if response.status != 204:
                    raise Exception(f"Failed to trigger typing indicator: {response.status}")

    async def webhooks(self):
        url = f"https://discord.com/api/v10/channels/{self.id}/webhooks"
        headers = {
            "Authorization": f"Bot {self.bot.token}"
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"Failed to fetch webhooks: {response.status}")

class VoiceChannel():
    def __init__(self, data, bot=None, guild_id=None, channel_id=None, user_id=None):
        self.bot = bot
        self.id = channel_id
        self.type = data.get('type')
        self.last_message_id = data.get('last_message_id')
        self.flags = data.get('flags')
        self.type_channel = "voice"
        self.guild_id = guild_id
        self.name = data.get('name')
        self.category_id = data.get('parent_id')
        self.rate_limit_per_user = data.get('rate_limit_per_user', 0)
        self.bitrate = data.get('bitrate')
        self.user_limit = data.get('user_limit')
        self.rtc_region = data.get('rtc_region')
        self.position = data.get('position')
        self.permission_overwrites = data.get('permission_overwrites')
        self.nsfw = data.get('nsfw')
        self.user_id = user_id
        

    @classmethod
    async def from_channel_id(cls, bot, guild_id, channel_id, user_id):
        cache_key = f"channel_{channel_id}"
        data = bot.get_cache_data(cache_key)

        if data:
            return cls(data, bot, guild_id, channel_id, user_id)

        url = f"https://discord.com/api/v10/channels/{channel_id}"
        headers = {
            "Authorization": f"Bot {bot.token}"
        }

        """
        data: {'id': '1130837585502150809', 'type': 2, 'last_message_id': None, 'flags': 0, 
                'guild_id': '1130837584742977697', 'name': 'Geral', 'parent_id': '1130837585502150807', 
                'rate_limit_per_user': 0, 'bitrate': 64000, 'user_limit': 0, 'rtc_region': None, 'position': 0, 
                'permission_overwrites': [{'id': '1130837584742977697', 'type': 0, 'allow': '2150630400', 
                'deny': '0'}], 'nsfw': False
            }
        """
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    bot.set_cache_data(cache_key, data, seconds=120)
                    return cls(data, bot, guild_id, channel_id, user_id)
                else:
                    raise Exception(f"Failed to fetch channel data: {response.status}")

    def getChhanelType(self):
        return self.type_channel

    async def clone(self, name=None, reason=None):
        url = f"https://discord.com/api/v10/channels/{self.id}/clone"
        headers = {
            "Authorization": f"Bot {self.bot.token}",
            "Content-Type": "application/json"
        }
        json_data = {
            "name": name or self.name,
            "reason": reason
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=json_data) as response:
                if response.status != 200:
                    raise Exception(f"Failed to clone channel {self.id}: {response.status}")

    async def _heartbeat(self, ws, interval):
        while True:
            await asyncio.sleep(interval / 1000)
            await ws.send(json.dumps({"op": 3, "d": None}))

    async def create_invite(self, max_age=86400, max_uses=0, temporary=False, unique=True):
        url = f"https://discord.com/api/v10/channels/{self.id}/invites"
        headers = {
            "Authorization": f"Bot {self.bot.token}",
            "Content-Type": "application/json"
        }
        json_data = {
            "max_age": max_age,
            "max_uses": max_uses,
            "temporary": temporary,
            "unique": unique
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=json_data) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"Failed to create invite for channel {self.id}: {response.status}")

    async def create_webhook(self, name, avatar=None, reason=None):
        url = f"https://discord.com/api/v10/channels/{self.id}/webhooks"
        headers = {
            "Authorization": f"Bot {self.bot.token}",
            "Content-Type": "application/json"
        }
        json_data = {
            "name": name,
            "avatar": avatar,
            "reason": reason
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=json_data) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"Failed to create webhook for channel {self.id}: {response.status}")

    async def delete(self, reason=None):
        url = f"https://discord.com/api/v10/channels/{self.id}"
        headers = {
            "Authorization": f"Bot {self.bot.token}",
            "Content-Type": "application/json"
        }
        async with aiohttp.ClientSession() as session:
            async with session.delete(url, headers=headers) as response:
                if response.status != 204:
                    raise Exception(f"Failed to delete channel {self.id}: {response.status}")

    async def delete_messages(self, message_ids):
        # Implementation of the delete messages method for voice channels if applicable
        pass

    async def edit(self, **options):
        url = f"https://discord.com/api/v10/channels/{self.id}"
        headers = {
            "Authorization": f"Bot {self.bot.token}",
            "Content-Type": "application/json"
        }
        async with aiohttp.ClientSession() as session:
            async with session.patch(url, headers=headers, json=options) as response:
                if response.status != 200:
                    raise Exception(f"Failed to edit channel {self.id}: {response.status}")

    async def fetch_message(self, message_id):
        url = f"https://discord.com/api/v10/channels/{self.id}/messages/{message_id}"
        headers = {
            "Authorization": f"Bot {self.bot.token}"
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"Failed to fetch message {message_id} from channel {self.id}: {response.status}")

    async def get_partial_message(self, message_id):
        # Implementation of the get partial message method if applicable
        pass

    async def history(self, limit=100):
        url = f"https://discord.com/api/v10/channels/{self.id}/messages?limit={limit}"
        headers = {
            "Authorization": f"Bot {self.bot.token}"
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"Failed to fetch message history for channel {self.id}: {response.status}")

    async def invites(self):
        url = f"https://discord.com/api/v10/channels/{self.id}/invites"
        headers = {
            "Authorization": f"Bot {self.bot.token}"
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"Failed to fetch invites for channel {self.id}: {response.status}")

    def is_nsfw(self):
        return self.nsfw

    async def move(self, position, parent_id=None, lock_permissions=False, reason=None):
        url = f"https://discord.com/api/v10/channels/{self.id}"
        headers = {
            "Authorization": f"Bot {self.bot.token}",
            "Content-Type": "application/json"
        }
        json_data = {
            "position": position,
            "parent_id": parent_id,
            "lock_permissions": lock_permissions,
            "reason": reason
        }
        async with aiohttp.ClientSession() as session:
            async with session.patch(url, headers=headers, json=json_data) as response:
                if response.status != 200:
                    raise Exception(f"Failed to move channel {self.id}: {response.status}")

    def overwrites_for(self, member_or_role):
        return self.overwrites.get(str(member_or_role.id))

    async def permissions_for(self, member_or_role):
        url = f"https://discord.com/api/v10/channels/{self.id}/permissions/{member_or_role.id}"
        headers = {
            "Authorization": f"Bot {self.bot.token}"
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"Failed to fetch permissions for {member_or_role.id} in channel {self.id}: {response.status}")

    async def pins(self):
        url = f"https://discord.com/api/v10/channels/{self.id}/pins"
        headers = {
            "Authorization": f"Bot {self.bot.token}"
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"Failed to fetch pinned messages: {response.status}")

    async def purge(self, limit=100, check=None, before=None, after=None, around=None):
        messages = []
        async for message in self.history(limit=limit, before=before, after=after, around=around):
            if check is None or check(message):
                messages.append(message)
        if messages:
            await self.delete_messages([message['id'] for message in messages])

    async def send(self, content=None, embed=None, embeds=None, files=None, components=None, ephemeral=False):
        url = f"https://discord.com/api/v10/channels/{self.id}/messages"
        data = {}
        if content:
            data["content"] = str(content)
        if embed:
            data["embeds"] = [embed]
        if embeds:
            data["embeds"] = embeds
        if components:
            data["components"] = components
        if ephemeral:
            data["flags"] = 64  # This flag makes the response ephemeral

        async with aiohttp.ClientSession() as session:
            if files:
                form = aiohttp.FormData()
                form.add_field('payload_json', json.dumps(data))
                for file in files:
                    form.add_field('file', file['data'], filename=file['filename'], content_type=file['content_type'])
                async with session.post(url, headers=self.headers, data=form) as response:
                    if response.status != 200:
                        logging.error(f"Failed to send message with file: {response.status} - {await response.text()}")
                        return None
                    else:
                        response_json = await response.json()
                        logging.info(f"Message sent with file: {response_json}")
                        return response_json
            else:
                async with session.post(url, headers=self.headers, json=data) as response:
                    if response.status != 200:
                        logging.error(f"Failed to send message: {response.status} - {await response.text()}")
                        return None
                    else:
                        response_json = await response.json()
                        logging.info(f"Message sent: {response_json}")
                        return response_json

    async def set_permissions(self, member_or_role, allow, deny, reason=None):
        url = f"https://discord.com/api/v10/channels/{self.id}/permissions/{member_or_role.id}"
        headers = {
            "Authorization": f"Bot {self.bot.token}",
            "Content-Type": "application/json"
        }
        json_data = {
            "allow": allow,
            "deny": deny,
            "reason": reason
        }
        async with aiohttp.ClientSession() as session:
            async with session.put(url, headers=headers, json=json_data) as response:
                if response.status != 204:
                    raise Exception(f"Failed to set permissions for {member_or_role.id} in channel {self.id}: {response.status}")

    async def typing(self):
        url = f"https://discord.com/api/v10/channels/{self.id}/typing"
        headers = {
            "Authorization": f"Bot {self.bot.token}"
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers) as response:
                if response.status != 204:
                    raise Exception(f"Failed to trigger typing indicator in channel {self.id}: {response.status}")

    async def webhooks(self):
        url = f"https://discord.com/api/v10/channels/{self.id}/webhooks"
        headers = {
            "Authorization": f"Bot {self.bot.token}"
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"Failed to fetch webhooks for channel {self.id}: {response.status}")
