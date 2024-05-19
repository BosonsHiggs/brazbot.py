import aiohttp

class CommandContext:
    def __init__(self, bot, message, interaction=None):
        self.bot = bot
        self.message = message
        self.interaction = interaction
        self.channel_id = message.get('channel_id')
        self.author = message.get('author') or (interaction.get('member', {}).get('user') if interaction else None)
        self.content = message.get('content')
        self.guild_id = message.get('guild_id') if message.get('guild_id') else (interaction.get('guild_id') if interaction else None)

class CommandHandler:
    def __init__(self, bot):
        self.bot = bot
        self.commands = {}

    def register_command(self, func, name=None, description=None):
        command_name = name or func.__name__
        self.commands[command_name] = {
            "func": func,
            "description": description or "No description"
        }

    async def handle_command(self, message):
        if 'content' in message['d']:
            content = message['d']['content']
            if self.bot.command_prefix and content.startswith(self.bot.command_prefix):
                command_name, *args = content[len(self.bot.command_prefix):].split()
                if command_name in self.commands:
                    ctx = CommandContext(self.bot, message['d'])
                    await self.commands[command_name]["func"](ctx, *args)
        elif message['d']['type'] == 2:  # Slash command type
            command_name = message['d']['data']['name']
            if command_name in self.commands:
                ctx = CommandContext(self.bot, message['d'], interaction=message['d'])
                options = message['d']['data'].get('options', [])
                await self.commands[command_name]["func"](ctx, **{opt['name']: opt['value'] for opt in options})

    async def sync_commands(self, guild_id=None, commands=None):
        if commands is None:
            commands = [
                {
                    "name": name,
                    "description": cmd["description"],
                    "options": []
                } for name, cmd in self.commands.items()
            ]

        url = f"{self.bot.base_url}/applications/{self.bot.application_id}/commands"
        if guild_id:
            url = f"{self.bot.base_url}/applications/{self.bot.application_id}/guilds/{guild_id}/commands"

        async with aiohttp.ClientSession() as session:
            async with session.put(url, headers=self.bot.headers, json=commands) as response:
                if response.status != 200:
                    print(f"Failed to sync commands: {response.status}")
                else:
                    print(f"Commands synced successfully: {await response.json()}")

    async def get_existing_commands(self, guild_id=None):
        url = f"{self.bot.base_url}/applications/{self.bot.application_id}/commands"
        if guild_id:
            url = f"{self.bot.base_url}/applications/{self.bot.application_id}/guilds/{guild_id}/commands"

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.bot.headers) as response:
                if response.status == 200:
                    return {cmd['name']: cmd for cmd in await response.json()}
                return {}
