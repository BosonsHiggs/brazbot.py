from typing import Optional

def optional_argument_command(bot, name=None, description=None):
    def decorator(func):
        bot.command_handler.register_command(func, name, description)
        return func
    return decorator
