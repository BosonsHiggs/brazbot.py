class Cog:
    def __init__(self, bot):
        self.bot = bot

    def event(self, func):
        event_name = func.__name__
        self.bot.event_handler.register(event_name, func)
        return func

    def command(self, name=None, description=None):
        def decorator(func):
            self.bot.command_handler.register_command(func, name, description)
            return func
        return decorator
