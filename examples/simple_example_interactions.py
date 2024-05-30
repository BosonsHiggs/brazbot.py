import asyncio
import os
import logging
from brazbot.bot import DiscordBot
from brazbot.decorators import is_admin, sync_slash_commands, rate_limit
from brazbot.utils import create_embed, format_command_response
from brazbot.file import File

# Define os intents necessários
intents = ["GUILD_MESSAGES", "MESSAGE_CONTENT"]

MY_GUILD = "1130837584742977697"

logging.basicConfig(level=logging.DEBUG)
logging.getLogger().setLevel(logging.CRITICAL)

class MyBot(DiscordBot):
    def __init__(self, token, command_prefix=None, intents=None):
        super().__init__(token, command_prefix, intents)

    async def on_ready(self, data):
        logging.info(f"Bot is ready! Application ID: {self.application_id}")
        #await self.command_handler.sync_commands(guild_id=MY_GUILD)

    async def on_message_create(self, data):
        logging.info(f"Message create event received: {data}")

    async def on_error(self, data):
        if 'time_left' in data:
            time_left = data['time_left']
            error_message = f"Você atingiu o limite de uso deste comando. Tente novamente em {time_left:.2f} segundos."
            channel_id = data['channel_id']
            await self.message_handler.send_message(channel_id, error_message)
        else:
            error_message = data.get('message', 'Ocorreu um erro.')
            logging.error(error_message)

token = os.getenv("DISCORD_TOKEN")
if not token:
    logging.error("DISCORD_TOKEN not found in environment variables.")
    exit(1)

bot = MyBot(token, command_prefix="!", intents=intents)

@bot.command(name="hello", description="Says hello")
@sync_slash_commands(guild_id=MY_GUILD)
async def hello_command(ctx):
    embed = create_embed("Saudações", "Olá, mundo!")
    logging.debug(f"Interaction: {ctx.interaction}")
    await ctx.bot.message_handler.send_interaction(ctx.interaction, embed=embed, ephemeral=True)

@bot.command(name="echo", description="Repeats your message")
@sync_slash_commands(guild_id=MY_GUILD)
@rate_limit(limit=1, per=60, scope="user")
async def echo_command(ctx, message: str):
    response = format_command_response(message)
    await ctx.bot.message_handler.send_interaction(ctx.interaction, content=response, ephemeral=True)

@bot.command(name="send_file", description="Sends a file")
@sync_slash_commands(guild_id=MY_GUILD)
@rate_limit(limit=1, per=60, scope="user")
async def send_file_command(ctx, file: bytes):
    await ctx.bot.message_handler.send_interaction(ctx.interaction, content="Here is your file:", files=[file])

async def main():
    await bot.start()

# Executa o bot de forma assíncrona
if __name__ == "__main__":
    asyncio.run(main())
