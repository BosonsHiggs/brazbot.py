"""
Módulos auxiliares de decoradores de argumentos (`argument_descriptions`, `autocomplete`,
`literal_arguments`, `optional_arguments`) mantidos para compatibilidade total.
"""

from typing import Any, Callable, Optional


def command_with_description(
    bot: Any, name: Optional[str] = None, description: Optional[str] = None
) -> Callable[..., Any]:
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        bot.command_handler.register_command(func, name, description)
        return func

    return decorator
