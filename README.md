# brazbot.py
brazbot.py is a Brazilian library for creating bots for Discord using the Python language

---

# Brazbot

Brazbot is a powerful and flexible library for creating Discord bots using Python. It provides a comprehensive set of features to help you build and manage your bots, including support for buttons, dropdowns, forms, autocomplete, embeds, file uploads, and more.

## Features

- **Comprehensive Command Handling**: Easily create and manage commands for your bot.
- **Interactive Components**: Support for buttons, dropdowns, and forms.
- **Autocomplete**: Enhance your bot commands with autocomplete functionality.
- **Embeds and Attachments**: Create rich embeds and handle file uploads.
- **Caching and Event Handling**: Efficient caching and event handling to optimize your bot's performance.

## Installation

You can install the library using pip. Make sure you have Python 3.10 or later installed.

```bash
pip install git+https://github.com/BosonsHiggs/brazbot.py
```

## Creating a Bot

Here's an example of how to create a simple bot using Brazbot.

1. **Set up a virtual environment:**

   ```bash
   python -m venv myenv
   source myenv/bin/activate  # On Windows use `myenv\Scripts\activate`
   ```

2. **Install Brazbot:**

   ```bash
   pip install git+https://github.com/BosonsHiggs/brazbot.py
   ```

3. **Create a bot script (bot.py):**

   ```python
   from brazbot.bot import Bot
   from brazbot.commands import command

   bot = Bot(command_prefix="!")

   @bot.event
   async def on_ready():
       print(f'Logged in as {bot.user}')

   @command()
   async def ping(ctx):
       await ctx.send('Pong!')

   bot.run('YOUR_BOT_TOKEN')
   ```

4. **Run your bot:**

   ```bash
   python bot.py
   ```

## Voice package

Here's a comprehensive guide on how to install `pynacl` and `ffmpeg` on Linux, Windows, and macOS.

### Installing `pynacl` and `ffmpeg`

#### Linux

**1. Install `pynacl`:**

Open your terminal and run:
```sh
pip install pynacl
```

**2. Install `ffmpeg`:**

For Debian-based systems (like Ubuntu):
```sh
sudo apt update
sudo apt install ffmpeg
```

For Red Hat-based systems (like Fedora):
```sh
sudo dnf install ffmpeg
```

For Arch Linux:
```sh
sudo pacman -S ffmpeg
```

**Verification:**

To verify the installation, run:
```sh
python -c "import nacl; print(nacl.__version__)"
ffmpeg -version
```

#### Windows

**1. Install `pynacl`:**

Open Command Prompt (or PowerShell) and run:
```sh
pip install pynacl
```

**2. Install `ffmpeg`:**

