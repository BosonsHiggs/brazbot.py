"""
Channel models for Discord API v10 (Channel, TextChannel, VoiceChannel, StageChannel,
CategoryChannel, ForumChannel, MediaChannel, DMChannel).
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional, Union

import aiohttp

from brazbot.snowflake import Snowflake
from brazbot.voiceclient import VoiceClient

logger = logging.getLogger(__name__)


class Channel:
    """Base class for all Discord channels (API v10)."""

    def __init__(
        self,
        data: Dict[str, Any],
        bot: Any = None,
        guild_id: Optional[str] = None,
        channel_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ):
        self._raw = data or {}
        self.bot = bot
        self.id = str(channel_id or data.get("id") or "0")
        self.name = data.get("name", f"channel-{self.id}")
        self.category = data.get("category")
        self.changed_roles = data.get("changed_roles", [])
        self.created_at = (
            Snowflake.to_datetime(self.id)
            if Snowflake.is_valid(self.id)
            else datetime.now(timezone.utc)
        )
        self.guild = data.get("guild")
        self.guild_id = str(guild_id or data.get("guild_id") or "") or None
        self.jump_url = (
            data.get("jump_url")
            or f"https://discord.com/channels/{self.guild_id or '@me'}/{self.id}"
        )
        self.mention = data.get("mention") or f"<#{self.id}>"
        raw_overwrites = data.get("permission_overwrites", [])
        if isinstance(raw_overwrites, list):
            self.overwrites = {str(ov.get("id")): ov for ov in raw_overwrites if isinstance(ov, dict)}
        elif isinstance(raw_overwrites, dict):
            self.overwrites = raw_overwrites
        else:
            self.overwrites = {}
        self.permissions_synced = data.get("permissions_synced", False)
        self.position = data.get("position", 0)
        self.type = data.get("type", 0)
        self.type_channel = "channel"
        self.user_id = user_id
        self.last_message_id = data.get("last_message_id")
        self.flags = data.get("flags", 0)
        self.nsfw = data.get("nsfw", False)
        self.parent_id = data.get("parent_id")
        self.rate_limit_per_user = data.get("rate_limit_per_user", 0)

    def __getitem__(self, key: str) -> Any:
        if key in self._raw:
            return self._raw[key]
        if hasattr(self, key):
            return getattr(self, key)
        raise KeyError(key)

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default

    @classmethod
    async def from_channel_id(
        cls,
        bot: Any,
        guild_id: Optional[str],
        channel_id: str,
        user_id: Optional[str] = None,
    ) -> "Channel":
        """Fetches a channel by ID (using bot cache when available)."""
        cache_key = f"channel_{channel_id}"
        data = bot.get_cache_data(cache_key) if hasattr(bot, "get_cache_data") else None

        if not data:
            if hasattr(bot, "http"):
                data = await bot.http.request("GET", f"/channels/{channel_id}")
            else:
                url = f"https://discord.com/api/v10/channels/{channel_id}"
                headers = {"Authorization": f"Bot {bot.token}"}
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=headers) as response:
                        if response.status == 200:
                            data = await response.json()
                        else:
                            error_text = await response.text()
                            raise Exception(
                                f"Failed to fetch channel data: {response.status} - {error_text}"
                            )
            if hasattr(bot, "set_cache_data") and data:
                bot.set_cache_data(cache_key, data, seconds=120)

        if cls is Channel:
            return channel_factory(data, bot=bot, guild_id=guild_id, user_id=user_id)
        return cls(data, bot, guild_id, channel_id, user_id)

    def get_channel_type(self) -> str:
        return self.type_channel

    def __str__(self) -> str:
        return str(self.name or self.id)

    async def send_message(
        self,
        content: Optional[str] = None,
        embed: Any = None,
        embeds: Optional[List[Any]] = None,
        files: Optional[List[Any]] = None,
        components: Optional[List[Any]] = None,
        ephemeral: bool = False,
        poll: Any = None,
        tts: bool = False,
    ) -> Any:
        """Sends a message to the channel."""
        if not hasattr(self.bot, "message_handler"):
            raise Exception("Bot message handler not available")
        return await self.bot.message_handler.send_message(
            self.id,
            content=content,
            embed=embed,
            embeds=embeds,
            files=files,
            components=components,
            ephemeral=ephemeral,
            poll=poll,
            tts=tts,
        )

    async def send(self, content: Optional[str] = None, **kwargs: Any) -> Any:
        return await self.send_message(content, **kwargs)

    async def clone(self, name: Optional[str] = None, reason: Optional[str] = None) -> "Channel":
        """Clones this channel in the same guild with identical settings and permission overwrites."""
        if not self.guild_id:
            raise ValueError("Cannot clone a channel without guild_id")
        payload = {
            "name": name or self.name,
            "type": self.type,
            "topic": getattr(self, "topic", None),
            "nsfw": self.nsfw,
            "rate_limit_per_user": self.rate_limit_per_user,
            "position": self.position,
            "parent_id": self.parent_id,
            "permission_overwrites": list(self.overwrites.values()),
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        data = await self.bot.http.request(
            "POST", f"/guilds/{self.guild_id}/channels", json_data=payload, reason=reason
        )
        return channel_factory(data, self.bot, self.guild_id)

    async def create_invite(
        self,
        max_age: int = 86400,
        max_uses: int = 0,
        temporary: bool = False,
        unique: bool = True,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Creates an instant invite for this channel."""
        payload = {
            "max_age": max_age,
            "max_uses": max_uses,
            "temporary": temporary,
            "unique": unique,
        }
        return await self.bot.http.request(
            "POST", f"/channels/{self.id}/invites", json_data=payload, reason=reason
        )

    async def delete(self, reason: Optional[str] = None) -> bool:
        """Deletes this channel."""
        await self.bot.http.request("DELETE", f"/channels/{self.id}", reason=reason)
        if hasattr(self.bot, "delete_cache_data"):
            self.bot.delete_cache_data(f"channel_{self.id}")
        return True

    async def invites(self) -> List[Dict[str, Any]]:
        """Lists active invites for this channel."""
        return await self.bot.http.request("GET", f"/channels/{self.id}/invites")

    async def move(
        self,
        position: int,
        parent_id: Optional[str] = None,
        lock_permissions: bool = False,
        reason: Optional[str] = None,
    ) -> "Channel":
        """Moves this channel to a new position or category."""
        payload: Dict[str, Any] = {
            "position": position,
            "lock_permissions": lock_permissions,
        }
        if parent_id is not None:
            payload["parent_id"] = parent_id
        data = await self.bot.http.request(
            "PATCH", f"/channels/{self.id}", json_data=payload, reason=reason
        )
        self.position = data.get("position", self.position)
        self.parent_id = data.get("parent_id", self.parent_id)
        return self

    def overwrites_for(self, member_or_role: Any) -> Optional[Dict[str, Any]]:
        target_id = str(getattr(member_or_role, "id", member_or_role))
        return self.overwrites.get(target_id)

    async def set_permissions(
        self,
        member_or_role: Any,
        allow: Union[str, int] = "0",
        deny: Union[str, int] = "0",
        target_type: Optional[int] = None,
        reason: Optional[str] = None,
    ) -> bool:
        """Sets permission overwrites for a member (type=1) or role (type=0)."""
        target_id = str(getattr(member_or_role, "id", member_or_role))
        if target_type is None:
            target_type = 1 if hasattr(member_or_role, "username") or hasattr(member_or_role, "roles") else 0
        payload = {
            "allow": str(int(allow)),
            "deny": str(int(deny)),
            "type": target_type,
        }
        await self.bot.http.request(
            "PUT",
            f"/channels/{self.id}/permissions/{target_id}",
            json_data=payload,
            reason=reason,
        )
        return True

    async def set_lock(self, locked: bool = True, reason: Optional[str] = None) -> bool:
        """Locks or unlocks message sending for the @everyone role (id = guild_id)."""
        if not self.guild_id:
            return False
        send_messages_bit = 1 << 11
        current = self.overwrites.get(str(self.guild_id), {})
        allow = int(current.get("allow", 0))
        deny = int(current.get("deny", 0))
        if locked:
            allow &= ~send_messages_bit
            deny |= send_messages_bit
        else:
            deny &= ~send_messages_bit
        return await self.set_permissions(
            self.guild_id, allow=str(allow), deny=str(deny), target_type=0, reason=reason
        )

    def channel_type_name(self) -> str:
        channel_types = {
            0: "Text",
            1: "DM",
            2: "Voice",
            3: "Group DM",
            4: "Category",
            5: "Announcement",
            10: "Announcement Thread",
            11: "Public Thread",
            12: "Private Thread",
            13: "Stage",
            14: "Directory",
            15: "Forum",
            16: "Media",
        }
        return channel_types.get(self.type, f"Unknown ({self.type})")


