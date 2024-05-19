class EventHandler:
    def __init__(self):
        self.events = {}

    def register(self, event_name, func):
        self.events[event_name] = func

    async def handle_event(self, message):
        event_type = message['t']
        event_data = message['d']
        if event_type in self.events:
            await self.events[event_type](event_data)

# Funções de eventos como pass
async def on_ready(data):
    pass

async def on_message_create(data):
    pass

async def on_error(data):
    pass