- Download the latest `ffmpeg` build from the [official website](https://ffmpeg.org/download.html).
- Extract the downloaded zip file to a desired location.
- Add the `bin` folder to your system's PATH environment variable:
  1. Right-click on "This PC" or "Computer" on the Desktop or in File Explorer.
  2. Click "Properties".
  3. Click "Advanced system settings".
  4. Click "Environment Variables".
  5. In the "System variables" section, find the `Path` variable and click "Edit".
  6. Click "New" and add the path to the `bin` folder of the extracted `ffmpeg`.

**Verification:**

To verify the installation, run:
```sh
python -c "import nacl; print(nacl.__version__)"
ffmpeg -version
```

#### macOS

**1. Install `pynacl`:**

Open Terminal and run:
```sh
pip install pynacl
```

**2. Install `ffmpeg`:**

You can use Homebrew to install `ffmpeg`. If you don't have Homebrew installed, first install it by running:
```sh
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Then, install `ffmpeg`:
```sh
brew install ffmpeg
```

**Verification:**

To verify the installation, run:
```sh
python -c "import nacl; print(nacl.__version__)"
ffmpeg -version
```

### Troubleshooting

If you encounter any issues, here are a few tips:

- Ensure that Python and pip are installed and up-to-date.
- Make sure that the PATH variable is correctly set, especially on Windows.
- If you face permission issues on Linux or macOS, you might need to use `sudo` for some commands.

### References
- [PyNaCl Documentation](https://pynacl.readthedocs.io/en/stable/)
- [FFmpeg Documentation](https://ffmpeg.org/documentation.html)
- [Homebrew](https://brew.sh/)
- [FFmpeg Downloads](https://ffmpeg.org/download.html)

This guide should help you get `pynacl` and `ffmpeg` up and running on your system. If you need further assistance, refer to the respective documentation or seek help from community forums.

## Example Usage

Below is a more detailed example demonstrating various features of the Brazbot library.

```python
import asyncio
import os
import logging
from brazbot.bot import DiscordBot
from brazbot.decorators import is_admin, sync_slash_commands, rate_limit
from brazbot.utils import create_embed, format_command_response
from brazbot.file import File

# Define os intents necessários
intents = ["GUILD_MESSAGES", "MESSAGE_CONTENT", "GUILD_MEMBERS", "GUILD_MESSAGE_REACTIONS"]

MY_GUILD = "1130837584742977697"

logging.basicConfig(level=logging.DEBUG)

class MyBot(DiscordBot):
    def __init__(self, token, command_prefix=None, intents=None):
        super().__init__(token, command_prefix, intents)

    async def on_ready(self, data):
        logging.info(f"Bot is ready! Application ID: {self.application_id}")
        await self.command_handler.sync_commands(guild_id=MY_GUILD)

    async def on_message_create(self, data):
        logging.info(f"Message create event received: {data}")

    async def on_error(self, data):
        if 'time_left' in data:
            time_left = data['time_left']
            error_message = f"Você atingiu o limite de uso deste comando. Tente novamente em {time_left:.2f} segundos."
            channel_id = data['channel_id']
            await self.message_handler.send_message(channel_id, error_message)
        else:
            error_message = data.get('message', 'Ocorreu um erro.')
            logging.error(error_message)

token = os.getenv("DISCORD_TOKEN")
if not token:
    logging.error("DISCORD_TOKEN not found in environment variables.")
    exit(1)

bot = MyBot(token, command_prefix="!", intents=intents)

@bot.command(name="delete_message", description="Deletes a message by ID")
@sync_slash_commands(guild_id=MY_GUILD)
@rate_limit(limit=1, per=60, scope="user")
async def delete_message_command(ctx, message_id: str):
    await ctx.defer()
    success = await ctx.bot.message_handler.delete_message(ctx.channel_id, message_id)
    if success:
        await ctx.send_followup_message(content="Message deleted successfully.")
    else:
        await ctx.send_followup_message(content="Failed to delete the message.")

@bot.command(name="add_reaction", description="Adds a reaction to a message")
@sync_slash_commands(guild_id=MY_GUILD)
@rate_limit(limit=1, per=60, scope="user")
async def add_reaction_command(ctx, message_id: str, emoji: str):
    await ctx.defer()

    success = await ctx.bot.message_handler.add_reaction(ctx.channel_id, message_id, emoji)
    if success:
        await ctx.send_followup_message(content="Reaction added successfully.")
    else:
        await ctx.send_followup_message(content="Failed to add reaction.")

@bot.command(name="bulk_delete", description="Bulk delete messages")
@sync_slash_commands(guild_id=MY_GUILD)
@rate_limit(limit=1, per=60, scope="user")
async def bulk_delete_command(ctx, message_ids: str):
    await ctx.defer()
    message_id_list = message_ids.split(',')
    success = await ctx.bot.message_handler.bulk_delete_messages(ctx.channel_id, message_id_list)
    if success:
        await ctx.send_followup_message(content="Messages deleted successfully.")
    else:
        await ctx.send_followup_message(content="Failed to delete messages.")

@bot.command(name="pin_message", description="Pins a message")
@sync_slash_commands(guild_id=MY_GUILD)
@rate_limit(limit=1, per=60, scope="user")
async def pin_message_command(ctx, message_id: str):
    await ctx.defer()
    success = await ctx.bot.message_handler.pin_message(ctx.channel_id, message_id)
    if success:
        await ctx.send_followup_message(content="Message pinned successfully.")
    else:
        await ctx.send_followup_message(content="Failed to pin the message.")

@bot.command(name="unpin_message", description="Unpins a message")
@sync_slash_commands(guild_id=MY_GUILD)
@rate_limit(limit=1, per=60, scope="user")
async def unpin_message_command(ctx, str, message_id: str):
    await ctx.defer()
    success = await ctx.bot.message_handler.unpin_message(ctx.channel_id, message_id)
    if success:
        await ctx.send_followup_message(content="Message unpinned successfully.")
    else:
        await ctx.send_followup_message(content="Failed to unpin the message.")

@bot.command(name="create_webhook", description="Creates a webhook")
@sync_slash_commands(guild_id=MY_GUILD)
@rate_limit(limit=1, per=60, scope="user")
async def create_webhook_command(ctx, name: str):
    await ctx.defer()
    webhook = await ctx.bot.message_handler.create_webhook(ctx.channel_id, name)
    if webhook:
        await ctx.send_followup_message(content=f"Webhook created successfully. URL: {webhook['url']}")
    else:
        await ctx.send_followup_message(content="Failed to create webhook.")

@bot.command(name="send_webhook_message", description="Sends a message using a webhook")
@sync_slash_commands(guild_id=MY_GUILD)
@rate_limit(limit=1, per=60, scope="user")
async def send_webhook_message_command(ctx, webhook_url: str, content: str):
    await ctx.defer()
    response = await ctx.bot.message_handler.send_webhook_message(webhook_url, content=content)
    if response:
        await ctx.send_followup_message(content="Webhook message sent successfully.")
    else:
        await ctx.send_followup_message(content="Failed to send webhook message.")

async def main():
    await bot.start()

# Executa o bot de forma assíncrona
if __name__ == "__main__":
    asyncio.run(main())
```

## Contact

If you have any questions or need support, join our Discord server: [Brazbot Discord](https://discord.gg/m33KxxKaEB).

---

This documentation provides an overview of the Brazbot library, including installation instructions, an example of creating a bot, and how to utilize various features such as embeds, buttons, dropdowns, and forms. For detailed usage and more examples, refer to the example scripts included in the repository.