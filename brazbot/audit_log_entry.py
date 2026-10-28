"""
Modelo de Entrada de Log de Auditoria (`AuditLogEntry`) da API v10 do Discord.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from brazbot.snowflake import Snowflake


class AuditLogEntry:
    """Representa um registro do Log de Auditoria de um servidor na API v10 do Discord."""

    def __init__(
        self,
        *,
        users: Dict[str, Any],
        integrations: Any,
        app_commands: Any,
        automod_rules: Any,
        webhooks: Any,
        data: Dict[str, Any],
        guild: str,
        bot: Any,
    ):
        self.action = data.get("action_type") if data.get("action_type") else -10000
        changes_raw = data.get("changes")
        self.changes: List[Dict[str, Any]] = (
            changes_raw if isinstance(changes_raw, list) else []
        )
        self.after = self.changes[0].get("new_value") if self.changes else None
        self.before = self.changes[0].get("old_value") if self.changes else None
        self.category = data.get("target_type")
        self.id = str(data.get("id") or "0")
        self.created_at = (
            Snowflake.to_datetime(self.id)
            if Snowflake.is_valid(self.id)
            else datetime.now(timezone.utc)
        )
        self.extra = data.get("options")
        self.guild = guild
        self.reason = data.get("reason")
        self.target = data.get("target_id")
        self.user_id = data.get("user_id")
        self.user = users.get(str(self.user_id), {"id": self.user_id, "username": "Unknown"})
        self.bot = bot

    @classmethod
    async def from_guild_id(
        cls, bot: Any, guild_id: str, limit: int = 50
    ) -> List["AuditLogEntry"]:
        cache_key = f"audit_log_{guild_id}"
        data = bot.get_cache_data(cache_key) if hasattr(bot, "get_cache_data") else None

        if not data:
            data = await bot.http.request(
                "GET", f"/guilds/{guild_id}/audit-logs", params={"limit": limit}
            )
            if hasattr(bot, "set_cache_data") and data:
                bot.set_cache_data(cache_key, data, seconds=10)

        users = {str(u["id"]): u for u in data.get("users", []) if "id" in u}
        entries = data.get("audit_log_entries", [])
        return [
            cls(
                users=users,
                integrations=data.get("integrations", {}),
                app_commands=data.get("application_commands", {}),
                automod_rules=data.get("auto_moderation_rules", {}),
                webhooks=data.get("webhooks", {}),
                data=entry,
                guild=guild_id,
                bot=bot,
            )
            for entry in entries
        ]

    def __str__(self) -> str:
        return f"AuditLogEntry(action={self.action}, user={self.user}, target={self.target})"
