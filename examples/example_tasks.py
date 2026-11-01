"""
Background Tasks Example — brazbot v2.0.0
=========================================
Demonstrates periodic background loops using `@loop`.
"""

import os
from brazbot import Client, Intents, loop

bot = Client(command_prefix="!", intents=Intents.default())


@loop(seconds=60)
async def heartbeat_log():
    print("Periodic task tick (every 60s)")


@bot.event
async def on_ready():
    heartbeat_log.start()


if __name__ == "__main__":
    bot.run(os.environ["DISCORD_TOKEN"])
