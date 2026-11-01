"""
Voice Call Bridge Example — brazbot v2.0.0
==========================================
Demonstrates Voice Gateway v8 bidirectional audio reception and transmission.
"""

import os
from brazbot import Client, CommandContext, Intents

bot = Client(command_prefix="!", intents=Intents.default() | Intents.MESSAGE_CONTENT | Intents.GUILD_VOICE_STATES)


@bot.command(name="join_call", description="Join a voice channel with full-duplex Opus support")
async def join_call(ctx: CommandContext, channel_id: str):
    vc = await bot.join_voice_channel(int(ctx.guild_id), int(channel_id))
    await ctx.reply(f"Joined <#{channel_id}> with encryption `{vc.encryption_mode}`.")


if __name__ == "__main__":
    bot.run(os.environ["DISCORD_TOKEN"])
