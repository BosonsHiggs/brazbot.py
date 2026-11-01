"""
Asynchronous Gateway Event Handler for the brazbot.py library.
Supports multiple listeners per event and safe coroutine dispatching.
"""

import asyncio
import inspect
import logging
from typing import Any, Callable, Dict, List

logger = logging.getLogger(__name__)


class EventHandler:
    """Registers and dispatches Gateway events to one or more asynchronous event handlers."""

    def __init__(self, bot: Any = None):
        self.bot = bot
        self.events: Dict[str, List[Callable[..., Any]]] = {}

    def register(self, event_name: str, func: Callable[..., Any]) -> Callable[..., Any]:
        """Registers an asynchronous function for an event (e.g., `on_ready`, `on_message_create`)."""
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
        """Dispatches a Gateway event to all registered listeners."""
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
                    logger.error(f"Error in event handler '{key}': {e}", exc_info=True)
