"""
Gerenciador assíncrono de Eventos do Gateway da biblioteca brazbot.py.
Suporta múltiplos listeners por evento e despacho seguro de corrotinas.
"""

import asyncio
import inspect
import logging
from typing import Any, Callable, Dict, List

logger = logging.getLogger(__name__)


class EventHandler:
    """Registra e despacha eventos do Gateway para um ou mais handlers assíncronos."""

    def __init__(self, bot: Any = None):
        self.bot = bot
        self.events: Dict[str, List[Callable[..., Any]]] = {}

    def register(self, event_name: str, func: Callable[..., Any]) -> Callable[..., Any]:
        """Registra uma função assíncrona para um evento (ex.: `on_ready`, `on_message_create`)."""
        key = event_name.lower() if event_name.startswith("on_") else event_name
        listeners = self.events.setdefault(key, [])
        if func not in listeners:
            listeners.append(func)
        return func

    def unregister(self, event_name: str, func: Callable[..., Any]) -> None:
        key = event_name.lower() if event_name.startswith("on_") else event_name
        if key in self.events and func in self.events[key]:
            self.events[key].remove(func)

    async def handle_event(self, message: Dict[str, Any]) -> None:
        """Despacha um evento recebido pelo Gateway para todos os handlers registrados."""
        raw_type = message.get("t") or ""
        event_data = message.get("d")

        candidate_keys = [raw_type]
        lower_type = raw_type.lower()
        if not lower_type.startswith("on_"):
            candidate_keys.append(f"on_{lower_type}")
        else:
            candidate_keys.append(lower_type)

        for key in candidate_keys:
            for handler in list(self.events.get(key, [])):
                try:
                    sig = inspect.signature(handler)
                    params = [
                        p
                        for p in sig.parameters.values()
                        if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)
                    ]
                    if len(params) == 0:
                        res = handler()
                    elif len(params) >= 2 and params[0].name == "bot":
                        res = handler(self.bot, event_data)
                    else:
                        res = handler(event_data)

                    if asyncio.iscoroutine(res):
                        await res
                except Exception as e:
                    logger.error(f"Erro no handler do evento '{key}': {e}", exc_info=True)
