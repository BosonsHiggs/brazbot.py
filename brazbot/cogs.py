"""
Sistema modular de Cogs (`Cog`) para organização limpa de comandos, listeners e estado em bots grandes.
Suporta tanto registro imperativo (`@self.command`, `@self.event`) quanto declarativo (`@Cog.listener`, `@command`).
"""

from typing import Any, Callable, List, Optional


class Cog:
    """
    Classe base para módulos de extensão (Cogs) na biblioteca brazbot.py.
    """

    def __init__(self, bot: Any = None):
        self.bot = bot

    @staticmethod
    def listener(name: Optional[str] = None) -> Callable[..., Any]:
        """Decorador declarativo para métodos de eventos dentro de uma subclasse de Cog."""

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            func._cog_listener = name or func.__name__
            return func

        return decorator

    def event(self, func: Callable[..., Any]) -> Callable[..., Any]:
        """Registra um evento diretamente no bot associado à Cog."""
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
        """Registra um comando diretamente no bot associado à Cog."""

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
