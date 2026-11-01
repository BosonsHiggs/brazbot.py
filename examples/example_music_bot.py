"""
Music Bot Example — brazbot v2.0.0
==================================
Demonstrates Voice Gateway v8 connection and streaming via MusicPlayer and FFmpegOpusAudio.
"""

import os
from brazbot import Client, Intents, MusicCog, VoiceCog

bot = Client(command_prefix="!", intents=Intents.default() | Intents.MESSAGE_CONTENT | Intents.GUILD_VOICE_STATES)
bot.add_cog(VoiceCog(bot))
bot.add_cog(MusicCog(bot))

if __name__ == "__main__":
    bot.run(os.environ["DISCORD_TOKEN"])
