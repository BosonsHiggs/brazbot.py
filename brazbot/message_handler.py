import aiohttp
import logging

from aiohttp import FormData

class MessageHandler:
    def __init__(self, token):
        self.token = token
        self.base_url = "https://discord.com/api/v10"
        self.headers = {
            "Authorization": f"Bot {self.token}",
            "Content-Type": "application/json"
        }

    async def send_message(self, channel_id, content):
        url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=self.headers, json={"content": content}) as response:
                if response.status != 200:
                    print(f"Failed to send message: {response.status}")
                else:
                    print(f"Message sent: {await response.json()}")

    async def send_embed(self, channel_id, embed):
        url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=self.headers, json={"embeds": [embed]}) as response:
                if response.status != 200:
                    print(f"Failed to send embed: {response.status}")
                else:
                    print(f"Embed sent: {await response.json()}")

    async def send_file(self, channel_id, file_path):
        url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
        with open(file_path, 'rb') as file:
            form = FormData()
            form.add_field('file', file, filename=file_path)
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=self.headers, data=form) as response:
                    if response.status != 200:
                        print(f"Failed to send file: {response.status}")
                    else:
                        print(f"File sent: {await response.json()}")

    async def send_interaction(self, interaction, content=None, embed=None, embeds=None, files=None, ephemeral=False):
        url = f"https://discord.com/api/v10/interactions/{interaction['id']}/{interaction['token']}/callback"
        data = {
            "type": 4,
            "data": {}
        }
        if content:
            data["data"]["content"] = str(content)  # Ensure content is a string
        if embed:
            data["data"]["embeds"] = [embed]
        if embeds:
            data["data"]["embeds"] = embeds
        if files:
            data["data"]["attachments"] = files
        if ephemeral:
            data["data"]["flags"] = 64  # This flag makes the response ephemeral

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=self.headers, json=data) as response:
                if response.status != 200:
                    print(f"Failed to send interaction: {response.status}")
                    print(await response.text())
                else:
                    print(f"Interaction sent: {await response.json()}")

    async def send_followup_message(self, application_id, interaction_token, content):
        url = f"{self.base_url}/webhooks/{application_id}/{interaction_token}"
        json_data = {
            "content": content
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=json_data) as response:
                if response.status != 200:
                    logging.error(f"Failed to send follow-up message: {response.status}")
                else:
                    logging.info("Follow-up message sent successfully")