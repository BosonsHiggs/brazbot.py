"""
Attachment model for Discord API v10.
"""

from typing import Any, Dict

import aiohttp


class Attachment:
    """Represents a file attached to a message or slash command in Discord API v10."""

    def __init__(self, attachment_data: Dict[str, Any]):
        self._raw = attachment_data or {}
        self.id = str(attachment_data.get("id") or "0")
        self.filename = attachment_data.get("filename", "attachment.bin")
        self.description = attachment_data.get("description")
        self.content_type = attachment_data.get("content_type", "application/octet-stream")
        self.size = int(attachment_data.get("size") or 0)
        self.url = attachment_data.get("url", "")
        self.proxy_url = attachment_data.get("proxy_url", self.url)
        self.height = attachment_data.get("height")
        self.width = attachment_data.get("width")
        self.ephemeral = bool(attachment_data.get("ephemeral", False))
        self.duration_secs = attachment_data.get("duration_secs")
        self.waveform = attachment_data.get("waveform")

    async def read(self) -> bytes:
        """Downloads and returns the raw bytes of the attachment."""
        async with aiohttp.ClientSession() as session:
            async with session.get(self.url) as response:
                if response.status == 200:
                    return await response.read()
                raise Exception(f"Failed to download attachment: HTTP {response.status}")

    async def save(self, destination_path: str) -> int:
        """Downloads and saves the attachment to a local file path."""
        data = await self.read()
        with open(destination_path, "wb") as fp:
            return fp.write(data)

    async def to_file(self) -> Dict[str, Any]:
        """Downloads the attachment and returns a dictionary ready for `files=[...]` upload."""
        data = await self.read()
        return {
            "filename": self.filename,
            "data": data,
            "content_type": self.content_type,
            "description": self.description,
        }

    def __str__(self) -> str:
        return self.url or self.filename
