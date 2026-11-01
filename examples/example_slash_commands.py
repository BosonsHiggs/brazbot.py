"""
Slash Commands Example — brazbot v2.0.0
=======================================
Demonstrates application commands with typed options, choices, and autocomplete.
"""

import os
from brazbot import ApplicationCommandOption, Client, Intents, InteractionContext

bot = Client(command_prefix="!", intents=Intents.default(), sync_commands=True)


@bot.slash_command(
    name="echo",
    description="Repeat a text message",
    options=[ApplicationCommandOption(name="text", description="Text to repeat", type=3, required=True)],
)
async def slash_echo(ctx: InteractionContext, text: str):
    await ctx.respond(f"You said: {text}")


if __name__ == "__main__":
    bot.run(os.environ["DISCORD_TOKEN"])
