import aiohttp
from datetime import datetime

class Role:
    def __init__(self, data, bot=None):
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

    @classmethod
    async def from_role_id(cls, bot, guild_id, role_id):
        url = f"https://discord.com/api/v10/guilds/{guild_id}/roles/{role_id}"
        headers = {
            "Authorization": f"Bot {bot.token}"
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return cls(data, bot)
                else:
                    raise Exception(f"Failed to fetch role data: {response.status}")

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
                if response.status != 200:
                    raise Exception(f"Failed to edit role {self.id}: {response.status}")

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
