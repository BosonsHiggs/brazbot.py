class InteractionResponse:
    def __init__(self, bot, message):
        self.bot = bot
        self.message = message
        self.interaction_id = message['id']
        self.interaction_token = message['token']

    async def send(self, content=None, embeds=None, embed=None, files=None, ephemeral=False):
        url = f"https://discord.com/api/v10/interactions/{self.interaction_id}/{self.interaction_token}/callback"
        data = {
            "type": 4,  # Type 4 means responding with a message
            "data": {}
        }
        if content:
            data["data"]["content"] = content
        if embeds:
            data["data"]["embeds"] = embeds
        if embed:
            data["data"]["embeds"] = [embed]
        if ephemeral:
            data["data"]["flags"] = 64  # Ephemeral message

        if files:
            multipart_data = aiohttp.FormData()
            multipart_data.add_field('payload_json', json.dumps(data))
            for file in files:
                multipart_data.add_field('file', open(file, 'rb'))
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=multipart_data, headers={"Authorization": f"Bot {self.bot.token}"}) as response:
                    if response.status != 200:
                        logging.error(f"Failed to send interaction response: {response.status} - {await response.text()}")
                    return await response.json()
        else:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data, headers={"Authorization": f"Bot {self.bot.token}"}) as response:
                    if response.status != 200:
                        logging.error(f"Failed to send interaction response: {response.status} - {await response.text()}")
                    return await response.json()
