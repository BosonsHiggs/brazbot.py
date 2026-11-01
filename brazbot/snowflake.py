"""
Utilities for manipulating Discord Snowflakes (64-bit unique identifiers).
"""

from datetime import datetime, timezone
from typing import Union

DISCORD_EPOCH = 1420070400000  # January 1, 2015 00:00:00 UTC in milliseconds


class Snowflake:
    """
    Represents and validates a 64-bit Discord API Snowflake identifier.
    """

    def __init__(self, value: Union[int, str]):
        self.value = self.parse(value)

    @staticmethod
    def is_valid(snowflake: Union[int, str, None]) -> bool:
        """Checks whether the given value is a valid positive Discord Snowflake."""
        if snowflake is None or isinstance(snowflake, bool):
            return False
        try:
            int_snowflake = int(str(snowflake).strip())
            return int_snowflake > 0
        except (ValueError, TypeError):
            return False

    @staticmethod
    def parse(snowflake: Union[int, str]) -> int:
        """Converts a value to an integer if it is a valid Snowflake."""
        if Snowflake.is_valid(snowflake):
            return int(str(snowflake).strip())
        raise ValueError(f"Invalid snowflake value: {snowflake}")

    @staticmethod
    def to_datetime(snowflake: Union[int, str]) -> datetime:
        """Extracts the UTC creation timestamp from a Snowflake."""
        val = Snowflake.parse(snowflake)
        timestamp_ms = (val >> 22) + DISCORD_EPOCH
        return datetime.fromtimestamp(timestamp_ms / 1000.0, tz=timezone.utc)

    @staticmethod
    def from_datetime(dt: datetime) -> int:
        """Generates a synthetic Snowflake from a datetime object."""
        timestamp_ms = int(dt.timestamp() * 1000)
        return max(0, (timestamp_ms - DISCORD_EPOCH) << 22)

    @property
    def created_at(self) -> datetime:
        return self.to_datetime(self.value)

    @property
    def internal_worker_id(self) -> int:
        return (self.value & 0x3E0000) >> 17

    @property
    def internal_process_id(self) -> int:
        return (self.value & 0x1F000) >> 12

    @property
    def increment(self) -> int:
        return self.value & 0xFFF

    def __int__(self) -> int:
        return self.value

    def __str__(self) -> str:
        return str(self.value)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, (int, str, Snowflake)):
            try:
                return self.value == Snowflake.parse(other)  # type: ignore[arg-type]
            except ValueError:
                return False
        return False

    def __hash__(self) -> int:
        return hash(self.value)

    def __repr__(self) -> str:
        return f"Snowflake({self.value})"
