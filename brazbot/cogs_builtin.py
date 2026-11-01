"""
Built-in ready-to-use Cogs for rapid bot creation with brazbot.py:
- `MusicCog`: Full music and voice commands (`/join`, `/leave`, `/play`, `/search`, `/pause`, `/resume`,
  `/skip`, `/stop`, `/queue`, `/nowplaying`, `/loop`, `/volume`, `/shuffle`, `/seek`, `/filter`, `/voice_status`)
- `ModerationCog`: Complete server moderation & anti-flood/profanity suite (`/ban`, `/unban`, `/softban`,
  `/massban`, `/kick`, `/timeout`, `/untimeout`, `/warn`, `/warnings`, `/clear_warnings`, `/purge`,
  `/purge_user`, `/clean_all`, `/slowmode`, `/lock`, `/unlock`, `/profanity_add`, `/profanity_remove`,
  `/profanity_list`, `/antiflood_config`, `/automod_sync`, `/modstats`)
- `UtilityCog`: Server and utility commands (`/ping`, `/serverinfo`, `/userinfo`, `/avatar`, `/poll`)
- `FunCog`: Fun and engagement commands (`/8ball`, `/dice`, `/coinflip`)
"""

import random
from typing import Any, Dict, Literal, Optional

from brazbot.channels import TextChannel, VoiceChannel
from brazbot.cogs import Cog
from brazbot.decorators import describe, has_permissions
from brazbot.embed import Embed
from brazbot.member import Member
from brazbot.polls import Poll
from brazbot.utils import create_error_embed, format_discord_timestamp


