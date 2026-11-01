"""
Basic Bot Example — brazbot v2.0.0
==================================
Demonstrates prefix commands, slash commands, embeds, and Gateway v10 events.
"""

import os
from brazbot import Client, CommandContext, Embed, Intents, InteractionContext

bot = Client(command_prefix="!", intents=Intents.default() | Intents.MESSAGE_CONTENT, sync_commands=True)


@bot.event
async def on_ready():
    print(f"Bot online as {bot.user}")


@bot.command(name="ping", description="Check gateway and REST latency")
async def ping_cmd(ctx: CommandContext):
    await ctx.reply("Pong! BrazBot v2.0.0 is online.")


@bot.slash_command(name="hello", description="Greet the user via a Discord API v10 Slash Command")
async def slash_hello(ctx: InteractionContext):
    embed = Embed(title="Hello!", description=f"Welcome to **brazbot v2.0.0**, <@{ctx.author.id}>!", color=0x5865F2)
    await ctx.respond(embed=embed)


if __name__ == "__main__":
    bot.run(os.environ["DISCORD_TOKEN"])
