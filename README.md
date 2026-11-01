# brazbot.py v2.0.0

**Production-ready native Python library for Discord API v10 and Voice Gateway v8 — built from scratch with zero third-party Discord library dependencies.**


[Discord API v10](https://discord.com/developers/docs/reference)


## Key Features

* **100% Native Discord API v10 & Voice Gateway v8**: Communicates directly with `https://discord.com/api/v10` and `wss://gateway.discord.gg/?v=10&encoding=json` using `aiohttp` and `cryptography`. No wrapper libraries (`discord.py`, `nextcord`, etc.) are used.

* **Compliant with Discord API Library Guidelines (`meew0` specification)**:

  * Explicit `DiscordBot (https://github.com/BosonsHiggs/brazbot.py, 2.0.0)` `User-Agent` header on every request.

  * Pre-emptive per-bucket rate limiting (`X-RateLimit-Bucket`, `X-RateLimit-Remaining`, `X-RateLimit-Reset-After`) keyed by `(method, route_template, major_parameter)` (`channel_id`, `guild_id`, `webhook_id`), plus global `asyncio.Event` lock and `429 Too Many Requests` backoff.

  * Typed `Intents` bitfield (`Intents.default()`, `Intents.all()`) and full Snowflake utilities (`Snowflake`).

* **Voice Gateway v8 & Modern AEAD Encryption**:

  * Connects to `?v=8`, handles Opcode `8 Hello` dynamic heartbeat intervals, and includes sequence recognition (`seq_ack`) in Opcode `3 Heartbeat` and Opcode `6 Resume`.

  * Standard 74-byte UDP IP Discovery packet (`0x0001` request / `0x0002` response).

  * Supports Discord's mandatory modern AEAD voice encryption modes (`aead_aes256_gcm_rtpsize` and `aead_xchacha20_poly1305_rtpsize`).

  * Native `ctypes` `libopus` `OpusEncoder` / `OpusDecoder`, pure-Python `OggOpusDemuxer`, `FFmpegOpusAudio`, and `MusicPlayer` with `yt-dlp` integration.

* **High-Throughput Server Moderation (`brazbot.moderation`)**:

  * **`BatchDeleteQueue`**: Coalesces message deletions from flood bursts or profanity triggers over a configurable window (default `0.5s`) and executes a single `POST /channels/{id}/messages/bulk-delete` call (deleting up to **100 messages per HTTP request** instead of hammering the Discord API with individual `DELETE` calls).

  * **`AntiFloodManager`**: Detects sliding-window message bursts, duplicate spam, mention spam, and CAPS-lock spam, automatically queuing offending messages for bulk deletion and applying temporary timeouts.

  * **`ProfanityFilter`**: Anti-evasion obscene word detector that normalizes leetspeak (`@ -> a`, `$ -> s`, `0 -> o`, `1 -> i`, `3 -> e`), strips Unicode accents/diacritics, removes zero-width characters, collapses character repeats, and syncs directly with native Discord AutoMod v10 rules.

  * **Multi-Message & Full-Channel Cleanup**: `TextChannel.purge()` (paginated 100-message bulk-delete batches) and `TextChannel.clean_all_messages()` (`mode="clone"` wipes an entire channel's history in **2 API calls** via clone + delete, or `mode="batch"` for 100-message bulk batches).

* **Modern Discord v10 Capabilities**:

  * Slash Commands (`@bot.slash_command`), Context Menus (`@bot.user_command`, `@bot.message_command`), Autocomplete, and Modals.

  * **Components v2** (`IS_COMPONENTS_V2 = 1 << 15`): `Container`, `Section`, `TextDisplay`, `Thumbnail`, `MediaGallery`, `FileComponent`, `Separator`, plus `ActionRow`, `Button`, and `SelectMenu`.

  * **Polls API**, **AutoMod v10**, **Bulk Ban** (`POST /guilds/{id}/bulk-ban` up to 200 users in 1 call), **Forum & Stage Channels**, **Scheduled Events**, and **Monetization / Entitlements / SKUs**.

## Installation

Install directly from the official GitHub repository via `pip`:

```
pip install git+https://github.com/BosonsHiggs/brazbot.py.git

```

Or install with optional high-performance extras (`aiodns`, `Brotli`, `PyNaCl`) directly from GitHub:

```
pip install "brazbot[speed] @ git+https://github.com/BosonsHiggs/brazbot.py.git"

```

You can also clone the repository and install locally or in editable development mode:

```
git clone https://github.com/BosonsHiggs/brazbot.py.git
cd brazbot.py
pip install .
# or for development:
pip install -e ".[speed,dev]"

```

### System Requirements for Voice & Music

* **Python**: `>= 3.10`

* **FFmpeg**: Installed on system `PATH` (for `FFmpegOpusAudio` transcoding)

* **libopus**: System shared library (`libopus.so.0` on Linux, `libopus.dylib` on macOS, or `opus.dll` on Windows) for raw PCM encoding/decoding

## Quick Start: Slash Commands & Prefix Commands

```
import os
from brazbot import Client, CommandContext, Embed, Intents, InteractionContext

intents = Intents.default() | Intents.MESSAGE_CONTENT
bot = Client(command_prefix="!", intents=intents, sync_commands=True)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")


@bot.command(name="ping", description="Check bot responsiveness")
async def ping(ctx: CommandContext):
    await ctx.reply("Pong!")


@bot.slash_command(name="info", description="Display server information")
async def info(ctx: InteractionContext):
    embed = Embed(
        title="BrazBot v2.0.0",
        description="Running natively on Discord HTTP/Gateway API v10.",
        color=0x5865F2,
    )
    await ctx.respond(embed=embed)


bot.run(os.environ["DISCORD_TOKEN"])

```

## Full Server Moderation Example (Anti-Flood, Bulk Delete & Profanity Filter)

See [example_moderation_bot.py](https://www.google.com/search?q=example_moderation_bot.py) for a complete moderation bot featuring:

* **Automatic flood removal** via `AntiFloodManager` + `BatchDeleteQueue` (deletes up to 100 flood messages in a single `bulk-delete` HTTP request).

* **Bulk message removal & full-channel wipe** (`/purge`, `/purge_user`, `/clean_all`) without forcing the API with individual `DELETE` calls.

* **Anti-evasion obscene word filter** (`ProfanityFilter`) with leetspeak/accent normalization and native Discord AutoMod v10 synchronization (`/automod_sync`).

* **20+ Slash Commands**: `/ban`, `/softban`, `/massban`, `/unban`, `/kick`, `/timeout`, `/untimeout`, `/warn`, `/warnings`, `/clear_warnings`, `/purge`, `/purge_user`, `/clean_all`, `/slowmode`, `/lock`, `/unlock`, `/profanity_add`, `/profanity_remove`, `/profanity_list`, `/antiflood_config`, `/automod_sync`, and `/modstats`.

```
from brazbot import Client, FloodConfig, Intents, ModerationGuard, ProfanityFilter

bot = Client(command_prefix="!", intents=Intents.all(), sync_commands=True)

mod_guard = ModerationGuard(
    bot,
    profanity_filter=ProfanityFilter(words=["badword", "scamlink"]),
    flood_config=FloodConfig(max_messages=5, window_seconds=4.0, auto_timeout_seconds=300),
    flush_interval=0.5,  # Coalesces deletions every 0.5s into bulk-delete calls (up to 100 msgs/call)
)

```

## Package Architecture

```
brazbot/
├── __init__.py          # Public API exports and version metadata
├── client.py            # Main Client (Gateway v10, HTTP v10, Slash & Prefix routing, Voice manager)
├── http.py              # Discord HTTP v10 client with per-route pre-emptive rate-limit buckets
├── gateway.py           # Gateway v10 WebSocket client with heartbeat, zlib-stream, and resume
├── voice.py             # Voice Gateway v8 + 74-byte UDP IP Discovery + AEAD AES-GCM / XChaCha20
├── music.py             # yt-dlp extractor, FFmpegOpusAudio, OggOpusDemuxer, and MusicPlayer queue
├── moderation.py        # BatchDeleteQueue, AntiFloodManager, ProfanityFilter, and ModerationGuard
├── interactions.py      # Slash commands, Context Menus, Autocomplete, and InteractionContext
├── components.py        # Components v1 & v2 (Buttons, Selects, Modals, Containers, Views)
├── automod.py           # Discord AutoMod v10 rule and action models
├── polls.py             # Discord Polls v10 models
├── models.py            # User, Member, Guild, Role, Attachment, Sticker, ScheduledEvent, SKU
├── channels.py          # TextChannel (multi-page purge & clean_all_messages), VoiceChannel, ThreadChannel
├── embed.py             # Rich Embed builder with validation
├── flags.py             # Intents, Permission, MessageFlags, SystemChannelFlags
├── snowflake.py         # Discord Snowflake ID parser & generator
├── cogs.py              # Modular Cog and command registration base classes
├── cogs_builtin.py      # Ready-to-use ModerationCog, MusicCog, VoiceCog, UtilityCog, FunCog
├── cache.py             # LRU entity cache for guilds, channels, users, and members
├── sharding.py          # Multi-shard gateway manager (ShardManager)
└── tasks.py             # Asynchronous periodic background task loops (@loop)

```

## Running Tests

```
pytest
# or
python3 -m unittest discover -s tests

```

## License

Released under the [MIT License](https://www.google.com/search?q=LICENSE).