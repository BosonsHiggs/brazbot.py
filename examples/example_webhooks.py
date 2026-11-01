"""
Webhooks Example — brazbot.py v2.0.0
====================================
Demonstrates creating and executing Discord Webhooks via API v10.
"""

import os
from brazbot import Bot, CommandContext, Intents, Webhook

bot = Bot(
    token=os.getenv("DISCORD_TOKEN", ""),
    command_prefix="!",
    intents=Intents.default() | Intents.MESSAGE_CONTENT,
)


@bot.command(name="webhook_demo", description="Creates and executes a channel webhook")
async def webhook_demo(ctx: CommandContext):
    await ctx.defer()
    wh = await Webhook.create(bot, ctx.channel_id, name="BrazBot Webhook")
    await wh.send(content="Hello from BrazBot v2.0.0 Webhook!")
    await ctx.send("Webhook executed!")


if __name__ == "__main__":
    bot.run(os.environ["DISCORD_TOKEN"])