class TextChannel(Channel):
    """Text or Announcement channel in Discord API v10."""

    def __init__(
        self,
        data: Dict[str, Any],
        bot: Any = None,
        guild_id: Optional[str] = None,
        channel_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ):
        super().__init__(data, bot, guild_id, channel_id, user_id)
        self.topic = data.get("topic")
        self.slowmode_delay = data.get("rate_limit_per_user", 0)
        self.default_auto_archive_duration = data.get("default_auto_archive_duration", 1440)
        self.default_thread_slowmode_delay = data.get("default_thread_slowmode_delay", 0)
        self.threads = data.get("threads", [])
        self.members = data.get("members", [])
        self.last_message = None
        self.type_channel = "text"

    @classmethod
    async def from_channel_id(
        cls,
        bot: Any,
        guild_id: Optional[str],
        channel_id: str,
        user_id: Optional[str] = None,
    ) -> "TextChannel":
        ch = await super().from_channel_id(bot, guild_id, channel_id, user_id)
        if isinstance(ch, TextChannel):
            return ch
        return cls(ch._raw, bot, guild_id, channel_id, user_id)

    async def archived_threads(
        self, before: Optional[str] = None, limit: int = 50, private: bool = False
    ) -> Dict[str, Any]:
        visibility = "private" if private else "public"
        params: Dict[str, Any] = {"limit": limit}
        if before:
            params["before"] = before
        return await self.bot.http.request(
            "GET", f"/channels/{self.id}/threads/archived/{visibility}", params=params
        )

    async def create_thread(
        self,
        name: str,
        auto_archive_duration: int = 1440,
        thread_type: int = 11,
        message_id: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        payload = {
            "name": name,
            "auto_archive_duration": auto_archive_duration,
            "type": thread_type,
        }
        endpoint = (
            f"/channels/{self.id}/messages/{message_id}/threads"
            if message_id
            else f"/channels/{self.id}/threads"
        )
        return await self.bot.http.request("POST", endpoint, json_data=payload, reason=reason)

    async def create_webhook(
        self, name: str, avatar: Optional[str] = None, reason: Optional[str] = None
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"name": name}
        if avatar:
            payload["avatar"] = avatar
        return await self.bot.http.request(
            "POST", f"/channels/{self.id}/webhooks", json_data=payload, reason=reason
        )

    async def delete_messages(
        self, message_ids: List[str], reason: Optional[str] = None
    ) -> bool:
        """
        Deletes up to 100 messages in a single bulk-delete API call (`POST /channels/{id}/messages/bulk-delete`).
        Automatically filters out messages older than 14 days so the bulk-delete call never fails with error 50034.
        """
        if not message_ids:
            return True
        cutoff = Snowflake.from_datetime(datetime.now(timezone.utc) - timedelta(days=14, seconds=-30))
        valid_ids = [
            str(m) for m in message_ids if Snowflake.is_valid(m) and Snowflake.parse(m) > cutoff
        ]
        if not valid_ids:
            return False
        if len(valid_ids) == 1:
            await self.bot.http.request(
                "DELETE", f"/channels/{self.id}/messages/{valid_ids[0]}", reason=reason
            )
            return True
        if len(valid_ids) > 100:
            raise ValueError("Cannot bulk delete more than 100 messages at once")
        await self.bot.http.request(
            "POST",
            f"/channels/{self.id}/messages/bulk-delete",
            json_data={"messages": valid_ids},
            reason=reason,
        )
        return True

    async def edit(self, reason: Optional[str] = None, **fields: Any) -> "TextChannel":
        data = await self.bot.http.request(
            "PATCH", f"/channels/{self.id}", json_data=fields, reason=reason
        )
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)
        if hasattr(self.bot, "set_cache_data"):
            self.bot.set_cache_data(f"channel_{self.id}", data, seconds=120)
        return self

    async def set_slowmode(self, seconds: int, reason: Optional[str] = None) -> "TextChannel":
        """Sets channel slowmode delay (0 to 21600 seconds)."""
        seconds = max(0, min(21600, int(seconds)))
        return await self.edit(rate_limit_per_user=seconds, reason=reason)

    async def fetch_message(self, message_id: str) -> Dict[str, Any]:
        return await self.bot.http.request("GET", f"/channels/{self.id}/messages/{message_id}")

    async def follow(
        self, webhook_channel_id: str, reason: Optional[str] = None
    ) -> Dict[str, Any]:
        if self.type != 5:
            raise ValueError("Can only follow announcement channels (type=5)")
        return await self.bot.http.request(
            "POST",
            f"/channels/{self.id}/followers",
            json_data={"webhook_channel_id": str(webhook_channel_id)},
            reason=reason,
        )

    def get_partial_message(self, message_id: str) -> Dict[str, str]:
        return {"id": str(message_id), "channel_id": self.id}

    async def get_thread(self, thread_id: str) -> Any:
        from brazbot.threads import Thread
        return await Thread.from_thread_id(self.bot, self.guild_id, thread_id)

    async def history(
        self,
        limit: int = 100,
        before: Optional[str] = None,
        after: Optional[str] = None,
        around: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"limit": min(max(1, limit), 100)}
        if before:
            params["before"] = before
        if after:
            params["after"] = after
        if around:
            params["around"] = around
        return await self.bot.http.request("GET", f"/channels/{self.id}/messages", params=params)

    def is_news(self) -> bool:
        return self.type == 5

    def is_nsfw(self) -> bool:
        return bool(self.nsfw)

    async def pins(self) -> List[Dict[str, Any]]:
        return await self.bot.http.request("GET", f"/channels/{self.id}/pins")

    async def purge(
        self,
        limit: int = 100,
        check: Optional[Callable[[Dict[str, Any]], bool]] = None,
        before: Optional[str] = None,
        after: Optional[str] = None,
        around: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Purges up to `limit` messages (even >100 across multiple pages) matching `check`
        using batched `bulk-delete` requests (100 messages per API call) without hammering the API.
        """
        collected: List[Dict[str, Any]] = []
        cursor_before = before
        remaining_to_scan = max(1, int(limit))
        cutoff = Snowflake.from_datetime(datetime.now(timezone.utc) - timedelta(days=14, seconds=-30))

        while remaining_to_scan > 0:
            fetch_size = min(100, remaining_to_scan)
            page = await self.history(
                limit=fetch_size, before=cursor_before, after=after, around=around
            )
            if not page:
                break

            for msg in page:
                msg_id = msg.get("id")
                if msg_id and Snowflake.is_valid(msg_id) and Snowflake.parse(msg_id) <= cutoff:
                    # Reached messages older than 14 days (cannot be bulk-deleted)
                    remaining_to_scan = 0
                    break
                if check is None or check(msg):
                    collected.append(msg)

            cursor_before = page[-1].get("id")
            remaining_to_scan -= len(page)
            if len(page) < fetch_size:
                break

        if collected:
            for i in range(0, len(collected), 100):
                batch = collected[i : i + 100]
                await self.delete_messages([m["id"] for m in batch], reason=reason)
        return collected

    async def clean_all_messages(
        self,
        strategy: str = "clone",
        max_batches: int = 20,
        reason: Optional[str] = None,
    ) -> Union["TextChannel", int]:
        """
        Wipes all messages in the channel without hammering the API:
        - `strategy='clone'`: Clones the channel and deletes the old one in just 2 API calls total!
          Returns the newly created `TextChannel`.
        - `strategy='batch'`: Paginates and bulk-deletes up to `max_batches * 100` messages (1 API call per 100 messages).
          Returns the number of deleted messages.
        """
        if strategy == "clone":
            new_channel = await self.clone(name=self.name, reason=reason or "Channel clean_all (clone)")
            await self.delete(reason=reason or "Channel clean_all (delete old)")
            return new_channel  # type: ignore[return-value]

        deleted = await self.purge(limit=max_batches * 100, reason=reason)
        return len(deleted)

    async def trigger_typing(self) -> bool:
        await self.bot.http.request("POST", f"/channels/{self.id}/typing")
        return True

    async def webhooks(self) -> List[Dict[str, Any]]:
        return await self.bot.http.request("GET", f"/channels/{self.id}/webhooks")


class VoiceChannel(Channel):
    """Voice channel in Discord API v10 with full support for VoiceClient, Status, and Soundboard."""

    def __init__(
        self,
        data: Dict[str, Any],
        bot: Any = None,
        guild_id: Optional[str] = None,
        channel_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ):
        super().__init__(data, bot, guild_id, channel_id, user_id)
        self.bitrate = data.get("bitrate", 64000)
        self.user_limit = data.get("user_limit", 0)
        self.rtc_region = data.get("rtc_region")
        self.video_quality_mode = data.get("video_quality_mode", 1)
        self.voice_states: List[Dict[str, Any]] = []
        self._voice_client: Optional[VoiceClient] = None
        self.type_channel = "voice"

    @property
    def voice_client(self) -> Optional[VoiceClient]:
        if self._voice_client and self._voice_client.is_connected():
            return self._voice_client
        if hasattr(self.bot, "voice_clients") and self.guild_id in self.bot.voice_clients:
            vc = self.bot.voice_clients[self.guild_id]
            if vc.channel.id == self.id:
                return vc
        return self._voice_client

    @classmethod
    async def from_channel_id(
        cls,
        bot: Any,
        guild_id: Optional[str],
        channel_id: str,
        user_id: Optional[str] = None,
    ) -> "VoiceChannel":
        ch = await super().from_channel_id(bot, guild_id, channel_id, user_id)
        if isinstance(ch, VoiceChannel):
            return ch
        return cls(ch._raw, bot, guild_id, channel_id, user_id)

    async def connect(self, self_mute: bool = False, self_deaf: bool = False) -> VoiceClient:
        """Connects the bot to this voice channel."""
        if not self.bot:
            raise Exception("Bot instance not available")
        if self._voice_client and self._voice_client.is_connected():
            return self._voice_client

        self._voice_client = VoiceClient(self.bot, self)
        await self._voice_client.connect(self_mute=self_mute, self_deaf=self_deaf)
        return self._voice_client

    async def disconnect(self) -> None:
        """Disconnects the bot from this voice channel."""
        if self._voice_client:
            await self._voice_client.disconnect()
            self._voice_client = None

    async def get_voice_states(self) -> List[Dict[str, Any]]:
        if hasattr(self.bot, "voice_states") and self.guild_id in self.bot.voice_states:
            guild_vs = self.bot.voice_states[self.guild_id]
            return [vs for vs in guild_vs.values() if str(vs.get("channel_id")) == self.id]
        return self.voice_states

    def is_full(self) -> bool:
        return self.user_limit > 0 and len(self.voice_states) >= self.user_limit

    async def move_member(self, member_id: str, reason: Optional[str] = None) -> bool:
        await self.bot.http.request(
            "PATCH",
            f"/guilds/{self.guild_id}/members/{member_id}",
            json_data={"channel_id": self.id},
            reason=reason,
        )
        return True

    async def set_voice_status(self, status: Optional[str] = None) -> bool:
        """
        Sets the custom status text of the voice channel (`PUT /channels/{channel.id}/voice-status` - API v10).
        """
        await self.bot.http.request(
            "PUT",
            f"/channels/{self.id}/voice-status",
            json_data={"status": status or ""},
        )
        return True

    async def set_status(self, status: Union[bool, str]) -> bool:
        if isinstance(status, str):
            return await self.set_voice_status(status)
        return True

    async def send_soundboard_sound(
        self, sound_id: str, source_guild_id: Optional[str] = None
    ) -> bool:
        """Plays a Soundboard sound effect in this voice channel (bot must be connected to the channel)."""
        payload: Dict[str, Any] = {"sound_id": str(sound_id)}
        if source_guild_id:
            payload["source_guild_id"] = str(source_guild_id)
        await self.bot.http.request(
            "POST", f"/channels/{self.id}/send-soundboard-sound", json_data=payload
        )
        return True


class StageChannel(VoiceChannel):
    """Stage channel (type 13) in Discord API v10."""

    def __init__(
        self,
        data: Dict[str, Any],
        bot: Any = None,
        guild_id: Optional[str] = None,
        channel_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ):
        super().__init__(data, bot, guild_id, channel_id, user_id)
        self.type_channel = "stage"
        self.topic = data.get("topic")
        self.privacy_level = data.get("privacy_level", 2)

    async def create_instance(
        self,
        topic: str,
        privacy_level: int = 2,
        send_notification: bool = False,
        guild_scheduled_event_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "channel_id": self.id,
            "topic": topic,
            "privacy_level": privacy_level,
            "send_start_notification": send_notification,
        }
        if guild_scheduled_event_id:
            payload["guild_scheduled_event_id"] = str(guild_scheduled_event_id)
        return await self.bot.http.request("POST", "/stage-instances", json_data=payload)

    async def get_instance(self) -> Optional[Dict[str, Any]]:
        return await self.bot.http.request(
            "GET", f"/stage-instances/{self.id}", raise_on_error=False
        )

    async def edit_instance(
        self, topic: Optional[str] = None, privacy_level: Optional[int] = None
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {}
        if topic is not None:
            payload["topic"] = topic
        if privacy_level is not None:
            payload["privacy_level"] = privacy_level
        return await self.bot.http.request(
            "PATCH", f"/stage-instances/{self.id}", json_data=payload
        )

    async def delete_instance(self) -> bool:
        await self.bot.http.request("DELETE", f"/stage-instances/{self.id}")
        return True


class CategoryChannel(Channel):
    """Category channel (type 4) in Discord API v10."""

    def __init__(
        self,
        data: Dict[str, Any],
        bot: Any = None,
        guild_id: Optional[str] = None,
        channel_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ):
        super().__init__(data, bot, guild_id, channel_id, user_id)
        self.type_channel = "category"
        self.channels: List[Dict[str, Any]] = []

    async def create_text_channel(self, name: str, **kwargs: Any) -> Dict[str, Any]:
        payload = {"name": name, "type": 0, "parent_id": self.id, **kwargs}
        return await self.bot.http.request(
            "POST", f"/guilds/{self.guild_id}/channels", json_data=payload
        )

    async def create_voice_channel(self, name: str, **kwargs: Any) -> Dict[str, Any]:
        payload = {"name": name, "type": 2, "parent_id": self.id, **kwargs}
        return await self.bot.http.request(
            "POST", f"/guilds/{self.guild_id}/channels", json_data=payload
        )

    async def create_stage_channel(self, name: str, **kwargs: Any) -> Dict[str, Any]:
        payload = {"name": name, "type": 13, "parent_id": self.id, **kwargs}
        return await self.bot.http.request(
            "POST", f"/guilds/{self.guild_id}/channels", json_data=payload
        )

    async def get_channels(self) -> List[Dict[str, Any]]:
        all_channels = await self.bot.http.request("GET", f"/guilds/{self.guild_id}/channels")
        self.channels = [c for c in all_channels if c.get("parent_id") == self.id]
        return self.channels


class ForumChannel(TextChannel):
    """Forum channel (type 15) in Discord API v10."""

    def __init__(
        self,
        data: Dict[str, Any],
        bot: Any = None,
        guild_id: Optional[str] = None,
        channel_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ):
        super().__init__(data, bot, guild_id, channel_id, user_id)
        self.type_channel = "forum"
        self.available_tags = data.get("available_tags", [])
        self.default_reaction_emoji = data.get("default_reaction_emoji")
        self.default_thread_rate_limit_per_user = data.get("default_thread_rate_limit_per_user", 0)
        self.default_sort_order = data.get("default_sort_order", 0)
        self.default_forum_layout = data.get("default_forum_layout", 0)

    async def create_post(
        self,
        name: str,
        content: str,
        tags: Optional[List[str]] = None,
        embed: Optional[Dict[str, Any]] = None,
        files: Optional[List[Any]] = None,
    ) -> Dict[str, Any]:
        message_payload: Dict[str, Any] = {"content": content}
        if embed:
            message_payload["embeds"] = [embed]
        payload = {
            "name": name,
            "message": message_payload,
            "applied_tags": tags or [],
        }
        return await self.bot.http.request(
            "POST", f"/channels/{self.id}/threads", json_data=payload, files=files
        )


class MediaChannel(ForumChannel):
    """Media channel (type 16) in Discord API v10."""

    def __init__(
        self,
        data: Dict[str, Any],
        bot: Any = None,
        guild_id: Optional[str] = None,
        channel_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ):
        super().__init__(data, bot, guild_id, channel_id, user_id)
        self.type_channel = "media"


class DMChannel(TextChannel):
    """Direct Message channel (type 1 / type 3) in Discord API v10."""

    def __init__(
        self,
        data: Dict[str, Any],
        bot: Any = None,
        guild_id: Optional[str] = None,
        channel_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ):
        super().__init__(data, bot, guild_id, channel_id, user_id)
        self.type_channel = "dm"
        self.recipients = data.get("recipients", [])


def channel_factory(
    data: Dict[str, Any],
    bot: Any = None,
    guild_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Channel:
    """Instantiates the specific Channel subclass matching the Discord API v10 `type` field."""
    ch_type = data.get("type", 0)
    if ch_type in (0, 5):
        return TextChannel(data, bot=bot, guild_id=guild_id, user_id=user_id)
    if ch_type in (1, 3):
        return DMChannel(data, bot=bot, guild_id=guild_id, user_id=user_id)
    if ch_type == 2:
        return VoiceChannel(data, bot=bot, guild_id=guild_id, user_id=user_id)
    if ch_type == 4:
        return CategoryChannel(data, bot=bot, guild_id=guild_id, user_id=user_id)
    if ch_type == 13:
        return StageChannel(data, bot=bot, guild_id=guild_id, user_id=user_id)
    if ch_type == 15:
        return ForumChannel(data, bot=bot, guild_id=guild_id, user_id=user_id)
    if ch_type == 16:
        return MediaChannel(data, bot=bot, guild_id=guild_id, user_id=user_id)
    return Channel(data, bot=bot, guild_id=guild_id, user_id=user_id)
