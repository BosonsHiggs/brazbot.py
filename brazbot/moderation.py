"""
Advanced Server Moderation Engine for brazbot.py (Discord API v10).
Includes:
- `BatchDeleteQueue`: Coalesces message deletions across a short time window (e.g. 0.5s) and executes
  batched `POST /channels/{id}/messages/bulk-delete` (up to 100 messages per single API call) so flood/raid
  waves never hammer the Discord API with individual DELETE calls.
- `ProfanityFilter`: Anti-evasion profanity and slur detector with Unicode normalization, zero-width stripping,
  leetspeak translation, character-stretch collapsing, and Discord AutoMod v10 synchronization.
- `AntiFloodManager`: Sliding-window flood, duplicate-message, mass-mention, and caps-spam detector with
  automatic batch message removal and escalating punishments (Warning -> Timeout -> Kick/Ban).
- `ModerationGuard`: Unified guard that hooks into `on_message_create` and tracks warnings and moderation stats.
"""

import asyncio
import logging
import re
import time
import unicodedata
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Deque, Dict, Iterable, List, Optional, Set, Tuple

from brazbot.automod import AutoModRule
from brazbot.embed import Embed
from brazbot.member import Member

logger = logging.getLogger(__name__)

DEFAULT_PROFANITY_WORDS: Set[str] = {
    "fuck",
    "shit",
    "bitch",
    "asshole",
    "bastard",
    "motherfucker",
    "dickhead",
    "cunt",
    "retard",
    "nigger",
    "faggot",
    "whore",
    "slut",
}

_LEET_MAP = str.maketrans(
    {
        "@": "a",
        "4": "a",
        "3": "e",
        "1": "i",
        "!": "i",
        "|": "i",
        "0": "o",
        "$": "s",
        "5": "s",
        "7": "t",
        "+": "t",
    }
)

_ZERO_WIDTH_RE = re.compile(r"[​‌‍⁠﻿]")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9\s]+")
_STRETCH_RE = re.compile(r"(.)\1+")


class BatchDeleteQueue:
    """
    Coalesces message deletions per channel into batches of up to 100 IDs and flushes them
    via a single `bulk_delete_messages` call (`POST /channels/{id}/messages/bulk-delete`).
    Prevents API rate-limit exhaustion during message floods or spam raids.
    """

    def __init__(self, bot: Any, flush_interval: float = 0.5):
        self.bot = bot
        self.flush_interval = float(flush_interval)
        self._queues: Dict[str, List[str]] = {}
        self._flush_tasks: Dict[str, asyncio.Task] = {}
        self._locks: Dict[str, asyncio.Lock] = {}

        # Telemetry metrics
        self.total_messages_deleted: int = 0
        self.total_api_calls_used: int = 0

    @property
    def api_calls_saved(self) -> int:
        """Number of HTTP DELETE calls saved by batching into bulk-delete."""
        return max(0, self.total_messages_deleted - self.total_api_calls_used)

    async def enqueue(self, channel_id: str, message_ids: Iterable[str]) -> None:
        """Queues one or more message IDs for coalesced batch deletion in `channel_id`."""
        cid = str(channel_id)
        q = self._queues.setdefault(cid, [])
        for mid in message_ids:
            s_mid = str(mid).strip()
            if s_mid and s_mid not in q:
                q.append(s_mid)

        if len(q) >= 100:
            await self.flush_channel(cid)
        elif cid not in self._flush_tasks or self._flush_tasks[cid].done():
            self._flush_tasks[cid] = asyncio.create_task(self._delayed_flush(cid))

    async def _delayed_flush(self, channel_id: str) -> None:
        await asyncio.sleep(self.flush_interval)
        await self.flush_channel(channel_id)

    async def flush_channel(self, channel_id: str) -> int:
        """Immediately flushes all queued message IDs for `channel_id` in batches of 100."""
        cid = str(channel_id)
        lock = self._locks.setdefault(cid, asyncio.Lock())
        deleted_count = 0

        async with lock:
            pending = self._queues.get(cid, [])
            if not pending:
                return 0
            self._queues[cid] = []

            for i in range(0, len(pending), 100):
                batch = pending[i : i + 100]
                ok = await self.bot.message_handler.bulk_delete_messages(
                    cid, batch, reason="Automated moderation batch delete"
                )
                if ok:
                    deleted_count += len(batch)
                    self.total_messages_deleted += len(batch)
                    self.total_api_calls_used += 1

        return deleted_count


