"""
Music Bot Example — brazbot.py v2.0.0 (Discord API v10 + Voice Gateway v8)
==========================================================================
Demonstrates joining voice channels, queuing YouTube/direct audio streams via
`yt-dlp` + `FFmpegAudioSource`, real-time audio filters, volume control, and slash commands.
"""

from __future__ import annotations

import os
from brazbot import Bot, Intents, MusicCog, UtilityCog

intents = Intents.default() | Intents.MESSAGE_CONTENT | Intents.GUILD_VOICE_STATES
bot = Bot(token=os.getenv("DISCORD_TOKEN", ""), command_prefix="!", intents=intents)

# Register built-in Music & Utility Cogs (/join, /leave, /play, /pause, /resume, /skip, /queue, /stop, /volume, /filter)
bot.add_cog(MusicCog(bot))
bot.add_cog(UtilityCog(bot))


@bot.event
async def on_ready(data):
    user = data.get("user", {}) if isinstance(data, dict) else {}
    print(f"[MusicBot] Connected as {user.get('username')} — Voice Gateway v8 + AEAD encryption ready.")


if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise SystemExit("Please set the DISCORD_TOKEN environment variable before running.")
    bot.run(token)
