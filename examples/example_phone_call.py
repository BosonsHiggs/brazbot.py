"""
Full-Duplex Voice Bridge ("Phone Call") Example — brazbot.py v2.0.0
===================================================================
Demonstrates connecting to voice channels using Voice Gateway v8 (`?v=8`)
with 74-byte UDP IP Discovery and AEAD encryption (`aead_aes256_gcm_rtpsize`).
"""

from __future__ import annotations

import os
from typing import Optional
from brazbot import Bot, CommandContext, Intents, VoiceChannel, describe

intents = Intents.default() | Intents.MESSAGE_CONTENT | Intents.GUILD_VOICE_STATES
bot = Bot(token=os.getenv("DISCORD_TOKEN", ""), command_prefix="!", intents=intents)


@bot.event
async def on_ready(data):
    user = data.get("user", {}) if isinstance(data, dict) else {}
    print(f"[PhoneCallBot] Ready as {user.get('username')}")


@bot.command(name="call", description="Connects to a voice channel using Voice Gateway v8")
@describe(channel="Target voice channel to join")
async def cmd_call(ctx: CommandContext, channel: Optional[VoiceChannel] = None):
    await ctx.defer()
    target = channel or (ctx.author.voice.channel if ctx.author and ctx.author.voice else None)
    if not target:
        await ctx.send("Join a voice channel first or specify one!")
        return
    vc = await target.connect()
    await ctx.send(f"Connected to **{target.name}** with Voice Gateway v8 (`{vc.udp.mode}`).")


if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise SystemExit("Please set the DISCORD_TOKEN environment variable before running.")
    bot.run(token)
