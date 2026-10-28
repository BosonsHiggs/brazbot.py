"""
Modelo de Tópico (Thread) da API v10 do Discord.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from brazbot.snowflake import Snowflake


class Thread:
    """Representa uma Thread (pública, privada ou de anúncios) na API v10 do Discord."""

    def __init__(self, data: Dict[str, Any], bot: Any = None):
        self._raw = data or {}
        self.bot = bot
        self.id = str(data.get("id") or "0")
        self.name = data.get("name", f"thread-{self.id}")
        self.guild = data.get("guild") or data.get("guild_id")
        self.guild_id = str(self.guild) if self.guild else None
        self.parent_id = data.get("parent_id")
        self.owner_id = data.get("owner_id")
        metadata = data.get("thread_metadata") or {}
        self.archived = metadata.get("archived", data.get("archived", False))
        self.archiver_id = metadata.get("archiver_id", data.get("archiver_id"))
        self.auto_archive_duration = metadata.get(
            "auto_archive_duration", data.get("auto_archive_duration", 1440)
        )
        self.archive_timestamp = metadata.get(
            "archive_timestamp", data.get("archive_timestamp")
        )
        self.locked = metadata.get("locked", data.get("locked", False))
        self.invitable = metadata.get("invitable", data.get("invitable", True))
        self.slowmode_delay = data.get("rate_limit_per_user", data.get("slowmode_delay", 0))
        self.last_message_id = data.get("last_message_id")
        self.last_message = data.get("last_message")
        self.message_count = data.get("message_count", 0)
        self.member_count = data.get("member_count", 0)
        self.created_at = (
            Snowflake.to_datetime(self.id)
            if Snowflake.is_valid(self.id)
            else datetime.now(timezone.utc)
        )
        self.category = data.get("category")
        self.category_id = data.get("category_id")
        self.members = data.get("members", [])
        self.flags = int(data.get("flags") or 0)
        self.applied_tags = data.get("applied_tags", [])
        self.type = data.get("type", 11)
        self.mention = f"<#{self.id}>"
        self.jump_url = f"https://discord.com/channels/{self.guild_id or '@me'}/{self.id}"

    @classmethod
    async def from_thread_id(
        cls, bot: Any, guild_id: Optional[str], thread_id: str
    ) -> "Thread":
        cache_key = f"thread_{thread_id}"
        data = bot.get_cache_data(cache_key) if hasattr(bot, "get_cache_data") else None
        if data:
            return cls(data, bot=bot)

        data = await bot.http.request("GET", f"/channels/{thread_id}")
        if guild_id and "guild" not in data:
            data["guild"] = guild_id
        if hasattr(bot, "set_cache_data"):
            bot.set_cache_data(cache_key, data, seconds=120)
        return cls(data, bot=bot)

    def __str__(self) -> str:
        return str(self.name)

    async def add_tags(self, tags: List[str]) -> Dict[str, Any]:
        merged = list(dict.fromkeys(list(self.applied_tags) + list(tags)))
        data = await self.bot.http.request(
            "PATCH", f"/channels/{self.id}", json_data={"applied_tags": merged}
        )
        self.applied_tags = merged
        return data

    async def remove_tags(self, tags: List[str]) -> Dict[str, Any]:
        remaining = [t for t in self.applied_tags if t not in tags]
        data = await self.bot.http.request(
            "PATCH", f"/channels/{self.id}", json_data={"applied_tags": remaining}
        )
        self.applied_tags = remaining
        return data

    async def add_user(self, user_id: str) -> bool:
        await self.bot.http.request("PUT", f"/channels/{self.id}/thread-members/{user_id}")
        return True

    async def remove_user(self, user_id: str) -> bool:
        await self.bot.http.request("DELETE", f"/channels/{self.id}/thread-members/{user_id}")
        return True

    async def join(self) -> bool:
        await self.bot.http.request("PUT", f"/channels/{self.id}/thread-members/@me")
        return True

    async def leave(self) -> bool:
        await self.bot.http.request("DELETE", f"/channels/{self.id}/thread-members/@me")
        return True

    async def delete(self, reason: Optional[str] = None) -> bool:
        await self.bot.http.request("DELETE", f"/channels/{self.id}", reason=reason)
        return True

    async def delete_messages(self, message_ids: List[str]) -> bool:
        await self.bot.http.request(
            "POST",
            f"/channels/{self.id}/messages/bulk-delete",
            json_data={"messages": [str(m) for m in message_ids]},
        )
        return True

    async def edit(self, reason: Optional[str] = None, **fields: Any) -> Dict[str, Any]:
        return await self.bot.http.request(
            "PATCH", f"/channels/{self.id}", json_data=fields, reason=reason
        )

    async def archive(self, locked: bool = False) -> Dict[str, Any]:
        return await self.edit(archived=True, locked=locked)

    async def unarchive(self) -> Dict[str, Any]:
        return await self.edit(archived=False)

    async def fetch_member(self, user_id: str) -> Dict[str, Any]:
        return await self.bot.http.request(
            "GET", f"/channels/{self.id}/thread-members/{user_id}"
        )

    async def fetch_members(self) -> List[Dict[str, Any]]:
        return await self.bot.http.request("GET", f"/channels/{self.id}/thread-members")

    async def fetch_message(self, message_id: str) -> Dict[str, Any]:
        return await self.bot.http.request("GET", f"/channels/{self.id}/messages/{message_id}")

    def get_partial_message(self, message_id: str) -> Dict[str, str]:
        return {"id": str(message_id), "channel_id": self.id}

    async def history(self, limit: int = 100) -> List[Dict[str, Any]]:
        return await self.bot.http.request(
            "GET", f"/channels/{self.id}/messages", params={"limit": limit}
        )

    def is_news(self) -> bool:
        return self.type in (5, 10)

    def is_nsfw(self) -> bool:
        return bool(self.flags & (1 << 5))

    def is_private(self) -> bool:
        return self.type in (2, 12)

    async def pins(self) -> List[Dict[str, Any]]:
        return await self.bot.http.request("GET", f"/channels/{self.id}/pins")

    async def purge(self, limit: int = 50) -> int:
        msgs = await self.history(limit=limit)
        if not msgs:
            return 0
        await self.delete_messages([m["id"] for m in msgs])
        return len(msgs)

    async def send(self, content: Optional[str] = None, **kwargs: Any) -> Any:
        return await self.bot.message_handler.send_message(self.id, content=content, **kwargs)

    async def typing(self) -> bool:
        await self.bot.http.request("POST", f"/channels/{self.id}/typing")
        return True
