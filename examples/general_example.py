import asyncio
import os
import logging
from brazbot.bot import DiscordBot
from brazbot.decorators import is_admin, sync_slash_commands, rate_limit
from brazbot.utils import create_embed, format_command_response
from brazbot.file import File

# Define os intents necessários
intents = ["GUILD_MESSAGES", "MESSAGE_CONTENT", "GUILD_MEMBERS", "GUILD_MESSAGE_REACTIONS"]

MY_GUILD = "1130837584742977697"

logging.basicConfig(level=logging.DEBUG)

class MyBot(DiscordBot):
    def __init__(self, token, command_prefix=None, intents=None):
        super().__init__(token, command_prefix, intents)

    async def on_ready(self, data):
        logging.info(f"Bot is ready! Application ID: {self.application_id}")
        await self.command_handler.sync_commands(guild_id=MY_GUILD)

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

@bot.command(name="delete_message", description="Deletes a message by ID")
@sync_slash_commands(guild_id=MY_GUILD)
@rate_limit(limit=1, per=60, scope="user")
async def delete_message_command(ctx, message_id: str):
    await ctx.defer()
    success = await ctx.bot.message_handler.delete_message(ctx.channel_id, message_id)
    if success:
        await ctx.send_followup_message(content="Message deleted successfully.")
    else:
        await ctx.send_followup_message(content="Failed to delete the message.")

@bot.command(name="add_reaction", description="Adds a reaction to a message")
@sync_slash_commands(guild_id=MY_GUILD)
@rate_limit(limit=1, per=60, scope="user")
async def add_reaction_command(ctx, message_id: str, emoji: str):
    await ctx.defer()

    success = await ctx.bot.message_handler.add_reaction(ctx.channel_id, message_id, emoji)
    if success:
        await ctx.send_followup_message(content="Reaction added successfully.")
    else:
        await ctx.send_followup_message(content="Failed to add reaction.")

@bot.command(name="bulk_delete", description="Bulk delete messages")
@sync_slash_commands(guild_id=MY_GUILD)
@rate_limit(limit=1, per=60, scope="user")
async def bulk_delete_command(ctx, message_ids: str):
    await ctx.defer()
    message_id_list = message_ids.split(',')
    success = await ctx.bot.message_handler.bulk_delete_messages(ctx.channel_id, message_id_list)
    if success:
        await ctx.send_followup_message(content="Messages deleted successfully.")
    else:
        await ctx.send_followup_message(content="Failed to delete messages.")

@bot.command(name="pin_message", description="Pins a message")
@sync_slash_commands(guild_id=MY_GUILD)
@rate_limit(limit=1, per=60, scope="user")
async def pin_message_command(ctx, message_id: str):
    await ctx.defer()
    success = await ctx.bot.message_handler.pin_message(ctx.channel_id, message_id)
    if success:
        await ctx.send_followup_message(content="Message pinned successfully.")
    else:
        await ctx.send_followup_message(content="Failed to pin the message.")

@bot.command(name="unpin_message", description="Unpins a message")
@sync_slash_commands(guild_id=MY_GUILD)
@rate_limit(limit=1, per=60, scope="user")
async def unpin_message_command(ctx, str, message_id: str):
    await ctx.defer()
    success = await ctx.bot.message_handler.unpin_message(ctx.channel_id, message_id)
    if success:
        await ctx.send_followup_message(content="Message unpinned successfully.")
    else:
        await ctx.send_followup_message(content="Failed to unpin the message.")

@bot.command(name="create_webhook", description="Creates a webhook")
@sync_slash_commands(guild_id=MY_GUILD)
@rate_limit(limit=1, per=60, scope="user")
async def create_webhook_command(ctx, name: str):
    await ctx.defer()
    webhook = await ctx.bot.message_handler.create_webhook(ctx.channel_id, name)
    if webhook:
        await ctx.send_followup_message(content=f"Webhook created successfully. URL: {webhook['url']}")
    else:
        await ctx.send_followup_message(content="Failed to create webhook.")

@bot.command(name="send_webhook_message", description="Sends a message using a webhook")
@sync_slash_commands(guild_id=MY_GUILD)
@rate_limit(limit=1, per=60, scope="user")
async def send_webhook_message_command(ctx, webhook_url: str, content: str):
    await ctx.defer()
    response = await ctx.bot.message_handler.send_webhook_message(webhook_url, content=content)
    if response:
        await ctx.send_followup_message(content="Webhook message sent successfully.")
    else:
        await ctx.send_followup_message(content="Failed to send webhook message.")

async def main():
    await bot.start()

# Executa o bot de forma assíncrona
if __name__ == "__main__":
    asyncio.run(main())
