import aiohttp
import logging
import asyncio
import json
from aiohttp import FormData

"""
SEE:    1. https://discord.com/developers/docs/interactions/receiving-and-responding#interaction-response-object
        2. https://discord.com/developers/docs/topics/rate-limits#global-rate-limit
        3. https://discord.com/developers/docs/resources/webhook#edit-webhook-message
"""

class MessageHandler:
    def __init__(self, token):
        self.token = token
        self.base_url = "https://discord.com/api/v10"
        self.headers = {
            "Authorization": f"Bot {self.token}"
        }

    async def send_message(self, channel_id, content):
        url = f"{self.base_url}/channels/{channel_id}/messages"
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=self.headers, json={"content": content}) as response:
                if response.status != 200:
                    logging.error(f"Failed to send message: {response.status} - {await response.text()}")
                    return None
                else:
                    response_json = await response.json()
                    logging.info(f"Message sent: {response_json}")
                    return response_json

    async def send_embed(self, channel_id, embed):
        url = f"{self.base_url}/channels/{channel_id}/messages"
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=self.headers, json={"embeds": [embed]}) as response:
                if response.status != 200:
                    logging.error(f"Failed to send embed: {response.status} - {await response.text()}")
                    return None
                else:
                    response_json = await response.json()
                    logging.info(f"Embed sent: {response_json}")
                    return response_json

    async def send_file(self, channel_id, file_path):
        url = f"{self.base_url}/channels/{channel_id}/messages"
        with open(file_path, 'rb') as file:
            form = FormData()
            form.add_field('file', file, filename=file_path)
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=self.headers, data=form) as response:
                    if response.status != 200:
                        logging.error(f"Failed to send file: {response.status} - {await response.text()}")
                        return None
                    else:
                        response_json = await response.json()
                        logging.info(f"File sent: {response_json}")
                        return response_json

    async def edit_message(self, channel_id, message_id, content=None, embed=None, files=None, components=None):
        url = f"{self.base_url}/channels/{channel_id}/messages/{message_id}"
        data = {}
        if content:
            data["content"] = content
        if embed:
            data["embeds"] = [embed] if isinstance(embed, dict) else embed
        if components:
            data["components"] = components

        async with aiohttp.ClientSession() as session:
            if files:
                form = FormData()
                form.add_field('payload_json', json.dumps(data))
                for file in files:
                    form.add_field('file', file['data'], filename=file['filename'], content_type=file['content_type'])
                async with session.patch(url, headers=self.headers, data=form) as response:
                    if response.status != 200:
                        logging.error(f"Failed to edit message with file: {response.status} - {await response.text()}")
                        return None
                    else:
                        response_json = await response.json()
                        logging.info(f"Message edited with file: {response_json}")
                        return response_json
            else:
                async with session.patch(url, headers=self.headers, json=data) as response:
                    if response.status != 200:
                        logging.error(f"Failed to edit message: {response.status} - {await response.text()}")
                        return None
                    else:
                        response_json = await response.json()
                        logging.info(f"Message edited: {response_json}")
                        return response_json

    async def send_interaction(self, interaction, content=None, embed=None, embeds=None, files=None, components=None, ephemeral=False):
        url = f"{self.base_url}/interactions/{interaction['id']}/{interaction['token']}/callback"
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
        if components:
            data["data"]["components"] = components
        if ephemeral:
            data["data"]["flags"] = 64  # This flag makes the response ephemeral

        logging.debug(f"send_interaction payload: {json.dumps(data, indent=2)}")

        async with aiohttp.ClientSession() as session:
            if files:
                form = FormData()
                form.add_field('payload_json', json.dumps(data))
                for file in files:
                    form.add_field('file', file['data'], filename=file['filename'], content_type=file['content_type'])
                async with session.post(url, headers={"Authorization": self.headers["Authorization"]}, data=form) as response:
                    if response.status == 429:  # Rate limit
                        retry_after = int(response.headers.get("Retry-After", 1))
                        logging.error(f"Rate limited. Retrying after {retry_after} seconds.")
                        await asyncio.sleep(retry_after)
                        return await self.send_interaction(interaction, content, embed, embeds, files, components, ephemeral)
                    elif response.status != 200:
                        logging.error(f"Failed to send interaction: {response.status} - {await response.text()}")
                        return None
                    else:
                        response_json = await response.json()
                        logging.info(f"Interaction sent: {response_json}")
                        return response_json
            else:
                async with session.post(url, headers=self.headers, json=data) as response:
                    if response.status == 429:  # Rate limit
                        retry_after = int(response.headers.get("Retry-After", 1))
                        logging.error(f"Rate limited. Retrying after {retry_after} seconds.")
                        await asyncio.sleep(retry_after)
                        return await self.send_interaction(interaction, content, embed, embeds, files, components, ephemeral)
                    elif response.status != 200:
                        logging.error(f"Failed to send interaction: {response.status} - {await response.text()}")
                        return None
                    else:
                        response_json = await response.json()
                        logging.info(f"Interaction sent: {response_json}")
                        return response_json

    async def send_followup_message(self, application_id, interaction_token, content=None, embed=None, embeds=None, files=None, components=None, ephemeral=False):
        url = f"{self.base_url}/webhooks/{application_id}/{interaction_token}"
        data = {
            "content": str(content) if content else "",
            "embeds": [embed] if embed else embeds,
            "components": components,
            "attachments": files,
            "flags": 64 if ephemeral else 0
        }

        logging.debug(f"send_followup_message payload: {json.dumps(data, indent=2)}")

        async with aiohttp.ClientSession() as session:
            if files:
                form = FormData()
                form.add_field('payload_json', json.dumps(data))
                for file in files:
                    form.add_field('file', file['data'], filename=file['filename'], content_type=file['content_type'])
                async with session.post(url, headers={"Authorization": self.headers["Authorization"]}, data=form) as response:
                    if response.status == 429:  # Rate limit
                        retry_after = int(response.headers.get("Retry-After", 1))
                        logging.error(f"Rate limited. Retrying after {retry_after} seconds.")
                        await asyncio.sleep(retry_after)
                        return await self.send_followup_message(application_id, interaction_token, content, embed, embeds, files, components, ephemeral)
                    elif response.status != 200:
                        logging.error(f"Failed to send follow-up message: {response.status} - {await response.text()}")
                        return None
                    else:
                        response_json = await response.json()
                        logging.info(f"Follow-up message sent: {response_json}")
                        return response_json
            else:
                async with session.post(url, headers=self.headers, json=data) as response:
                    if response.status == 429:  # Rate limit
                        retry_after = int(response.headers.get("Retry-After", 1))
                        logging.error(f"Rate limited. Retrying after {retry_after} seconds.")
                        await asyncio.sleep(retry_after)
                        return await self.send_followup_message(application_id, interaction_token, content, embed, embeds, files, components, ephemeral)
                    elif response.status != 200:
                        logging.error(f"Failed to send follow-up message: {response.status} - {await response.text()}")
                        return None
                    else:
                        response_json = await response.json()
                        logging.info(f"Follow-up message sent: {response_json}")
                        return response_json


    #https://discord.com/developers/docs/interactions/message-components#text-inputs
    async def send_modal(self, interaction, title, custom_id, data):
        url = f"{self.base_url}/interactions/{interaction['id']}/{interaction['token']}/callback"

        logging.debug(f"send_modal payload: {json.dumps(data, indent=2)}")

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=self.headers, json=data) as response:
                if response.status == 429:  # Rate limit
                    retry_after = int(response.headers.get("Retry-After", 1))
                    logging.error(f"Rate limited. Retrying after {retry_after} seconds.")
                    #await asyncio.sleep(retry_after)
                    return await self.send_modal(interaction, title, custom_id, components)
                elif response.status != 200:
                    logging.error(f"Failed to send modal: {response.status} - {await response.text()}")
                    return None
                else:
                    response_json = await response.json()
                    logging.info(f"Modal sent: {response_json}")
                    return response_json

    async def delete_message(self, channel_id, message_id):
        url = f"{self.base_url}/channels/{channel_id}/messages/{message_id}"
        async with aiohttp.ClientSession() as session:
            async with session.delete(url, headers=self.headers) as response:
                if response.status != 204:
                    logging.error(f"Failed to delete message: {response.status} - {await response.text()}")
                    return False
                else:
                    logging.info(f"Message deleted")
                    return True

    async def add_reaction(self, channel_id, message_id, emoji):
        url = f"{self.base_url}/channels/{channel_id}/messages/{message_id}/reactions/{emoji}/@me"
        async with aiohttp.ClientSession() as session:
            async with session.put(url, headers=self.headers) as response:
                if response.status != 204:
                    logging.error(f"Failed to add reaction: {response.status} - {await response.text()}")
                    return False
                else:
                    logging.info(f"Reaction added")
                    return True

    async def remove_reaction(self, channel_id, message_id, emoji, user_id):
        url = f"{self.base_url}/channels/{channel_id}/messages/{message_id}/reactions/{emoji}/{user_id}"
        async with aiohttp.ClientSession() as session:
            async with session.delete(url, headers=self.headers) as response:
                if response.status != 204:
                    logging.error(f"Failed to remove reaction: {response.status} - {await response.text()}")
                    return False
                else:
                    logging.info(f"Reaction removed")
                    return True

    async def bulk_delete_messages(self, channel_id, message_ids):
        url = f"{self.base_url}/channels/{channel_id}/messages/bulk-delete"
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=self.headers, json={"messages": message_ids}) as response:
                if response.status != 204:
                    logging.error(f"Failed to bulk delete messages: {response.status} - {await response.text()}")
                    return False
                else:
                    logging.info(f"Messages bulk deleted")
                    return True

    async def pin_message(self, channel_id, message_id):
        url = f"{self.base_url}/channels/{channel_id}/pins/{message_id}"
        async with aiohttp.ClientSession() as session:
            async with session.put(url, headers=self.headers) as response:
                if response.status != 204:
                    logging.error(f"Failed to pin message: {response.status} - {await response.text()}")
                    return False
                else:
                    logging.info(f"Message pinned")
                    return True

    async def unpin_message(self, channel_id, message_id):
        url = f"{self.base_url}/channels/{channel_id}/pins/{message_id}"
        async with aiohttp.ClientSession() as session:
            async with session.delete(url, headers=self.headers) as response:
                if response.status != 204:
                    logging.error(f"Failed to unpin message: {response.status} - {await response.text()}")
                    return False
                else:
                    logging.info(f"Message unpinned")
                    return True

    async def create_webhook(self, channel_id, name, avatar=None):
        url = f"{self.base_url}/channels/{channel_id}/webhooks"
        json_data = {"name": name}
        if avatar:
            json_data["avatar"] = avatar
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=self.headers, json=json_data) as response:
                if response.status != 200:
                    logging.error(f"Failed to create webhook: {response.status} - {await response.text()}")
                    return None
                else:
                    response_json = await response.json()
                    logging.info(f"Webhook created: {response_json}")
                    return response_json

    async def send_webhook_message(self, webhook_url, content=None, username=None, avatar_url=None, embeds=None):
        json_data = {"content": content}
        if username:
            json_data["username"] = username
        if avatar_url:
            json_data["avatar_url"] = avatar_url
        if embeds:
            json_data["embeds"] = embeds
        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, json=json_data) as response:
                if response.status != 200:
                    logging.error(f"Failed to send webhook message: {response.status} - {await response.text()}")
                    return None
                else:
                    response_json = await response.json()
                    logging.info(f"Webhook message sent: {response_json}")
                    return response_json

