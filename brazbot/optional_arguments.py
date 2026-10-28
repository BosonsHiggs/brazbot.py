"""
Compatibilidade para `optional_argument_command`.
"""

from typing import Any, Callable, Optional


def optional_argument_command(
    bot: Any, name: Optional[str] = None, description: Optional[str] = None
) -> Callable[..., Any]:
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        bot.command_handler.register_command(func, name, description)
        return func

    return decorator


__all__ = ["Optional", "optional_argument_command"]
