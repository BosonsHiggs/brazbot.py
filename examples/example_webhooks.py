"""
Webhooks Example — brazbot v2.0.0
=================================
Demonstrates executing and managing Discord Webhooks via API v10.
"""

import os
from brazbot import Client, CommandContext, Embed, Intents

bot = Client(command_prefix="!", intents=Intents.default() | Intents.MESSAGE_CONTENT)


@bot.command(name="webhook_demo", description="Create and execute a channel webhook")
async def webhook_demo(ctx: CommandContext):
    wh = await bot._http.create_webhook(ctx.channel_id, name="BrazBot Webhook")
    await bot._http.execute_webhook(wh["id"], wh["token"], content="Hello from BrazBot v2.0.0 Webhook!")
    await ctx.reply("Webhook executed!")


if __name__ == "__main__":
    bot.run(os.environ["DISCORD_TOKEN"])
