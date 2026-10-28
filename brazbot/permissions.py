"""
Sistema de Permissões e Intents nativos da API v10 do Discord.
"""

from typing import Union, List, Dict, Iterable

# Mapeamento oficial de Gateway Intents (Discord API v10)
INTENTS: Dict[str, int] = {
    "GUILDS": 1 << 0,
    "GUILD_MEMBERS": 1 << 1,
    "GUILD_MODERATION": 1 << 2,
    "GUILD_BANS": 1 << 2,  # Alias de compatibilidade
    "GUILD_EXPRESSIONS": 1 << 3,
    "GUILD_EMOJIS_AND_STICKERS": 1 << 3,  # Alias de compatibilidade
    "GUILD_INTEGRATIONS": 1 << 4,
    "GUILD_WEBHOOKS": 1 << 5,
    "GUILD_INVITES": 1 << 6,
    "GUILD_VOICE_STATES": 1 << 7,
    "GUILD_PRESENCES": 1 << 8,
    "GUILD_MESSAGES": 1 << 9,
    "GUILD_MESSAGE_REACTIONS": 1 << 10,
    "GUILD_MESSAGE_TYPING": 1 << 11,
    "DIRECT_MESSAGES": 1 << 12,
    "DIRECT_MESSAGE_REACTIONS": 1 << 13,
    "DIRECT_MESSAGE_TYPING": 1 << 14,
    "MESSAGE_CONTENT": 1 << 15,
    "GUILD_SCHEDULED_EVENTS": 1 << 16,
    "AUTO_MODERATION_CONFIGURATION": 1 << 20,
    "AUTO_MODERATION_EXECUTION": 1 << 21,
    "GUILD_MESSAGE_POLLS": 1 << 24,
    "DIRECT_MESSAGE_POLLS": 1 << 25,
}

PRIVILEGED_INTENTS = {"GUILD_MEMBERS", "GUILD_PRESENCES", "MESSAGE_CONTENT"}


class Intents:
    """
    Construtor e gerenciador de Gateway Intents da API v10 do Discord.
    Pode ser passado como inteiro, lista de strings ou instância de `Intents`.
    """

    def __init__(self, value: int = 0, **kwargs: bool):
        self.value = int(value)
        for name, enabled in kwargs.items():
            upper = name.upper()
            if upper in INTENTS:
                if enabled:
                    self.value |= INTENTS[upper]
                else:
                    self.value &= ~INTENTS[upper]

    @classmethod
    def default(cls) -> "Intents":
        """Retorna todas as intents padrão (não privilegiadas)."""
        val = 0
        for name, bit in INTENTS.items():
            if name not in PRIVILEGED_INTENTS:
                val |= bit
        return cls(val)

    @classmethod
    def all(cls) -> "Intents":
        """Retorna todas as intents disponíveis na API v10 (incluindo privilegiadas)."""
        val = 0
        for bit in INTENTS.values():
            val |= bit
        return cls(val)

    @classmethod
    def none(cls) -> "Intents":
        """Retorna intents zeradas."""
        return cls(0)

    @classmethod
    def resolve(cls, intents: Union[None, int, "Intents", Iterable[str]]) -> int:
        """Converte qualquer representação de intents em um bitfield inteiro."""
        if intents is None:
            return int(cls.default())
        if isinstance(intents, Intents):
            return intents.value
        if isinstance(intents, int):
            return intents
        if isinstance(intents, (list, tuple, set)):
            total = 0
            for item in intents:
                key = str(item).upper().strip()
                if key in INTENTS:
                    total |= INTENTS[key]
            return total
        return int(cls.default())

    def __int__(self) -> int:
        return self.value

    def __or__(self, other: Union["Intents", int]) -> "Intents":
        return Intents(self.value | int(other))

    def __repr__(self) -> str:
        return f"Intents(value={self.value})"


