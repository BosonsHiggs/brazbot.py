import aiohttp
from datetime import datetime

class Thread:
    def __init__(self, data, bot=None):
        self.bot = bot
        self.id = data.get('id')
        self.name = data.get('name')
        self.guild = data.get('guild')
        self.parent_id = data.get('parent_id')
        self.owner_id = data.get('owner_id')
        self.archived = data.get('archived')
        self.archiver_id = data.get('archiver_id')
        self.auto_archive_duration = data.get('auto_archive_duration')
        self.archive_timestamp = data.get('archive_timestamp')
        self.locked = data.get('locked')
        self.slowmode_delay = data.get('slowmode_delay')
        self.invitable = data.get('invitable')
        self.last_message_id = data.get('last_message_id')
        self.last_message = data.get('last_message')
        self.message_count = data.get('message_count')
        self.member_count = data.get('member_count')
        self.created_at = datetime.fromtimestamp(((int(self.id) >> 22) + 1420070400000) / 1000)
        self.category = data.get('category')
        self.category_id = data.get('category_id')
        self.members = data.get('members', [])
        self.flags = data.get('flags')
        self.applied_tags = data.get('applied_tags', [])
        self.type = data.get('type')
        self.mention = f"<#{self.id}>"
        self.jump_url = f"https://discord.com/channels/{self.guild}/{self.id}"

    @classmethod
    async def from_thread_id(cls, bot, guild_id, thread_id):
        cache_key = f"thread_{guild_id}"
        data = bot.get_cache_data(cache_key)

        if data:
            return cls(data, bot)

        url = f"https://discord.com/api/v10/channels/{thread_id}"
        headers = {
            "Authorization": f"Bot {bot.token}"
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    bot.set_cache_data(cache_key, data, seconds=120)
                    data['guild'] = guild_id
                    return cls(data, bot)
                else:
                    raise Exception(f"Failed to fetch thread data: {response.status}")

    def __str__(self):
        return self.name

    # Methods to interact with the Discord API
    async def add_tags(self, tags):
        url = f"https://discord.com/api/v10/channels/{self.id}"
        headers = {
            "Authorization": f"Bot {self.bot.token}",
            "Content-Type": "application/json"
        }
        json_data = {"applied_tags": tags}
        async with aiohttp.ClientSession() as session:
            async with session.patch(url, headers=headers, json=json_data) as response:
                if response.status != 200:
                    raise Exception(f"Failed to add tags: {response.status}")

    async def add_user(self, user_id):
        url = f"https://discord.com/api/v10/channels/{self.id}/thread-members/{user_id}"
        headers = {
            "Authorization": f"Bot {self.bot.token}"
        }
        async with aiohttp.ClientSession() as session:
            async with session.put(url, headers=headers) as response:
                if response.status != 204:
                    raise Exception(f"Failed to add user to thread: {response.status}")

    async def delete(self):
        url = f"https://discord.com/api/v10/channels/{self.id}"
        headers = {
            "Authorization": f"Bot {self.bot.token}"
        }
        async with aiohttp.ClientSession() as session:
            async with session.delete(url, headers=headers) as response:
                if response.status != 204:
                    raise Exception(f"Failed to delete thread: {response.status}")

    async def delete_messages(self, message_ids):
        url = f"https://discord.com/api/v10/channels/{self.id}/messages/bulk-delete"
        headers = {
            "Authorization": f"Bot {self.bot.token}",
            "Content-Type": "application/json"
        }
        json_data = {"messages": message_ids}
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
                    raise Exception(f"Failed to edit thread: {response.status}")

    async def fetch_member(self, user_id):
        url = f"https://discord.com/api/v10/channels/{self.id}/thread-members/{user_id}"
        headers = {
            "Authorization": f"Bot {self.bot.token}"
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"Failed to fetch thread member: {response.status}")

    async def fetch_members(self):
        url = f"https://discord.com/api/v10/channels/{self.id}/thread-members"
        headers = {
            "Authorization": f"Bot {self.bot.token}"
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"Failed to fetch thread members: {response.status}")

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

    def get_partial_message(self, message_id):
        return {"id": message_id, "channel_id": self.id}

    async def history(self):
        url = f"https://discord.com/api/v10/channels/{self.id}/messages"
        headers = {
            "Authorization": f"Bot {self.bot.token}"
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"Failed to fetch message history: {response.status}")

    def is_news(self):
        return self.type == 5

    def is_nsfw(self):
        return self.flags & 1 << 5 != 0

    def is_private(self):
        return self.type in (2, 12)

    async def join(self):
        url = f"https://discord.com/api/v10/channels/{self.id}/thread-members/@me"
        headers = {
            "Authorization": f"Bot {self.bot.token}"
        }
        async with aiohttp.ClientSession() as session:
            async with session.put(url, headers=headers) as response:
                if response.status != 204:
                    raise Exception(f"Failed to join thread: {response.status}")

    async def leave(self):
        url = f"https://discord.com/api/v10/channels/{self.id}/thread-members/@me"
        headers = {
            "Authorization": f"Bot {self.bot.token}"
        }
        async with aiohttp.ClientSession() as session:
            async with session.delete(url, headers=headers) as response:
                if response.status != 204:
                    raise Exception(f"Failed to leave thread: {response.status}")

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
                    raise Exception(f"Failed to fetch permissions: {response.status}")

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

    async def purge(self, limit):
        url = f"https://discord.com/api/v10/channels/{self.id}/messages"
        headers = {
            "Authorization": f"Bot {self.bot.token}"
        }
        params = {"limit": limit}
        async with aiohttp.ClientSession() as session:
            async with session.delete(url, headers=headers, params=params) as response:
                if response.status != 204:
                    raise Exception(f"Failed to purge messages: {response.status}")

    async def remove_tags(self, tags):
        url = f"https://discord.com/api/v10/channels/{self.id}"
        headers = {
            "Authorization": f"Bot {self.bot.token}",
            "Content-Type": "application/json"
        }
        json_data = {"applied_tags": [tag for tag in self.applied_tags if tag not in tags]}
        async with aiohttp.ClientSession() as session:
            async with session.patch(url, headers=headers, json=json_data) as response:
                if response.status != 200:
                    raise Exception(f"Failed to remove tags: {response.status}")

    async def remove_user(self, user_id):
        url = f"https://discord.com/api/v10/channels/{self.id}/thread-members/{user_id}"
        headers = {
            "Authorization": f"Bot {self.bot.token}"
        }
        async with aiohttp.ClientSession() as session:
            async with session.delete(url, headers=headers) as response:
                if response.status != 204:
                    raise Exception(f"Failed to remove user from thread: {response.status}")

    async def send(self, content):
        url = f"https://discord.com/api/v10/channels/{self.id}/messages"
        headers = {
            "Authorization": f"Bot {self.bot.token}",
            "Content-Type": "application/json"
        }
        json_data = {"content": content}
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=json_data) as response:
                if response.status != 200:
                    raise Exception(f"Failed to send message: {response.status}")

    async def typing(self):
        url = f"https://discord.com/api/v10/channels/{self.id}/typing"
        headers = {
            "Authorization": f"Bot {self.bot.token}"
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers) as response:
                if response.status != 204:
                    raise Exception(f"Failed to send typing indicator: {response.status}")
