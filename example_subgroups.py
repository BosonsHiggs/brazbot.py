import os
from brazbot.bot import DiscordBot
from brazbot.subgroups import SubCommandGroup

# Inicialize o bot com o token e prefixo de comando
bot = DiscordBot(token=os.getenv("DISCORD_TOKEN"), command_prefix="!", intents=["GUILD_MESSAGES", "MESSAGE_CONTENT"])

class FunCommands(SubCommandGroup):
    def __init__(self, bot):
        super().__init__(bot, group_name="fun")
        self.add_commands()

    def add_commands(self):
        @self.command(name="helloworld", description="Sends a hello world message")
        async def helloworld_command(ctx):
            await ctx.bot.message_handler.send_message(ctx.channel_id, content="Hello, world!")

        # Adiciona subcomandos para "sorrir"
        sorrir_group = self.subgroup("sorrir")

        @sorrir_group.command(name="alto", description="Sends a loud smiling message")
        async def sorrir_alto_command(ctx):
            await ctx.bot.message_handler.send_message(ctx.channel_id, content="😊😊😊 LOUD!")

        @sorrir_group.command(name="baixo", description="Sends a quiet smiling message")
        async def sorrir_baixo_command(ctx):
            await ctx.bot.message_handler.send_message(ctx.channel_id, content="😊😊😊 quiet...")

        # Adiciona subgrupo "sorrir" ao bot
        bot.add_cog(sorrir_group)

# Cria uma instância de FunCommands e adiciona ao bot
fun_commands = FunCommands(bot)
bot.add_cog(fun_commands)

# Função principal para iniciar o bot
async def main():
    await bot.start()

# Executa o bot de forma assíncrona
import asyncio
asyncio.run(main())
