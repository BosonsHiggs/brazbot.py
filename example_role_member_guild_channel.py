import os
import asyncio
import logging
from brazbot.bot import DiscordBot
from brazbot.decorators import sync_slash_commands, describe
from brazbot.member import Member
from brazbot.roles import Role
from brazbot.channels import Channel
from brazbot.guilds import Guild

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

bot = MyBot(os.getenv("DISCORD_TOKEN"), command_prefix="!", intents=intents)

@bot.command(name="hi", description="Says hi")
@sync_slash_commands(guild_id=MY_GUILD)
@describe(user="A user in the guild")
async def hi_command(ctx, user: Member):
    await ctx.defer()
    await ctx.send_followup_message(content=f'User: {user.username}#{user.discriminator}')

@bot.command(name="role_info", description="Shows role information")
@sync_slash_commands(guild_id=MY_GUILD)
@describe(role="A role in the guild")
async def role_info_command(ctx, role: Role):
    await ctx.defer()
    await ctx.send_followup_message(content=f'Role: {role.name}, Members: {role.members}')

@bot.command(name="channel_info", description="Shows channel information")
@sync_slash_commands(guild_id=MY_GUILD)
@describe(channel="A channel in the guild")
async def channel_info_command(ctx, channel: Channel):
    await ctx.defer()
    await ctx.send_followup_message(content=f'Channel: {channel.name}, Category: {channel.category}')

@bot.command(name="guild_info", description="Shows guild information")
@sync_slash_commands(guild_id=MY_GUILD)
@describe(guild="The guild")
async def guild_info_command(ctx, guild: Guild):
    await ctx.defer()

    members = await guild.fetch_all_members()
    print(type(members))
    print()
    for member in members:
        print(member)
        #await ctx.send_followup_message(content=f'Guild: {guild.name}, Member: {member.username}')

async def main():
    await bot.start()

if __name__ == "__main__":
    asyncio.run(main())
