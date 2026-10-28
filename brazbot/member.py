"""
Modelo de Membro e Estado de Voz (Member & VoiceState) para a API v10 do Discord.
Suporta acesso via atributos (`member.username`, `member.voice.channel`) e via dicionário
(`member['id']`, `member.get('username')`) para compatibilidade total.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Union

from brazbot.channels import VoiceChannel
from brazbot.permissions import Permissions
from brazbot.roles import Role
from brazbot.snowflake import Snowflake


class VoiceState:
    """Representa o estado de voz de um usuário em um servidor (Voice State Object da API v10)."""

    def __init__(self, data: Dict[str, Any], bot: Any = None, guild_id: Optional[str] = None):
        self._raw = data or {}
        self.bot = bot
        self.guild_id = str(guild_id or data.get("guild_id") or "") or None
        self.channel_id = str(data["channel_id"]) if data.get("channel_id") else None
        self.user_id = str(data.get("user_id") or "")
        self.session_id = data.get("session_id")
        self.deaf = bool(data.get("deaf", False))
        self.mute = bool(data.get("mute", False))
        self.self_deaf = bool(data.get("self_deaf", False))
        self.self_mute = bool(data.get("self_mute", False))
        self.self_stream = bool(data.get("self_stream", False))
        self.self_video = bool(data.get("self_video", False))
        self.suppress = bool(data.get("suppress", False))
        self.request_to_speak_timestamp = data.get("request_to_speak_timestamp")

        # Cria um objeto VoiceChannel acessível via `member.voice.channel`
        self.channel: Optional[VoiceChannel] = None
        if self.channel_id:
            ch_data = (
                bot.get_cache_data(f"channel_{self.channel_id}")
                if bot and hasattr(bot, "get_cache_data")
                else None
            ) or {"id": self.channel_id, "guild_id": self.guild_id, "type": 2}
            self.channel = VoiceChannel(
                ch_data, bot=bot, guild_id=self.guild_id, channel_id=self.channel_id
            )

    def __bool__(self) -> bool:
        return self.channel_id is not None

    def __repr__(self) -> str:
        return f"VoiceState(user_id={self.user_id!r}, channel_id={self.channel_id!r})"


class Member:
    """
    Representa um Usuário / Membro de Servidor na API v10 do Discord.
    """

    def __init__(
        self,
        data: Dict[str, Any],
        bot: Any = None,
        guild_id: Optional[str] = None,
        voice_state: Optional[Union[VoiceState, Dict[str, Any]]] = None,
    ):
        self._raw = dict(data or {})
        user_obj = self._raw.get("user") if isinstance(self._raw.get("user"), dict) else self._raw
        self.bot = bot
        self.id = str(user_obj.get("id") or self._raw.get("id") or "0")
        self.username = user_obj.get("username") or self._raw.get("username") or "Unknown"
        self.discriminator = str(user_obj.get("discriminator") or self._raw.get("discriminator") or "0")
        self.global_name = user_obj.get("global_name") or self._raw.get("global_name")
        self.avatar = user_obj.get("avatar") or self._raw.get("avatar")
        self.is_bot = bool(user_obj.get("bot", self._raw.get("bot", False)))
        self.system = bool(user_obj.get("system", self._raw.get("system", False)))
        self.mfa_enabled = bool(user_obj.get("mfa_enabled", False))
        self.locale = user_obj.get("locale")
        self.verified = bool(user_obj.get("verified", False))
        self.email = user_obj.get("email")
        self.flags = int(self._raw.get("flags") or user_obj.get("flags") or 0)
        self.premium_type = int(user_obj.get("premium_type") or 0)
        self.public_flags = int(user_obj.get("public_flags") or 0)
        self.accent_color = user_obj.get("accent_color")
        self.accent_colour = self.accent_color
        self.activities = self._raw.get("activities", [])
        self.activity = self.activities[0] if self.activities else None
        self.avatar_decoration_data = user_obj.get("avatar_decoration_data")
        self.banner = user_obj.get("banner")
        self.color = self.accent_color
        self.colour = self.color

        self.created_at = (
            Snowflake.to_datetime(self.id)
            if Snowflake.is_valid(self.id)
            else datetime.now(timezone.utc)
        )
        disc_mod = (int(self.id) >> 22) % 6 if self.discriminator in ("0", "0000") and Snowflake.is_valid(self.id) else (int(self.discriminator) % 5 if self.discriminator.isdigit() else 0)
        self.default_avatar = f"https://cdn.discordapp.com/embed/avatars/{disc_mod}.png"
        self.avatar_url = (
            f"https://cdn.discordapp.com/avatars/{self.id}/{self.avatar}.png?size=512"
            if self.avatar
            else self.default_avatar
        )
        self.display_avatar = self.avatar_url
        self.display_icon = self.avatar_url

        self.nick = self._raw.get("nick")
        self.display_name = self.nick or self.global_name or self.username
        self.dm_channel = self._raw.get("dm_channel")
        self.guild_id = str(guild_id or self._raw.get("guild_id") or "") or None
        self.guild_avatar = self._raw.get("avatar") if "user" in self._raw else None
        self.guild_permissions = self._raw.get("permissions")
        self.permissions = Permissions(self.guild_permissions or 0)
        self.joined_at = (
            datetime.fromisoformat(self._raw["joined_at"])
            if self._raw.get("joined_at")
            else None
        )
        self.mention = f"<@{self.id}>"
        self.desktop_status = self._raw.get("desktop_status")
        self.mobile_status = self._raw.get("mobile_status")
        self.web_status = self._raw.get("web_status")
        self.mutual_guilds = self._raw.get("mutual_guilds", [])
        self.name = self.username
        self.pending = bool(self._raw.get("pending", False))
        self.premium_since = (
            datetime.fromisoformat(self._raw["premium_since"])
            if self._raw.get("premium_since")
            else None
        )
        self.raw_status = self._raw.get("raw_status")
        self.resolved_permissions = self._raw.get("permissions")
        self.roles: List[str] = [str(r) for r in self._raw.get("roles", [])]
        self.status = self._raw.get("status")
        self.timed_out_until = (
            datetime.fromisoformat(self._raw["communication_disabled_until"])
            if self._raw.get("communication_disabled_until")
            else (
                datetime.fromisoformat(self._raw["timed_out_until"])
                if self._raw.get("timed_out_until")
                else None
            )
        )
        self.top_role = self.roles[-1] if self.roles else None

        # Estado de voz (VoiceState)
        raw_voice = voice_state or self._raw.get("voice")
        if isinstance(raw_voice, VoiceState):
            self.voice: Optional[VoiceState] = raw_voice if raw_voice.channel_id else None
        elif isinstance(raw_voice, dict) and raw_voice.get("channel_id"):
            self.voice = VoiceState(raw_voice, bot=bot, guild_id=self.guild_id)
        elif bot and hasattr(bot, "get_member_voice_state") and self.guild_id:
            self.voice = bot.get_member_voice_state(self.guild_id, self.id)
        else:
            self.voice = None

    # Compatibilidade total com código que acessa `ctx.author['id']` ou `ctx.member['roles']`
    def __getitem__(self, key: str) -> Any:
        if hasattr(self, key):
            return getattr(self, key)
        if key in self._raw:
            return self._raw[key]
        if "user" in self._raw and isinstance(self._raw["user"], dict) and key in self._raw["user"]:
            return self._raw["user"][key]
        raise KeyError(key)

    def __contains__(self, key: str) -> bool:
        return hasattr(self, key) or key in self._raw

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default

    @classmethod
    async def from_user_id(
        cls, bot: Any, user_id: str, guild_id: Optional[str] = None
    ) -> "Member":
        cache_key = f"member_{guild_id}_{user_id}" if guild_id else f"user_{user_id}"
        data = bot.get_cache_data(cache_key) if hasattr(bot, "get_cache_data") else None

        if not data:
            if guild_id:
                data = await bot.http.request(
                    "GET", f"/guilds/{guild_id}/members/{user_id}", raise_on_error=False
                )
            if not data:
                data = await bot.http.request("GET", f"/users/{user_id}")
            if hasattr(bot, "set_cache_data") and data:
                bot.set_cache_data(cache_key, data, seconds=200)

        return cls(data, bot=bot, guild_id=guild_id)

    def __str__(self) -> str:
        if self.discriminator and self.discriminator not in ("0", "0000"):
            return f"{self.username}#{self.discriminator}"
        return self.username

    async def add_role(self, role: Union[Role, str], reason: Optional[str] = None) -> bool:
        role_id = str(role.id if hasattr(role, "id") else role)
        await self.bot.http.request(
            "PUT",
            f"/guilds/{self.guild_id}/members/{self.id}/roles/{role_id}",
            reason=reason,
        )
        if role_id not in self.roles:
            self.roles.append(role_id)
        return True

    async def add_roles(self, *roles: Union[Role, str], reason: Optional[str] = None) -> bool:
        for role in roles:
            await self.add_role(role, reason=reason)
        return True

    async def remove_role(self, role: Union[Role, str], reason: Optional[str] = None) -> bool:
        role_id = str(role.id if hasattr(role, "id") else role)
        await self.bot.http.request(
            "DELETE",
            f"/guilds/{self.guild_id}/members/{self.id}/roles/{role_id}",
            reason=reason,
        )
        if role_id in self.roles:
            self.roles.remove(role_id)
        return True

    async def remove_roles(self, *roles: Union[Role, str], reason: Optional[str] = None) -> bool:
        for role in roles:
            await self.remove_role(role, reason=reason)
        return True

    async def ban(
        self,
        reason: Optional[str] = None,
        delete_message_days: int = 0,
        delete_message_seconds: Optional[int] = None,
    ) -> bool:
        secs = (
            delete_message_seconds
            if delete_message_seconds is not None
            else int(delete_message_days) * 86400
        )
        payload = {"delete_message_seconds": min(604800, max(0, secs))}
        await self.bot.http.request(
            "PUT",
            f"/guilds/{self.guild_id}/bans/{self.id}",
            json_data=payload,
            reason=reason,
        )
        return True

    async def unban(self, reason: Optional[str] = None) -> bool:
        await self.bot.http.request(
            "DELETE", f"/guilds/{self.guild_id}/bans/{self.id}", reason=reason
        )
        return True

    async def kick(self, reason: Optional[str] = None) -> bool:
        await self.bot.http.request(
            "DELETE", f"/guilds/{self.guild_id}/members/{self.id}", reason=reason
        )
        return True

    async def timeout(
        self,
        duration: Optional[Union[timedelta, int, float]],
        reason: Optional[str] = None,
    ) -> bool:
        """
        Aplica ou remove (se `duration=None` ou `0`) um castigo/timeout no membro (API v10).
        `duration` pode ser `timedelta` ou segundos (`int`/`float`, máximo 28 dias).
        """
        if duration is None or (isinstance(duration, (int, float)) and duration <= 0):
            until_iso = None
            self.timed_out_until = None
        else:
            delta = (
                duration
                if isinstance(duration, timedelta)
                else timedelta(seconds=float(duration))
            )
            until_dt = datetime.now(timezone.utc) + delta
            until_iso = until_dt.isoformat()
            self.timed_out_until = until_dt

        await self.bot.http.request(
            "PATCH",
            f"/guilds/{self.guild_id}/members/{self.id}",
            json_data={"communication_disabled_until": until_iso},
            reason=reason,
        )
        return True

    async def untimeout(self, reason: Optional[str] = None) -> bool:
        """Remove o castigo/timeout ativo do membro."""
        return await self.timeout(None, reason=reason)

    async def edit(self, reason: Optional[str] = None, **fields: Any) -> "Member":
        data = await self.bot.http.request(
            "PATCH",
            f"/guilds/{self.guild_id}/members/{self.id}",
            json_data=fields,
            reason=reason,
        )
        if isinstance(data, dict):
            self.nick = data.get("nick", self.nick)
            self.roles = [str(r) for r in data.get("roles", self.roles)]
        return self

    async def set_nickname(self, nick: Optional[str], reason: Optional[str] = None) -> "Member":
        return await self.edit(nick=nick, reason=reason)

    async def move_to(self, channel_id: Optional[str], reason: Optional[str] = None) -> bool:
        await self.bot.http.request(
            "PATCH",
            f"/guilds/{self.guild_id}/members/{self.id}",
            json_data={"channel_id": str(channel_id) if channel_id else None},
            reason=reason,
        )
        return True

    async def create_dm(self) -> Dict[str, Any]:
        data = await self.bot.http.request(
            "POST", "/users/@me/channels", json_data={"recipient_id": self.id}
        )
        self.dm_channel = data
        return data

    async def send(
        self,
        content: Optional[str] = None,
        embed: Any = None,
        embeds: Optional[List[Any]] = None,
        files: Optional[List[Any]] = None,
        components: Optional[List[Any]] = None,
        ephemeral: bool = False,
    ) -> Any:
        if not self.dm_channel:
            await self.create_dm()
        return await self.bot.message_handler.send_message(
            self.dm_channel["id"],
            content=content,
            embed=embed,
            embeds=embeds,
            files=files,
            components=components,
            ephemeral=ephemeral,
        )

    async def fetch_message(self, channel_id: str, message_id: str) -> Dict[str, Any]:
        return await self.bot.http.request("GET", f"/channels/{channel_id}/messages/{message_id}")

    def get_role(self, role_id: str) -> Optional[str]:
        return next((r for r in self.roles if str(r) == str(role_id)), None)

    async def history(self, limit: int = 100) -> List[Dict[str, Any]]:
        if not self.dm_channel:
            await self.create_dm()
        return await self.bot.http.request(
            "GET", f"/channels/{self.dm_channel['id']}/messages", params={"limit": limit}
        )

    def is_on_mobile(self) -> bool:
        return self.mobile_status == "online"

    def is_timed_out(self) -> bool:
        if not self.timed_out_until:
            return False
        now = datetime.now(self.timed_out_until.tzinfo or timezone.utc)
        return self.timed_out_until > now

    async def mentioned_in(self, message: Dict[str, Any]) -> bool:
        content = message.get("content", "")
        return f"<@{self.id}>" in content or f"<@!{self.id}>" in content

    async def pins(self) -> List[Dict[str, Any]]:
        if not self.dm_channel:
            await self.create_dm()
        return await self.bot.http.request("GET", f"/channels/{self.dm_channel['id']}/pins")

    async def request_to_speak(self) -> bool:
        await self.bot.http.request(
            "PATCH",
            f"/guilds/{self.guild_id}/voice-states/{self.id}",
            json_data={"request_to_speak_timestamp": datetime.now(timezone.utc).isoformat()},
        )
        return True

    async def typing(self) -> bool:
        if not self.dm_channel:
            await self.create_dm()
        await self.bot.http.request("POST", f"/channels/{self.dm_channel['id']}/typing")
        return True
