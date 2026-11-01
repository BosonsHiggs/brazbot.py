"""
Components v2 & Interactive Views Example — brazbot v2.0.0
==========================================================
Demonstrates Discord API v10 Components v2 (`IS_COMPONENTS_V2 = 1 << 15`),
containers, text displays, media galleries, buttons, and modal dialogs.
"""

import os
from brazbot import (
    ActionRow,
    Button,
    ButtonStyle,
    Client,
    Container,
    Intents,
    InteractionContext,
    Separator,
    TextDisplay,
)

bot = Client(command_prefix="!", intents=Intents.default(), sync_commands=True)


@bot.slash_command(name="card", description="Render a Discord Components v2 layout card")
async def slash_card(ctx: InteractionContext):
    container = Container(
        TextDisplay("## BrazBot v2.0.0 Components v2"),
        Separator(),
        TextDisplay("Native layout containers without legacy embed limits."),
        accent_color=0x5865F2,
    )
    row = ActionRow(Button(label="Documentation", style=ButtonStyle.LINK, url="https://github.com/BosonsHiggs/brazbot.py"))
    await ctx.respond(components=[container.to_dict(), row.to_dict()], flags=1 << 15)


if __name__ == "__main__":
    bot.run(os.environ["DISCORD_TOKEN"])
