"""
Polls & AutoMod v10 Example — brazbot v2.0.0
============================================
Demonstrates creating native Discord Polls and AutoMod rules via Discord API v10.
"""

import os
from brazbot import AutoModRule, Client, Intents, InteractionContext, Poll, PollMedia

bot = Client(command_prefix="!", intents=Intents.default(), sync_commands=True)


@bot.slash_command(name="poll", description="Create a native Discord poll")
async def slash_poll(ctx: InteractionContext):
    poll = Poll(
        question=PollMedia(text="Which Discord API v10 feature is your favorite?"),
        answers=[
            PollMedia(text="Voice Gateway v8 AEAD"),
            PollMedia(text="Components v2"),
            PollMedia(text="Bulk Ban & AutoMod"),
        ],
        duration=24,
        allow_multiselect=False,
    )
    await bot._http.send_message(ctx.channel_id, poll=poll.to_dict())
    await ctx.respond("Poll created!", ephemeral=True)


if __name__ == "__main__":
    bot.run(os.environ["DISCORD_TOKEN"])
