import aiohttp
import logging
import json
from typing import Union, Literal, get_args, _GenericAlias
from brazbot.greedy_union import Greedy
from brazbot.attachments import Attachment
from brazbot.snowflake import Snowflake
from brazbot.member import Member
from brazbot.roles import Role
from brazbot.channels import Channel
from brazbot.guilds import Guild

logging.basicConfig(level=logging.DEBUG)
#logging.getLogger().setLevel(logging.CRITICAL)

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

	async def defer(self, ephemeral=False):
		url = f"https://discord.com/api/v10/interactions/{self.interaction['id']}/{self.interaction['token']}/callback"
		json_data = {
			"type": 5  # Type 5 is for deferred responses
		}
		if ephemeral:
			json_data["data"] = {"flags": 64}

		async with aiohttp.ClientSession() as session:
			async with session.post(url, json=json_data) as response:
				if response.status != 204:
					logging.error(f"Failed to defer interaction: {response.status}")
				else:
					logging.info("Interaction deferred successfully")

	async def send_modal(self, title, custom_id, data):
		await self.bot.message_handler.send_modal(self.interaction, title, custom_id, data)

	async def send_followup_message(self, content=None, embed=None, embeds=None, files=None, components=None, ephemeral=False):
		await self.bot.message_handler.send_followup_message(self.bot.application_id, self.interaction["token"], content, embed, embeds, files, components, ephemeral)

