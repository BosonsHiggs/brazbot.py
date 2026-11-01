"""
Full Server Moderation Bot Example — brazbot.py v2.0.0 (Discord API v10)
========================================================================

Complete, production-ready Discord server moderation bot built exclusively with
`brazbot.py` (direct Discord HTTP & Gateway v10 API, zero third-party bot libraries).

Features demonstrated:
1. **Automatic Anti-Flood & Spam Removal (`AntiFloodManager` + `BatchDeleteQueue`)**:
   - Detects rapid message bursts per user within a sliding window, duplicate message spam,
     mass-mention spam, and excessive CAPS spam.
   - Enqueues offending message IDs into `BatchDeleteQueue`, which coalesces deletions over
     a short 0.5-second window and executes a single `POST /channels/{id}/messages/bulk-delete`
     call (deleting up to 100 messages per HTTP request instead of hammering the Discord API
     with individual `DELETE` calls).
   - Issues escalating automatic punishments (Warning #1 -> 5m Timeout on #2 -> 60m Timeout on #3 -> Kick on #4).

2. **Anti-Evasion Obscene / Profane Word Filter (`ProfanityFilter` + Discord AutoMod v10)**:
   - Normalizes Unicode accents/diacritics, strips zero-width characters, decodes leetspeak
     (`@ -> a`, `$ -> s`, `0 -> o`, `1 -> i`, `3 -> e`, `4 -> a`, `5 -> s`, `7 -> t`), and
     collapses stretched characters (`fuuuuck -> fuck`) before matching.
   - Queues profane messages into `BatchDeleteQueue` for rate-limit-friendly batch removal
     and synchronizes the blocked dictionary directly with native Discord AutoMod v10 (`/automod_sync`).

3. **High-Throughput Multi-Message & Full-Channel Cleanup (Zero API Hammering)**:
   - `/purge`: Deletes up to 1,000 messages using paginated 100-message chunks via
     `POST /channels/{id}/messages/bulk-delete` (only 10 API calls for 1,000 messages).
   - `/purge_user`: Scans recent channel history and bulk-deletes only messages sent by a specific user.
   - `/clean_all`: Wipes **all** messages in a channel either via `mode="clone"` (clones the
     channel with identical permissions/topic/position and deletes the old channel in **2 API calls**
     total, bypassing the 14-day bulk-delete limit) or `mode="batch"` (100-message bulk batches).

4. **Complete Slash Command Moderation Suite (22 Slash Commands)**:
   - Member Sanctions: `/ban`, `/softban`, `/massban` (v10 Bulk Ban up to 200 users in 1 API call), `/unban`, `/kick`, `/timeout`, `/untimeout`
   - Warning Ledger: `/warn`, `/warnings`, `/clear_warnings`
   - Channel Cleanup: `/purge`, `/purge_user`, `/clean_all`
   - Channel Access Control: `/slowmode`, `/lock`, `/unlock`, `/lockdown`
   - Filter & Anti-Flood Controls: `/profanity_add`, `/profanity_remove`, `/profanity_list`, `/automod_sync`, `/antiflood_config`, `/modstats`
"""

from __future__ import annotations

import os
from typing import Any, Dict, Literal, Optional

from brazbot import (
    Bot,
    CommandContext,
    Embed,
    FloodConfig,
    Intents,
    Member,
    TextChannel,
    create_error_embed,
    describe,
    has_permissions,
)


