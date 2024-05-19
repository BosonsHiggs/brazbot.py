def command_with_description(bot, name=None, description=None):
    def decorator(func):
        bot.command_handler.register_command(func, name, description)
        return func
    return decorator
