"""
Native exception hierarchy for the brazbot.py library.
"""

from typing import Any, Dict, Optional


class BrazbotError(Exception):
    """Base exception for all errors raised by the brazbot library."""
    pass


class HTTPException(BrazbotError):
    """Exception raised when an HTTP request to the Discord API fails."""

    def __init__(
        self,
        status: int,
        message: str = "",
        code: Optional[int] = None,
        errors: Optional[Dict[str, Any]] = None,
        response_data: Optional[Any] = None,
    ):
        self.status = status
        self.code = code or 0
        self.errors = errors or {}
        self.response_data = response_data
        self.discord_message = message
        formatted = f"HTTP {status}"
        if self.code:
            formatted += f" (Discord Code {self.code})"
        if message:
            formatted += f": {message}"
        if self.errors:
            formatted += f" | Details: {self.errors}"
        super().__init__(formatted)


class BadRequest(HTTPException):
    """HTTP 400 - Invalid request payload or parameters."""
    pass


class Unauthorized(HTTPException):
    """HTTP 401 - Invalid or unauthorized bot token."""
    pass


class Forbidden(HTTPException):
    """HTTP 403 - Insufficient permissions on the Discord API."""
    pass


class NotFound(HTTPException):
    """HTTP 404 - Requested Discord resource was not found."""
    pass


class RateLimited(HTTPException):
    """HTTP 429 - Rate limit reached."""

    def __init__(self, retry_after: float, is_global: bool = False, scope: str = "shared"):
        self.retry_after = float(retry_after)
        self.is_global = is_global
        self.scope = scope
        super().__init__(
            429,
            f"Rate limited ({scope}, global={is_global}). Retry after {self.retry_after:.2f}s",
        )


class DiscordServerError(HTTPException):
    """HTTP 5xx - Internal server error on Discord's infrastructure."""
    pass


class GatewayError(BrazbotError):
    """Error related to the Discord Gateway WebSocket connection."""

    def __init__(self, message: str, close_code: Optional[int] = None):
        self.close_code = close_code
        super().__init__(f"{message} (close_code={close_code})" if close_code else message)


class VoiceConnectionError(BrazbotError):
    """Error while connecting, authenticating, or streaming audio over Voice Gateway/UDP."""
    pass


class OpusError(VoiceConnectionError):
    """Error encoding or decoding Opus audio packets."""
    pass


class CommandError(BrazbotError):
    """Base error during command registration or execution."""
    pass


class CommandNotFound(CommandError):
    """Requested command was not found."""
    pass


class MissingRequiredArgument(CommandError):
    """A required command argument was omitted."""

    def __init__(self, param_name: str):
        self.param_name = param_name
        super().__init__(f"Required argument '{param_name}' is missing.")


class BadArgument(CommandError):
    """Failed to convert or validate a command argument."""
    pass


class CheckFailure(CommandError):
    """A command permission or restriction check failed."""
    pass


class MissingPermissions(CheckFailure):
    """The invoking user lacks the required permissions to run the command."""

    def __init__(self, missing_perms: list):
        self.missing_perms = missing_perms
        perms_str = ", ".join(missing_perms)
        super().__init__(f"You are missing required permissions: {perms_str}")


class BotMissingPermissions(CheckFailure):
    """The bot lacks the required permissions to perform the action."""

    def __init__(self, missing_perms: list):
        self.missing_perms = missing_perms
        perms_str = ", ".join(missing_perms)
        super().__init__(f"Bot is missing required permissions: {perms_str}")


class NotOwner(CheckFailure):
    """The invoking user is not the guild or bot owner."""
    pass


class CooldownError(CommandError):
    """The command is currently on cooldown (rate limit)."""

    def __init__(self, retry_after: float, scope: str = "user"):
        self.retry_after = float(retry_after)
        self.scope = scope
        super().__init__(
            f"Command is on cooldown ({scope}). Try again in {self.retry_after:.2f} seconds."
        )
