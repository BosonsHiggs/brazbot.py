def autocomplete_command(bot, name=None, description=None):
    def decorator(func):
        bot.command_handler.register_command(func, name, description)
        return func

    def autocomplete(option):
        def decorator(func):
            bot.command_handler.register_autocomplete(func, option)
            return func
        return decorator
    
    return decorator
