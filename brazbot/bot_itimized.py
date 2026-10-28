"""
Versão otimizada com compressão `zlib-stream` habilitada por padrão (`bot_itimized.py`).
"""

from typing import Iterable, Optional, Union

from brazbot.bot import DiscordBot as _BaseDiscordBot
from brazbot.permissions import INTENTS, Intents


class DiscordBot(_BaseDiscordBot):
    """Subclasse de `DiscordBot` com compressão `zlib-stream` habilitada por padrão no Gateway v10."""

    def __init__(
        self,
        token: Optional[str] = None,
        command_prefix: Optional[str] = None,
        intents: Optional[Union[int, Intents, Iterable[str]]] = None,
        num_shards: int = 1,
        shard_id: int = 0,
    ):
        super().__init__(
            token=token,
            command_prefix=command_prefix,
            intents=intents,
            num_shards=num_shards,
            shard_id=shard_id,
            compress=True,
        )


__all__ = ["DiscordBot", "INTENTS"]
