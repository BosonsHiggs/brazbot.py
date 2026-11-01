"""
Interaction Response object (`InteractionResponse`) for Discord API v10.
"""

from typing import Any, Dict, List, Optional


class InteractionResponse:
    """Encapsulates direct responses to an incoming interaction in Discord API v10."""

    def __init__(self, bot: Any, message: Dict[str, Any]):
        self.bot = bot
        self.message = message
        self.interaction_id = message["id"]
        self.interaction_token = message["token"]

    async def send(
        self,
        content: Optional[str] = None,
        embeds: Optional[List[Any]] = None,
        embed: Any = None,
        files: Optional[List[Any]] = None,
        components: Optional[Any] = None,
        ephemeral: bool = False,
        poll: Any = None,
    ) -> Any:
        return await self.bot.message_handler.send_interaction(
            self.message,
            content=content,
            embed=embed,
            embeds=embeds,
            files=files,
            components=components,
            ephemeral=ephemeral,
            poll=poll,
        )

    async def defer(self, ephemeral: bool = False) -> Any:
        payload: Dict[str, Any] = {"type": 5}
        if ephemeral:
            payload["data"] = {"flags": 64}
        self.message["_deferred"] = True
        return await self.bot.http.request(
            "POST",
            f"/interactions/{self.interaction_id}/{self.interaction_token}/callback",
            json_data=payload,
            auth=False,
            raise_on_error=False,
        )
