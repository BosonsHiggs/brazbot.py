"""
Background Tasks Example — brazbot.py v2.0.0
============================================
Demonstrates periodic background coroutines using `@tasks(seconds=...)`.
"""

import asyncio
import os
from brazbot import Bot, Intents, tasks

bot = Bot(token=os.getenv("DISCORD_TOKEN", ""), command_prefix="!", intents=Intents.default())


@tasks(seconds=60)
async def heartbeat_log():
    print("Periodic task tick (every 60s)")


@bot.event
async def on_ready(data):
    asyncio.create_task(heartbeat_log())


if __name__ == "__main__":
    bot.run(os.environ["DISCORD_TOKEN"])