class ModerationBot(Bot):
    """Production Server Moderation Bot powered by brazbot.py v2.0.0."""

    def __init__(self, token: str):
        intents = (
            Intents.default()
            | Intents.GUILD_MEMBERS
            | Intents.GUILD_MODERATION
            | Intents.GUILD_MESSAGES
            | Intents.MESSAGE_CONTENT
        )
        super().__init__(token=token, command_prefix="!", intents=intents)

        # Configure automatic Anti-Flood thresholds & BatchDeleteQueue coalescing (0.5s window)
        self.moderation.batch_deleter.flush_interval = 0.5
        self.moderation.antiflood.config = FloodConfig(
            enabled=True,
            max_messages=5,              # Max 5 messages allowed...
            window_seconds=5.0,          # ...within a 5.0-second sliding window
            max_duplicates=3,            # Max 3 identical messages within 15 seconds
            duplicate_window_seconds=15.0,
            max_mentions=5,              # Max 5 mentions per message
            max_caps_ratio=0.80,         # Max 80% uppercase letters
            auto_timeout_seconds=300,    # 5-minute automatic timeout on repeat flood
        )

        # Add custom obscene/profane words to the anti-evasion filter
        self.moderation.profanity.add_words([
            "scamlink",
            "freenitro",
            "toxicinsult",
            "slurword",
        ])

    async def on_ready(self, data: Dict[str, Any]) -> None:
        user = data.get("user", {})
        print(f"[ModerationBot] Online as {user.get('username')} (ID: {user.get('id')})")
        await self.command_handler.sync_commands()
        print(
            f"[ModerationBot] Anti-Flood ({self.moderation.antiflood.config.max_messages} msgs/"
            f"{self.moderation.antiflood.config.window_seconds}s) + ProfanityFilter "
            f"({len(self.moderation.profanity.blocked_words)} words) + BatchDeleteQueue active."
        )

    async def on_message_create(self, data: Dict[str, Any]) -> None:
        """
        Automatically inspects every incoming server message for:
        1. Obscene/profane words (with leetspeak, accent, zero-width, and repeat normalization)
        2. Message flood bursts, duplicate spam, mass mentions, and CAPS spam.
        Violating messages are queued into `BatchDeleteQueue` so bursts of up to 100 messages
        are removed in a SINGLE `POST /channels/{id}/messages/bulk-delete` HTTP request.
        """
        if isinstance(data, dict):
            await self.moderation.inspect_message(data)


