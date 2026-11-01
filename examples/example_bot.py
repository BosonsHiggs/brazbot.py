"""
Basic Bot Example — brazbot.py v2.0.0
=====================================
Demonstrates hybrid prefix (`!`) and slash (`/`) commands, embeds, and Gateway v10 events.
"""

import os
from brazbot import Bot, CommandContext, Embed, Intents

bot = Bot(
    token=os.getenv("DISCORD_TOKEN", ""),
    command_prefix="!",
    intents=Intents.default() | Intents.MESSAGE_CONTENT,
)


@bot.event
async def on_ready(data):
    user = data.get("user", {}) if isinstance(data, dict) else {}
    print(f"Bot online as {user.get('username')}")


@bot.command(name="ping", description="Checks Gateway latency")
async def ping_cmd(ctx: CommandContext):
    ms = round(bot.latency * 1000, 1)
    await ctx.reply(f"Pong! Gateway latency: `{ms} ms`")


@bot.command(name="hello", description="Greets the user via a Discord API v10 Embed")
async def hello_cmd(ctx: CommandContext):
    embed = Embed(
        title="Hello!",
        description=f"Welcome to **brazbot.py v2.0.0**, {ctx.author.mention if ctx.author else 'friend'}!",
        color=Embed.Color.BLURPLE,
    )
    await ctx.send(embed=embed)


if __name__ == "__main__":
    bot.run(os.environ["DISCORD_TOKEN"])
