import os
import asyncio
import logging
from brazbot.bot import DiscordBot
from brazbot.decorators import sync_slash_commands, rate_limit, describe
from brazbot.member import Member

# Define os intents necessários
intents = ["GUILD_MESSAGES", "MESSAGE_CONTENT", "GUILD_PRESENCES"]

MY_GUILD = "1130837584742977697"

logging.basicConfig(level=logging.CRITICAL)

class MyBot(DiscordBot):
	def __init__(self, token, command_prefix=None, intents=None):
		super().__init__(token, command_prefix, intents)

	async def on_ready(self, data):
		await bot.command_handler.sync_commands(guild_id=MY_GUILD)
		print(f"Bot is ready! Application ID: {self.application_id}")
		"""
		Activity Types

		ID	NAME	FORMAT	EXAMPLE
		0	Game	Playing {name}	"Playing Rocket League"
		1	Streaming	Streaming {details}	"Streaming Rocket League"
		2	Listening	Listening to {name}	"Listening to Spotify"
		3	Watching	Watching {name}	"Watching YouTube Together"
		4	Custom	{emoji} {state}	":smiley: I am cool"
		5	Competing	Competing in {name}	"Competing in Arena World Champions"
		"""
		await self.change_presence("Playing with APIs", activity_type=0)  # 0 for Playing

bot = MyBot(os.getenv("DISCORD_TOKEN"), command_prefix="!", intents=intents)

@bot.command(name="hi", description="Says hi")
@sync_slash_commands(guild_id=MY_GUILD)
@describe(user="Hello world!")
async def hi_command(ctx, user: Member):
	await ctx.defer()
	print(dir(user), user)
	await ctx.send_followup_message(content=f'{user.username} and color {user.color}')

async def main():
	await bot.start()

if __name__ == "__main__":
	asyncio.run(main())
