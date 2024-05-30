import asyncio
import os
from typing import Optional
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
        error_message = data.get('message', 'Ocorreu um erro.')
        print(error_message)

# Define the required intents
intents = ["GUILD_MESSAGES", "MESSAGE_CONTENT"]

token = os.getenv("DISCORD_TOKEN")
bot = MyBot(token, command_prefix="!", intents=intents)

@bot.command(name="greet", description="Greet a user")
@sync_slash_commands(guild_id=MY_GUILD)
@rate_limit(limit=1, per=60, scope="user")
async def greet_command(ctx, user: Optional[str] = None):
    await ctx.defer()
    greeting = f"Hello, {user}!" if user else "Hello!"
    await ctx.send_followup_message(content=greeting)

# Main function to start the bot
async def main():
    await bot.start()

# Run the bot asynchronously
asyncio.run(main())
