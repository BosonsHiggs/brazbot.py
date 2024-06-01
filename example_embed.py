import asyncio
import os
import logging
from brazbot.bot import DiscordBot
from brazbot.decorators import sync_slash_commands, rate_limit
from brazbot.embed import Embed

logging.basicConfig(level=logging.DEBUG)

MY_GUILD = "1130837584742977697"

class MyBot(DiscordBot):
    async def on_ready(self, data):
        logging.info(f"Bot is ready! Application ID: {self.application_id}")
        await self.command_handler.sync_commands(guild_id=MY_GUILD)

# Define os intents necessários
intents = ["GUILD_MESSAGES", "MESSAGE_CONTENT"]

token = os.getenv("DISCORD_TOKEN")
bot = MyBot(token, command_prefix="!", intents=intents)

@bot.command(name="send_embed", description="Send a complete embed")
@sync_slash_commands(guild_id=MY_GUILD)
@rate_limit(limit=1, per=60, scope="user")
async def send_embed_command(ctx):
    await ctx.defer(ephemeral=True)
    
    embed = Embed(
        title="Sample Embed",
        description="This is an example of an embed.",
        url="https://github.com/BosonsHiggs/brazbot.py/",
        color=0x00ff00
    ).set_timestamp().set_footer(
        text="Footer Text",
        icon_url="https://i.imgur.com/hLTgRY1.png"
    ).set_image(
        url="https://i.imgur.com/hLTgRY1.png"
    ).set_thumbnail(
        url="https://i.imgur.com/hLTgRY1.png"
    ).set_author(
        name="Author Name",
        url="https://github.com/BosonsHiggs/brazbot.py/",
        icon_url="https://i.imgur.com/hLTgRY1.png"
    ).add_field(
        name="Field 1", value="Value 1", inline=False
    ).add_field(
        name="Field 2", value="Value 2"
    )

    await ctx.send_followup_message(content="Here is a complete embed:", embed=embed.to_dict())

# Função principal para iniciar o bot
async def main():
    try:
        await bot.start()
    except Exception as e:
        logging.error(f"Error in main: {e}")

asyncio.run(main())
