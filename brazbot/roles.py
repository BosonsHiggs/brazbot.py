import aiohttp
from datetime import datetime

class Role:
    def __init__(self, data, bot=None, guild_id=None):
        self.bot = bot
        self.id = data.get('id')
        self.name = data.get('name')
        self.color = data.get('color')
        self.colour = self.color
        self.created_at = datetime.fromtimestamp(((int(self.id) >> 22) + 1420070400000) / 1000)
        self.display_icon = data.get('icon')
        self.flags = data.get('flags', 0)
        self.guild = data.get('guild')
        self.hoist = data.get('hoist', False)
        self.icon = data.get('icon')
        self.managed = data.get('managed', False)
        self.members = data.get('members', [])
        self.mention = f"<@&{self.id}>"
        self.mentionable = data.get('mentionable', False)
        self.permissions = data.get('permissions')
        self.position = data.get('position')
        self.tags = data.get('tags', {})
        self.unicode_emoji = data.get('unicode_emoji')
        self.guild_id = guild_id

    @classmethod
    async def from_role_id(cls, bot, guild_id, role_id):
        cache_key = f"role_{role_id}"
        data = bot.get_cache_data(cache_key)

        if data:
            return cls(data, bot, guild_id)

        url = f"https://discord.com/api/v10/guilds/{guild_id}/roles"
        headers = {
            "Authorization": f"Bot {bot.token}"
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    roles = await response.json()
                    role_data = next((role for role in roles if role['id'] == role_id), None)
                    if role_data:
                        bot.set_cache_data(cache_key, role_data, seconds=120)
                        return cls(role_data, bot, guild_id)
                    else:
                        raise Exception(f"Role {role_id} not found in guild {guild_id}")
                else:
                    raise Exception(f"Failed to fetch roles data: {response.status}")

    def __str__(self):
        return self.name

    # Methods to interact with the Discord API
    async def delete(self, reason=None):
        url = f"https://discord.com/api/v10/guilds/{self.guild['id']}/roles/{self.id}"
        headers = {
            "Authorization": f"Bot {self.bot.token}",
            "Content-Type": "application/json"
        }
        async with aiohttp.ClientSession() as session:
            async with session.delete(url, headers=headers) as response:
                if response.status != 204:
                    raise Exception(f"Failed to delete role {self.id}: {response.status}")

    async def edit(self, **fields):
        url = f"https://discord.com/api/v10/guilds/{self.guild['id']}/roles/{self.id}"
        headers = {
            "Authorization": f"Bot {self.bot.token}",
            "Content-Type": "application/json"
        }
        async with aiohttp.ClientSession() as session:
            async with session.patch(url, headers=headers, json=fields) as response:
                if response.status == 200:
                    data = await response.json()
                    # Update the role instance with the new data
                    self.__init__(data, self.bot)
                    return self
                else:
                    raise Exception(f"Failed to edit role {self.id}: {response.status}")

    async def add_to_member(self, member_id, reason=None):
        url = f"https://discord.com/api/v10/guilds/{self.guild['id']}/members/{member_id}/roles/{self.id}"
        headers = {
            "Authorization": f"Bot {self.bot.token}",
            "Content-Type": "application/json",
            "X-Audit-Log-Reason": reason if reason else ""
        }
        async with aiohttp.ClientSession() as session:
            async with session.put(url, headers=headers) as response:
                if response.status != 204:
                    raise Exception(f"Failed to add role {self.id} to member {member_id}: {response.status}")

    async def remove_from_member(self, member_id, reason=None):
        url = f"https://discord.com/api/v10/guilds/{self.guild['id']}/members/{member_id}/roles/{self.id}"
        headers = {
            "Authorization": f"Bot {self.bot.token}",
            "Content-Type": "application/json",
            "X-Audit-Log-Reason": reason if reason else ""
        }
        async with aiohttp.ClientSession() as session:
            async with session.delete(url, headers=headers) as response:
                if response.status != 204:
                    raise Exception(f"Failed to remove role {self.id} from member {member_id}: {response.status}")

    def is_assignable(self):
        return not self.managed and self.permissions != 0

    def is_bot_managed(self):
        return self.tags.get('bot_id') is not None

    def is_default(self):
        return self.id == self.guild['id']

    def is_integration(self):
        return self.tags.get('integration_id') is not None

    def is_premium_subscriber(self):
        return self.tags.get('premium_subscriber') is not None

    async def fetch_all_roles(bot, guild_id):
        url = f"https://discord.com/api/v10/guilds/{guild_id}/roles"
        headers = {
            "Authorization": f"Bot {bot.token}"
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    roles = [Role(role_data, bot) for role_data in data]
                    return roles
                else:
                    raise Exception(f"Failed to fetch roles: {response.status}")

    async def create_role(bot, guild_id, name, color=0, hoist=False, mentionable=False, permissions=0, reason=None):
        url = f"https://discord.com/api/v10/guilds/{guild_id}/roles"
        headers = {
            "Authorization": f"Bot {bot.token}",
            "Content-Type": "application/json",
            "X-Audit-Log-Reason": reason if reason else ""
        }
        json_data = {
            "name": name,
            "color": color,
            "hoist": hoist,
            "mentionable": mentionable,
            "permissions": str(permissions)
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=json_data) as response:
                if response.status == 201:
                    data = await response.json()
                    return Role(data, bot)
                else:
                    raise Exception(f"Failed to create role: {response.status}")
