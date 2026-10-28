"""
Classe utilitária para envio de arquivos locais (`File`) na API v10 do Discord.
"""

import mimetypes
import os
from typing import Any, Dict, Optional, Union


class File:
    """Representa um arquivo local ou buffer em memória para envio ao Discord."""

    def __init__(
        self,
        file_path_or_bytes: Union[str, bytes],
        filename: Optional[str] = None,
        description: Optional[str] = None,
        spoiler: bool = False,
    ):
        if isinstance(file_path_or_bytes, str):
            self.file_path: Optional[str] = file_path_or_bytes
            self._data: Optional[bytes] = None
            base_name = filename or os.path.basename(file_path_or_bytes)
        else:
            self.file_path = None
            self._data = bytes(file_path_or_bytes)
            base_name = filename or "attachment.bin"

        if spoiler and not base_name.startswith("SPOILER_"):
            base_name = f"SPOILER_{base_name}"
        self.filename = base_name
        self.description = description
        guessed_type, _ = mimetypes.guess_type(self.filename)
        self.content_type = guessed_type or "application/octet-stream"

    def read_bytes(self) -> bytes:
        if self._data is not None:
            return self._data
        if self.file_path:
            with open(self.file_path, "rb") as fp:
                return fp.read()
        return b""

    def to_file_dict(self) -> Dict[str, Any]:
        return {
            "filename": self.filename,
            "data": self.read_bytes(),
            "content_type": self.content_type,
            "description": self.description,
        }

    def to_dict(self) -> Dict[str, Any]:
        if self.file_path:
            return {"file": open(self.file_path, "rb")}
        return self.to_file_dict()
