import asyncio
import os
import logging
from brazbot.bot import DiscordBot
from brazbot.decorators import sync_slash_commands, rate_limit
from brazbot.buttons import Button
from brazbot.dropdowns import Dropdown, DropdownOption
from brazbot.forms import Form, FormField

logging.basicConfig(level=logging.DEBUG)

MY_GUILD = "1130837584742977697"

class MyBot(DiscordBot):
    async def on_ready(self, data):
        logging.info(f"Bot is ready! Application ID: {self.application_id}")
        await self.command_handler.sync_commands(guild_id=MY_GUILD)

    async def on_interaction_create(self, interaction):
        logging.debug(f"Interaction received: {interaction}")
        custom_id = interaction['data'].get('custom_id')
        if custom_id == "button_click":
            await self.message_handler.send_interaction(
                interaction,
                content="Button was clicked!"
            )
        elif custom_id == "dropdown_select":
            selected_option = interaction['data'].get('values', [])[0]
            await self.message_handler.send_interaction(
                interaction,
                content=f"Dropdown option selected: {selected_option}"
            )
        elif custom_id == "user_form":
            components = interaction['data'].get('components', [])
            responses = {comp['components'][0]['custom_id']: comp['components'][0]['value'] for comp in components}
            await self.message_handler.send_interaction(
                interaction,
                content=f"Form responses: {responses}"
            )

# Define the required intents
intents = ["GUILD_MESSAGES", "MESSAGE_CONTENT"]

token = os.getenv("DISCORD_TOKEN")
bot = MyBot(token, command_prefix="!", intents=intents)

@bot.command(name="button", description="Send a button")
@sync_slash_commands(guild_id=MY_GUILD)
@rate_limit(limit=1, per=60, scope="user")
async def button_command(ctx):
    await ctx.defer()
    try:
        button = Button(label="Click Me", style=1, custom_id="button_click")
        logging.debug(f"Button: {button.to_dict()}")
        await ctx.send_followup_message(content="Here is a button:", components=button)
    except Exception as e:
        print(f"Error in button_command: {e}")

@bot.command(name="dropdown", description="Send a dropdown")
@sync_slash_commands(guild_id=MY_GUILD)
@rate_limit(limit=1, per=60, scope="user")
async def dropdown_command(ctx):
    print(0)
    await ctx.defer()
    print(1)
    try:
        print(2)
        options = [
            DropdownOption(label="Option 1", value="1"),
            DropdownOption(label="Option 2", value="2")
        ]
        print(3)
        dropdown = Dropdown(custom_id="dropdown_select", options=options)
        print(4)
        logging.debug(f"Dropdown: {dropdown.to_dict()}")
        print(5)
        await ctx.send_followup_message(content="Here is a dropdown:", components=[{"type": 1, "components": [dropdown.to_dict()]}])
        print(6)
    except Exception as e:
        logging.error(f"Error in dropdown_command: {e}")

@bot.command(name="form", description="Send a form")
@sync_slash_commands(guild_id=MY_GUILD)
@rate_limit(limit=1, per=60, scope="user")
async def form_command(ctx):
    await ctx.defer()
    try:
        fields = [
            FormField(label="Name", placeholder="Enter your name", custom_id="name"),
            FormField(label="Age", placeholder="Enter your age", custom_id="age", style=2)
        ]
        form = Form(title="User Info", custom_id="user_form", fields=fields)
        logging.debug(f"Form: {form.to_dict()}")
        await ctx.send_followup_message(content="Please fill out the form:", components=[form.to_dict()])
    except Exception as e:
        logging.error(f"Error in form_command: {e}")

# Main function to start the bot
async def main():
    try:
        await bot.start()
    except Exception as e:
        logging.error(f"Error in main: {e}")

asyncio.run(main())