class MusicCog(Cog):
    """Built-in Music and Voice Cog with YouTube (`yt-dlp`), FFmpeg audio filters, seek, and queue support."""

    def __init__(self, bot: Any):
        super().__init__(bot)
        self.register_commands()

    def register_commands(self) -> None:
        @self.command(name="join", description="Connects the bot to a voice channel")
        @describe(channel="Voice channel to join (optional if you are already in one)")
        async def join(ctx, channel: Optional[VoiceChannel] = None):
            await ctx.defer()
            target_channel = channel or (
                ctx.author.voice.channel if ctx.author and ctx.author.voice else None
            )
            if not target_channel:
                await ctx.send(embed=create_error_embed("You must be in a voice channel or specify one!"))
                return
            vc = await target_channel.connect()
            embed = Embed(
                title="🔊 Connected to Voice Channel",
                description=f"Successfully connected to **{target_channel.name}**",
                color=Embed.Color.GREEN,
            ).add_field("Encryption Mode", f"`{vc.udp.mode}`", inline=True)
            await ctx.send(embed=embed)

        @self.command(name="leave", description="Disconnects the bot from the voice channel and clears the queue")
        async def leave(ctx):
            await ctx.defer()
            vc = ctx.voice_client
            if not vc:
                await ctx.send(embed=create_error_embed("The bot is not connected to any voice channel."))
                return
            ch_name = vc.channel.name
            player = self.bot.get_music_player(ctx.guild_id)
            player.queue.clear()
            player.current = None
            await vc.disconnect()
            await ctx.send(
                embed=Embed(
                    title="👋 Disconnected",
                    description=f"Left voice channel **{ch_name}**.",
                    color=Embed.Color.GOLD,
                )
            )

        @self.command(name="play", aliases=["p"], description="Plays music from a URL or YouTube search query")
        @describe(query="Song title, YouTube URL, Playlist, or direct MP3/OGG URL")
        async def play(ctx, query: str):
            await ctx.defer()
            vc = ctx.voice_client
            if not vc or not vc.is_connected():
                if ctx.author and ctx.author.voice and ctx.author.voice.channel:
                    vc = await ctx.author.voice.channel.connect()
                else:
                    await ctx.send(embed=create_error_embed("Join a voice channel first or use `/join`!"))
                    return

            player = self.bot.get_music_player(ctx.guild_id)
            player.text_channel_id = ctx.channel_id
            requester = str(ctx.author) if ctx.author else "Unknown"

            tracks = await player.enqueue(query, requester=requester)
            if not tracks:
                await ctx.send(embed=create_error_embed("No tracks found for your query."))
                return

            first = tracks[0]
            desc = (
                f"**[{first.title}]({first.url})**"
                if len(tracks) == 1
                else f"Added **{len(tracks)} tracks** from the playlist to the queue!"
            )
            embed = (
                Embed(title="🎵 Added to Queue", description=desc, color=Embed.Color.GREEN)
                .add_field("Duration", first.formatted_duration, inline=True)
                .add_field("Requested by", requester, inline=True)
                .set_footer(f"Total in queue: {len(player.queue)} track(s)")
            )
            if first.thumbnail:
                embed.set_thumbnail(first.thumbnail)
            await ctx.send(embed=embed)

        @self.command(name="pause", description="Pauses the currently playing track")
        async def pause(ctx):
            await ctx.defer()
            vc = ctx.voice_client
            if not vc or not vc.is_playing():
                await ctx.send(embed=create_error_embed("Nothing is currently playing."))
                return
            await vc.pause()
            await ctx.send(embed=Embed(title="⏸️ Paused", description="Playback paused.", color=Embed.Color.GOLD))

        @self.command(name="resume", description="Resumes a paused track")
        async def resume(ctx):
            await ctx.defer()
            vc = ctx.voice_client
            if not vc or not vc.is_paused():
                await ctx.send(embed=create_error_embed("Playback is not paused."))
                return
            await vc.resume()
            await ctx.send(embed=Embed(title="▶️ Resumed", description="Playback resumed!", color=Embed.Color.GREEN))

        @self.command(name="skip", aliases=["s"], description="Skips to the next track in the queue")
        async def skip(ctx):
            await ctx.defer()
            vc = ctx.voice_client
            player = self.bot.get_music_player(ctx.guild_id)
            if not vc or not player.current:
                await ctx.send(embed=create_error_embed("Nothing is currently playing to skip."))
                return
            skipped_title = player.current.title
            vc._after_callback = None
            await vc.stop()
            await player.play_next()
            await ctx.send(
                embed=Embed(
                    title="⏭️ Track Skipped",
                    description=f"Skipped **{skipped_title}**.",
                    color=Embed.Color.GOLD,
                )
            )

        @self.command(name="stop", description="Stops playback and clears the music queue")
        async def stop(ctx):
            await ctx.defer()
            vc = ctx.voice_client
            player = self.bot.get_music_player(ctx.guild_id)
            player.queue.clear()
            player.current = None
            if vc:
                await vc.stop()
            await ctx.send(
                embed=Embed(
                    title="⏹️ Stopped",
                    description="Playback stopped and queue cleared.",
                    color=Embed.Color.RED,
                )
            )

        @self.command(name="queue", aliases=["q"], description="Displays the current music queue")
        async def queue(ctx):
            await ctx.defer()
            player = self.bot.get_music_player(ctx.guild_id)
            if not player.current and not player.queue:
                await ctx.send("📭 The music queue is empty.")
                return
            embed = Embed(title="🎶 Music Queue", color=Embed.Color.BLURPLE)
            if player.current:
                embed.add_field(
                    "▶️ Now Playing",
                    f"**[{player.current.title}]({player.current.url})** (`{player.current.formatted_duration}`)\n"
                    f"{player.current.progress_bar()}\nRequested by: {player.current.requester}",
                    inline=False,
                )
            if player.queue:
                lines = [
                    f"`{idx}.` **{t.title}** (`{t.formatted_duration}`) — {t.requester}"
                    for idx, t in enumerate(player.queue[:10], 1)
                ]
                if len(player.queue) > 10:
                    lines.append(f"... and **{len(player.queue) - 10}** more track(s)")
                embed.add_field(f"📋 Up Next ({len(player.queue)})", "\n".join(lines), inline=False)
            embed.set_footer(
                f"Loop: {player.loop_mode} | Volume: {int(player.volume * 100)}% | Filter: {player.audio_filter}"
            )
            await ctx.send(embed=embed)

        @self.command(name="nowplaying", aliases=["np"], description="Shows details and progress bar for the current track")
        async def nowplaying(ctx):
            await ctx.defer()
            player = self.bot.get_music_player(ctx.guild_id)
            curr = player.current
            if not curr:
                await ctx.send(embed=create_error_embed("Nothing is currently playing."))
                return
            embed = (
                Embed(
                    title="🎵 Now Playing",
                    description=f"**[{curr.title}]({curr.url})**\n\n{curr.progress_bar()}",
                    color=Embed.Color.GREEN,
                )
                .add_field("Requested by", curr.requester, inline=True)
                .add_field("Uploader", curr.uploader or "Unknown", inline=True)
                .add_field("Filter", f"`{player.audio_filter}`", inline=True)
            )
            if curr.thumbnail:
                embed.set_thumbnail(curr.thumbnail)
            await ctx.send(embed=embed)

        @self.command(name="volume", description="Adjusts player volume (0 to 200%)")
        @describe(level="Volume percentage between 0 and 200")
        async def volume(ctx, level: int):
            await ctx.defer()
            if not (0 <= level <= 200):
                await ctx.send(embed=create_error_embed("Volume must be between 0 and 200%."))
                return
            player = self.bot.get_music_player(ctx.guild_id)
            player.set_volume(level / 100.0)
            filled = int((level / 200.0) * 20)
            bar = "█" * filled + "░" * (20 - filled)
            await ctx.send(
                embed=Embed(
                    title="🔊 Volume Adjusted",
                    description=f"`{bar}` **{level}%**",
                    color=Embed.Color.GREEN,
                )
            )

        @self.command(name="seek", description="Seeks to a specific timestamp (in seconds) in the current track")
        @describe(seconds="Position in seconds to jump to")
        async def seek(ctx, seconds: int):
            await ctx.defer()
            player = self.bot.get_music_player(ctx.guild_id)
            ok = await player.seek(seconds)
            if not ok:
                await ctx.send(embed=create_error_embed("Could not seek the current track."))
                return
            m, s = divmod(max(0, int(seconds)), 60)
            await ctx.send(
                embed=Embed(
                    title="⏩ Position Updated",
                    description=f"Seeked track to `{m}:{s:02d}`.",
                    color=Embed.Color.GREEN,
                )
            )

        @self.command(name="filter", description="Applies a real-time FFmpeg audio filter effect")
        @describe(effect="Filter: off, bassboost, nightcore, vaporwave, 8d, treble, karaoke, echo")
        async def filter_cmd(
            ctx,
            effect: Literal[
                "off", "bassboost", "nightcore", "vaporwave", "8d", "treble", "karaoke", "echo"
            ],
        ):
            await ctx.defer()
            player = self.bot.get_music_player(ctx.guild_id)
            await player.set_filter(effect)
            await ctx.send(
                embed=Embed(
                    title="🎛️ Audio Filter",
                    description=f"Audio filter set to **`{effect}`**.",
                    color=Embed.Color.BLURPLE,
                )
            )

        @self.command(name="loop", description="Changes the repeat mode (off, track, queue)")
        @describe(mode="Repeat mode: off, track, or queue")
        async def loop_cmd(ctx, mode: Literal["off", "track", "queue"]):
            await ctx.defer()
            player = self.bot.get_music_player(ctx.guild_id)
            player.loop_mode = mode
            await ctx.send(
                embed=Embed(
                    title="🔁 Loop Mode",
                    description=f"Repeat mode set to **`{mode}`**.",
                    color=Embed.Color.GREEN,
                )
            )

        @self.command(name="shuffle", description="Shuffles the tracks in the queue")
        async def shuffle_cmd(ctx):
            await ctx.defer()
            player = self.bot.get_music_player(ctx.guild_id)
            count = player.shuffle()
            await ctx.send(
                embed=Embed(
                    title="🔀 Queue Shuffled",
                    description=f"Shuffled **{count}** tracks in the queue.",
                    color=Embed.Color.GREEN,
                )
            )

        @self.command(name="voice_status", description="Sets the custom status text of the current voice channel")
        @describe(status="Status text for the voice channel")
        async def voice_status_cmd(ctx, status: str):
            await ctx.defer()
            vc = ctx.voice_client
            if not vc:
                await ctx.send(embed=create_error_embed("The bot must be connected to a voice channel!"))
                return
            await vc.channel.set_voice_status(status)
            await ctx.send(
                embed=Embed(
                    title="💬 Voice Channel Status Updated",
                    description=f"New status: **{status}**",
                    color=Embed.Color.GREEN,
                )
            )


