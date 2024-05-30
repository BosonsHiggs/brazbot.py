def autocomplete_command(bot, name=None, description=None):
    def decorator(func):
        bot.command_handler.register_command(func, name, description)
        func._is_autocomplete = True
        return func

    def autocomplete(option):
        def decorator(func):
            if not hasattr(func, 'autocomplete_options'):
                func.autocomplete_options = []
            func.autocomplete_options.append(option)
            bot.command_handler.register_autocomplete(func, option)
            return func
        return decorator
    
    decorator.autocomplete = autocomplete
    return decorator
