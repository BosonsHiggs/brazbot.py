"""
Suporte ao Soundboard da API v10 do Discord.
"""

from typing import Any, Dict, List, Optional


class SoundboardSound:
    """Representa um som do Soundboard na API v10 do Discord."""

    def __init__(self, data: Dict[str, Any], bot: Any = None):
        self._raw = data or {}
        self.bot = bot
        self.sound_id = str(data.get("sound_id") or "0")
        self.name = data.get("name", "sound")
        self.volume = float(data.get("volume", 1.0))
        self.emoji_id = data.get("emoji_id")
        self.emoji_name = data.get("emoji_name")
        self.guild_id = data.get("guild_id")
        self.available = bool(data.get("available", True))
        self.user = data.get("user")


class Soundboard:
    """Gerenciador de efeitos sonoros do Soundboard (API v10)."""

    @staticmethod
    async def list_default_sounds(bot: Any) -> List[SoundboardSound]:
        data = await bot.http.request("GET", "/soundboard-default-sounds")
        return [SoundboardSound(item, bot=bot) for item in data]

    @staticmethod
    async def list_guild_sounds(bot: Any, guild_id: str) -> List[SoundboardSound]:
        data = await bot.http.request("GET", f"/guilds/{guild_id}/soundboard-sounds")
        items = data.get("items", data) if isinstance(data, dict) else data
        return [SoundboardSound(item, bot=bot) for item in items]

    @staticmethod
    async def send_sound(
        bot: Any,
        channel_id: str,
        sound_id: str,
        source_guild_id: Optional[str] = None,
    ) -> bool:
        payload: Dict[str, Any] = {"sound_id": str(sound_id)}
        if source_guild_id:
            payload["source_guild_id"] = str(source_guild_id)
        await bot.http.request(
            "POST", f"/channels/{channel_id}/send-soundboard-sound", json_data=payload
        )
        return True
