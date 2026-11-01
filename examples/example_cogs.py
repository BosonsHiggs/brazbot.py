"""
Cogs Example — brazbot v2.0.0
=============================
Demonstrates modular bot architecture using built-in Moderation, Music, Utility, and Fun Cogs.
"""

import os
from brazbot import Client, FunCog, Intents, ModerationCog, MusicCog, UtilityCog

bot = Client(command_prefix="!", intents=Intents.all(), sync_commands=True)

bot.add_cog(ModerationCog(bot))
bot.add_cog(MusicCog(bot))
bot.add_cog(UtilityCog(bot))
bot.add_cog(FunCog(bot))

if __name__ == "__main__":
    bot.run(os.environ["DISCORD_TOKEN"])
