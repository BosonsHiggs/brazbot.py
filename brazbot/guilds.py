"""
Modelo de Servidor (Guild) completo para a API v10 do Discord.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from brazbot.member import Member
from brazbot.snowflake import Snowflake


class Guild:
    """Representa um servidor (Guild) na API v10 do Discord."""

    def __init__(self, data: Dict[str, Any], bot: Any = None):
        self._raw = data or {}
        self.bot = bot
        self.id = str(data.get("id") or "0")
        self.name = data.get("name", f"Guild {self.id}")
        self.icon = data.get("icon")
        self.icon_url = (
            f"https://cdn.discordapp.com/icons/{self.id}/{self.icon}.png?size=512"
            if self.icon
            else None
        )
        self.splash = data.get("splash")
        self.discovery_splash = data.get("discovery_splash")
        self.owner_id = str(data.get("owner_id") or "")
        self.owner = data.get("owner")
        self.permissions = data.get("permissions")
        self.region = data.get("region")
        self.afk_channel = data.get("afk_channel_id") or data.get("afk_channel")
        self.afk_timeout = data.get("afk_timeout")
        self.widget_enabled = data.get("widget_enabled")
        self.widget_channel = data.get("widget_channel_id") or data.get("widget_channel")
        self.verification_level = data.get("verification_level")
        self.default_notifications = data.get("default_message_notifications") or data.get(
            "default_notifications"
        )
        self.explicit_content_filter = data.get("explicit_content_filter")
        self.roles = data.get("roles", [])
        self.emojis = data.get("emojis", [])
        self. stickers = data.get("stickers", [])
        self.features = data.get("features", [])
        self.mfa_level = data.get("mfa_level")
        self.application_id = data.get("application_id")
        self.system_channel = data.get("system_channel_id") or data.get("system_channel")
        self.system_channel_flags = data.get("system_channel_flags")
        self.rules_channel = data.get("rules_channel_id") or data.get("rules_channel")
        self.max_presences = data.get("max_presences")
        self.max_members = data.get("max_members")
        self.vanity_url_code = data.get("vanity_url_code")
        self.description = data.get("description")
        self.banner = data.get("banner")
        self.banner_url = (
            f"https://cdn.discordapp.com/banners/{self.id}/{self.banner}.png?size=1024"
            if self.banner
            else None
        )
        self.premium_tier = data.get("premium_tier", 0)
        self.premium_subscription_count = data.get("premium_subscription_count", 0)
        self.preferred_locale = data.get("preferred_locale", "pt-BR")
        self.public_updates_channel = data.get("public_updates_channel_id") or data.get(
            "public_updates_channel"
        )
        self.max_video_channel_users = data.get("max_video_channel_users")
        self.approximate_member_count = data.get("approximate_member_count")
        self.approximate_presence_count = data.get("approximate_presence_count")
        self.welcome_screen_data = data.get("welcome_screen")
        self.nsfw_level = data.get("nsfw_level", 0)
        self.premium_progress_bar_enabled = data.get("premium_progress_bar_enabled", False)
        self.large = data.get("large", False)
        self.member_count = data.get("member_count") or self.approximate_member_count or 0
        self.members = data.get("members", [])
        self.channels = data.get("channels", [])
        self.threads = data.get("threads", [])
        self.stage_channels = data.get("stage_channels", [])
        self.voice_channels = data.get("voice_channels", [])
        self.categories = data.get("categories", [])
        self.shard_id = data.get("shard_id", 0)
        self.unavailable = data.get("unavailable", False)
        self.invites_paused_until = data.get("invites_paused_until")
        self.dms_paused_until = data.get("dms_paused_until")
        self.filesize_limit = data.get("filesize_limit")
        self.emoji_limit = data.get("emoji_limit")
        self.sticker_limit = data.get("sticker_limit")
        self.stage_instances = data.get("stage_instances", [])
        self.scheduled_events = data.get("guild_scheduled_events") or data.get(
            "scheduled_events", []
        )
        self.default_role = data.get("default_role")
        self.self_role = data.get("self_role")
        self.public_updates_channel_id = data.get("public_updates_channel_id")
        self.created_at = (
            Snowflake.to_datetime(self.id)
            if Snowflake.is_valid(self.id)
            else datetime.now(timezone.utc)
        )

    @classmethod
    async def from_guild_id(cls, bot: Any, guild_id: str, with_counts: bool = True) -> "Guild":
        cache_key = f"guild_{guild_id}"
        data = bot.get_cache_data(cache_key) if hasattr(bot, "get_cache_data") else None
        if data:
            return cls(data, bot=bot)

        params = {"with_counts": "true"} if with_counts else None
        data = await bot.http.request("GET", f"/guilds/{guild_id}", params=params)
        if hasattr(bot, "set_cache_data") and data:
            bot.set_cache_data(cache_key, data, seconds=120)
        return cls(data, bot=bot)

    def __str__(self) -> str:
        return str(self.name)

    def roles_count(self) -> int:
        return len(self.roles)

    async def fetch_all_members(self) -> List[Member]:
        members: List[Member] = []
        limit = 1000
        after: Optional[str] = None
        while True:
            params: Dict[str, Any] = {"limit": limit}
            if after:
                params["after"] = after
            data = await self.bot.http.request(
                "GET", f"/guilds/{self.id}/members", params=params
            )
            if not data:
                break
            for member_data in data:
                members.append(Member(member_data, self.bot, guild_id=self.id))
            user_obj = data[-1].get("user", data[-1])
            after = user_obj.get("id")
            if len(data) < limit:
                break
            await asyncio.sleep(0.5)
        return members

    async def active_threads(self) -> Dict[str, Any]:
        return await self.bot.http.request("GET", f"/guilds/{self.id}/threads/active")

    async def audit_logs(self, limit: int = 50, action_type: Optional[int] = None) -> Dict[str, Any]:
        params: Dict[str, Any] = {"limit": limit}
        if action_type is not None:
            params["action_type"] = action_type
        return await self.bot.http.request("GET", f"/guilds/{self.id}/audit-logs", params=params)

    async def ban(
        self,
        user_id: str,
        delete_message_days: int = 0,
        reason: Optional[str] = None,
    ) -> bool:
        payload = {"delete_message_seconds": min(604800, max(0, int(delete_message_days) * 86400))}
        await self.bot.http.request(
            "PUT", f"/guilds/{self.id}/bans/{user_id}", json_data=payload, reason=reason
        )
        return True

    async def bans(self, limit: int = 1000) -> List[Dict[str, Any]]:
        return await self.bot.http.request(
            "GET", f"/guilds/{self.id}/bans", params={"limit": limit}
        )

    async def bulk_ban(
        self,
        user_ids: List[str],
        delete_message_days: int = 0,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Usa o endpoint nativo de Bulk Ban da API v10 (`POST /guilds/{guild.id}/bulk-ban`)."""
        payload = {
            "user_ids": [str(uid) for uid in user_ids[:200]],
            "delete_message_seconds": min(604800, max(0, int(delete_message_days) * 86400)),
        }
        return await self.bot.http.request(
            "POST", f"/guilds/{self.id}/bulk-ban", json_data=payload, reason=reason
        )

    async def by_category(self) -> Dict[Optional[str], List[Dict[str, Any]]]:
        channels = await self.fetch_channels()
        categories: Dict[Optional[str], List[Dict[str, Any]]] = {}
        for channel in channels:
            category_id = channel.get("parent_id")
            categories.setdefault(category_id, []).append(channel)
        return categories

    async def change_voice_state(
        self,
        channel_id: Optional[str],
        self_mute: bool = False,
        self_deaf: bool = False,
    ) -> bool:
        if getattr(self.bot, "_ws", None) and not self.bot._ws.closed:
            await self.bot._ws.send_json(
                {
                    "op": 4,
                    "d": {
                        "guild_id": self.id,
                        "channel_id": str(channel_id) if channel_id else None,
                        "self_mute": self_mute,
                        "self_deaf": self_deaf,
                    },
                }
            )
            return True
        return False

    async def fetch_voice_state(self, user_id: str = "@me") -> Dict[str, Any]:
        """Busca o estado de voz de um membro via HTTP (`GET /guilds/{guild.id}/voice-states/{user.id}`)."""
        return await self.bot.http.request(
            "GET", f"/guilds/{self.id}/voice-states/{user_id}"
        )

    async def chunk(self) -> List[Dict[str, Any]]:
        return await self.bot.http.request(
            "GET", f"/guilds/{self.id}/members", params={"limit": 1000}
        )

    async def create_automod_rule(
        self, data: Dict[str, Any], reason: Optional[str] = None
    ) -> Dict[str, Any]:
        return await self.bot.http.request(
            "POST", f"/guilds/{self.id}/auto-moderation/rules", json_data=data, reason=reason
        )

    async def create_category(self, name: str, reason: Optional[str] = None) -> Dict[str, Any]:
        return await self.create_channel(name, 4, reason=reason)

    async def create_channel(
        self, name: str, type: int = 0, reason: Optional[str] = None, **kwargs: Any
    ) -> Dict[str, Any]:
        payload = {"name": name, "type": type, **kwargs}
        return await self.bot.http.request(
            "POST", f"/guilds/{self.id}/channels", json_data=payload, reason=reason
        )

    async def create_custom_emoji(
        self,
        name: str,
        image: str,
        roles: Optional[List[str]] = None,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        payload = {"name": name, "image": image, "roles": roles or []}
        return await self.bot.http.request(
            "POST", f"/guilds/{self.id}/emojis", json_data=payload, reason=reason
        )

    async def create_forum(self, name: str, reason: Optional[str] = None) -> Dict[str, Any]:
        return await self.create_channel(name, 15, reason=reason)

    async def create_integration(self, type: str, id: str) -> bool:
        await self.bot.http.request(
            "POST", f"/guilds/{self.id}/integrations", json_data={"type": type, "id": id}
        )
        return True

    async def create_role(
        self, data: Dict[str, Any], reason: Optional[str] = None
    ) -> Dict[str, Any]:
        return await self.bot.http.request(
            "POST", f"/guilds/{self.id}/roles", json_data=data, reason=reason
        )

    async def create_scheduled_event(
        self, data: Dict[str, Any], reason: Optional[str] = None
    ) -> Dict[str, Any]:
        return await self.bot.http.request(
            "POST", f"/guilds/{self.id}/scheduled-events", json_data=data, reason=reason
        )

    async def create_stage_channel(self, name: str, reason: Optional[str] = None) -> Dict[str, Any]:
        return await self.create_channel(name, 13, reason=reason)

    async def create_sticker(
        self, data: Dict[str, Any], reason: Optional[str] = None
    ) -> Dict[str, Any]:
        return await self.bot.http.request(
            "POST", f"/guilds/{self.id}/stickers", json_data=data, reason=reason
        )

    async def create_template(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self.bot.http.request(
            "POST", f"/guilds/{self.id}/templates", json_data=data
        )

    async def create_text_channel(
        self, name: str, reason: Optional[str] = None, **kwargs: Any
    ) -> Dict[str, Any]:
        return await self.create_channel(name, 0, reason=reason, **kwargs)

    async def create_voice_channel(
        self, name: str, reason: Optional[str] = None, **kwargs: Any
    ) -> Dict[str, Any]:
        return await self.create_channel(name, 2, reason=reason, **kwargs)

    async def delete(self) -> bool:
        await self.bot.http.request("DELETE", f"/guilds/{self.id}")
        return True

    async def delete_emoji(self, emoji_id: str, reason: Optional[str] = None) -> bool:
        await self.bot.http.request(
            "DELETE", f"/guilds/{self.id}/emojis/{emoji_id}", reason=reason
        )
        return True

    async def delete_sticker(self, sticker_id: str, reason: Optional[str] = None) -> bool:
        await self.bot.http.request(
            "DELETE", f"/guilds/{self.id}/stickers/{sticker_id}", reason=reason
        )
        return True

    def dms_paused(self) -> bool:
        return self.dms_paused_until is not None

    async def edit(self, reason: Optional[str] = None, **fields: Any) -> Dict[str, Any]:
        return await self.bot.http.request(
            "PATCH", f"/guilds/{self.id}", json_data=fields, reason=reason
        )

    async def edit_role_positions(
        self, roles: List[Dict[str, Any]], reason: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        return await self.bot.http.request(
            "PATCH", f"/guilds/{self.id}/roles", json_data=roles, reason=reason
        )

    async def edit_welcome_screen(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self.bot.http.request(
            "PATCH", f"/guilds/{self.id}/welcome-screen", json_data=data
        )

    async def edit_widget(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self.bot.http.request("PATCH", f"/guilds/{self.id}/widget", json_data=data)

    async def estimate_pruned_members(self, days: int = 7) -> Dict[str, Any]:
        return await self.bot.http.request(
            "GET", f"/guilds/{self.id}/prune", params={"days": days}
        )

    async def fetch_automod_rule(self, rule_id: str) -> Dict[str, Any]:
        return await self.bot.http.request(
            "GET", f"/guilds/{self.id}/auto-moderation/rules/{rule_id}"
        )

    async def fetch_automod_rules(self) -> List[Dict[str, Any]]:
        return await self.bot.http.request("GET", f"/guilds/{self.id}/auto-moderation/rules")

    async def fetch_ban(self, user_id: str) -> Dict[str, Any]:
        return await self.bot.http.request("GET", f"/guilds/{self.id}/bans/{user_id}")

    async def fetch_channel(self, channel_id: str) -> Dict[str, Any]:
        return await self.bot.http.request("GET", f"/channels/{channel_id}")

    async def fetch_channels(self) -> List[Dict[str, Any]]:
        return await self.bot.http.request("GET", f"/guilds/{self.id}/channels")

    async def fetch_emoji(self, emoji_id: str) -> Dict[str, Any]:
        return await self.bot.http.request("GET", f"/guilds/{self.id}/emojis/{emoji_id}")

    async def fetch_emojis(self) -> List[Dict[str, Any]]:
        return await self.bot.http.request("GET", f"/guilds/{self.id}/emojis")

    async def fetch_member(self, user_id: str) -> Dict[str, Any]:
        return await self.bot.http.request("GET", f"/guilds/{self.id}/members/{user_id}")

    async def fetch_members(self, limit: int = 100) -> List[Dict[str, Any]]:
        return await self.bot.http.request(
            "GET", f"/guilds/{self.id}/members", params={"limit": limit}
        )

    async def fetch_roles(self) -> List[Dict[str, Any]]:
        return await self.bot.http.request("GET", f"/guilds/{self.id}/roles")

    async def fetch_scheduled_event(self, event_id: str) -> Dict[str, Any]:
        return await self.bot.http.request(
            "GET", f"/guilds/{self.id}/scheduled-events/{event_id}"
        )

    async def fetch_scheduled_events(self) -> List[Dict[str, Any]]:
        return await self.bot.http.request("GET", f"/guilds/{self.id}/scheduled-events")

    async def fetch_sticker(self, sticker_id: str) -> Dict[str, Any]:
        return await self.bot.http.request("GET", f"/guilds/{self.id}/stickers/{sticker_id}")

    async def fetch_stickers(self) -> List[Dict[str, Any]]:
        return await self.bot.http.request("GET", f"/guilds/{self.id}/stickers")

    def get_channel(self, channel_id: str) -> Optional[Dict[str, Any]]:
        return next((c for c in self.channels if str(c.get("id")) == str(channel_id)), None)

    def get_channel_or_thread(self, channel_id: str) -> Optional[Dict[str, Any]]:
        for collection in (self.channels, self.threads):
            for item in collection:
                if str(item.get("id")) == str(channel_id):
                    return item
        return None

    def get_emoji(self, emoji_id: str) -> Optional[Dict[str, Any]]:
        return next((e for e in self.emojis if str(e.get("id")) == str(emoji_id)), None)

    def get_member(self, user_id: str) -> Optional[Dict[str, Any]]:
        for m in self.members:
            uid = m.get("id") or m.get("user", {}).get("id")
            if str(uid) == str(user_id):
                return m
        return None

    def get_member_named(self, name: str) -> Optional[Dict[str, Any]]:
        for m in self.members:
            uname = m.get("username") or m.get("user", {}).get("username")
            nick = m.get("nick")
            if uname == name or nick == name:
                return m
        return None

    def get_role(self, role_id: str) -> Optional[Dict[str, Any]]:
        return next((r for r in self.roles if str(r.get("id")) == str(role_id)), None)

    def get_scheduled_event(self, event_id: str) -> Optional[Dict[str, Any]]:
        return next((e for e in self.scheduled_events if str(e.get("id")) == str(event_id)), None)

    def get_stage_instance(self, stage_id: str) -> Optional[Dict[str, Any]]:
        return next((s for s in self.stage_instances if str(s.get("id")) == str(stage_id)), None)

    def get_thread(self, thread_id: str) -> Optional[Dict[str, Any]]:
        return next((t for t in self.threads if str(t.get("id")) == str(thread_id)), None)

    async def integrations(self) -> List[Dict[str, Any]]:
        return await self.bot.http.request("GET", f"/guilds/{self.id}/integrations")

    async def invites(self) -> List[Dict[str, Any]]:
        return await self.bot.http.request("GET", f"/guilds/{self.id}/invites")

    def invites_paused(self) -> bool:
        return self.invites_paused_until is not None

    async def kick(self, user_id: str, reason: Optional[str] = None) -> bool:
        await self.bot.http.request(
            "DELETE", f"/guilds/{self.id}/members/{user_id}", reason=reason
        )
        return True

    async def leave(self) -> bool:
        await self.bot.http.request("DELETE", f"/users/@me/guilds/{self.id}")
        return True

    async def prune_members(self, days: int = 7, reason: Optional[str] = None) -> Dict[str, Any]:
        return await self.bot.http.request(
            "POST", f"/guilds/{self.id}/prune", json_data={"days": days}, reason=reason
        )

    async def query_members(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        return await self.bot.http.request(
            "GET",
            f"/guilds/{self.id}/members/search",
            params={"query": query, "limit": limit},
        )

    async def templates(self) -> List[Dict[str, Any]]:
        return await self.bot.http.request("GET", f"/guilds/{self.id}/templates")

    async def unban(self, user_id: str, reason: Optional[str] = None) -> bool:
        await self.bot.http.request(
            "DELETE", f"/guilds/{self.id}/bans/{user_id}", reason=reason
        )
        return True

    async def vanity_invite(self) -> Dict[str, Any]:
        return await self.bot.http.request("GET", f"/guilds/{self.id}/vanity-url")

    async def webhooks(self) -> List[Dict[str, Any]]:
        return await self.bot.http.request("GET", f"/guilds/{self.id}/webhooks")

    async def welcome_screen(self) -> Dict[str, Any]:
        return await self.bot.http.request("GET", f"/guilds/{self.id}/welcome-screen")

    async def widget(self) -> Dict[str, Any]:
        return await self.bot.http.request("GET", f"/guilds/{self.id}/widget.json")
