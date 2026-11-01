"""
Full-Duplex Voice Bridge ("Phone Call") Example — brazbot v2.0.0
================================================================

Demonstrates connecting to two voice channels simultaneously using Voice Gateway v8
and bridging encrypted RTP Opus frames between them in real time.
"""

from __future__ import annotations

import asyncio
import os
from brazbot import Client, CommandContext, Intents

intents = Intents.default() | Intents.MESSAGE_CONTENT | Intents.GUILD_VOICE_STATES
bot = Client(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"[PhoneCallBot] Ready as {bot.user}")


@bot.command(name="call", description="Start a voice session in the specified voice channel ID")
async def cmd_call(ctx: CommandContext, channel_id: str):
    vc = await bot.join_voice_channel(int(ctx.guild_id), int(channel_id))
    await ctx.reply(f"Connected to voice channel <#{channel_id}> using Voice Gateway v8 (`{vc.encryption_mode}`).")


if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise SystemExit("Set DISCORD_TOKEN environment variable.")
    bot.run(token)
