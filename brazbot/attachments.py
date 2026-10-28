"""
Modelo de Anexo (Attachment) da API v10 do Discord.
"""

from typing import Any, Dict, Optional

import aiohttp


class Attachment:
    """Representa um arquivo anexado em uma mensagem ou comando slash da API v10."""

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
        """Baixa e retorna os bytes brutos do anexo."""
        async with aiohttp.ClientSession() as session:
            async with session.get(self.url) as response:
                if response.status == 200:
                    return await response.read()
                raise Exception(f"Failed to download attachment: HTTP {response.status}")

    async def save(self, destination_path: str) -> int:
        """Baixa e salva o anexo em um caminho local no disco."""
        data = await self.read()
        with open(destination_path, "wb") as fp:
            return fp.write(data)

    async def to_file(self) -> Dict[str, Any]:
        """Baixa o anexo e retorna um dicionário pronto para envio em `files=[...]`."""
        data = await self.read()
        return {
            "filename": self.filename,
            "data": data,
            "content_type": self.content_type,
            "description": self.description,
        }

    def __str__(self) -> str:
        return self.url or self.filename
