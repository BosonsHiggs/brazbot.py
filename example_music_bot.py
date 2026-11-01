"""
Music Bot Example — brazbot v2.0.0 (Discord API v10 + Voice Gateway v8)
=======================================================================

Demonstrates joining voice channels, queuing YouTube/direct audio streams via
``yt-dlp`` + ``FFmpegOpusAudio``, volume control, pause/resume/skip, and slash commands.
"""

from __future__ import annotations

import os
from brazbot import Client, CommandContext, Intents, MusicCog, VoiceCog

intents = Intents.default() | Intents.MESSAGE_CONTENT | Intents.GUILD_VOICE_STATES
bot = Client(command_prefix="!", intents=intents, sync_commands=True)

# Register built-in Voice & Music Cogs (!join, !leave, !play, !pause, !resume, !skip, !queue, !stop, !volume)
bot.add_cog(VoiceCog(bot))
bot.add_cog(MusicCog(bot))


@bot.event
async def on_ready():
    print(f"[MusicBot] Connected as {bot.user} — Voice Gateway v8 + AEAD encryption ready.")


if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise SystemExit("Set DISCORD_TOKEN environment variable to run the music bot.")
    bot.run(token)
