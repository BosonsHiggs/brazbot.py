"""
Gateway Sharding Example — brazbot.py v2.0.0
============================================
Demonstrates running a sharded Discord bot instance via `num_shards` and `shard_id`.
"""

import os
from brazbot import Bot, Intents

bot = Bot(
    token=os.getenv("DISCORD_TOKEN", ""),
    command_prefix="!",
    intents=Intents.default(),
    num_shards=2,
    shard_id=0,
)

if __name__ == "__main__":
    bot.run(os.environ["DISCORD_TOKEN"])
