"""
Construtor fluente de Embeds da API v10 do Discord com paleta de cores semânticas.
"""

import datetime
import json
from typing import Any, Dict, List, Optional, Union


class EmbedColor:
    """Paleta de cores oficiais do Discord para Embeds."""

    DEFAULT = 0x000000
    BLURPLE = 0x5865F2
    GREEN = 0x57F287
    YELLOW = 0xFEE75C
    FUCHSIA = 0xEB459E
    RED = 0xED4245
    WHITE = 0xFFFFFF
    BLUE = 0x3498DB
    GOLD = 0xF1C40F
    ORANGE = 0xE67E22
    PURPLE = 0x9B59B6
    DARK_THEME = 0x2B2D31


class Embed:
    """
    Representa e constrói um Rich Embed da API v10 do Discord.
    """

    Color = EmbedColor

    def __init__(
        self,
        title: Optional[str] = None,
        description: Optional[str] = None,
        url: Optional[str] = None,
        color: Optional[int] = None,
        timestamp: Optional[Union[datetime.datetime, str]] = None,
    ):
        self.title = title
        self.description = description
        self.url = url
        self.color = color
        self.timestamp: Optional[str] = None
        if timestamp is not None:
            self.set_timestamp(timestamp)
        self.footer: Dict[str, Any] = {}
        self.image: Dict[str, Any] = {}
        self.thumbnail: Dict[str, Any] = {}
        self.author: Dict[str, Any] = {}
        self.fields: List[Dict[str, Any]] = []

    def set_title(self, title: str) -> "Embed":
        self.title = str(title)
        return self

    def set_description(self, description: str) -> "Embed":
        self.description = str(description)
        return self

    def set_url(self, url: str) -> "Embed":
        self.url = str(url)
        return self

    def set_color(self, color: int) -> "Embed":
        self.color = int(color)
        return self

    def set_timestamp(
        self, timestamp: Optional[Union[datetime.datetime, str]] = None
    ) -> "Embed":
        if timestamp is None:
            timestamp = datetime.datetime.now(datetime.timezone.utc)
        if isinstance(timestamp, datetime.datetime):
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=datetime.timezone.utc)
            self.timestamp = timestamp.isoformat()
        else:
            self.timestamp = str(timestamp)
        return self

    def set_footer(self, text: str, icon_url: Optional[str] = None) -> "Embed":
        self.footer = {"text": str(text)}
        if icon_url:
            self.footer["icon_url"] = str(icon_url)
        return self

    def set_image(self, url: str) -> "Embed":
        self.image = {"url": str(url)}
        return self

    def set_thumbnail(self, url: str) -> "Embed":
        self.thumbnail = {"url": str(url)}
        return self

    def set_author(
        self,
        name: str,
        url: Optional[str] = None,
        icon_url: Optional[str] = None,
    ) -> "Embed":
        self.author = {"name": str(name)}
        if url:
            self.author["url"] = str(url)
        if icon_url:
            self.author["icon_url"] = str(icon_url)
        return self

    def add_field(self, name: str, value: Any, inline: bool = True) -> "Embed":
        self.fields.append({"name": str(name), "value": str(value), "inline": bool(inline)})
        return self

    def clear_fields(self) -> "Embed":
        self.fields.clear()
        return self

    def to_dict(self) -> Dict[str, Any]:
        embed: Dict[str, Any] = {}
        if self.title is not None:
            embed["title"] = self.title
        if self.description is not None:
            embed["description"] = self.description
        if self.url is not None:
            embed["url"] = self.url
        if self.color is not None:
            embed["color"] = self.color
        if self.timestamp is not None:
            embed["timestamp"] = self.timestamp
        if self.footer:
            embed["footer"] = self.footer
        if self.image:
            embed["image"] = self.image
        if self.thumbnail:
            embed["thumbnail"] = self.thumbnail
        if self.author:
            embed["author"] = self.author
        if self.fields:
            embed["fields"] = self.fields
        return embed

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=4)

    def __len__(self) -> int:
        total = len(self.title or "") + len(self.description or "")
        total += len(self.footer.get("text", "")) + len(self.author.get("name", ""))
        for f in self.fields:
            total += len(f.get("name", "")) + len(f.get("value", ""))
        return total
