import aiohttp

class Attachment:
    def __init__(self, attachment_data):
        self.id = attachment_data['id']
        self.filename = attachment_data['filename']
        self.url = attachment_data['url']
        self.content_type = attachment_data['content_type']

    async def to_file(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(self.url) as response:
                if response.status == 200:
                    return {
                        'filename': self.filename,
                        'data': await response.read(),
                        'content_type': self.content_type
                    }
                else:
                    raise Exception(f"Failed to download file: {response.status}")
