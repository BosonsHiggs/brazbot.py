"""
Suporte completo ao sistema de AutoModeração (AutoMod) da API v10 do Discord.
"""

from enum import IntEnum
from typing import Any, Dict, List, Optional


class AutoModTriggerType(IntEnum):
    KEYWORD = 1
    SPAM = 3
    KEYWORD_PRESET = 4
    MENTION_SPAM = 5
    MEMBER_PROFILE = 6


class AutoModActionType(IntEnum):
    BLOCK_MESSAGE = 1
    SEND_ALERT_MESSAGE = 2
    TIMEOUT = 3
    BLOCK_MEMBER_INTERACTION = 4


class AutoModKeywordPresetType(IntEnum):
    PROFANITY = 1
    SEXUAL_CONTENT = 2
    SLURS = 3


class AutoModRule:
    """Representa e gerencia uma regra de AutoModeração na API v10 do Discord."""

    def __init__(self, data: Dict[str, Any], bot: Any = None):
        self._raw = data or {}
        self.bot = bot
        self.id = str(data.get("id") or "0")
        self.guild_id = str(data.get("guild_id") or "0")
        self.name = data.get("name", "AutoMod Rule")
        self.creator_id = data.get("creator_id")
        self.event_type = int(data.get("event_type", 1))
        self.trigger_type = int(data.get("trigger_type", 1))
        self.trigger_metadata = data.get("trigger_metadata", {})
        self.actions = data.get("actions", [])
        self.enabled = bool(data.get("enabled", True))
        self.exempt_roles = data.get("exempt_roles", [])
        self.exempt_channels = data.get("exempt_channels", [])

    @classmethod
    async def list_rules(cls, bot: Any, guild_id: str) -> List["AutoModRule"]:
        data = await bot.http.request("GET", f"/guilds/{guild_id}/auto-moderation/rules")
        return [cls(item, bot=bot) for item in data]

    @classmethod
    async def create_keyword_rule(
        cls,
        bot: Any,
        guild_id: str,
        name: str,
        keywords: List[str],
        *,
        regex_patterns: Optional[List[str]] = None,
        allow_list: Optional[List[str]] = None,
        alert_channel_id: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
        custom_message: Optional[str] = None,
        exempt_roles: Optional[List[str]] = None,
        exempt_channels: Optional[List[str]] = None,
        reason: Optional[str] = None,
    ) -> "AutoModRule":
        actions: List[Dict[str, Any]] = [
            {
                "type": int(AutoModActionType.BLOCK_MESSAGE),
                "metadata": {"custom_message": custom_message} if custom_message else {},
            }
        ]
        if alert_channel_id:
            actions.append(
                {
                    "type": int(AutoModActionType.SEND_ALERT_MESSAGE),
                    "metadata": {"channel_id": str(alert_channel_id)},
                }
            )
        if timeout_seconds and timeout_seconds > 0:
            actions.append(
                {
                    "type": int(AutoModActionType.TIMEOUT),
                    "metadata": {"duration_seconds": min(2419200, int(timeout_seconds))},
                }
            )

        payload = {
            "name": name,
            "event_type": 1,
            "trigger_type": int(AutoModTriggerType.KEYWORD),
            "trigger_metadata": {
                "keyword_filter": keywords,
                "regex_patterns": regex_patterns or [],
                "allow_list": allow_list or [],
            },
            "actions": actions,
            "enabled": True,
            "exempt_roles": exempt_roles or [],
            "exempt_channels": exempt_channels or [],
        }
        data = await bot.http.request(
            "POST", f"/guilds/{guild_id}/auto-moderation/rules", json_data=payload, reason=reason
        )
        return cls(data, bot=bot)

    @classmethod
    async def create_mention_spam_rule(
        cls,
        bot: Any,
        guild_id: str,
        name: str,
        mention_limit: int = 5,
        *,
        raid_protection_enabled: bool = True,
        timeout_seconds: int = 60,
        reason: Optional[str] = None,
    ) -> "AutoModRule":
        actions: List[Dict[str, Any]] = [
            {"type": int(AutoModActionType.BLOCK_MESSAGE), "metadata": {}}
        ]
        if timeout_seconds > 0:
            actions.append(
                {
                    "type": int(AutoModActionType.TIMEOUT),
                    "metadata": {"duration_seconds": min(2419200, int(timeout_seconds))},
                }
            )
        payload = {
            "name": name,
            "event_type": 1,
            "trigger_type": int(AutoModTriggerType.MENTION_SPAM),
            "trigger_metadata": {
                "mention_total_limit": min(50, max(1, int(mention_limit))),
                "mention_raid_protection_enabled": bool(raid_protection_enabled),
            },
            "actions": actions,
            "enabled": True,
        }
        data = await bot.http.request(
            "POST", f"/guilds/{guild_id}/auto-moderation/rules", json_data=payload, reason=reason
        )
        return cls(data, bot=bot)

    async def delete(self, reason: Optional[str] = None) -> bool:
        await self.bot.http.request(
            "DELETE",
            f"/guilds/{self.guild_id}/auto-moderation/rules/{self.id}",
            reason=reason,
        )
        return True