# Flags completas de permissão da API v10 do Discord
PERMISSION_FLAGS: Dict[str, int] = {
    "create_instant_invite": 1 << 0,
    "kick_members": 1 << 1,
    "ban_members": 1 << 2,
    "administrator": 1 << 3,
    "manage_channels": 1 << 4,
    "manage_guild": 1 << 5,
    "add_reactions": 1 << 6,
    "view_audit_log": 1 << 7,
    "priority_speaker": 1 << 8,
    "stream": 1 << 9,
    "view_channel": 1 << 10,
    "read_messages": 1 << 10,
    "send_messages": 1 << 11,
    "send_tts_messages": 1 << 12,
    "manage_messages": 1 << 13,
    "embed_links": 1 << 14,
    "attach_files": 1 << 15,
    "read_message_history": 1 << 16,
    "mention_everyone": 1 << 17,
    "use_external_emojis": 1 << 18,
    "view_guild_insights": 1 << 19,
    "connect": 1 << 20,
    "speak": 1 << 21,
    "mute_members": 1 << 22,
    "deafen_members": 1 << 23,
    "move_members": 1 << 24,
    "use_vad": 1 << 25,
    "change_nickname": 1 << 26,
    "manage_nicknames": 1 << 27,
    "manage_roles": 1 << 28,
    "manage_webhooks": 1 << 29,
    "manage_expressions": 1 << 30,
    "manage_emojis_and_stickers": 1 << 30,
    "use_application_commands": 1 << 31,
    "request_to_speak": 1 << 32,
    "manage_events": 1 << 33,
    "manage_threads": 1 << 34,
    "create_public_threads": 1 << 35,
    "create_private_threads": 1 << 36,
    "use_external_stickers": 1 << 37,
    "send_messages_in_threads": 1 << 38,
    "use_embedded_activities": 1 << 39,
    "moderate_members": 1 << 40,
    "view_creator_monetization_analytics": 1 << 41,
    "use_soundboard": 1 << 42,
    "create_guild_expressions": 1 << 43,
    "create_events": 1 << 44,
    "use_external_sounds": 1 << 45,
    "send_voice_messages": 1 << 46,
    "send_polls": 1 << 49,
    "use_external_apps": 1 << 50,
}


class Permissions:
    """
    Representa e calcula o conjunto de permissões de um membro ou cargo na API v10 do Discord.
    """

    def __init__(self, value: Union[int, str] = 0, **kwargs: bool):
        self.value = int(value) if value is not None else 0
        for perm_name, enabled in kwargs.items():
            key = perm_name.lower()
            if key in PERMISSION_FLAGS:
                if enabled:
                    self.value |= PERMISSION_FLAGS[key]
                else:
                    self.value &= ~PERMISSION_FLAGS[key]
            else:
                raise ValueError(f"Permissão desconhecida: {perm_name}")

    @classmethod
    def all(cls) -> "Permissions":
        val = 0
        for bit in PERMISSION_FLAGS.values():
            val |= bit
        return cls(val)

    @classmethod
    def none(cls) -> "Permissions":
        return cls(0)

    def has(self, **perms: bool) -> bool:
        """Verifica se todas as permissões especificadas são satisfeitas (ou se possui administrator)."""
        if self.value & PERMISSION_FLAGS["administrator"]:
            return True
        for perm_name, expected in perms.items():
            key = perm_name.lower()
            if key not in PERMISSION_FLAGS:
                raise ValueError(f"Permissão desconhecida: {perm_name}")
            has_bit = bool(self.value & PERMISSION_FLAGS[key])
            if has_bit != expected:
                return False
        return True

    def missing(self, **perms: bool) -> List[str]:
        """Retorna a lista de permissões ausentes."""
        if self.value & PERMISSION_FLAGS["administrator"]:
            return []
        missing_list: List[str] = []
        for perm_name, expected in perms.items():
            key = perm_name.lower()
            if key in PERMISSION_FLAGS:
                has_bit = bool(self.value & PERMISSION_FLAGS[key])
                if has_bit != expected:
                    missing_list.append(key)
        return missing_list

    def __getattr__(self, name: str) -> bool:
        key = name.lower()
        if key in PERMISSION_FLAGS:
            return bool(self.value & PERMISSION_FLAGS[key])
        raise AttributeError(f"'Permissions' object has no attribute '{name}'")

    def __int__(self) -> int:
        return self.value

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"Permissions({self.value})"