class CommandHandler:
	def __init__(self, bot):
		self.bot = bot
		self.commands = {}
		self.autocomplete_functions = {}

	def register_command(self, func, name=None, description=None):
		name = name or func.__name__
		description = description or func.__doc__ or "No description provided"

		options = []
		for param_name, param in func.__annotations__.items():
			option = {"name": param_name, "required": True}
			if param == str:
				option["type"] = 3  # STRING
				if hasattr(func, "autocomplete_options") and param_name in func.autocomplete_options:
					option["autocomplete"] = True
			elif param == int:
				option["type"] = 4  # INTEGER
			elif param == float:
				option["type"] = 10  # NUMBER
			elif param == bytes:  # Handle file attachments
				option["type"] = 11  # ATTACHMENT
			elif param == bool:
				option["type"] = 5  # BOOLEAN
			elif param == Attachment:
				option["type"] = 11  # ATTACHMENT
			elif isinstance(param, type) and issubclass(param, Member):
				option["type"] = 6  # USER type (custom Member object)
			elif param == dict and "channel" in param_name:
				option["type"] = 7  # CHANNEL
			elif isinstance(param, type) and issubclass(param, Guild):
				option["type"] = 9  # GUILD type (custom Guild object)
			elif isinstance(param, type) and issubclass(param, Role):
				option["type"] = 8  # ROLE type (custom Role object)
			elif isinstance(param, type) and issubclass(param, Channel):
				option["type"] = 7  # CHANNEL type (custom Channel object)
			elif isinstance(param, type) and issubclass(param, Thread):
				option["type"] = 11  # THREAD type (custom Thread object)
			elif isinstance(param, _GenericAlias) and param.__origin__ is Literal:
				option["type"] = 3  # STRING
				option["choices"] = [{"name": v, "value": v} for v in get_args(param)]
			elif isinstance(param, _GenericAlias) and param.__origin__ is Union and len(param.__args__) == 2 and param.__args__[1] is type(None):
				option["type"] = 3  # STRING
				option["required"] = False
			elif isinstance(param, _GenericAlias) and param.__origin__ is Greedy:
				option["type"] = 3  # STRING
				option["required"] = False
			elif isinstance(param, _GenericAlias) and param.__origin__ is Union:
				if str in param.__args__:
					option["type"] = 3
				if int in param.__args__:
					option["type"] = 4
				if float in param.__args__:
					option["type"] = 10

			if hasattr(func, "parameter_descriptions") and param_name in func.parameter_descriptions:
				option["description"] = func.parameter_descriptions[param_name]
			else:
				option["description"] = param_name  # Default to the parameter name if no description is provided

			options.append(option)

		self.commands[name] = {
			"func": func,
			"description": description,
			"options": options,
			"type": 1  # 1 indicates a CHAT_INPUT command
		}

		logging.debug(f"Registered command: {name} with options: {options}")

		#logging.debug(f"Registered command: {name} with options: {options}")

	def register_autocomplete(self, func, command_name, option_name):
		if command_name not in self.commands:
			raise ValueError(f"Command '{command_name}' not found")
		for option in self.commands[command_name]["options"]:
			if option["name"] == option_name:
				option["autocomplete"] = True
				self.autocomplete_functions[(command_name, option_name)] = func
				return
		raise ValueError(f"Option '{option_name}' not found in command '{command_name}'")

	async def send_autocomplete_response(self, interaction, suggestions):
		response_data = {
			"type": 8,  # Autocomplete result type
			"data": {
				"choices": suggestions
			}
		}
		url = f"https://discord.com/api/v10/interactions/{interaction['id']}/{interaction['token']}/callback"
		async with aiohttp.ClientSession() as session:
			async with session.post(url, json=response_data) as response:
				if response.status != 200:
					logging.error(f"Failed to send autocomplete response: {response.status}")


	async def handle_autocomplete(self, interaction):
		command_name = interaction['data']['name']
		options = interaction['data']['options']
		focused_option = next((opt for opt in options if opt.get('focused')), None)
		if focused_option:
			option_name = focused_option['name']
			if (command_name, option_name) in self.autocomplete_functions:
				await self.autocomplete_functions[(command_name, option_name)](interaction)
			else:
				logging.warning(f"No autocomplete function registered for command '{command_name}' and option '{option_name}'")


	#logging.debug(f"Handling command for message: {message}")
	async def handle_command(self, message):
		logging.debug(f"Handling command for message: {message}")
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
				args = {}
				for opt in options:
					if opt['type'] == 6:  # USER type
						args[opt['name']] = await Member.from_user_id(self.bot, opt['value'], ctx.guild_id)
					elif opt['type'] == 8:  # ROLE type
						args[opt['name']] = await Role.from_role_id(self.bot, ctx.guild_id, opt['value'])
					elif opt['type'] == 7:  # CHANNEL type
						args[opt['name']] = await Channel.from_channel_id(self.bot, ctx.guild_id, opt['value'])
					elif opt['type'] == 9:  # GUILD type 
						args[opt['name']] = await Guild.from_guild_id(self.bot, ctx.guild_id)
					elif opt['type'] == 11:  # THREAD type 
						args[opt['name']] = await Thread.from_thread_id(cls, self.bot, ctx.guild_id, opt['value'])
					else:
						args[opt['name']] = opt['value']
				logging.debug(f"Executing command: {command_name} with options: {options}")
				await self.commands[command_name]["func"](ctx, **args)
		elif message['d']['type'] == 4:  # Autocomplete interaction
			await self.handle_autocomplete(message['d'])

	async def get_existing_commands(self, guild_id=None):
		url = f"{self.bot.base_url}/applications/{self.bot.application_id}/commands"
		if guild_id:
			url = f"{self.bot.base_url}/applications/{self.bot.application_id}/guilds/{guild_id}/commands"

		async with aiohttp.ClientSession() as session:
			async with session.get(url, headers=self.bot.headers) as response:
				if response.status == 200:
					return {cmd['name']: cmd for cmd in await response.json()}
				return {}

	async def sync_commands(self, guild_id=None):
		try:
			if not Snowflake.is_valid(self.bot.application_id):
				raise ValueError(f"Invalid application_id: {self.bot.application_id}")

			current_commands = [
				{
					"name": name,
					"description": cmd["description"],
					"options": cmd["options"],
					"type": 1  # 1 indica um comando CHAT_INPUT
				} for name, cmd in self.commands.items()
			]

			existing_commands = await self.get_existing_commands(guild_id)
			transformed_existing_commands = [
				{
					"name": cmd['name'],
					"description": cmd['description'],
					"options": [
						{
							"name": opt['name'],
							"description": opt.get('description', ''),
							"type": opt['type'],
							"required": opt.get('required', False)
						} for opt in cmd.get('options', [])
					],
					"type": cmd['type']
				} for cmd in existing_commands.values()
			]

			if self.commands_changed(current_commands, transformed_existing_commands):
				url = f"{self.bot.base_url}/applications/{self.bot.application_id}/commands"
				if guild_id:
					url = f"{self.bot.base_url}/applications/{self.bot.application_id}/guilds/{guild_id}/commands"

				async with aiohttp.ClientSession() as session:
					async with session.put(url, headers=self.bot.headers, json=current_commands) as response:
						response_text = await response.text()
						if response.status != 200:
							logging.error(f"Failed to sync commands: {response.status}")
							logging.error(f"Response: {response_text}")
							return f"Failed to sync commands: {response.status}\nResponse: {response_text}"
						else:
							logging.info("Commands synced successfully: " + response_text)
							return f"Commands synced successfully: {response_text}"
			else:
				logging.info("No changes in commands. Sync skipped.")
				return "No changes in commands. Sync skipped."
		except Exception as e:
			logging.error(f"Exception occurred while syncing commands: {e}")
			return f"Exception occurred while syncing commands: {e}"

	async def send_response(self, content):
		url = f"https://discord.com/api/v10/interactions/{self.interaction['id']}/{self.interaction['token']}/callback"
		json_data = {
			"type": 4,
			"data": {
				"content": content
			}
		}
	   #logging.debug(f"Sending response to interaction: {json_data}")
		async with aiohttp.ClientSession() as session:
			async with session.post(url, json=json_data) as response:
				"""
				if response.status != 200:
				   #logging.error(f"Failed to send response: {response.status}")
				   #logging.error(f"Response text: {await response.text()}")
				else:
				   #logging.info("Response sent successfully.")
				"""
				return await response.json()
	
	def commands_changed(self, current_commands, existing_commands):
		if len(current_commands) != len(existing_commands):
		   #logging.debug("Number of commands changed.")
			return True

		for current, existing in zip(current_commands, existing_commands):
			if current["name"] != existing["name"]:
			   #logging.debug(f"Command name changed: {current['name']} != {existing['name']}")
				return True
			if current["description"] != existing["description"]:
			   #logging.debug(f"Description for command {current['name']} changed: {current['description']} != {existing['description']}")
				return True
			if current["options"] != existing["options"]:
			   #logging.debug(f"Options for command {current['name']} changed.")
				return True

		return False

   
	async def check_rate_limits(self):
		endpoints = [
			"/gateway",
			"/channels/{self.channel_id}/messages",
			"/guilds/{self.guild_id}/members/{self.user_id}"
		]
		results = []
		async with aiohttp.ClientSession() as session:
			for endpoint in endpoints:
				url = f"{self.bot.base_url}{endpoint}"
				async with session.get(url, headers=self.bot.headers) as response:
					rate_limit_info = {
						"endpoint": endpoint,
						"status": response.status,
						"limit": response.headers.get("X-RateLimit-Limit"),
						"remaining": response.headers.get("X-RateLimit-Remaining"),
						"reset": response.headers.get("X-RateLimit-Reset"),
						"reset_after": response.headers.get("X-RateLimit-Reset-After"),
						"bucket": response.headers.get("X-RateLimit-Bucket"),
						"retry_after": response.headers.get("Retry-After"),
						"global": response.headers.get("X-RateLimit-Global"),
					}
					results.append(rate_limit_info)
				   #logging.info(f"Rate limit info for {endpoint}: {rate_limit_info}")
		return results
