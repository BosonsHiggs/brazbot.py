"""
Decorador `autocomplete_command` para comandos Slash com sugestões dinâmicas (Autocomplete).
"""

from typing import Any, Callable, Optional


def autocomplete_command(
    bot: Any, name: Optional[str] = None, description: Optional[str] = None
) -> Callable[..., Any]:
    cmd_name = name

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        nonlocal cmd_name
        cmd_name = cmd_name or func.__name__
        bot.command_handler.register_command(func, cmd_name, description)
        func._is_autocomplete = True
        return func

    def autocomplete(option: str) -> Callable[..., Any]:
        def opt_decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            if not hasattr(func, "autocomplete_options"):
                func.autocomplete_options = []
            func.autocomplete_options.append(option)
            if cmd_name:
                bot.command_handler.register_autocomplete(func, cmd_name, option)
            return func

        return opt_decorator

    decorator.autocomplete = autocomplete  # type: ignore[attr-defined]
    return decorator