class ProfanityFilter:
    """
    Profanity and obscene word detector with anti-evasion text normalization
    (strips accents, zero-width characters, leetspeak, and character stretching).
    """

    def __init__(self, words: Optional[Iterable[str]] = None):
        self.blocked_words: Set[str] = {
            self.normalize_word(w)
            for w in (words if words is not None else DEFAULT_PROFANITY_WORDS)
            if w and w.strip()
        }

    @staticmethod
    def normalize_word(text: str) -> str:
        text = _ZERO_WIDTH_RE.sub("", text.lower())
        nfkd = unicodedata.normalize("NFKD", text)
        ascii_text = "".join(c for c in nfkd if not unicodedata.combining(c))
        leet_decoded = ascii_text.translate(_LEET_MAP)
        collapsed = _STRETCH_RE.sub(r"\1\1", leet_decoded)
        return _NON_ALNUM_RE.sub("", collapsed).strip()

    @classmethod
    def normalize_message(cls, content: str) -> Tuple[List[str], str]:
        cleaned = _ZERO_WIDTH_RE.sub("", content.lower())
        nfkd = unicodedata.normalize("NFKD", cleaned)
        ascii_text = "".join(c for c in nfkd if not unicodedata.combining(c))
        leet_decoded = ascii_text.translate(_LEET_MAP)
        alnum_spaces = _NON_ALNUM_RE.sub(" ", leet_decoded)
        tokens = [_STRETCH_RE.sub(r"\1", tok) for tok in alnum_spaces.split() if tok]
        compact = "".join(tokens)
        return tokens, compact

    def add_words(self, words: Iterable[str]) -> int:
        added = 0
        for w in words:
            norm = self.normalize_word(w)
            if norm and norm not in self.blocked_words:
                self.blocked_words.add(norm)
                added += 1
        return added

    def remove_words(self, words: Iterable[str]) -> int:
        removed = 0
        for w in words:
            norm = self.normalize_word(w)
            if norm in self.blocked_words:
                self.blocked_words.remove(norm)
                removed += 1
        return removed

    def find_matches(self, content: str) -> List[str]:
        """Returns a list of blocked words detected in `content`."""
        if not content or not self.blocked_words:
            return []
        tokens, compact = self.normalize_message(content)
        token_set = set(tokens)
        matched: List[str] = []
        for bad in self.blocked_words:
            collapsed_bad = _STRETCH_RE.sub(r"\1", bad)
            if bad in token_set or collapsed_bad in token_set:
                matched.append(bad)
            elif len(bad) >= 4 and (bad in compact or collapsed_bad in compact):
                matched.append(bad)
        return matched

    def contains_profanity(self, content: str) -> bool:
        return bool(self.find_matches(content))

    async def sync_to_discord_automod(
        self,
        bot: Any,
        guild_id: str,
        rule_name: str = "Brazbot Profanity Filter",
        timeout_seconds: int = 60,
    ) -> AutoModRule:
        """Synchronizes the current blocked word list with Discord's native AutoMod v10."""
        existing = await AutoModRule.list_rules(bot, guild_id)
        for rule in existing:
            if rule.name == rule_name:
                await rule.delete(reason="Updating Brazbot Profanity Filter")
        keywords = [f"*{w}*" for w in sorted(self.blocked_words)[:100]]
        return await AutoModRule.create_keyword_rule(
            bot,
            guild_id,
            name=rule_name,
            keywords=keywords,
            timeout_seconds=timeout_seconds,
            custom_message="Message blocked by server profanity filter.",
        )


@dataclass
class FloodConfig:
    """Configuration parameters for automatic flood/spam detection."""

    enabled: bool = True
    max_messages: int = 5
    window_seconds: float = 5.0
    max_duplicates: int = 3
    duplicate_window_seconds: float = 15.0
    max_mentions: int = 5
    max_caps_ratio: float = 0.80
    auto_timeout_seconds: int = 300  # 5 minutes default timeout on repeat flood


@dataclass
class UserMessageRecord:
    message_id: str
    timestamp: float
    content_hash: int


