"""
Modular Cog system (`Cog`) for clean organization of commands, listeners, and state in large bots.
Supports both imperative registration (`@self.command`, `@self.event`) and declarative (`@Cog.listener`, `@command`).
"""

from typing import Any, Callable, List, Optional


class Cog:
    """
    Base class for extension modules (Cogs) in the brazbot.py library.
    """

    def __init__(self, bot: Any = None):
        self.bot = bot

    @staticmethod
    def listener(name: Optional[str] = None) -> Callable[..., Any]:
        """Declarative decorator for event listener methods inside a Cog subclass."""

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            func._cog_listener = name or func.__name__
            return func

        return decorator

    def event(self, func: Callable[..., Any]) -> Callable[..., Any]:
        """Registers an event handler directly on the bot associated with this Cog."""
        event_name = func.__name__
        if self.bot:
            self.bot.event_handler.register(event_name, func)
        else:
            func._cog_listener = event_name
        return func

    def command(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        aliases: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> Callable[..., Any]:
        """Registers a command directly on the bot associated with this Cog."""

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            if self.bot:
                self.bot.command_handler.register_command(
                    func, name=name, description=description, aliases=aliases, **kwargs
                )
            else:
                func._command = {
                    "name": name or func.__name__,
                    "description": description or func.__doc__ or "No description provided",
                    "aliases": aliases or [],
                    "kwargs": kwargs,
                }
            return func

        return decorator
