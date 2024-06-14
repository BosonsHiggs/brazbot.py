import os
import asyncio
import logging
import aiohttp
from brazbot.bot import DiscordBot
from brazbot.decorators import sync_slash_commands, rate_limit, describe
from brazbot.voiceclient import VoiceClient
from brazbot.channels import VoiceChannel
from brazbot.utils import create_error_embed

MY_GUILD = "1130837584742977697"

class MyBot(DiscordBot):
    def __init__(self, token, command_prefix=None, intents=None):
        super().__init__(token, command_prefix, intents)
        self.voice_client = None
        self.queue = []
        self.currently_playing = None

    async def on_ready(self, data):
        print(f"Bot is ready! Application ID: {self.application_id}")
        await self.command_handler.sync_commands(guild_id=MY_GUILD)

    async def on_message_create(self, data):
        print(f"Message create event received: {data}")

    async def on_error(self, data):
        if 'time_left' in data:
            time_left = data['time_left']
            error_message = f"You have reached the usage limit for this command. Please try again in {time_left:.2f} seconds."

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

    async def play_next(self):
        if self.queue:
            self.currently_playing = self.queue.pop(0)
            if self.voice_client:
                await self.voice_client.play(self.currently_playing)
        else:
            self.currently_playing = None

    async def join_voice_channel(self, ctx, voice_channel):
        try:
            self.voice_client = VoiceClient(self, voice_channel)
            await self.voice_client.connect()
        except Exception as e:
            print(e)
        await ctx.send_followup_message(f"Joined voice channel: {voice_channel.name}")

    async def add_to_queue(self, ctx, file_url):
        self.queue.append(file_url)
        await ctx.send_followup_message(f"Added to queue: {file_url}")
        if not self.currently_playing:
            await self.play_next()

# Define the necessary intents
intents = ["GUILDS", "GUILD_VOICE_STATES", "GUILD_MESSAGES", "MESSAGE_CONTENT"]
token = os.getenv("DISCORD_TOKEN")
bot = MyBot(token, command_prefix="!", intents=intents)

@bot.command(name="join", description="Join a voice channel")
@sync_slash_commands(guild_id=MY_GUILD)
@rate_limit(limit=1, per=5, scope="user")
@describe(channel="A channel in the guild")
async def join_command(ctx, channel: VoiceChannel):
    await ctx.defer()
    try:
        await bot.join_voice_channel(ctx, channel)
    except Exception as e:
        await ctx.send_followup_message(f"Failed to join voice channel: {str(e)}")

@bot.command(name="play", description="Play an mp3 file from a URL")
@sync_slash_commands(guild_id=MY_GUILD)
@rate_limit(limit=1, per=5, scope="user")
async def play_command(ctx, file_url: str):
    await ctx.defer()
    if bot.voice_client is None:
        await ctx.send_followup_message("Bot is not connected to a voice channel.")
        return
    await bot.add_to_queue(ctx, file_url)

# Main function to start the bot
async def main():
    await bot.start()

# Run the bot asynchronously
asyncio.run(main())