class AntiFloodManager:
    """
    Sliding-window anti-flood and spam detector.
    Collects all message IDs from a user's flood burst and hands them to `BatchDeleteQueue`
    so the entire burst is removed in a single `bulk-delete` API call.
    """

    def __init__(self, config: Optional[FloodConfig] = None):
        self.config = config or FloodConfig()
        self._user_history: Dict[Tuple[str, str], Deque[UserMessageRecord]] = {}
        self._last_alert_at: Dict[Tuple[str, str], float] = {}

    def check_message(
        self,
        guild_id: str,
        channel_id: str,
        user_id: str,
        message_id: str,
        content: str,
        mention_count: int = 0,
    ) -> Optional[Tuple[str, List[str]]]:
        """
        Evaluates an incoming message for flood/spam violations.
        Returns `(reason, list_of_message_ids_to_delete)` if a violation occurred, or `None`.
        """
        if not self.config.enabled:
            return None

        now = time.monotonic()
        key = (str(guild_id), str(user_id))
        history = self._user_history.setdefault(key, deque(maxlen=50))

        # Prune entries older than max window
        max_horizon = max(self.config.window_seconds, self.config.duplicate_window_seconds)
        while history and (now - history[0].timestamp) > max_horizon:
            history.popleft()

        norm_content = content.strip().lower()
        c_hash = hash(norm_content) if norm_content else 0
        history.append(UserMessageRecord(str(message_id), now, c_hash))

        # 1. Check Mention Spam
        if mention_count >= self.config.max_mentions:
            return (
                f"Mass mention spam ({mention_count} mentions)",
                [str(message_id)],
            )

        # 2. Check Message Rate Flood (N messages within window_seconds)
        recent_burst = [
            rec.message_id
            for rec in history
            if (now - rec.timestamp) <= self.config.window_seconds
        ]
        if len(recent_burst) >= self.config.max_messages:
            return (
                f"Message flood ({len(recent_burst)} messages in {self.config.window_seconds:.0f}s)",
                recent_burst,
            )

        # 3. Check Duplicate Message Spam
        if norm_content:
            dup_burst = [
                rec.message_id
                for rec in history
                if rec.content_hash == c_hash
                and (now - rec.timestamp) <= self.config.duplicate_window_seconds
            ]
            if len(dup_burst) >= self.config.max_duplicates:
                return (
                    f"Duplicate message spam ({len(dup_burst)} identical messages)",
                    dup_burst,
                )

        # 4. Check Excessive CAPS (for messages >= 16 alphabetic characters)
        alpha_chars = [c for c in content if c.isalpha()]
        if len(alpha_chars) >= 16:
            upper_ratio = sum(1 for c in alpha_chars if c.isupper()) / float(len(alpha_chars))
            if upper_ratio >= self.config.max_caps_ratio:
                return ("Excessive CAPS spam", [str(message_id)])

        return None

    def should_send_alert(self, channel_id: str, user_id: str, cooldown: float = 8.0) -> bool:
        """Debounces channel warning messages so the bot never spams the channel during a flood."""
        now = time.monotonic()
        key = (str(channel_id), str(user_id))
        last = self._last_alert_at.get(key, 0.0)
        if (now - last) >= cooldown:
            self._last_alert_at[key] = now
            return True
        return False


