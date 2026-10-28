"""
brazbot.py — Biblioteca brasileira nativa e assíncrona para criação de bots na API v10 e Voice Gateway v8 do Discord.
Repositório oficial: https://github.com/BosonsHiggs/brazbot.py
"""

from brazbot.attachments import Attachment
from brazbot.audit_log_entry import AuditLogEntry
from brazbot.automod import (
    AutoModActionType,
    AutoModKeywordPresetType,
    AutoModRule,
    AutoModTriggerType,
)
from brazbot.bot import Bot, DiscordBot
from brazbot.buttons import ActionRow, Button, ButtonStyle, View
from brazbot.cache import Cache
from brazbot.channels import (
    CategoryChannel,
    Channel,
    DMChannel,
    ForumChannel,
    MediaChannel,
    StageChannel,
    TextChannel,
    VoiceChannel,
    channel_factory,
)
from brazbot.cogs import Cog
from brazbot.cogs_builtin import FunCog, ModerationCog, MusicCog, UtilityCog
from brazbot.commands import CommandContext, CommandHandler, command
from brazbot.decorators import (
    cooldown,
    describe,
    guild_only,
    has_permissions,
    has_role,
    in_voice_channel,
    is_admin,
    is_owner,
    rate_limit,
    sync_commands,
    sync_slash_commands,
    sync_test_servers,
    tasks,
)
from brazbot.dropdowns import (
    ChannelSelect,
    Dropdown,
    DropdownOption,
    MentionableSelect,
    RoleSelect,
    UserSelect,
)
from brazbot.embed import Embed, EmbedColor
from brazbot.errors import (
    BadArgument,
    BadRequest,
    BotMissingPermissions,
    BrazbotError,
    CheckFailure,
    CommandError,
    CommandNotFound,
    CooldownError,
    DiscordServerError,
    Forbidden,
    GatewayError,
    HTTPException,
    MissingPermissions,
    MissingRequiredArgument,
    NotFound,
    NotOwner,
    OpusError,
    RateLimited,
    Unauthorized,
    VoiceConnectionError,
)
from brazbot.events import EventHandler
from brazbot.eventstype import EventTypes
from brazbot.file import File
from brazbot.forms import Form, FormField
from brazbot.greedy_union import Greedy
from brazbot.guilds import Guild
from brazbot.http import API_VERSION, BASE_URL, HTTPClient, LIBRARY_VERSION, USER_AGENT
from brazbot.member import Member, VoiceState
from brazbot.message_handler import MessageHandler
from brazbot.messages import Message, PartialMessage
from brazbot.music import AUDIO_FILTERS, GuildMusicPlayer, Track, YTDLSource
from brazbot.permissions import INTENTS, Intents, Permissions
from brazbot.polls import Poll, PollAnswer, PollMedia
from brazbot.responses import InteractionResponse
from brazbot.roles import Role
from brazbot.scheduled_events import (
    ScheduledEvent,
    ScheduledEventEntityType,
    ScheduledEventStatus,
)
from brazbot.snowflake import Snowflake
from brazbot.soundboard import Soundboard, SoundboardSound
from brazbot.subgroups import SubCommandGroup
from brazbot.threads import Thread
from brazbot.utils import (
    chunk_list,
    create_embed,
    create_error_embed,
    create_success_embed,
    format_command_response,
    format_discord_timestamp,
    generate_list,
    generate_unique_id,
)
from brazbot.voiceclient import (
    AudioSource,
    FFmpegAudioSource,
    OggOpusDemuxer,
    OpusDecoder,
    OpusEncoder,
    PCMAudioSource,
    UDPVoiceConnection,
    VoiceClient,
    VoiceWebSocket,
)
from brazbot.webhooks import Webhook

__version__ = LIBRARY_VERSION
__author__ = "Aril Ogai (BosonsHiggs)"
__license__ = "MIT"

__all__ = [
    "__version__",
    "API_VERSION",
    "BASE_URL",
    "USER_AGENT",
    "Bot",
    "DiscordBot",
    "HTTPClient",
    "Cache",
    "Snowflake",
    "Intents",
    "INTENTS",
    "Permissions",
    "CommandContext",
    "CommandHandler",
    "command",
    "Cog",
    "MusicCog",
    "ModerationCog",
    "UtilityCog",
    "FunCog",
    "SubCommandGroup",
    "EventHandler",
    "EventTypes",
    "Channel",
    "TextChannel",
    "VoiceChannel",
    "StageChannel",
    "CategoryChannel",
    "ForumChannel",
    "MediaChannel",
    "DMChannel",
    "channel_factory",
    "Guild",
    "Member",
    "VoiceState",
    "Role",
    "Thread",
    "Message",
    "PartialMessage",
    "MessageHandler",
    "Embed",
    "EmbedColor",
    "Button",
    "ButtonStyle",
    "ActionRow",
    "View",
    "Dropdown",
    "DropdownOption",
    "UserSelect",
    "RoleSelect",
    "MentionableSelect",
    "ChannelSelect",
    "Form",
    "FormField",
    "Poll",
    "PollAnswer",
    "PollMedia",
    "AutoModRule",
    "AutoModTriggerType",
    "AutoModActionType",
    "AutoModKeywordPresetType",
    "Soundboard",
    "SoundboardSound",
    "ScheduledEvent",
    "ScheduledEventEntityType",
    "ScheduledEventStatus",
    "Webhook",
    "Attachment",
    "File",
    "AuditLogEntry",
    "InteractionResponse",
    "Greedy",
    "VoiceClient",
    "VoiceWebSocket",
    "UDPVoiceConnection",
    "AudioSource",
    "FFmpegAudioSource",
    "PCMAudioSource",
    "OpusEncoder",
    "OpusDecoder",
    "OggOpusDemuxer",
    "YTDLSource",
    "GuildMusicPlayer",
    "Track",
    "AUDIO_FILTERS",
    "tasks",
    "sync_slash_commands",
    "sync_commands",
    "sync_test_servers",
    "describe",
    "is_admin",
    "is_owner",
    "has_role",
    "has_permissions",
    "guild_only",
    "in_voice_channel",
    "rate_limit",
    "cooldown",
    "create_embed",
    "create_error_embed",
    "create_success_embed",
    "format_command_response",
    "format_discord_timestamp",
    "generate_unique_id",
    "generate_list",
    "chunk_list",
    "BrazbotError",
    "HTTPException",
    "BadRequest",
    "Unauthorized",
    "Forbidden",
    "NotFound",
    "RateLimited",
    "DiscordServerError",
    "GatewayError",
    "VoiceConnectionError",
    "OpusError",
    "CommandError",
    "CommandNotFound",
    "MissingRequiredArgument",
    "BadArgument",
    "CheckFailure",
    "MissingPermissions",
    "BotMissingPermissions",
    "NotOwner",
    "CooldownError",
]