class ModerationCog(Cog):
    """
    Full Server Moderation Cog (Discord API v10) with automatic Anti-Flood batch deletion,
    Profanity Filter, Bulk/Clone Message Cleanup, Mass Ban, Softban, Warnings, and Channel Locks.
    """

    def __init__(self, bot: Any, enable_auto_guard: bool = True):
        super().__init__(bot)
        self.enable_auto_guard = enable_auto_guard
        self.register_commands()
        if self.enable_auto_guard:
            self.bot.event_handler.register("on_message_create", self._on_message_guard)

    async def _on_message_guard(self, data: Dict[str, Any]) -> None:
        if isinstance(data, dict):
            await self.bot.moderation.inspect_message(data)

    def register_commands(self) -> None:
        @self.command(name="ban", description="Bans a member from the server")
        @has_permissions(ban_members=True)
        @describe(member="Member to ban", reason="Reason for the ban")
        async def ban_cmd(ctx, member: Member, reason: Optional[str] = None):
            await ctx.defer()
            await member.ban(reason=reason, delete_message_days=1)
            embed = (
                Embed(
                    title="🔨 Member Banned",
                    description=f"**{member}** (`{member.id}`) has been banned from the server.",
                    color=Embed.Color.RED,
                )
                .add_field("Moderator", str(ctx.author), inline=True)
                .add_field("Reason", reason or "Not specified", inline=True)
                .set_timestamp()
            )
            await ctx.send(embed=embed)

        @self.command(name="softban", description="Bans and immediately unbans a member to wipe their recent messages")
        @has_permissions(ban_members=True)
        @describe(member="Member to softban", reason="Reason for the softban")
        async def softban_cmd(ctx, member: Member, reason: Optional[str] = None):
            await ctx.defer()
            await member.ban(reason=f"Softban: {reason or 'Message cleanup'}", delete_message_days=7)
            await member.unban(reason="Softban unban")
            await ctx.send(
                embed=Embed(
                    title="🧹 Member Softbanned",
                    description=f"**{member}** was softbanned and their last 7 days of messages were wiped in 2 API calls.",
                    color=Embed.Color.ORANGE,
                )
            )

        @self.command(name="massban", description="Bans up to 200 user IDs in a single API call (Discord API v10 Bulk Ban)")
        @has_permissions(ban_members=True, administrator=True)
        @describe(user_ids="Comma or space-separated list of user IDs", reason="Audit log reason")
        async def massban_cmd(ctx, user_ids: str, reason: Optional[str] = None):
            await ctx.defer()
            ids = [u.strip() for u in user_ids.replace(",", " ").split() if u.strip()]
            if not ids:
                await ctx.send(embed=create_error_embed("Please provide at least one valid user ID."))
                return
            guild = await ctx.get_guild()
            res = await guild.bulk_ban(ids[:200], delete_message_days=1, reason=reason)
            banned_count = len(res.get("banned_users", ids)) if isinstance(res, dict) else len(ids)
            await ctx.send(
                embed=Embed(
                    title="⚡ Mass Ban Executed (1 API Call)",
                    description=f"Banned **{banned_count}** account(s) via native Bulk Ban endpoint.",
                    color=Embed.Color.RED,
                )
            )

        @self.command(name="unban", description="Revokes a user ban by User ID")
        @has_permissions(ban_members=True)
        @describe(user_id="User ID to unban", reason="Reason")
        async def unban_cmd(ctx, user_id: str, reason: Optional[str] = None):
            await ctx.defer()
            guild = await ctx.get_guild()
            await guild.unban(user_id, reason=reason)
            await ctx.send(
                embed=Embed(
                    title="🔓 User Unbanned",
                    description=f"User `{user_id}` has been unbanned.",
                    color=Embed.Color.GREEN,
                )
            )

        @self.command(name="kick", description="Kicks a member from the server")
        @has_permissions(kick_members=True)
        @describe(member="Member to kick", reason="Reason for kicking")
        async def kick_cmd(ctx, member: Member, reason: Optional[str] = None):
            await ctx.defer()
            await member.kick(reason=reason)
            await ctx.send(
                embed=Embed(
                    title="👢 Member Kicked",
                    description=f"**{member}** has been kicked. Reason: {reason or 'Not specified'}",
                    color=Embed.Color.ORANGE,
                )
            )

        @self.command(name="timeout", description="Applies a temporary communication timeout (mute) to a member")
        @has_permissions(moderate_members=True)
        @describe(member="Target member", minutes="Duration in minutes (0 to remove)", reason="Reason")
        async def timeout_cmd(ctx, member: Member, minutes: int, reason: Optional[str] = None):
            await ctx.defer()
            await member.timeout(minutes * 60 if minutes > 0 else None, reason=reason)
            if minutes > 0:
                await ctx.send(
                    embed=Embed(
                        title="🔇 Member Timed Out",
                        description=f"**{member}** has been timed out for **{minutes} minute(s)**.\nReason: {reason or 'Not specified'}",
                        color=Embed.Color.ORANGE,
                    )
                )
            else:
                await ctx.send(
                    embed=Embed(
                        title="🔊 Timeout Removed",
                        description=f"Timeout removed for **{member}**.",
                        color=Embed.Color.GREEN,
                    )
                )

        @self.command(name="warn", description="Issues a formal warning to a member")
        @has_permissions(moderate_members=True)
        @describe(member="Member to warn", reason="Warning reason")
        async def warn_cmd(ctx, member: Member, reason: str):
            await ctx.defer()
            count = self.bot.moderation.add_warning(
                ctx.guild_id, member.id, ctx.author.id if ctx.author else "mod", reason
            )
            await ctx.send(
                embed=Embed(
                    title="⚠️ Member Warned",
                    description=f"**{member}** received warning **#{count}**.",
                    color=Embed.Color.GOLD,
                ).add_field("Reason", reason, inline=False)
            )

        @self.command(name="warnings", description="Lists all active warnings for a member")
        @has_permissions(moderate_members=True)
        @describe(member="Member to inspect")
        async def warnings_cmd(ctx, member: Member):
            await ctx.defer()
            records = self.bot.moderation.get_warnings(ctx.guild_id, member.id)
            if not records:
                await ctx.send(f"✅ **{member}** has no active warnings.")
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

        @self.command(name="clear_warnings", description="Clears all warnings for a member")
        @has_permissions(moderate_members=True)
        @describe(member="Member whose warnings will be cleared")
        async def clear_warnings_cmd(ctx, member: Member):
            await ctx.defer()
            removed = self.bot.moderation.clear_warnings(ctx.guild_id, member.id)
            await ctx.send(
                embed=Embed(
                    title="🧹 Warnings Cleared",
                    description=f"Cleared **{removed}** warning(s) for **{member}**.",
                    color=Embed.Color.GREEN,
                )
            )

        @self.command(name="purge", description="Bulk-deletes messages in batches of 100 without hammering the API")
        @has_permissions(manage_messages=True)
        @describe(amount="Number of messages to delete (1 to 1000)")
        async def purge_cmd(ctx, amount: int):
            await ctx.defer(ephemeral=True)
            ch = await TextChannel.from_channel_id(self.bot, ctx.guild_id, ctx.channel_id)
            deleted = await ch.purge(limit=min(1000, max(1, int(amount))))
            batches_used = max(1, (len(deleted) + 99) // 100) if deleted else 0
            await ctx.send(
                f"🗑️ Bulk-deleted **{len(deleted)}** messages using only **{batches_used}** bulk-delete API call(s).",
                ephemeral=True,
            )

        @self.command(name="purge_user", description="Bulk-deletes recent messages from a specific user in batches")
        @has_permissions(manage_messages=True)
        @describe(member="Target user whose messages will be removed", scan_limit="Number of recent messages to scan (up to 500)")
        async def purge_user_cmd(ctx, member: Member, scan_limit: Optional[int] = 200):
            await ctx.defer(ephemeral=True)
            ch = await TextChannel.from_channel_id(self.bot, ctx.guild_id, ctx.channel_id)
            deleted = await ch.purge(
                limit=min(500, max(1, int(scan_limit or 200))),
                check=lambda m: str(m.get("author", {}).get("id")) == str(member.id),
            )
            await ctx.send(
                f"🗑️ Bulk-deleted **{len(deleted)}** message(s) from **{member}** without single-delete API spam.",
                ephemeral=True,
            )

        @self.command(name="clean_all", description="Wipes all messages in the channel using Clone (2 API calls) or Batched Bulk-Delete")
        @has_permissions(manage_channels=True, manage_messages=True)
        @describe(mode="clone (instant full wipe in 2 API calls) or batch (in-place bulk delete)")
        async def clean_all_cmd(ctx, mode: Literal["clone", "batch"] = "batch"):
            await ctx.defer(ephemeral=True)
            ch = await TextChannel.from_channel_id(self.bot, ctx.guild_id, ctx.channel_id)
            if mode == "clone":
                new_ch = await ch.clean_all_messages(
                    strategy="clone", reason=f"Clean all requested by {ctx.author}"
                )
                if hasattr(new_ch, "send"):
                    await new_ch.send(
                        embed=Embed(
                            title="✨ Channel Wiped Clean",
                            description=f"All messages were wiped in **2 API calls** (clone + delete) by {ctx.author.mention}.",
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

        @self.command(name="slowmode", description="Sets the channel slowmode delay")
        @has_permissions(manage_channels=True)
        @describe(seconds="Seconds between messages (0 to disable)")
        async def slowmode_cmd(ctx, seconds: int):
            await ctx.defer()
            ch = await TextChannel.from_channel_id(self.bot, ctx.guild_id, ctx.channel_id)
            await ch.set_slowmode(seconds)
            await ctx.send(
                embed=Embed(
                    title="⏱️ Slowmode Updated",
                    description=f"Slowmode set to **{seconds}s** in this channel.",
                    color=Embed.Color.BLURPLE,
                )
            )

        @self.command(name="lock", description="Locks the current channel for regular members")
        @has_permissions(manage_channels=True)
        async def lock_cmd(ctx):
            await ctx.defer()
            ch = await ctx.get_channel()
            await ch.set_lock(True, reason=f"Locked by {ctx.author}")
            await ctx.send(
                embed=Embed(
                    title="🔒 Channel Locked",
                    description="This channel has been locked for regular members.",
                    color=Embed.Color.RED,
                )
            )

        @self.command(name="unlock", description="Unlocks the current channel")
        @has_permissions(manage_channels=True)
        async def unlock_cmd(ctx):
            await ctx.defer()
            ch = await ctx.get_channel()
            await ch.set_lock(False, reason=f"Unlocked by {ctx.author}")
            await ctx.send(
                embed=Embed(
                    title="🔓 Channel Unlocked",
                    description="This channel has been unlocked.",
                    color=Embed.Color.GREEN,
                )
            )

        @self.command(name="profanity_add", description="Adds blocked words to the real-time profanity filter")
        @has_permissions(manage_guild=True)
        @describe(words="Comma-separated list of words to block")
        async def profanity_add_cmd(ctx, words: str):
            await ctx.defer(ephemeral=True)
            items = [w.strip() for w in words.split(",") if w.strip()]
            added = self.bot.moderation.profanity.add_words(items)
            await ctx.send(
                embed=Embed(
                    title="🛡️ Profanity Filter Updated",
                    description=f"Added **{added}** new word(s). Total blocked words: **{len(self.bot.moderation.profanity.blocked_words)}**.",
                    color=Embed.Color.GREEN,
                ),
                ephemeral=True,
            )

        @self.command(name="profanity_remove", description="Removes words from the profanity filter")
        @has_permissions(manage_guild=True)
        @describe(words="Comma-separated list of words to remove")
        async def profanity_remove_cmd(ctx, words: str):
            await ctx.defer(ephemeral=True)
            items = [w.strip() for w in words.split(",") if w.strip()]
            removed = self.bot.moderation.profanity.remove_words(items)
            await ctx.send(
                embed=Embed(
                    title="🛡️ Profanity Filter Updated",
                    description=f"Removed **{removed}** word(s). Remaining: **{len(self.bot.moderation.profanity.blocked_words)}**.",
                    color=Embed.Color.GOLD,
                ),
                ephemeral=True,
            )

        @self.command(name="profanity_list", description="Displays the currently blocked profanity words")
        @has_permissions(manage_guild=True)
        async def profanity_list_cmd(ctx):
            await ctx.defer(ephemeral=True)
            words = sorted(self.bot.moderation.profanity.blocked_words)
            formatted = ", ".join(f"`{w}`" for w in words[:100]) or "None"
            await ctx.send(
                embed=Embed(
                    title=f"🚫 Blocked Profanity List ({len(words)})",
                    description=formatted,
                    color=Embed.Color.BLURPLE,
                ),
                ephemeral=True,
            )

        @self.command(name="automod_sync", description="Syncs the profanity filter and anti-mention rules to Discord AutoMod v10")
        @has_permissions(manage_guild=True)
        async def automod_sync_cmd(ctx):
            await ctx.defer()
            rule = await self.bot.moderation.profanity.sync_to_discord_automod(
                self.bot, ctx.guild_id
            )
            await ctx.send(
                embed=Embed(
                    title="✅ Synced with Discord AutoMod v10",
                    description=f"Rule **{rule.name}** (`{rule.id}`) is now active at the Discord server level.",
                    color=Embed.Color.GREEN,
                )
            )

        @self.command(name="antiflood_config", description="Configures automatic anti-flood protection settings")
        @has_permissions(manage_guild=True)
        @describe(
            max_messages="Maximum messages allowed within the time window (default: 5)",
            window_seconds="Sliding window in seconds (default: 5)",
            max_mentions="Max mentions per message before auto-removal (default: 5)",
            enabled="Enable or disable anti-flood protection",
        )
        async def antiflood_config_cmd(
            ctx,
            max_messages: int = 5,
            window_seconds: int = 5,
            max_mentions: int = 5,
            enabled: bool = True,
        ):
            await ctx.defer()
            cfg = self.bot.moderation.antiflood.config
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
                .add_field("Max Messages / Window", f"`{cfg.max_messages}` msgs / `{cfg.window_seconds:.0f}s`", inline=True)
                .add_field("Max Mentions", f"`{cfg.max_mentions}`", inline=True)
            )

        @self.command(name="modstats", description="Displays moderation statistics and API call savings from batch deletion")
        @has_permissions(moderate_members=True)
        async def modstats_cmd(ctx):
            await ctx.defer()
            mod = self.bot.moderation
            bd = mod.batch_deleter
            embed = (
                Embed(
                    title="📊 Server Moderation & API Efficiency Stats",
                    color=Embed.Color.BLURPLE,
                )
                .add_field("Flood Incidents Blocked", str(mod.flood_incidents_handled), inline=True)
                .add_field("Profanity Blocked", str(mod.profanity_incidents_handled), inline=True)
                .add_field("Auto-Timeouts Issued", str(mod.auto_timeouts_issued), inline=True)
                .add_field("Messages Batch-Deleted", str(bd.total_messages_deleted), inline=True)
                .add_field("Bulk API Calls Used", str(bd.total_api_calls_used), inline=True)
                .add_field("API Calls Saved", f"**{bd.api_calls_saved}**", inline=True)
            )
            await ctx.send(embed=embed)


class UtilityCog(Cog):
    """Built-in Utility, Server Info, and Native Polls Cog (Discord API v10)."""

    def __init__(self, bot: Any):
        super().__init__(bot)
        self.register_commands()

    def register_commands(self) -> None:
        @self.command(name="ping", description="Shows the bot's current Gateway latency")
        async def ping_cmd(ctx):
            ms = round(self.bot.latency * 1000, 1) if self.bot.latency else 0.0
            embed = Embed(
                title="🏓 Pong!",
                description=f"Gateway Latency: **`{ms} ms`**",
                color=Embed.Color.GREEN,
            )
            await ctx.send(embed=embed)

        @self.command(name="userinfo", description="Displays detailed information about a member")
        @describe(user="Member to inspect (optional)")
        async def userinfo_cmd(ctx, user: Optional[Member] = None):
            await ctx.defer()
            target = user or ctx.author
            if not target:
                await ctx.send(embed=create_error_embed("User not found."))
                return
            embed = (
                Embed(
                    title=f"👤 User Info: {target.display_name}",
                    color=target.color or Embed.Color.BLURPLE,
                )
                .set_thumbnail(target.avatar_url)
                .add_field("Username", str(target), inline=True)
                .add_field("ID", f"`{target.id}`", inline=True)
                .add_field("Account Created", format_discord_timestamp(target.created_at, "F"), inline=False)
            )
            if target.joined_at:
                embed.add_field("Joined Server", format_discord_timestamp(target.joined_at, "R"), inline=True)
            if target.roles:
                embed.add_field("Roles", f"{len(target.roles)} role(s)", inline=True)
            await ctx.send(embed=embed)

        @self.command(name="serverinfo", description="Displays detailed information about the current server")
        async def serverinfo_cmd(ctx):
            await ctx.defer()
            guild = await ctx.get_guild()
            if not guild:
                await ctx.send(embed=create_error_embed("This command is only available inside servers."))
                return
            embed = (
                Embed(
                    title=f"🏰 {guild.name}",
                    description=guild.description or "No server description set.",
                    color=Embed.Color.BLURPLE,
                )
                .add_field("Server ID", f"`{guild.id}`", inline=True)
                .add_field("Owner", f"<@{guild.owner_id}>", inline=True)
                .add_field("Members", str(guild.member_count or "N/A"), inline=True)
                .add_field("Roles", str(len(guild.roles)), inline=True)
                .add_field("Boost Tier", f"Tier {guild.premium_tier} ({guild.premium_subscription_count} boosts)", inline=True)
                .add_field("Created On", format_discord_timestamp(guild.created_at, "D"), inline=True)
            )
            if guild.icon_url:
                embed.set_thumbnail(guild.icon_url)
            await ctx.send(embed=embed)

        @self.command(name="avatar", description="Displays the high-resolution avatar of a user")
        @describe(user="User whose avatar will be displayed")
        async def avatar_cmd(ctx, user: Optional[Member] = None):
            await ctx.defer()
            target = user or ctx.author
            embed = Embed(
                title=f"🖼️ Avatar of {target.display_name}",
                color=Embed.Color.BLURPLE,
            ).set_image(target.avatar_url)
            await ctx.send(embed=embed)

        @self.command(name="poll", description="Creates a native Discord API v10 Poll")
        @describe(
            question="Poll question",
            options="Answers separated by vertical bar | (e.g. Yes | No | Maybe)",
            hours="Duration in hours (default: 24)",
        )
        async def poll_cmd(ctx, question: str, options: str, hours: Optional[int] = 24):
            await ctx.defer()
            choices = [o.strip() for o in options.split("|") if o.strip()]
            if len(choices) < 2:
                await ctx.send(
                    embed=create_error_embed("Provide at least 2 options separated by `|` (e.g. `Option 1 | Option 2`).")
                )
                return
            poll = Poll(question=question, answers=choices[:10], duration_hours=hours or 24)
            await ctx.send(poll=poll)


class FunCog(Cog):
    """Built-in Fun and Minigames Cog for Discord servers."""

    def __init__(self, bot: Any):
        super().__init__(bot)
        self.register_commands()

    def register_commands(self) -> None:
        @self.command(name="dice", description="Rolls an N-sided die")
        @describe(sides="Number of sides on the die (default: 6)")
        async def dice_cmd(ctx, sides: Optional[int] = 6):
            max_sides = max(2, min(1000, int(sides or 6)))
            value = random.randint(1, max_sides)
            await ctx.send(
                embed=Embed(
                    title="🎲 Dice Roll",
                    description=f"You rolled a **d{max_sides}** and got **`{value}`**!",
                    color=Embed.Color.GOLD,
                )
            )

        @self.command(name="coinflip", description="Flips a coin (Heads or Tails)")
        async def coinflip_cmd(ctx):
            result = random.choice(["🪙 **Heads**!", "👑 **Tails**!"])
            await ctx.send(
                embed=Embed(title="Coin Flip", description=result, color=Embed.Color.GOLD)
            )

        @self.command(name="8ball", description="Asks the Magic 8-Ball a question")
        @describe(question="Your question")
        async def eightball_cmd(ctx, question: str):
            answers = [
                "It is certain!",
                "Without a doubt.",
                "All signs point to yes.",
                "Most likely.",
                "Ask again later.",
                "Better not tell you now.",
                "Don't count on it.",
                "My sources say no.",
                "Very doubtful.",
            ]
            embed = (
                Embed(title="🎱 Magic 8-Ball", color=Embed.Color.PURPLE)
                .add_field("Question", question, inline=False)
                .add_field("Answer", random.choice(answers), inline=False)
            )
            await ctx.send(embed=embed)
