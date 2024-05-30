import asyncio
import os
from typing import Union
from brazbot.bot import DiscordBot
from brazbot.decorators import sync_slash_commands, rate_limit
from brazbot.greedy_union import Greedy
from brazbot.utils import create_error_embed

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

            embed = create_error_embed(error_message)

            if self.interaction:
                await self.message_handler.send_interaction(
                    self.interaction,
                    embeds=[embed]
                )
            else:
                print(error_message)
        else:
            error_message = data.get('message', 'Ocorreu um erro.')
            print(error_message)

# Define the required intents
intents = ["GUILD_MESSAGES", "MESSAGE_CONTENT"]

token = os.getenv("DISCORD_TOKEN")
bot = MyBot(token, command_prefix="!", intents=intents)

@bot.command(name="multiply", description="Multiply numbers")
@sync_slash_commands(guild_id=MY_GUILD)
@rate_limit(limit=1, per=60, scope="user")
async def multiply_command(ctx, numbers: Greedy[Union[int, float]]):
    print("---------------------------------------------")
    await ctx.defer()  # Defer the response
    print("---------------------------------------------")
    try:
        result = 1

        for num in numbers:
            result *= num

        await ctx.send_followup_message(content=f"The result is {result}")
    except Exception as e:
        print(e)

@bot.command(name="quickreply", description="Quick reply example")
@sync_slash_commands(guild_id=MY_GUILD)
@rate_limit(limit=1, per=60, scope="user")
async def quickreply_command(ctx):
    await ctx.bot.message_handler.send_interaction(ctx.interaction, content="This is a quick reply!")

# Main function to start the bot
async def main():
    await bot.start()

# Run the bot asynchronously
asyncio.run(main())
