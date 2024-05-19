import aiohttp
from typing import Union, Literal, get_args, _GenericAlias
import logging

# Ensure Greedy is imported
from brazbot.greedy_union import Greedy

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class CommandContext:
    def __init__(self, bot, message, interaction=None):
        self.bot = bot
        self.message = message
        self.interaction = interaction
        self.channel_id = message.get('channel_id')
        self.author = message.get('author') or (interaction.get('member', {}).get('user') if interaction else None)
        self.content = message.get('content')
        self.guild_id = message.get('guild_id') if message.get('guild_id') else (interaction.get('guild_id') if interaction else None)
        self.options = {opt['name']: opt['value'] for opt in (interaction['data'].get('options', []) if interaction and 'data' in interaction else [])}

    async def defer(self):
        url = f"https://discord.com/api/v10/interactions/{self.interaction['id']}/{self.interaction['token']}/callback"
        json_data = {
            "type": 5  # Type 5 is for deferred responses
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=json_data) as response:
                if response.status != 204:
                    logging.error(f"Failed to defer interaction: {response.status}")
                else:
                    logging.info("Interaction deferred successfully")

    async def send_followup_message(self, content):
        await self.bot.message_handler.send_followup_message(self.bot.application_id, self.interaction['token'], content)

class CommandHandler:
    def __init__(self, bot):
        self.bot = bot
        self.commands = {}

    def register_command(self, func, name=None, description=None):
        name = name or func.__name__
        description = description or func.__doc__ or "No description provided"

        options = []
        for param_name, param in func.__annotations__.items():
            option = {"name": param_name, "description": param_name, "required": True}
            if param == str:
                option["type"] = 3  # STRING
            elif param == int:
                option["type"] = 4  # INTEGER
            elif param == bool:
                option["type"] = 5  # BOOLEAN
            elif isinstance(param, _GenericAlias) and param.__origin__ is Literal:
                option["type"] = 3  # STRING
                option["choices"] = [{"name": v, "value": v} for v in get_args(param)]
            elif isinstance(param, _GenericAlias) and param.__origin__ is Union and len(param.__args__) == 2 and param.__args__[1] is type(None):
                option["type"] = 3  # STRING
                option["required"] = False
            elif isinstance(param, _GenericAlias) and param.__origin__ is Greedy:
                option["type"] = 3  # STRING
                option["required"] = False
            options.append(option)

        self.commands[name] = {
            "func": func,
            "description": description,
            "options": options,
            "type": 1  # 1 indicates a CHAT_INPUT command
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
                self.bot.interaction = message['d']  # Set the interaction attribute
                options = message['d']['data'].get('options', [])
                await self.commands[command_name]["func"](ctx, **{opt['name']: opt['value'] for opt in options})


    async def sync_commands(self, guild_id=None, commands=None):
        if commands is None:
            commands = [
                {
                    "name": name,
                    "description": cmd["description"],
                    "options": cmd["options"],
                    "type": cmd["type"]  # Ensure the command type is included
                } for name, cmd in self.commands.items()
            ]

        url = f"{self.bot.base_url}/applications/{self.bot.application_id}/commands"
        if guild_id:
            url = f"{self.bot.base_url}/applications/{self.bot.application_id}/guilds/{guild_id}/commands"

        logging.debug(f"Syncing commands to URL: {url}")
        logging.debug(f"Payload: {commands}")

        async with aiohttp.ClientSession() as session:
            async with session.put(url, headers=self.bot.headers, json=commands) as response:
                response_text = await response.text()
                if response.status != 200:
                    logging.error(f"Failed to sync commands: {response.status}")
                    logging.error(f"Response: {response_text}")
                else:
                    logging.info(f"Commands synced successfully: {response_text}")

    async def get_existing_commands(self, guild_id=None):
        url = f"{self.bot.base_url}/applications/{self.bot.application_id}/commands"
        if guild_id:
            url = f"{self.bot.base_url}/applications/{self.bot.application_id}/guilds/{guild_id}/commands"

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.bot.headers) as response:
                if response.status == 200:
                    return {cmd['name']: cmd for cmd in await response.json()}
                return {}

    async def send_response(self, content):
        url = f"https://discord.com/api/v10/interactions/{self.interaction['id']}/{self.interaction['token']}/callback"
        json_data = {
            "type": 4,
            "data": {
                "content": content
            }
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=json_data) as response:
                return await response.json()
