"""
Interactive Buttons, Dropdowns, and Modals Example — brazbot.py v2.0.0
======================================================================
Demonstrates interactive message components (`ActionRow`, `Button`, `Dropdown`, `Form`).
"""

import os
from brazbot import ActionRow, Bot, Button, ButtonStyle, CommandContext, Embed, Intents, View

bot = Bot(token=os.getenv("DISCORD_TOKEN", ""), command_prefix="!", intents=Intents.default())


@bot.command(name="card", description="Sends an interactive message with Buttons")
async def card_cmd(ctx: CommandContext):
    view = View(
        ActionRow(
            Button(
                label="GitHub Repository",
                style=ButtonStyle.LINK,
                url="https://github.com/BosonsHiggs/brazbot.py",
            )
        )
    )
    embed = Embed(
        title="BrazBot v2.0.0 Interactive Components",
        description="Click the button below to visit the official repository.",
        color=Embed.Color.BLURPLE,
    )
    await ctx.send(embed=embed, components=view)


if __name__ == "__main__":
    bot.run(os.environ["DISCORD_TOKEN"])