class ModerationGuard:
    """
    Unified server moderation controller combining `BatchDeleteQueue`, `ProfanityFilter`,
    `AntiFloodManager`, and a per-member warning ledger with automatic escalating punishments.
    """

    def __init__(self, bot: Any):
        self.bot = bot
        self.batch_deleter = BatchDeleteQueue(bot, flush_interval=0.5)
        self.profanity = ProfanityFilter()
        self.antiflood = AntiFloodManager()
        self.warnings: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
        self.exempt_role_ids: Set[str] = set()
        self.exempt_user_ids: Set[str] = set()
        self.log_channel_id: Optional[str] = None

        # Statistics
        self.flood_incidents_handled: int = 0
        self.profanity_incidents_handled: int = 0
        self.auto_timeouts_issued: int = 0

    def add_warning(
        self, guild_id: str, user_id: str, moderator_id: str, reason: str
    ) -> int:
        ledger = self.warnings.setdefault((str(guild_id), str(user_id)), [])
        ledger.append(
            {
                "moderator_id": str(moderator_id),
                "reason": reason,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        return len(ledger)

    def get_warnings(self, guild_id: str, user_id: str) -> List[Dict[str, Any]]:
        return list(self.warnings.get((str(guild_id), str(user_id)), []))

    def clear_warnings(self, guild_id: str, user_id: str) -> int:
        key = (str(guild_id), str(user_id))
        count = len(self.warnings.get(key, []))
        self.warnings.pop(key, None)
        return count

    def is_exempt(self, message_data: Dict[str, Any]) -> bool:
        author = message_data.get("author") or {}
        if author.get("bot"):
            return True
        uid = str(author.get("id") or "")
        if uid in self.exempt_user_ids or uid == str(self.bot.application_id):
            return True
        member_roles = {str(r) for r in (message_data.get("member") or {}).get("roles", [])}
        if member_roles & self.exempt_role_ids:
            return True
        return False

    async def inspect_message(self, message_data: Dict[str, Any]) -> bool:
        """
        Inspects a Gateway `MESSAGE_CREATE` payload for profanity and flood violations.
        Returns True if the message violated rules and was queued for batch removal.
        """
        guild_id = message_data.get("guild_id")
        channel_id = message_data.get("channel_id")
        message_id = message_data.get("id")
        if not guild_id or not channel_id or not message_id or self.is_exempt(message_data):
            return False

        author = message_data.get("author") or {}
        user_id = str(author.get("id") or "")
        username = author.get("username", "User")
        content = message_data.get("content", "")
        mentions = message_data.get("mentions", [])
        mention_count = len(mentions) + (5 if message_data.get("mention_everyone") else 0)

        # 1. Check Profanity
        bad_words = self.profanity.find_matches(content)
        if bad_words:
            self.profanity_incidents_handled += 1
            await self.batch_deleter.enqueue(channel_id, [message_id])
            warn_count = self.add_warning(
                guild_id,
                user_id,
                str(self.bot.application_id or "automod"),
                f"Profanity detected ({', '.join(bad_words[:3])})",
            )
            await self._apply_escalation(
                guild_id, channel_id, user_id, username, warn_count, "Profanity filter violation"
            )
            return True

        # 2. Check Flood / Spam
        flood_res = self.antiflood.check_message(
            guild_id, channel_id, user_id, message_id, content, mention_count=mention_count
        )
        if flood_res:
            reason, msg_ids_to_delete = flood_res
            self.flood_incidents_handled += 1
            await self.batch_deleter.enqueue(channel_id, msg_ids_to_delete)
            warn_count = self.add_warning(
                guild_id,
                user_id,
                str(self.bot.application_id or "antiflood"),
                reason,
            )
            await self._apply_escalation(
                guild_id, channel_id, user_id, username, warn_count, reason
            )
            return True

        return False

    async def _apply_escalation(
        self,
        guild_id: str,
        channel_id: str,
        user_id: str,
        username: str,
        warn_count: int,
        reason: str,
    ) -> None:
        action_taken = f"Warning #{warn_count}"
        member = Member({"id": user_id, "username": username}, bot=self.bot, guild_id=guild_id)

        try:
            if warn_count == 2:
                await member.timeout(self.antiflood.config.auto_timeout_seconds, reason=reason)
                self.auto_timeouts_issued += 1
                mins = self.antiflood.config.auto_timeout_seconds // 60
                action_taken = f"Warning #{warn_count} + {mins}m Timeout"
            elif warn_count == 3:
                await member.timeout(3600, reason=reason)
                self.auto_timeouts_issued += 1
                action_taken = f"Warning #{warn_count} + 60m Timeout"
            elif warn_count >= 4:
                await member.kick(reason=f"Exceeded moderation threshold ({warn_count} warnings): {reason}")
                action_taken = f"Warning #{warn_count} + Automatic Kick"
        except Exception as e:
            logger.debug(f"Could not apply auto-punishment to {user_id}: {e}")

        if self.antiflood.should_send_alert(channel_id, user_id):
            embed = (
                Embed(
                    title="🛡️ Automated Moderation",
                    description=f"<@{user_id}>, your message(s) were removed.",
                    color=Embed.Color.RED,
                )
                .add_field("Reason", reason, inline=True)
                .add_field("Action", action_taken, inline=True)
                .set_footer(
                    f"Batch deleter saved {self.batch_deleter.api_calls_saved} API call(s)"
                )
            )
            await self.bot.message_handler.send_message(channel_id, embed=embed)
            if self.log_channel_id and self.log_channel_id != str(channel_id):
                await self.bot.message_handler.send_message(self.log_channel_id, embed=embed)
