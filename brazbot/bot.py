import json
import asyncio
import aiohttp
from brazbot.events import EventHandler, on_ready, on_message_create, on_error
from brazbot.commands import CommandHandler
from brazbot.message_handler import MessageHandler
from brazbot.cache import Cache

# Mapeamento de intents
INTENTS = {
    "GUILDS": 1 << 0,
    "GUILD_MEMBERS": 1 << 1,
    "GUILD_BANS": 1 << 2,
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
    "GUILD_SCHEDULED_EVENTS": 1 << 16
}

class DiscordBot:
    def __init__(self, token, command_prefix=None, intents=None):
        self.token = token
        self.command_prefix = command_prefix
        self.intents = self.calculate_intents(intents)
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

        # Register events automatically
        self.auto_register_events()

    def calculate_intents(self, intents):
        if intents is None:
            return sum(INTENTS.values())
        elif isinstance(intents, list):
            return sum(INTENTS[intent] for intent in intents)
        return intents

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

    async def send_heartbeat(self, ws):
        while True:
            await asyncio.sleep(self.heartbeat_interval / 1000)
            await ws.send_json({"op": 1, "d": self.sequence})
            print("Heartbeat sent")

    async def start(self):
        while True:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.ws_connect(f"wss://gateway.discord.gg/?v=10&encoding=json") as ws:
                        if self.session_id and self.sequence:
                            await ws.send_json({
                                "op": 6,
                                "d": {
                                    "token": self.token,
                                    "session_id": self.session_id,
                                    "seq": self.sequence
                                }
                            })
                            print("Resuming session")
                        else:
                            await ws.send_json({
                                "op": 2,
                                "d": {
                                    "token": self.token,
                                    "intents": self.intents,
                                    "properties": {
                                        "$os": "linux",
                                        "$browser": "my_library",
                                        "$device": "my_library"
                                    }
                                }
                            })
                            print("Starting new session")
                        print("WebSocket connection established.")
                        async for msg in ws:
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                message = json.loads(msg.data)
                                self.sequence = message.get('s')
                                if message['op'] == 10:  # Opcode for Hello, contains heartbeat_interval
                                    self.heartbeat_interval = message['d']['heartbeat_interval']
                                    if self.heartbeat_task:
                                        self.heartbeat_task.cancel()
                                    self.heartbeat_task = asyncio.create_task(self.send_heartbeat(ws))
                                if message['t'] == 'READY':
                                    self.session_id = message['d']['session_id']
                                    self.application_id = message['d']['application']['id']
                                    print(f"READY message received: {message}")
                                    await self.event_handler.handle_event({
                                        't': 'on_ready',
                                        'd': message['d']
                                    })
                                elif message['t'] == 'MESSAGE_CREATE':
                                    print(f"Message received: {message}")
                                    asyncio.create_task(self.event_handler.handle_event(message))
                                    asyncio.create_task(self.command_handler.handle_command(message))
                                elif message['t'] == 'INTERACTION_CREATE':
                                    print(f"Interaction received: {message}")
                                    asyncio.create_task(self.event_handler.handle_event(message))
                                    asyncio.create_task(self.command_handler.handle_command(message))
                                elif message['t'] == 'ERROR':
                                    print(f"Error received: {message}")
                                    await self.event_handler.handle_event({
                                        't': 'on_error',
                                        'd': message['d']
                                    })
                            elif msg.type in {aiohttp.WSMsgType.ERROR, aiohttp.WSMsgType.CLOSED}:
                                print(f"WebSocket closed with message: {msg.data}")
                                if self.heartbeat_task:
                                    self.heartbeat_task.cancel()
                                break
            except Exception as e:
                print(f"Exception in WebSocket connection: {e}")

            print("Reconnecting in 5 seconds...")
            await asyncio.sleep(5)
