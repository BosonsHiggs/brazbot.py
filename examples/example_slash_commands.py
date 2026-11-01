"""
Slash Commands Example — brazbot.py v2.0.0
==========================================
Demonstrates hybrid/slash commands with typed options and descriptions.
"""

import os
from brazbot import Bot, CommandContext, Intents, describe

bot = Bot(token=os.getenv("DISCORD_TOKEN", ""), command_prefix="!", intents=Intents.default())


@bot.command(name="echo", description="Repeats a text message")
@describe(text="Text to repeat")
async def slash_echo(ctx: CommandContext, text: str):
    await ctx.send(f"You said: {text}")


if __name__ == "__main__":
    bot.run(os.environ["DISCORD_TOKEN"])
