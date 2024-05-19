import asyncio
import os
from brazbot.bot import DiscordBot
from brazbot.decorators import is_admin, sync_slash_commands, rate_limit
from brazbot.utils import create_embed, format_command_response
from brazbot.file import File

MY_GUILD = "1130837584742977697"

class MyBot(DiscordBot):
    def __init__(self, token, command_prefix=None, intents=None):
        super().__init__(token, command_prefix, intents)

    async def on_ready(self, data):
        print(f"Bot is ready! Application ID: {self.application_id}")

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

# Define os intents necessários
intents = ["GUILD_MESSAGES", "MESSAGE_CONTENT"]

token = os.getenv("DISCORD_TOKEN")
bot = MyBot(token, command_prefix="!", intents=intents)

@bot.command(name="hello", description="Says hello")
@sync_slash_commands(guild_id=MY_GUILD)
@is_admin()
@rate_limit(limit=1, per=60, scope="user")
async def hello_command(ctx):
    embed = create_embed("Saudações", "Olá, mundo!")
    await ctx.bot.message_handler.send_interaction(ctx.interaction, embed=embed, ephemeral=True)

@bot.command(name="echo", description="Repeats your message")
@sync_slash_commands(guild_id=MY_GUILD)
@rate_limit(limit=1, per=60, scope="user")
async def echo_command(ctx, *args):
    response = format_command_response(" ".join(args))
    await ctx.bot.message_handler.send_interaction(ctx.interaction, content=response, ephemeral=True)

@bot.command(name="send_file", description="Sends a file")
@sync_slash_commands(guild_id=MY_GUILD)
@rate_limit(limit=1, per=60, scope="user")
async def send_file_command(ctx):
    file = File("path/to/your/file.txt")
    await ctx.bot.message_handler.send_interaction(ctx.interaction, content="Here is your file:", files=[file])

@bot.command(name="sync", description="Sync slash commands with the specified guild")
@sync_slash_commands(guild_id=MY_GUILD)
@rate_limit(limit=1, per=3600, scope="guild")
async def sync_command(ctx):
    """
    Sincroniza comandos slash com a guilda especificada.
    
    Args:
        ctx (CommandContext): O contexto do comando, contendo informações sobre o bot, a mensagem, o autor, etc.
    
    Returns:
        None
    """
    pass

async def main():
    await bot.start()

# Executa o bot de forma assíncrona
asyncio.run(main())
