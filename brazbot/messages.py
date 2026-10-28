"""
Modelos de Mensagem (`Message`, `PartialMessage`) e re-exportação de `MessageHandler` para compatibilidade.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from brazbot.message_handler import MessageHandler
from brazbot.snowflake import Snowflake


class PartialMessage:
    """Representa uma referência leve a uma mensagem sem precisar buscá-la antes na API."""

    def __init__(self, channel: Any, id: str):
        self.channel = channel
        self.channel_id = str(getattr(channel, "id", channel))
        self.id = str(id)
        self.bot = getattr(channel, "bot", None)

    async def fetch(self) -> "Message":
        data = await self.bot.http.request(
            "GET", f"/channels/{self.channel_id}/messages/{self.id}"
        )
        return Message(data, bot=self.bot)

    async def edit(self, content: Optional[str] = None, **kwargs: Any) -> Optional[Dict[str, Any]]:
        return await self.bot.message_handler.edit_message(
            self.channel_id, self.id, content=content, **kwargs
        )

    async def delete(self, reason: Optional[str] = None) -> bool:
        return await self.bot.message_handler.delete_message(
            self.channel_id, self.id, reason=reason
        )

    async def pin(self, reason: Optional[str] = None) -> bool:
        return await self.bot.message_handler.pin_message(
            self.channel_id, self.id, reason=reason
        )

    async def unpin(self, reason: Optional[str] = None) -> bool:
        return await self.bot.message_handler.unpin_message(
            self.channel_id, self.id, reason=reason
        )

    async def add_reaction(self, emoji: str) -> bool:
        return await self.bot.message_handler.add_reaction(self.channel_id, self.id, emoji)


class Message(PartialMessage):
    """Representa uma Mensagem completa da API v10 do Discord."""

    def __init__(self, data: Dict[str, Any], bot: Any = None):
        self._raw = data or {}
        self.bot = bot
        self.id = str(data.get("id") or "0")
        self.channel_id = str(data.get("channel_id") or "0")
        self.guild_id = str(data.get("guild_id") or "") or None
        self.author = data.get("author") or {}
        self.member = data.get("member") or {}
        self.content = data.get("content", "")
        self.timestamp = data.get("timestamp")
        self.edited_timestamp = data.get("edited_timestamp")
        self.tts = bool(data.get("tts", False))
        self.mention_everyone = bool(data.get("mention_everyone", False))
        self.mentions = data.get("mentions", [])
        self.mention_roles = data.get("mention_roles", [])
        self.attachments = data.get("attachments", [])
        self.embeds = data.get("embeds", [])
        self.reactions = data.get("reactions", [])
        self.pinned = bool(data.get("pinned", False))
        self.webhook_id = data.get("webhook_id")
        self.type = int(data.get("type") or 0)
        self.flags = int(data.get("flags") or 0)
        self.components = data.get("components", [])
        self.poll = data.get("poll")
        self.created_at = (
            Snowflake.to_datetime(self.id)
            if Snowflake.is_valid(self.id)
            else datetime.now(timezone.utc)
        )
        self.jump_url = (
            f"https://discord.com/channels/{self.guild_id or '@me'}/{self.channel_id}/{self.id}"
        )

    def __getitem__(self, key: str) -> Any:
        if key in self._raw:
            return self._raw[key]
        if hasattr(self, key):
            return getattr(self, key)
        raise KeyError(key)

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default

    async def reply(self, content: Optional[str] = None, **kwargs: Any) -> Optional[Dict[str, Any]]:
        return await self.bot.message_handler.send_message(
            self.channel_id, content=content, reply_to=self.id, **kwargs
        )


__all__ = ["MessageHandler", "PartialMessage", "Message"]
