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

@bot.command(name="rate_limits", description="Check rate limits")
@sync_slash_commands(guild_id=MY_GUILD)
async def rate_limits_command(ctx):
    print()
    print()
    print("TESTE")
    rate_limits = await ctx.bot.command_handler.check_rate_limits()
    print(rate_limits)
    formatted_info = "\n".join([f"{info['endpoint']}:\nLimit: {info['limit']}\nRemaining: {info['remaining']}\nReset: {info['reset']}\nReset After: {info['reset_after']}\nBucket: {info['bucket']}\nRetry After: {info['retry_after']}\nGlobal: {info['global']}\n" for info in rate_limits])
    await ctx.send_followup_message(content=f"Rate limit information:\n{formatted_info}")


# Main function to start the bot
async def main():
    await bot.start()

# Run the bot asynchronously
asyncio.run(main())
