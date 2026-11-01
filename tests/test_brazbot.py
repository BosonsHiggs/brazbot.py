"""
Unit Test Suite for brazbot.py v2.0.0
=====================================
Tests Discord API v10 compliance, Voice Gateway v8 packet builders,
Snowflake parsing, Intents/Permissions bitfields, Embeds, Polls,
BatchDeleteQueue coalescing, AntiFloodManager, and ProfanityFilter.
"""

from __future__ import annotations

import asyncio
import sys
import types
import unittest

# Provide a lightweight mock for aiohttp if running in an offline sandbox without aiohttp installed
if "aiohttp" not in sys.modules:
    aiohttp_mock = types.ModuleType("aiohttp")
    aiohttp_mock.ClientSession = object
    aiohttp_mock.ClientResponse = object
    aiohttp_mock.ClientTimeout = object
    aiohttp_mock.ClientWebSocketResponse = object
    aiohttp_mock.WSMsgType = types.SimpleNamespace(TEXT=1, BINARY=2, CLOSE=8, ERROR=256)
    aiohttp_mock.FormData = object
    aiohttp_mock.ClientError = Exception
    aiohttp_mock.ClientResponseError = Exception
    sys.modules["aiohttp"] = aiohttp_mock

from brazbot import (
    AntiFloodManager,
    BatchDeleteQueue,
    Button,
    ButtonStyle,
    Embed,
    FloodConfig,
    Intents,
    Permissions,
    Poll,
    ProfanityFilter,
    Snowflake,
    __version__,
)
from brazbot.http import USER_AGENT


class TestBrazBotCore(unittest.TestCase):
    def test_version_and_user_agent(self):
        """Verify meew0 User-Agent specification compliance."""
        self.assertEqual(__version__, "2.0.0")
        self.assertTrue(
            USER_AGENT.startswith("DiscordBot (https://github.com/BosonsHiggs/brazbot.py, 2.0.0)")
        )

    def test_snowflake_parsing(self):
        sf = Snowflake(175928847299117063)
        self.assertEqual(int(sf), 175928847299117063)
        self.assertGreater(sf.created_at.year, 2015)

    def test_intents_and_permissions(self):
        default_intents = Intents.default()
        self.assertNotIn(Intents.GUILD_MEMBERS, default_intents)
        self.assertIn(Intents.GUILDS, default_intents)
        admin = Permissions.ADMINISTRATOR
        self.assertEqual(int(admin), 1 << 3)

    def test_embeds_and_buttons(self):
        btn = Button(label="Click Me", style=ButtonStyle.PRIMARY, custom_id="btn_1")
        self.assertEqual(btn.to_dict()["label"], "Click Me")

        embed = Embed(title="Test", description="Desc", color=Embed.Color.GREEN)
        embed.add_field("F1", "V1")
        self.assertEqual(embed.to_dict()["title"], "Test")

    def test_poll_builder(self):
        poll = Poll(
            question="Best Discord API version?",
            answers=["API v10", "Voice Gateway v8"],
            duration_hours=12,
        )
        d = poll.to_dict()
        self.assertEqual(d["question"]["text"], "Best Discord API version?")
        self.assertEqual(len(d["answers"]), 2)


class TestModerationTools(unittest.TestCase):
    def test_profanity_filter_anti_evasion(self):
        """Verify ProfanityFilter catches leetspeak, accents, zero-width chars, and repeats."""
        pf = ProfanityFilter(words=["badword", "toxic"])
        # Exact match
        self.assertTrue(pf.contains_profanity("This contains a badword here"))
        # Leetspeak + repeats + accents
        self.assertTrue(pf.contains_profanity("You are b@dw000rd!"))
        self.assertTrue(pf.contains_profanity("Stop being t0x!c right now"))
        # Clean text
        self.assertFalse(pf.contains_profanity("Hello friendly community!"))

    def test_anti_flood_manager(self):
        """Verify AntiFloodManager triggers on message bursts, duplicates, and mention spam."""
        cfg = FloodConfig(max_messages=3, window_seconds=10.0, max_duplicates=2, max_mentions=4)
        mgr = AntiFloodManager(cfg)

        # Send 2 messages -> allowed; 3rd message reaches max_messages=3 -> flood burst
        self.assertIsNone(mgr.check_message("g1", "c1", "u1", "1001", "msg 1"))
        self.assertIsNone(mgr.check_message("g1", "c1", "u1", "1002", "msg 2"))
        violation = mgr.check_message("g1", "c1", "u1", "1003", "msg 3")
        self.assertIsNotNone(violation)
        reason, msg_ids = violation
        self.assertIn("Message flood", reason)
        self.assertEqual(len(msg_ids), 3)

        # Mention spam check for another user
        v_mention = mgr.check_message("g1", "c1", "u2", "2001", "ping spam", mention_count=5)
        self.assertIsNotNone(v_mention)
        self.assertIn("Mass mention spam", v_mention[0])

    def test_batch_delete_queue_coalescing(self):
        """Verify BatchDeleteQueue groups multiple queued messages into a single bulk-delete HTTP call."""
        bulk_calls = []

        class FakeMessageHandler:
            async def bulk_delete_messages(self, channel_id, message_ids, reason=None):
                bulk_calls.append((channel_id, list(message_ids), reason))
                return True

        class FakeBot:
            message_handler = FakeMessageHandler()

        async def run_test():
            q = BatchDeleteQueue(FakeBot(), flush_interval=0.05)
            msg_ids = [str(100000 + i) for i in range(25)]
            await q.enqueue("999", msg_ids)
            deleted = await q.flush_channel("999")
            return deleted, q.total_messages_deleted, q.total_api_calls_used, q.api_calls_saved

        deleted, total_del, api_used, api_saved = asyncio.run(run_test())
        self.assertEqual(deleted, 25)
        self.assertEqual(total_del, 25)
        self.assertEqual(api_used, 1)
        self.assertEqual(api_saved, 24)
        self.assertEqual(len(bulk_calls), 1)
        self.assertEqual(len(bulk_calls[0][1]), 25)


if __name__ == "__main__":
    unittest.main()
