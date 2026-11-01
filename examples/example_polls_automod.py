"""
Polls & AutoMod v10 Example — brazbot.py v2.0.0
===============================================
Demonstrates creating native Discord Polls and AutoMod rules via Discord API v10.
"""

import os
from brazbot import AutoModRule, Bot, CommandContext, Intents, Poll

bot = Bot(token=os.getenv("DISCORD_TOKEN", ""), command_prefix="!", intents=Intents.default())


@bot.command(name="poll_demo", description="Creates a native Discord API v10 poll")
async def poll_demo_cmd(ctx: CommandContext):
    poll = Poll(
        question="Which Discord API v10 feature is your favorite?",
        answers=[
            "Voice Gateway v8 AEAD",
            "BatchDeleteQueue Anti-Flood",
            "Bulk Ban & AutoMod v10",
        ],
        duration_hours=24,
        allow_multiselect=False,
    )
    await ctx.send(poll=poll)


if __name__ == "__main__":
    bot.run(os.environ["DISCORD_TOKEN"])
