import os
import asyncio
import logging
from brazbot.bot import DiscordBot
from brazbot.decorators import sync_slash_commands, describe
from brazbot.audit_log_entry import AuditLogEntry
from brazbot.utils import generate_list
from brazbot.embed import Embed

# Define os intents necessários
intents = ["GUILDS", "GUILD_MESSAGES", "MESSAGE_CONTENT", "GUILD_INTEGRATIONS", "GUILD_BANS", "GUILD_MEMBERS"]

MY_GUILD = "1130837584742977697"

logging.basicConfig(level=logging.CRITICAL)

class MyBot(DiscordBot):
    def __init__(self, token, command_prefix=None, intents=None):
        super().__init__(token, command_prefix, intents)

    async def on_ready(self, data):
        await self.command_handler.sync_commands(guild_id=MY_GUILD)
        print(f"Bot is ready! Application ID: {self.application_id}")

    async def on_audit_log_entry(self, data: dict):
        audit_logs = await AuditLogEntry.from_guild_id(self, data['guild_id'])
        
        event_log = ''
        for event in audit_logs:  # Directly iterate over audit_logs
            if data['eventtype'].value == event.action:
                event_log = f"### Member {event.user['username']} (ID: {event.user['id']}) modified channel <#{event.target}> of {event.changes[0]['old_value']} to {event.changes[0]['new_value']}. 📝"
                break  # Exit the loop once the condition is met

        if event_log:  # Check if event_log is not empty
            try:
                embed = Embed(
                    title="Audit Log",
                    description=event_log,
                    color=0x00ff00
                )
                channel_id = 1243590181378850888
                await self.message_handler.send_message(channel_id, embed=embed.to_dict())
            except Exception as e:
                print(e)

bot = MyBot(os.getenv("DISCORD_TOKEN"), command_prefix="!", intents=intents)

async def main():
    await bot.start()

if __name__ == "__main__":
    asyncio.run(main())
