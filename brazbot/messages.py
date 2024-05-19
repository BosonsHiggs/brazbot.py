import aiohttp

class MessageHandler:
    def __init__(self, token):
        self.base_url = "https://discord.com/api/v10"
        self.token = token
        self.headers = {
            "Authorization": f"Bot {self.token}",
            "Content-Type": "application/json"
        }

    async def send_message(self, channel_id, content):
        url = f"{self.base_url}/channels/{channel_id}/messages"
        payload = {
            "content": content
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=self.headers, json=payload) as response:
                if response.status != 200:
                    print(f"Failed to send message: {response.status}")
                return await response.json()

    async def send_embed(self, channel_id, embed):
        url = f"{self.base_url}/channels/{channel_id}/messages"
        payload = {
            "embeds": [embed]
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=self.headers, json=payload) as response:
                if response.status != 200:
                    print(f"Failed to send embed: {response.status}")
                return await response.json()

    async def send_file(self, channel_id, file_path, content=None):
        url = f"{self.base_url}/channels/{channel_id}/messages"
        data = aiohttp.FormData()
        if content:
            data.add_field('content', content)
        data.add_field('file', open(file_path, 'rb'))
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers={"Authorization": f"Bot {self.token}"}, data=data) as response:
                if response.status != 200:
                    print(f"Failed to send file: {response.status}")
                return await response.json()

    async def send_image(self, channel_id, image_url, content=None):
        embed = {
            "image": {
                "url": image_url
            }
        }
        return await self.send_embed(channel_id, embed)
