import aiohttp
from datetime import datetime

class Channel:
    def __init__(self, data, bot=None):
        self.bot = bot
        self.id = data.get('id')
        self.name = data.get('name')
        self.category = data.get('category')
        self.changed_roles = data.get('changed_roles', [])
        self.created_at = datetime.fromtimestamp(((int(self.id) >> 22) + 1420070400000) / 1000)
        self.guild = data.get('guild')
        self.jump_url = data.get('jump_url')
        self.mention = f"<#{self.id}>"
        self.overwrites = data.get('overwrites', {})
        self.permissions_synced = data.get('permissions_synced', False)
        self.position = data.get('position')

    @classmethod
    async def from_channel_id(cls, bot, guild_id, channel_id):
        cache_key = f"channel_{channel_id}"
        data = bot.get_cache_data(cache_key)

        if data:
            return cls(data, bot)

        url = f"https://discord.com/api/v10/guilds/{guild_id}/channels/{channel_id}"
        headers = {
            "Authorization": f"Bot {bot.token}"
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    bot.set_cache_data(cache_key, data, seconds=600)
                    return cls(data, bot)
                else:
                    raise Exception(f"Failed to fetch channel data: {response.status}")

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
