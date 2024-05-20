import os
from brazbot.bot import DiscordBot
from brazbot.cogs import Cog

# Inicialize o bot com o token e prefixo de comando
bot = DiscordBot(token=os.getenv("DISCORD_TOKEN"), command_prefix="!", intents=["GUILD_MESSAGES", "MESSAGE_CONTENT"])

MY_GUILD = "1130837584742977697"
   
class MyCog(Cog):
    def __init__(self, bot):
        super().__init__(bot)
        self.add_commands()
        self.register_events()

    def add_commands(self):
        @self.command(name="hello", description="Says hello")
        async def hello_command(ctx):
            await ctx.bot.message_handler.send_message(ctx.channel_id, content="Hello, world!")

        @self.command(name="goodbye", description="Says goodbye")
        async def goodbye_command(ctx):
            await ctx.bot.message_handler.send_message(ctx.channel_id, content="Goodbye, world!")

    def register_events(self):
        @self.event
        async def on_ready(data):
            print("Bot is ready!")

# Cria uma instância de MyCog e adiciona ao bot
my_cog = MyCog(bot)
bot.add_cog(my_cog)

# Função principal para iniciar o bot
async def main():
    await bot.start()

# Executa o bot de forma assíncrona
import asyncio
asyncio.run(main())
