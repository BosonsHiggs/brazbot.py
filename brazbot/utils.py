"""
Utility functions for rapid Embed creation, unique IDs, timestamp formatting, and pagination.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Generator, Iterable, List, Optional


def create_embed(
    title: str,
    description: str,
    color: int = 0x5865F2,
    footer: Optional[str] = None,
    thumbnail: Optional[str] = None,
) -> Dict[str, Any]:
    """Creates an embed dictionary ready for sending to the Discord API."""
    embed: Dict[str, Any] = {
        "title": title,
        "description": description,
        "color": color,
    }
    if footer:
        embed["footer"] = {"text": footer}
    if thumbnail:
        embed["thumbnail"] = {"url": thumbnail}
    return embed


def format_command_response(response_text: str, is_error: bool = False) -> Dict[str, Any]:
    """Formats a command response as a success (green) or error (red) embed."""
    color = 0xED4245 if is_error else 0x57F287
    return create_embed("Command Response", str(response_text), color)


def create_error_embed(error_message: str, title: str = "❌ Error") -> Dict[str, Any]:
    """Creates a standardized error embed dictionary."""
    return {
        "title": title,
        "description": str(error_message),
        "color": 0xED4245,
    }


def create_success_embed(message: str, title: str = "✅ Success") -> Dict[str, Any]:
    """Creates a standardized success embed dictionary."""
    return {
        "title": title,
        "description": str(message),
        "color": 0x57F287,
    }


def generate_unique_id(max_length: int = 8) -> int:
    """Generates a unique pseudorandom integer ID based on UUID4."""
    unique_id = uuid.uuid4()
    shortened_hex = unique_id.hex[: max(1, min(32, max_length))]
    return int(shortened_hex, 16)


def generate_list(items: Optional[Iterable[Any]] = None) -> Generator[Any, None, None]:
    """Simple generator yielding items from an iterable."""
    if items:
        for item in items:
            yield item


def format_discord_timestamp(dt: Optional[datetime] = None, style: str = "R") -> str:
    """
    Formats a `datetime` object into native Discord timestamp syntax (`<t:UNIX:STYLE>`).
    Styles: 't' (short time), 'T' (long time), 'd' (short date), 'D' (long date),
    'f' (short date/time), 'F' (long date/time), 'R' (relative).
    """
    if dt is None:
        dt = datetime.now(timezone.utc)
    return f"<t:{int(dt.timestamp())}:{style}>"


def chunk_list(items: List[Any], chunk_size: int = 10) -> List[List[Any]]:
    """Splits a list into pages/chunks of size `chunk_size`."""
    return [items[i : i + chunk_size] for i in range(0, len(items), max(1, chunk_size))]
