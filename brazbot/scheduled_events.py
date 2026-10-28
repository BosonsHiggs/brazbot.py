"""
Gerenciamento de Eventos Agendados de Servidor (Guild Scheduled Events) da API v10 do Discord.
"""

from datetime import datetime
from enum import IntEnum
from typing import Any, Dict, List, Optional, Union


class ScheduledEventEntityType(IntEnum):
    STAGE_INSTANCE = 1
    VOICE = 2
    EXTERNAL = 3


class ScheduledEventStatus(IntEnum):
    SCHEDULED = 1
    ACTIVE = 2
    COMPLETED = 3
    CANCELED = 4


class ScheduledEvent:
    """Representa um Evento Agendado de Servidor na API v10 do Discord."""

    def __init__(self, data: Dict[str, Any], bot: Any = None):
        self._raw = data or {}
        self.bot = bot
        self.id = str(data.get("id") or "0")
        self.guild_id = str(data.get("guild_id") or "0")
        self.channel_id = data.get("channel_id")
        self.creator_id = data.get("creator_id")
        self.name = data.get("name", "Scheduled Event")
        self.description = data.get("description")
        self.scheduled_start_time = data.get("scheduled_start_time")
        self.scheduled_end_time = data.get("scheduled_end_time")
        self.privacy_level = int(data.get("privacy_level", 2))
        self.status = int(data.get("status", 1))
        self.entity_type = int(data.get("entity_type", 2))
        self.entity_metadata = data.get("entity_metadata")
        self.user_count = data.get("user_count", 0)

    @classmethod
    async def list_events(
        cls, bot: Any, guild_id: str, with_user_count: bool = True
    ) -> List["ScheduledEvent"]:
        params = {"with_user_count": "true"} if with_user_count else None
        data = await bot.http.request(
            "GET", f"/guilds/{guild_id}/scheduled-events", params=params
        )
        return [cls(item, bot=bot) for item in data]

    @classmethod
    async def create(
        cls,
        bot: Any,
        guild_id: str,
        name: str,
        start_time: Union[datetime, str],
        *,
        end_time: Optional[Union[datetime, str]] = None,
        description: Optional[str] = None,
        channel_id: Optional[str] = None,
        location: Optional[str] = None,
        entity_type: Optional[int] = None,
        reason: Optional[str] = None,
    ) -> "ScheduledEvent":
        start_iso = start_time.isoformat() if isinstance(start_time, datetime) else str(start_time)
        end_iso = (
            end_time.isoformat()
            if isinstance(end_time, datetime)
            else (str(end_time) if end_time else None)
        )
        if entity_type is None:
            entity_type = (
                int(ScheduledEventEntityType.EXTERNAL)
                if location
                else int(ScheduledEventEntityType.VOICE)
            )

        payload: Dict[str, Any] = {
            "name": name,
            "privacy_level": 2,
            "scheduled_start_time": start_iso,
            "entity_type": int(entity_type),
        }
        if description:
            payload["description"] = description
        if end_iso:
            payload["scheduled_end_time"] = end_iso
        if channel_id:
            payload["channel_id"] = str(channel_id)
        if location:
            payload["entity_metadata"] = {"location": str(location)}

        data = await bot.http.request(
            "POST", f"/guilds/{guild_id}/scheduled-events", json_data=payload, reason=reason
        )
        return cls(data, bot=bot)

    async def start(self) -> "ScheduledEvent":
        data = await self.bot.http.request(
            "PATCH",
            f"/guilds/{self.guild_id}/scheduled-events/{self.id}",
            json_data={"status": int(ScheduledEventStatus.ACTIVE)},
        )
        self.__init__(data, self.bot)
        return self

    async def complete(self) -> "ScheduledEvent":
        data = await self.bot.http.request(
            "PATCH",
            f"/guilds/{self.guild_id}/scheduled-events/{self.id}",
            json_data={"status": int(ScheduledEventStatus.COMPLETED)},
        )
        self.__init__(data, self.bot)
        return self

    async def delete(self) -> bool:
        await self.bot.http.request(
            "DELETE", f"/guilds/{self.guild_id}/scheduled-events/{self.id}"
        )
        return True