def register_moderation_commands(bot: ModerationBot) -> None:
    """Registers the complete suite of slash & prefix moderation commands on `bot`."""

    # =========================================================================
    # 1. Multi-Message & Full-Channel Cleanup (Zero API Hammering)
    # =========================================================================

    @bot.command(
        name="purge",
        description="Bulk-deletes multiple messages in batches of 100 without hammering the Discord API",
    )
    @has_permissions(manage_messages=True)
    @describe(
        amount="Number of messages to delete (1 to 1000)",
        contains="Optional text filter: only delete messages containing this substring",
    )
    async def purge_cmd(ctx: CommandContext, amount: int, contains: Optional[str] = None):
        await ctx.defer(ephemeral=True)
        ch = await TextChannel.from_channel_id(bot, ctx.guild_id, ctx.channel_id)
        pred = None
        if contains:
            needle = contains.lower()
            pred = lambda m: needle in (m.get("content", "") or "").lower()

        deleted = await ch.purge(
            limit=min(1000, max(1, int(amount))),
            check=pred,
            reason=f"Bulk purge by {ctx.author}",
        )
        batches_used = max(1, (len(deleted) + 99) // 100) if deleted else 0
        await ctx.send(
            embed=Embed(
                title="🗑️ Bulk Message Purge Complete",
                description=(
                    f"Removed **{len(deleted)}** message(s) using **{batches_used}** "
                    f"batched `bulk-delete` API call(s)."
                ),
                color=Embed.Color.GREEN,
            ),
            ephemeral=True,
        )

    @bot.command(
        name="purge_user",
        description="Bulk-deletes recent messages from a specific user in 100-message batches",
    )
    @has_permissions(manage_messages=True)
    @describe(
        member="Target member whose messages will be removed",
        scan_limit="Number of recent messages in the channel to scan (up to 1000)",
    )
    async def purge_user_cmd(
        ctx: CommandContext, member: Member, scan_limit: Optional[int] = 200
    ):
        await ctx.defer(ephemeral=True)
        ch = await TextChannel.from_channel_id(bot, ctx.guild_id, ctx.channel_id)
        deleted = await ch.purge(
            limit=min(1000, max(1, int(scan_limit or 200))),
            check=lambda m: str(m.get("author", {}).get("id")) == str(member.id),
            reason=f"User message purge by {ctx.author}",
        )
        await ctx.send(
            f"🗑️ Removed **{len(deleted)}** message(s) from **{member}** using batched `bulk-delete`.",
            ephemeral=True,
        )

    @bot.command(
        name="clean_all",
        description="Wipes ALL messages in the channel via Clone (2 API calls) or Batched Bulk-Delete",
    )
    @has_permissions(manage_channels=True, manage_messages=True)
    @describe(
        mode="clone (instant full channel wipe in 2 API calls) or batch (100-message bulk-delete chunks)"
    )
    async def clean_all_cmd(
        ctx: CommandContext, mode: Literal["clone", "batch"] = "clone"
    ):
        await ctx.defer(ephemeral=True)
        ch = await TextChannel.from_channel_id(bot, ctx.guild_id, ctx.channel_id)
        if mode == "clone":
            new_ch = await ch.clean_all_messages(
                strategy="clone", reason=f"Full channel wipe requested by {ctx.author}"
            )
            if hasattr(new_ch, "send"):
                await new_ch.send(
                    embed=Embed(
                        title="✨ Channel Wiped Clean (2 API Calls)",
                        description=(
                            f"All message history was wiped by {ctx.author.mention} via "
                            f"instant channel clone + delete without hitting rate limits."
                        ),
                        color=Embed.Color.GREEN,
                    )
                )
        else:
            count = await ch.clean_all_messages(
                strategy="batch", max_batches=10, reason=f"Batch clean by {ctx.author}"
            )
            await ctx.send(
                f"🗑️ Wiped **{count}** messages in batches of 100 via `bulk-delete`.",
                ephemeral=True,
            )

    # =========================================================================
    # 2. Member Sanctions: Ban, Softban, Massban (v10 Bulk-Ban), Kick, Timeout
    # =========================================================================

    @bot.command(name="ban", description="Bans a member and deletes 1 day of their messages")
    @has_permissions(ban_members=True)
    @describe(member="Member to ban", reason="Audit log reason for the ban")
    async def ban_cmd(ctx: CommandContext, member: Member, reason: Optional[str] = None):
        await ctx.defer()
        await member.ban(reason=reason, delete_message_days=1)
        await ctx.send(
            embed=Embed(
                title="🔨 Member Banned",
                description=f"**{member}** (`{member.id}`) was banned.\n**Reason:** {reason or 'Not specified'}",
                color=Embed.Color.RED,
            )
        )

    @bot.command(
        name="softban",
        description="Bans and immediately unbans a member to flush up to 7 days of their messages",
    )
    @has_permissions(ban_members=True)
    @describe(member="Member to softban", reason="Reason for the softban")
    async def softban_cmd(ctx: CommandContext, member: Member, reason: Optional[str] = None):
        await ctx.defer()
        await member.ban(reason=f"Softban: {reason or 'Message flush'}", delete_message_days=7)
        await member.unban(reason="Softban automatic unban")
        await ctx.send(
            embed=Embed(
                title="🧹 Member Softbanned",
                description=f"**{member}** was softbanned (7 days of messages flushed in 2 API calls).",
                color=Embed.Color.ORANGE,
            )
        )

    @bot.command(
        name="massban",
        description="Bans up to 200 user IDs in a single Discord API v10 Bulk-Ban request",
    )
    @has_permissions(ban_members=True, administrator=True)
    @describe(
        user_ids="Space or comma-separated list of user Snowflake IDs (max 200)",
        reason="Audit log reason for the mass ban",
    )
    async def massban_cmd(ctx: CommandContext, user_ids: str, reason: Optional[str] = None):
        await ctx.defer()
        ids = [u.strip("<@!>") for u in user_ids.replace(",", " ").split() if u.strip("<@!>").isdigit()]
        if not ids:
            await ctx.send(embed=create_error_embed("Provide at least one valid user Snowflake ID."))
            return
        guild = await ctx.get_guild()
        res = await guild.bulk_ban(ids[:200], delete_message_days=1, reason=reason)
        banned_count = len(res.get("banned_users", ids)) if isinstance(res, dict) else len(ids)
        await ctx.send(
            embed=Embed(
                title="⚡ Mass Ban Executed (1 API Call)",
                description=f"Banned **{banned_count}** account(s) via `POST /guilds/{{id}}/bulk-ban`.",
                color=Embed.Color.RED,
            )
        )

    @bot.command(name="unban", description="Unbans a user by their Snowflake ID")
    @has_permissions(ban_members=True)
    @describe(user_id="User ID to unban", reason="Audit log reason")
    async def unban_cmd(ctx: CommandContext, user_id: str, reason: Optional[str] = None):
        await ctx.defer()
        guild = await ctx.get_guild()
        await guild.unban(user_id.strip("<@!>"), reason=reason)
        await ctx.send(
            embed=Embed(
                title="🔓 User Unbanned",
                description=f"Unbanned user `{user_id}`.",
                color=Embed.Color.GREEN,
            )
        )

    @bot.command(name="kick", description="Kicks a member from the server")
    @has_permissions(kick_members=True)
    @describe(member="Member to kick", reason="Reason for kicking")
    async def kick_cmd(ctx: CommandContext, member: Member, reason: Optional[str] = None):
        await ctx.defer()
        await member.kick(reason=reason)
        await ctx.send(
            embed=Embed(
                title="👢 Member Kicked",
                description=f"**{member}** was kicked.\n**Reason:** {reason or 'Not specified'}",
                color=Embed.Color.ORANGE,
            )
        )

    @bot.command(
        name="timeout",
        description="Applies a temporary communication timeout (mute) to a member",
    )
    @has_permissions(moderate_members=True)
    @describe(member="Target member", minutes="Duration in minutes (0 to remove)", reason="Reason")
    async def timeout_cmd(
        ctx: CommandContext, member: Member, minutes: int, reason: Optional[str] = None
    ):
        await ctx.defer()
        await member.timeout(minutes * 60 if minutes > 0 else None, reason=reason)
        await ctx.send(
            embed=Embed(
                title="🔇 Member Timed Out" if minutes > 0 else "🔊 Timeout Removed",
                description=(
                    f"**{member}** timed out for **{minutes} minute(s)**."
                    if minutes > 0
                    else f"Timeout removed for **{member}**."
                ),
                color=Embed.Color.ORANGE if minutes > 0 else Embed.Color.GREEN,
            )
        )

    @bot.command(name="untimeout", description="Removes an active timeout from a member")
    @has_permissions(moderate_members=True)
    @describe(member="Member whose timeout will be removed")
    async def untimeout_cmd(ctx: CommandContext, member: Member):
        await ctx.defer()
        await member.timeout(None, reason=f"Timeout removed by {ctx.author}")
        await ctx.send(
            embed=Embed(
                title="🔊 Timeout Removed",
                description=f"Timeout removed for **{member}**.",
                color=Embed.Color.GREEN,
            )
        )

    # =========================================================================
    # 3. Warning Ledger & Escalation
    # =========================================================================

    @bot.command(name="warn", description="Issues a formal warning to a member")
    @has_permissions(moderate_members=True)
    @describe(member="Member to warn", reason="Warning reason")
    async def warn_cmd(ctx: CommandContext, member: Member, reason: str):
        await ctx.defer()
        count = bot.moderation.add_warning(
            ctx.guild_id, member.id, ctx.author.id if ctx.author else "mod", reason
        )
        await ctx.send(
            embed=Embed(
                title="⚠️ Warning Issued",
                description=f"**{member}** received warning **#{count}**.\n**Reason:** {reason}",
                color=Embed.Color.GOLD,
            )
        )

    @bot.command(name="warnings", description="Lists all active warnings for a member")
    @has_permissions(moderate_members=True)
    @describe(member="Member to inspect")
    async def warnings_cmd(ctx: CommandContext, member: Member):
        await ctx.defer()
        records = bot.moderation.get_warnings(ctx.guild_id, member.id)
        if not records:
            await ctx.send(f"✅ **{member}** has a clean record (0 warnings).")
            return
        lines = [
            f"`{i}.` **{r['reason']}** (by <@{r['moderator_id']}>)"
            for i, r in enumerate(records, 1)
        ]
        await ctx.send(
            embed=Embed(
                title=f"📋 Warnings for {member.display_name} ({len(records)})",
                description="\n".join(lines[:15]),
                color=Embed.Color.GOLD,
            )
        )

    @bot.command(name="clear_warnings", description="Clears all warnings for a member")
    @has_permissions(moderate_members=True)
    @describe(member="Member whose warnings will be cleared")
    async def clear_warnings_cmd(ctx: CommandContext, member: Member):
        await ctx.defer()
        removed = bot.moderation.clear_warnings(ctx.guild_id, member.id)
        await ctx.send(
            embed=Embed(
                title="🧹 Warnings Cleared",
                description=f"Cleared **{removed}** warning(s) for **{member}**.",
                color=Embed.Color.GREEN,
            )
        )

    # =========================================================================
    # 4. Channel Slowmode, Lock, Unlock & Server Lockdown
    # =========================================================================

    @bot.command(name="slowmode", description="Sets the per-user message rate limit in the current channel")
    @has_permissions(manage_channels=True)
    @describe(seconds="Slowmode delay in seconds (0 to disable, max 21600)")
    async def slowmode_cmd(ctx: CommandContext, seconds: int):
        await ctx.defer()
        ch = await TextChannel.from_channel_id(bot, ctx.guild_id, ctx.channel_id)
        await ch.set_slowmode(max(0, min(21600, int(seconds))))
        await ctx.send(
            embed=Embed(
                title="⏱️ Slowmode Updated",
                description=f"Channel slowmode set to **{seconds}s**.",
                color=Embed.Color.BLURPLE,
            )
        )

    @bot.command(name="lock", description="Locks the current channel for regular members")
    @has_permissions(manage_channels=True)
    async def lock_cmd(ctx: CommandContext):
        await ctx.defer()
        ch = await ctx.get_channel()
        await ch.set_lock(True, reason=f"Locked by {ctx.author}")
        await ctx.send(
            embed=Embed(
                title="🔒 Channel Locked",
                description="Regular members can no longer send messages in this channel.",
                color=Embed.Color.RED,
            )
        )

    @bot.command(name="unlock", description="Unlocks the current channel for regular members")
    @has_permissions(manage_channels=True)
    async def unlock_cmd(ctx: CommandContext):
        await ctx.defer()
        ch = await ctx.get_channel()
        await ch.set_lock(False, reason=f"Unlocked by {ctx.author}")
        await ctx.send(
            embed=Embed(
                title="🔓 Channel Unlocked",
                description="Regular members can send messages in this channel again.",
                color=Embed.Color.GREEN,
            )
        )

    @bot.command(
        name="lockdown",
        description="Locks or unlocks all text channels in the server during an active raid",
    )
    @has_permissions(administrator=True)
    @describe(active="True to lock all text channels, False to unlock them")
    async def lockdown_cmd(ctx: CommandContext, active: bool):
        await ctx.defer()
        guild = await ctx.get_guild()
        channels = await guild.fetch_channels()
        modified = 0
        for ch in channels:
            if isinstance(ch, TextChannel):
                await ch.set_lock(bool(active), reason=f"Server lockdown={active} by {ctx.author}")
                modified += 1
        await ctx.send(
            embed=Embed(
                title="🚨 Server Lockdown Activated" if active else "✅ Server Lockdown Lifted",
                description=f"Updated permissions on **{modified}** text channel(s).",
                color=Embed.Color.RED if active else Embed.Color.GREEN,
            )
        )

    # =========================================================================
    # 5. Profanity Filter, AutoMod v10 Sync & Anti-Flood Configuration
    # =========================================================================

    @bot.command(
        name="profanity_add",
        description="Adds one or more obscene/blocked words to the real-time anti-evasion filter",
    )
    @has_permissions(manage_guild=True)
    @describe(words="Comma-separated list of words to block")
    async def profanity_add_cmd(ctx: CommandContext, words: str):
        await ctx.defer(ephemeral=True)
        items = [w.strip() for w in words.split(",") if w.strip()]
        added = bot.moderation.profanity.add_words(items)
        await ctx.send(
            embed=Embed(
                title="🛡️ Profanity Filter Updated",
                description=(
                    f"Added **{added}** word(s). "
                    f"Total blocked words: **{len(bot.moderation.profanity.blocked_words)}**."
                ),
                color=Embed.Color.GREEN,
            ),
            ephemeral=True,
        )

    @bot.command(
        name="profanity_remove",
        description="Removes one or more words from the profanity filter",
    )
    @has_permissions(manage_guild=True)
    @describe(words="Comma-separated list of words to unblock")
    async def profanity_remove_cmd(ctx: CommandContext, words: str):
        await ctx.defer(ephemeral=True)
        items = [w.strip() for w in words.split(",") if w.strip()]
        removed = bot.moderation.profanity.remove_words(items)
        await ctx.send(
            embed=Embed(
                title="🛡️ Profanity Filter Updated",
                description=(
                    f"Removed **{removed}** word(s). "
                    f"Remaining: **{len(bot.moderation.profanity.blocked_words)}**."
                ),
                color=Embed.Color.GOLD,
            ),
            ephemeral=True,
        )

    @bot.command(
        name="profanity_list",
        description="Displays the active blocked profanity word list",
    )
    @has_permissions(manage_guild=True)
    async def profanity_list_cmd(ctx: CommandContext):
        await ctx.defer(ephemeral=True)
        words = sorted(bot.moderation.profanity.blocked_words)
        formatted = ", ".join(f"`{w}`" for w in words[:100]) or "None"
        await ctx.send(
            embed=Embed(
                title=f"🚫 Blocked Profanity Words ({len(words)})",
                description=formatted,
                color=Embed.Color.BLURPLE,
            ),
            ephemeral=True,
        )

    @bot.command(
        name="automod_sync",
        description="Synchronizes the profanity word list with native Discord AutoMod v10",
    )
    @has_permissions(manage_guild=True)
    async def automod_sync_cmd(ctx: CommandContext):
        await ctx.defer()
        rule = await bot.moderation.profanity.sync_to_discord_automod(bot, ctx.guild_id)
        await ctx.send(
            embed=Embed(
                title="✅ Synchronized with Discord AutoMod v10",
                description=f"Server-level AutoMod Rule **{rule.name}** (`{rule.id}`) is now active.",
                color=Embed.Color.GREEN,
            )
        )

    @bot.command(
        name="antiflood_config",
        description="Configures automatic anti-flood rate thresholds and auto-timeout settings",
    )
    @has_permissions(manage_guild=True)
    @describe(
        max_messages="Maximum messages allowed inside the sliding window (default: 5)",
        window_seconds="Sliding window duration in seconds (default: 5)",
        max_mentions="Maximum mentions per message before auto-removal (default: 5)",
        enabled="Enable or disable automatic anti-flood protection",
    )
    async def antiflood_config_cmd(
        ctx: CommandContext,
        max_messages: int = 5,
        window_seconds: int = 5,
        max_mentions: int = 5,
        enabled: bool = True,
    ):
        await ctx.defer()
        cfg = bot.moderation.antiflood.config
        cfg.max_messages = max(2, int(max_messages))
        cfg.window_seconds = max(1.0, float(window_seconds))
        cfg.max_mentions = max(2, int(max_mentions))
        cfg.enabled = bool(enabled)
        await ctx.send(
            embed=Embed(
                title="⚙️ Anti-Flood Configuration Updated",
                description=f"Status: **{'Enabled' if cfg.enabled else 'Disabled'}**",
                color=Embed.Color.GREEN if cfg.enabled else Embed.Color.ORANGE,
            )
            .add_field("Burst Threshold", f"`{cfg.max_messages}` msgs / `{cfg.window_seconds:.0f}s`", inline=True)
            .add_field("Max Mentions", f"`{cfg.max_mentions}`", inline=True)
        )

    @bot.command(
        name="modstats",
        description="Shows moderation telemetry and HTTP calls saved by BatchDeleteQueue",
    )
    @has_permissions(moderate_members=True)
    async def modstats_cmd(ctx: CommandContext):
        await ctx.defer()
        mod = bot.moderation
        bd = mod.batch_deleter
        embed = (
            Embed(
                title="📊 Server Moderation & BatchDeleteQueue Efficiency",
                description=(
                    "Coalesced `BatchDeleteQueue` groups rapid flood and profanity deletions "
                    "into single `POST /channels/{id}/messages/bulk-delete` requests."
                ),
                color=Embed.Color.BLURPLE,
            )
            .add_field("Flood Bursts Blocked", str(mod.flood_incidents_handled), inline=True)
            .add_field("Profanity Blocked", str(mod.profanity_incidents_handled), inline=True)
            .add_field("Auto-Timeouts Issued", str(mod.auto_timeouts_issued), inline=True)
            .add_field("Messages Batch-Deleted", str(bd.total_messages_deleted), inline=True)
            .add_field("Bulk API Calls Used", str(bd.total_api_calls_used), inline=True)
            .add_field("HTTP Calls Saved", f"**{bd.api_calls_saved}**", inline=True)
        )
        await ctx.send(embed=embed)


if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise SystemExit("Please set the DISCORD_TOKEN environment variable before running.")
    moderation_bot = ModerationBot(token=token)
    register_moderation_commands(moderation_bot)
    moderation_bot.run()
