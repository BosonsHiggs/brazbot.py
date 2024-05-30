import json
import asyncio
import aiohttp
import logging
import os
from brazbot.bot import DiscordBot
from brazbot.decorators import is_admin, sync_slash_commands, rate_limit
from brazbot.autocomplete import autocomplete_command

# Define os intents necessários
intents = ["GUILD_MESSAGES", "MESSAGE_CONTENT"]
MY_GUILD = "1130837584742977697"

logging.basicConfig(level=logging.CRITICAL)

class MyBot(DiscordBot):
    def __init__(self, token, command_prefix=None, intents=None):
        super().__init__(token, command_prefix, intents)

    async def on_ready(self, data):
        print(f"Bot is ready! Application ID: {self.application_id}")
        #await self.command_handler.sync_commands(guild_id=MY_GUILD)


    async def on_interaction_create(self, interaction):
        if interaction['type'] == 4:  # Type 4 is for autocomplete
            await self.command_handler.handle_autocomplete(interaction)
        else:
            await self.command_handler.handle_command(interaction)

token = os.getenv("DISCORD_TOKEN")
if not token:
    logging.error("DISCORD_TOKEN not found in environment variables.")
    exit(1)

bot = MyBot(token, command_prefix="!", intents=intents)

@autocomplete_command(bot, name="search", description="Search for items")
@sync_slash_commands(guild_id=MY_GUILD)
@rate_limit(limit=1, per=60, scope="user")
async def search_command(ctx, query: str):
    await ctx.defer()
    await ctx.send_followup_message(content=f"The option chosen was {query}.")

# Define as opções de autocomplete
async def autocomplete_query(interaction):
    options = interaction['data']['options']
    focused_option = next((opt for opt in options if opt.get('focused')), None)
    if focused_option:
        query = focused_option['value']
        suggestions = [
            {"name": "Suggestion 1", "value": "suggestion_1"},
            {"name": "Suggestion 2", "value": "suggestion_2"},
            {"name": "Suggestion 3", "value": "suggestion_3"}
        ]
        response_data = {
            "type": 8,  # Autocomplete result type
            "data": {
                "choices": suggestions
            }
        }
        url = f"https://discord.com/api/v10/interactions/{interaction['id']}/{interaction['token']}/callback"
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=response_data) as response:
                if response.status != 200:
                    logging.error(f"Failed to send autocomplete response: {response.status}")

bot.command_handler.register_autocomplete(autocomplete_query, "search", "query")

async def main():
    await bot.start()

# Executa o bot de forma assíncrona
if __name__ == "__main__":
    asyncio.run(main())
