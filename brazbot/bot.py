import json
import asyncio
import aiohttp
import logging
from aiohttp import ClientResponseError
from brazbot.events import EventHandler
from brazbot.commands import CommandHandler
from brazbot.message_handler import MessageHandler
from brazbot.cache import Cache
from brazbot.audit_log_entry import AuditLogEntry
from brazbot.eventstype import EventTypes
from brazbot.decorators import tasks
from datetime import datetime, timedelta

# Mapeamento de intents
INTENTS = {
    "GUILDS": 1 << 0,
    "GUILD_MEMBERS": 1 << 1,
    "GUILD_MODERATION": 1 << 2,
    "GUILD_EMOJIS_AND_STICKERS": 1 << 3,
    "GUILD_INTEGRATIONS": 1 << 4,
    "GUILD_WEBHOOKS": 1 << 5,
    "GUILD_INVITES": 1 << 6,
    "GUILD_VOICE_STATES": 1 << 7,
    "GUILD_PRESENCES": 1 << 8,
    "GUILD_MESSAGES": 1 << 9,
    "GUILD_MESSAGE_REACTIONS": 1 << 10,
    "GUILD_MESSAGE_TYPING": 1 << 11,
    "DIRECT_MESSAGES": 1 << 12,
    "DIRECT_MESSAGE_REACTIONS": 1 << 13,
    "DIRECT_MESSAGE_TYPING": 1 << 14,
    "MESSAGE_CONTENT": 1 << 15,
    "GUILD_SCHEDULED_EVENTS": 1 << 16,
    "AUTO_MODERATION_CONFIGURATION": 1 << 20,
    "AUTO_MODERATION_EXECUTION": 1 << 21,
    "GUILD_MESSAGE_POLLS": 1 << 24,
    "DIRECT_MESSAGE_POLLS": 1 << 25
}

logging.basicConfig(level=logging.DEBUG)

