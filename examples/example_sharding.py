"""
Gateway Sharding Example — brazbot v2.0.0
=========================================
Demonstrates running a multi-shard Discord bot via `ShardManager`.
"""

import asyncio
import os
from brazbot import Intents, ShardManager


async def main():
    manager = ShardManager(token=os.environ["DISCORD_TOKEN"], intents=Intents.default(), shard_count=2)
    await manager.start()


if __name__ == "__main__":
    asyncio.run(main())
