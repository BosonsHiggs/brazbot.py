"""
Modelo completo de Webhook da API v10 do Discord.
"""

from typing import Any, Dict, List, Optional


class Webhook:
    """Representa um Webhook da API v10 do Discord."""

    def __init__(self, data: Dict[str, Any], bot: Any = None):
        self._raw = data or {}
        self.bot = bot
        self.id = str(data.get("id") or "0")
        self.type = int(data.get("type", 1))
        self.guild_id = data.get("guild_id")
        self.channel_id = data.get("channel_id")
        self.user = data.get("user")
        self.name = data.get("name")
        self.avatar = data.get("avatar")
        self.token = data.get("token")
        self.application_id = data.get("application_id")
        self.url = (
            data.get("url")
            or f"https://discord.com/api/v10/webhooks/{self.id}/{self.token}"
        )

    @classmethod
    async def create(
        cls,
        bot: Any,
        channel_id: str,
        name: str,
        avatar: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> "Webhook":
        payload: Dict[str, Any] = {"name": name}
        if avatar:
            payload["avatar"] = avatar
        data = await bot.http.request(
            "POST", f"/channels/{channel_id}/webhooks", json_data=payload, reason=reason
        )
        return cls(data, bot=bot)

    @classmethod
    async def from_id(cls, bot: Any, webhook_id: str, token: Optional[str] = None) -> "Webhook":
        endpoint = f"/webhooks/{webhook_id}/{token}" if token else f"/webhooks/{webhook_id}"
        data = await bot.http.request("GET", endpoint, auth=token is None)
        return cls(data, bot=bot)

    async def send(
        self,
        content: Optional[str] = None,
        *,
        username: Optional[str] = None,
        avatar_url: Optional[str] = None,
        embed: Any = None,
        embeds: Optional[List[Any]] = None,
        files: Optional[List[Any]] = None,
        components: Optional[Any] = None,
        thread_name: Optional[str] = None,
        wait: bool = True,
    ) -> Optional[Dict[str, Any]]:
        payload = self.bot.message_handler._build_message_payload(
            content=content,
            embed=embed,
            embeds=embeds,
            components=components,
        )
        if username:
            payload["username"] = username
        if avatar_url:
            payload["avatar_url"] = avatar_url
        if thread_name:
            payload["thread_name"] = thread_name
        return await self.bot.http.request(
            "POST",
            f"/webhooks/{self.id}/{self.token}",
            params={"wait": "true" if wait else "false"},
            json_data=payload,
            files=files,
            auth=False,
        )

    async def delete(self, reason: Optional[str] = None) -> bool:
        endpoint = (
            f"/webhooks/{self.id}/{self.token}" if self.token else f"/webhooks/{self.id}"
        )
        await self.bot.http.request(
            "DELETE", endpoint, reason=reason, auth=self.token is None
        )
        return True