class DiscordBot:
    def __init__(self, token, command_prefix=None, intents=None, num_shards=1, shard_id=0):
        self.token = token
        self.endpoint = "wss://gateway.discord.gg/?v=10"
        self.session_id = None
        self.voice_server_endpoint = None
        self.command_prefix = command_prefix
        self.intents = self.calculate_intents(intents if intents is not None else ["GUILDS", "GUILD_VOICE_STATES"])

        self.num_shards = num_shards
        self.shard_id = shard_id
        self.base_url = "https://discord.com/api/v10"
        self.headers = {
            "Authorization": f"Bot {self.token}",
            "Content-Type": "application/json"
        }

        self.event_handler = EventHandler()
        self.command_handler = CommandHandler(self)
        self.message_handler = MessageHandler(self.token)
        self.cache = Cache()
        self.application_id = None
        self.heartbeat_interval = None
        self.heartbeat_task = None
        self.session_id = None
        self.sequence = None
        self.cogs = []
        self.eventtypes = tuple(map(lambda event_type: event_type.name, EventTypes))
        self.cache = {}
        self.wait_for_futures = []
        self.auto_register_events()
        self._ws = None
        self.message_queue = asyncio.Queue()

    def get_cache_data(self, key):
        if key in self.cache:
            entry = self.cache[key]
            if entry['expiry'] > datetime.now():
                return entry['data']
            else:
                self.delete_cache_data(key)
        return None

    def set_cache_data(self, key, data, seconds=60):
        self.cache[key] = {
            'data': data,
            'expiry': datetime.now() + timedelta(seconds=seconds)
        }

    def delete_cache_data(self, key):
        if key in self.cache:
            del self.cache[key]

    def update_cache_data(self, key, data):
        if key in self.cache:
            self.cache[key]['data'] = data

    @tasks(seconds=120)
    async def _cache_cleanup_task(self):
        now = datetime.now()
        keys_to_delete = [key for key, entry in self.cache.items() if entry['expiry'] <= now]
        for key in keys_to_delete:
            self.delete_cache_data(key)
        print(f"Deleted {len(keys_to_delete)} expired cache keys.")

    def calculate_intents(self, intents):
        if isinstance(intents, list):
            return sum(INTENTS[intent] for intent in intents if intent in INTENTS)
        return 0

    def event(self, func):
        event_name = func.__name__
        self.event_handler.register(event_name, func)
        return func

    def command(self, name=None, description=None):
        def decorator(func):
            self.command_handler.register_command(func, name, description)
            return func
        return decorator

    def auto_register_events(self):
        for attr_name in dir(self):
            if attr_name.startswith("on_"):
                attr = getattr(self, attr_name)
                if callable(attr):
                    self.event(attr)

    def add_cog(self, cog):
        self.cogs.append(cog)
        for attr_name in dir(cog):
            attr = getattr(cog, attr_name)
            if callable(attr):
                if attr_name.startswith("on_"):
                    self.event(attr)
                elif hasattr(attr, "_command"):
                    self.command(attr._command["name"], attr._command["description"])(attr)

    async def setup_hook(self):
        pass

    async def send_heartbeat(self, ws):
        while True:
            await asyncio.sleep(self.heartbeat_interval / 1000)
            await ws.send_json({"op": 1, "d": self.sequence})

    async def handle_rate_limit(self, response):
        if response.status == 429:
            retry_after = int(response.headers.get("Retry-After", 1))
            is_global = response.headers.get("X-RateLimit-Global", False)
            rate_limit_scope = response.headers.get("X-RateLimit-Scope", "unknown")

            logging.error(f"Rate limited. Retry after {retry_after} seconds. Scope: {rate_limit_scope}. Global: {is_global}")
            await asyncio.sleep(retry_after)

    async def change_presence(self, activity_name, activity_type=0):
        presence_payload = {
            "op": 3,
            "d": {
                "since": None,
                "activities": [
                    {
                        "name": activity_name,
                        "type": activity_type
                    }
                ],
                "status": "online",
                "afk": False
            }
        }
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(f"{self.endpoint}&encoding=json") as ws:
                await ws.send_json(presence_payload)

    async def wait_for(self, event_type, check, timeout=None):
        future = asyncio.get_event_loop().create_future()
        self.wait_for_futures.append((future, check))
        return await asyncio.wait_for(future, timeout)

    async def message_listener(self):
        while True:
            message = await self.message_queue.get()
            await self.process_message(message)

    async def process_message(self, message):
        message = json.loads(message)
        self.sequence = message.get('s')

        if message['op'] == 10:
            self.heartbeat_interval = message['d']['heartbeat_interval']
            if self.heartbeat_task:
                self.heartbeat_task.cancel()
            self.heartbeat_task = asyncio.create_task(self.send_heartbeat(self._ws))

        if message['t'] == 'READY':
            self._ws = self._ws
            self.endpoint = message['d']['resume_gateway_url']
            self.session_id = message['d']['session_id']
            self.application_id = message['d']['application']['id']
            await self.event_handler.handle_event({
                't': 'on_ready',
                'd': message['d']
            })

        elif message['t'] == 'MESSAGE_CREATE':
            asyncio.create_task(self.event_handler.handle_event(message))
            asyncio.create_task(self.command_handler.handle_command(message))

        if message['t'] == 'VOICE_SERVER_UPDATE':
            self.voice_server_endpoint = message['d']['endpoint']
            asyncio.create_task(self.event_handler.handle_event({
                't': 'on_voice_server_update',
                'd': message['d']
            }))
        elif message['t'] == 'VOICE_STATE_UPDATE':
            print(f"\n\n\nmessage['d']: {message['d']}\n\n\n")
            if 'endpoint' in message['d']:
                self.voice_server_endpoint = message['d']['endpoint']
            asyncio.create_task(self.event_handler.handle_event({
                't': 'on_voice_state_update',
                'd': message['d']
            }))
        elif message['t'] == 'INTERACTION_CREATE':
            valor = message.get('d', None)
            if valor is not None:
                if ('dropdown_select' or 'button_click' in message['d']['data']):
                    await self.event_handler.handle_event({
                        't': 'on_interaction_create',
                        'd': message['d']
                    })
                elif ('dropdown_select' or 'button_click' in message['components']):
                    await self.event_handler.handle_event({
                        't': 'on_interaction_send',
                        'd': message['d']
                    })
                if 'autocomplete' in message['d']['data']:
                    asyncio.create_task(self.command_handler.handle_autocomplete(message['d']))

                else:
                    asyncio.create_task(self.event_handler.handle_event(message))
                    asyncio.create_task(self.command_handler.handle_command(message))

        elif message['t'] in self.eventtypes:
            asyncio.create_task(self.event_handler.handle_event({
                't': 'on_audit_log_entry',
                'd': {'eventtype': EventTypes[message['t']], 'guild_id': message['d']['guild_id'], 'data': message['d']}
            }))

        elif message['t'] == 'ERROR':
            await self.event_handler.handle_event({
                't': 'on_error',
                'd': message['d']
            })

        # Handle wait_for futures
        for future, check in self.wait_for_futures:
            if check(message):
                future.set_result(message)
                self.wait_for_futures.remove((future, check))

    async def start(self):
        asyncio.create_task(self._cache_cleanup_task())
        await self.setup_hook()

        while True:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.ws_connect(f"{self.endpoint}&encoding=json") as ws:

                        identify_payload = {
                            "op": 2,
                            "d": {
                                "token": self.token,
                                "intents": self.intents,
                                "properties": {
                                    "$os": "linux",
                                    "$browser": "brazbot.py",
                                    "$device": "brazbot.py"
                                },
                                "shard": [self.shard_id, self.num_shards]
                            }
                        }

                        if self.session_id and self.sequence:
                            await ws.send_json({
                                "op": 6,
                                "d": {
                                    "token": self.token,
                                    "session_id": self.session_id,
                                    "seq": self.sequence
                                }
                            })
                        else:
                            await ws.send_json(identify_payload)

                        self._ws = ws
                        asyncio.create_task(self.message_listener())

                        async for msg in ws:
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                await self.message_queue.put(msg.data)
                            elif msg.type in {aiohttp.WSMsgType.ERROR, aiohttp.WSMsgType.CLOSED}:
                                if self.heartbeat_task:
                                    self.heartbeat_task.cancel()
                                break
            except ClientResponseError as e:
                await self.handle_rate_limit(e.response)
            except Exception as e:
                logging.error(f"Unexpected exception: {e}")

            print("Reconnecting in 5 seconds...")
            await asyncio.sleep(5)
