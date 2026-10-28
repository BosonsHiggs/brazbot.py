"""
Modelo de Cargo (Role) da API v10 do Discord.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from brazbot.permissions import Permissions
from brazbot.snowflake import Snowflake


class Role:
    """Representa um cargo (Role) de um servidor na API v10 do Discord."""

    def __init__(self, data: Dict[str, Any], bot: Any = None, guild_id: Optional[str] = None):
        self._raw = data or {}
        self.bot = bot
        self.id = str(data.get("id") or "0")
        self.name = data.get("name", "new role")
        self.color = int(data.get("color") or 0)
        self.colour = self.color
        self.created_at = (
            Snowflake.to_datetime(self.id)
            if Snowflake.is_valid(self.id)
            else datetime.now(timezone.utc)
        )
        self.display_icon = data.get("icon")
        self.flags = int(data.get("flags") or 0)
        self.guild = data.get("guild")
        self.guild_id = str(
            guild_id
            or (self.guild.get("id") if isinstance(self.guild, dict) else None)
            or data.get("guild_id")
            or ""
        ) or None
        self.hoist = bool(data.get("hoist", False))
        self.icon = data.get("icon")
        self.managed = bool(data.get("managed", False))
        self.members = data.get("members", [])
        self.mention = f"<@&{self.id}>"
        self.mentionable = bool(data.get("mentionable", False))
        self.permissions = str(data.get("permissions") or "0")
        self.permissions_obj = Permissions(self.permissions)
        self.position = int(data.get("position") or 0)
        self.tags = data.get("tags") or {}
        self.unicode_emoji = data.get("unicode_emoji")

    def __getitem__(self, key: str) -> Any:
        if hasattr(self, key):
            return getattr(self, key)
        return self._raw[key]

    @classmethod
    async def from_role_id(cls, bot: Any, guild_id: str, role_id: str) -> "Role":
        cache_key = f"role_{role_id}"
        data = bot.get_cache_data(cache_key) if hasattr(bot, "get_cache_data") else None
        if data:
            return cls(data, bot=bot, guild_id=guild_id)

        roles = await bot.http.request("GET", f"/guilds/{guild_id}/roles")
        role_data = next((r for r in roles if str(r.get("id")) == str(role_id)), None)
        if not role_data:
            raise ValueError(f"Role {role_id} not found in guild {guild_id}")
        if hasattr(bot, "set_cache_data"):
            bot.set_cache_data(cache_key, role_data, seconds=120)
        return cls(role_data, bot=bot, guild_id=guild_id)

    def __str__(self) -> str:
        return str(self.name)

    async def delete(self, reason: Optional[str] = None) -> bool:
        await self.bot.http.request(
            "DELETE", f"/guilds/{self.guild_id}/roles/{self.id}", reason=reason
        )
        return True

    async def edit(self, reason: Optional[str] = None, **fields: Any) -> "Role":
        if "permissions" in fields:
            fields["permissions"] = str(int(fields["permissions"]))
        data = await self.bot.http.request(
            "PATCH",
            f"/guilds/{self.guild_id}/roles/{self.id}",
            json_data=fields,
            reason=reason,
        )
        self.__init__(data, self.bot, self.guild_id)
        return self

    async def add_to_member(self, member_id: str, reason: Optional[str] = None) -> bool:
        await self.bot.http.request(
            "PUT",
            f"/guilds/{self.guild_id}/members/{member_id}/roles/{self.id}",
            reason=reason,
        )
        return True

    async def remove_from_member(self, member_id: str, reason: Optional[str] = None) -> bool:
        await self.bot.http.request(
            "DELETE",
            f"/guilds/{self.guild_id}/members/{member_id}/roles/{self.id}",
            reason=reason,
        )
        return True

    def is_assignable(self) -> bool:
        return not self.managed and int(self.permissions) != 0

    def is_bot_managed(self) -> bool:
        return self.tags.get("bot_id") is not None

    def is_default(self) -> bool:
        return str(self.id) == str(self.guild_id)

    def is_integration(self) -> bool:
        return self.tags.get("integration_id") is not None

    def is_premium_subscriber(self) -> bool:
        return "premium_subscriber" in self.tags

    @classmethod
    async def fetch_all_roles(cls, bot: Any, guild_id: str) -> List["Role"]:
        data = await bot.http.request("GET", f"/guilds/{guild_id}/roles")
        return [cls(role_data, bot=bot, guild_id=guild_id) for role_data in data]

    @classmethod
    async def create_role(
        cls,
        bot: Any,
        guild_id: str,
        name: str,
        color: int = 0,
        hoist: bool = False,
        mentionable: bool = False,
        permissions: int = 0,
        reason: Optional[str] = None,
    ) -> "Role":
        payload = {
            "name": name,
            "color": int(color),
            "hoist": bool(hoist),
            "mentionable": bool(mentionable),
            "permissions": str(int(permissions)),
        }
        data = await bot.http.request(
            "POST", f"/guilds/{guild_id}/roles", json_data=payload, reason=reason
        )
        return cls(data, bot=bot, guild_id=guild_id)
