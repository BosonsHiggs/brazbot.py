import asyncio
import os
from typing import Literal
from brazbot.bot import DiscordBot
from brazbot.decorators import sync_slash_commands, rate_limit

MY_GUILD = "1130837584742977697"

class MyBot(DiscordBot):
    def __init__(self, token, command_prefix=None, intents=None):
        super().__init__(token, command_prefix, intents)

    async def on_ready(self, data):
        print(f"Bot is ready! Application ID: {self.application_id}")
        await self.command_handler.sync_commands(guild_id=MY_GUILD)

    async def on_message_create(self, data):
        print(f"Message create event received: {data}")

    async def on_error(self, data):
        if 'time_left' in data:
            time_left = data['time_left']
            error_message = f"Você atingiu o limite de uso deste comando. Tente novamente em {time_left:.2f} segundos."
            channel_id = data['channel_id']
            await self.message_handler.send_message(channel_id, error_message)
        else:
            error_message = data.get('message', 'Ocorreu um erro.')
            print(error_message)

# Define the required intents
intents = ["GUILD_MESSAGES", "MESSAGE_CONTENT"]

token = os.getenv("DISCORD_TOKEN")
bot = MyBot(token, command_prefix="!", intents=intents)

@bot.command(name="helloname", description="Set your name")
@sync_slash_commands(guild_id=MY_GUILD)
@rate_limit(limit=1, per=60, scope="user")
async def helloname_command(ctx, name: str):
    await ctx.bot.message_handler.send_interaction(ctx.interaction, content=f"Hello, {name}!")

@bot.command(name="status", description="Set your status")
@sync_slash_commands(guild_id=MY_GUILD)
@rate_limit(limit=1, per=60, scope="user")
async def status_command(ctx, status: Literal['online', 'offline', 'idle']):
    await ctx.bot.message_handler.send_interaction(ctx.interaction, content=f"Setting status to {status}")

# Main function to start the bot
async def main():
    await bot.start()

# Run the bot asynchronously
asyncio.run(main())
