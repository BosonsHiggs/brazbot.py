import asyncio
import os
from brazbot.bot import DiscordBot
from brazbot.decorators import is_admin, sync_slash_commands, rate_limit
from brazbot.utils import create_embed, format_command_response

# Definindo os intents necessários
intents = ["GUILD_MESSAGES", "MESSAGE_CONTENT"]

token = os.getenv("DISCORD_TOKEN")
bot = DiscordBot(token, command_prefix="!", intents=intents)

@bot.event
async def on_ready(bot, data, message):
    print(f"Bot is ready! Application ID: {bot.application_id}")

@bot.event
async def on_message_create(bot, data, message):
    print(f"Message create event received: {data}")

@bot.event
async def on_error(bot, data, message):
    if 'time_left' in data:
        time_left = data['time_left']
        error_message = f"Você atingiu o limite de uso deste comando. Tente novamente em {time_left:.2f} segundos."
        channel_id = data['channel_id']
        await bot.message_handler.send_message(channel_id, error_message)
    else:
        error_message = data.get('message', 'Ocorreu um erro.')
        print(error_message)  # Você pode enviar isso para um canal específico no Discord se necessário

@bot.command(name="hello")
@is_admin()
@rate_limit(limit=1, per=60, scope="user")
async def hello_command(ctx):
    embed = create_embed("Saudações", "Olá, mundo!")
    await ctx.bot.message_handler.send_embed(ctx.channel_id, embed)

@bot.command(name="echo")
@rate_limit(limit=1, per=60, scope="user")
async def echo_command(ctx, *args):
    response = format_command_response(" ".join(args))
    await ctx.bot.message_handler.send_embed(ctx.channel_id, response)

@bot.command(name="sync")
@sync_slash_commands(guild_id="1130837584742977697")
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
