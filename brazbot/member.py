import aiohttp
from datetime import datetime

class Member:
    def __init__(self, data, bot=None):
        self.bot = bot
        self.id = data.get('id')
        self.username = data.get('username')
        self.discriminator = data.get('discriminator')
        self.avatar = data.get('avatar')
        self.bot = data.get('bot', False)
        self.system = data.get('system', False)
        self.mfa_enabled = data.get('mfa_enabled', False)
        self.locale = data.get('locale')
        self.verified = data.get('verified', False)
        self.email = data.get('email')
        self.flags = data.get('flags', 0)
        self.premium_type = data.get('premium_type', 0)
        self.public_flags = data.get('public_flags', 0)
        self.accent_color = data.get('accent_color')
        self.accent_colour = self.accent_color
        self.activities = data.get('activities', [])
        self.activity = self.activities[0] if self.activities else None
        self.avatar_decoration = data.get('avatar_decoration')
        self.avatar_decoration_sku_id = data.get('avatar_decoration_sku_id')
        self.banner = data.get('banner')
        self.color = self.accent_color
        self.colour = self.color
        self.created_at = datetime.fromisoformat(data.get('created_at')) if data.get('created_at') else None
        self.default_avatar = f"https://cdn.discordapp.com/embed/avatars/{int(self.discriminator) % 5}.png"
        self.desktop_status = data.get('desktop_status')
        self.display_avatar = self.avatar
        self.display_icon = self.avatar
        self.display_name = data.get('display_name', self.username)
        self.dm_channel = data.get('dm_channel')
        self.global_name = data.get('global_name')
        self.guild = data.get('guild')
        self.guild_avatar = data.get('guild_avatar')
        self.guild_permissions = data.get('guild_permissions')
        self.joined_at = datetime.fromisoformat(data.get('joined_at')) if data.get('joined_at') else None
        self.mention = f"<@{self.id}>"
        self.mobile_status = data.get('mobile_status')
        self.mutual_guilds = data.get('mutual_guilds', [])
        self.name = self.username
        self.nick = data.get('nick')
        self.pending = data.get('pending', False)
        self.premium_since = datetime.fromisoformat(data.get('premium_since')) if data.get('premium_since') else None
        self.raw_status = data.get('raw_status')
        self.resolved_permissions = data.get('resolved_permissions')
        self.roles = data.get('roles', [])
        self.status = data.get('status')
        self.system = data.get('system', False)
        self.timed_out_until = datetime.fromisoformat(data.get('timed_out_until')) if data.get('timed_out_until') else None
        self.top_role = data.get('top_role')
        self.voice = data.get('voice')
        self.web_status = data.get('web_status')

    @classmethod
    async def from_user_id(cls, bot, user_id, guild_id=None):
        url = f"https://discord.com/api/v10/users/{user_id}"
        headers = {
            "Authorization": f"Bot {bot.token}"
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return cls(data, bot)
                else:
                    raise Exception(f"Failed to fetch user data: {response.status}")

    def __str__(self):
        return f"{self.username}#{self.discriminator}"

    # Methods to interact with the Discord API
    async def add_roles(self, *roles):
        url = f"https://discord.com/api/v10/guilds/{self.guild['id']}/members/{self.id}/roles"
        headers = {
            "Authorization": f"Bot {self.bot.token}",
            "Content-Type": "application/json"
        }
        async with aiohttp.ClientSession() as session:
            for role in roles:
                async with session.put(f"{url}/{role.id}", headers=headers) as response:
                    if response.status != 204:
                        raise Exception(f"Failed to add role {role.id} to member {self.id}: {response.status}")

    async def ban(self, reason=None, delete_message_days=0):
        url = f"https://discord.com/api/v10/guilds/{self.guild['id']}/bans/{self.id}"
        headers = {
            "Authorization": f"Bot {self.bot.token}",
            "Content-Type": "application/json"
        }
        json_data = {
            "delete_message_days": delete_message_days,
            "reason": reason
        }
        async with aiohttp.ClientSession() as session:
            async with session.put(url, headers=headers, json=json_data) as response:
                if response.status != 204:
                    raise Exception(f"Failed to ban member {self.id}: {response.status}")

    async def create_dm(self):
        url = f"https://discord.com/api/v10/users/@me/channels"
        headers = {
            "Authorization": f"Bot {self.bot.token}",
            "Content-Type": "application/json"
        }
        json_data = {
            "recipient_id": self.id
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=json_data) as response:
                if response.status == 200:
                    data = await response.json()
                    self.dm_channel = data
                else:
                    raise Exception(f"Failed to create DM channel: {response.status}")

    async def edit(self, **fields):
        url = f"https://discord.com/api/v10/guilds/{self.guild['id']}/members/{self.id}"
        headers = {
            "Authorization": f"Bot {self.bot.token}",
            "Content-Type": "application/json"
        }
        async with aiohttp.ClientSession() as session:
            async with session.patch(url, headers=headers, json=fields) as response:
                if response.status != 200:
                    raise Exception(f"Failed to edit member {self.id}: {response.status}")

    async def fetch_message(self, channel_id, message_id):
        url = f"https://discord.com/api/v10/channels/{channel_id}/messages/{message_id}"
        headers = {
            "Authorization": f"Bot {self.bot.token}"
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"Failed to fetch message: {response.status}")

    def get_role(self, role_id):
        return next((role for role in self.roles if role['id'] == role_id), None)

    async def history(self, limit=100):
        url = f"https://discord.com/api/v10/channels/{self.dm_channel['id']}/messages?limit={limit}"
        headers = {
            "Authorization": f"Bot {self.bot.token}"
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"Failed to fetch message history: {response.status}")

    def is_on_mobile(self):
        return self.mobile_status == "online"

    def is_timed_out(self):
        return self.timed_out_until is not None

    async def kick(self, reason=None):
        url = f"https://discord.com/api/v10/guilds/{self.guild['id']}/members/{self.id}"
        headers = {
            "Authorization": f"Bot {self.bot.token}"
        }
        async with aiohttp.ClientSession() as session:
            async with session.delete(url, headers=headers) as response:
                if response.status != 204:
                    raise Exception(f"Failed to kick member {self.id}: {response.status}")

    async def mentioned_in(self, message):
        return f"<@{self.id}>" in message['content']

    async def move_to(self, channel_id):
        url = f"https://discord.com/api/v10/guilds/{self.guild['id']}/members/{self.id}"
        headers = {
            "Authorization": f"Bot {self.bot.token}",
            "Content-Type": "application/json"
        }
        json_data = {
            "channel_id": channel_id
        }
        async with aiohttp.ClientSession() as session:
            async with session.patch(url, headers=headers, json=json_data) as response:
                if response.status != 204:
                    raise Exception(f"Failed to move member {self.id} to channel {channel_id}: {response.status}")

    async def pins(self):
        url = f"https://discord.com/api/v10/channels/{self.dm_channel['id']}/pins"
        headers = {
            "Authorization": f"Bot {self.bot.token}"
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"Failed to fetch pinned messages: {response.status}")

    async def remove_roles(self, *roles):
        url = f"https://discord.com/api/v10/guilds/{self.guild['id']}/members/{self.id}/roles"
        headers = {
            "Authorization": f"Bot {self.bot.token}",
            "Content-Type": "application/json"
        }
        async with aiohttp.ClientSession() as session:
            for role in roles:
                async with session.delete(f"{url}/{role.id}", headers=headers) as response:
                    if response.status != 204:
                        raise Exception(f"Failed to remove role {role.id} from member {self.id}: {response.status}")

    async def request_to_speak(self):
        url = f"https://discord.com/api/v10/guilds/{self.guild['id']}/voice-states/{self.id}"
        headers = {
            "Authorization": f"Bot {self.bot.token}",
            "Content-Type": "application/json"
        }
        json_data = {
            "request_to_speak_timestamp": datetime.utcnow().isoformat()
        }
        async with aiohttp.ClientSession() as session:
            async with session.patch(url, headers=headers, json=json_data) as response:
                if response.status != 204:
                    raise Exception(f"Failed to request to speak: {response.status}")

    async def send(self, content=None, embed=None, embeds=None, files=None, components=None, ephemeral=False):
        if not self.dm_channel:
            await self.create_dm()
        url = f"https://discord.com/api/v10/channels/{self.dm_channel['id']}/messages"
        headers = {
            "Authorization": f"Bot {self.bot.token}",
            "Content-Type": "application/json"
        }
        json_data = {
            "content": content,
            "embed": embed,
            "embeds": embeds,
            "components": components,
            "flags": 64 if ephemeral else 0
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=json_data) as response:
                if response.status != 200:
                    raise Exception(f"Failed to send message: {response.status}")

    async def timeout(self, duration, reason=None):
        url = f"https://discord.com/api/v10/guilds/{self.guild['id']}/members/{self.id}"
        headers = {
            "Authorization": f"Bot {self.bot.token}",
            "Content-Type": "application/json"
        }
        json_data = {
            "communication_disabled_until": (datetime.utcnow() + duration).isoformat(),
            "reason": reason
        }
        async with aiohttp.ClientSession() as session:
            async with session.patch(url, headers=headers, json=json_data) as response:
                if response.status != 204:
                    raise Exception(f"Failed to timeout member {self.id}: {response.status}")

    async def typing(self):
        url = f"https://discord.com/api/v10/channels/{self.dm_channel['id']}/typing"
        headers = {
            "Authorization": f"Bot {self.bot.token}"
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers) as response:
                if response.status != 204:
                    raise Exception(f"Failed to send typing indication: {response.status}")

    async def unban(self):
        url = f"https://discord.com/api/v10/guilds/{self.guild['id']}/bans/{self.id}"
        headers = {
            "Authorization": f"Bot {self.bot.token}"
        }
        async with aiohttp.ClientSession() as session:
            async with session.delete(url, headers=headers) as response:
                if response.status != 204:
                    raise Exception(f"Failed to unban member {self.id}: {response.status}")
