"""
Decorators for permission checks, Slash Command synchronization, periodic background tasks,
rate limiting (cooldowns), and parameter descriptions.
"""

import asyncio
import functools
import logging
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Set, Union

from brazbot.cache import Cache
from brazbot.permissions import Permissions

logger = logging.getLogger(__name__)
cache = Cache()
_SYNCED_TARGETS: Set[str] = set()


def tasks(seconds: float = 120.0, run_immediately: bool = False) -> Callable[..., Any]:
    """Executes an asynchronous coroutine periodically every `seconds` seconds in the background."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> None:
            if run_immediately:
                try:
                    await func(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Error in background task {func.__name__}: {e}")
            while True:
                await asyncio.sleep(seconds)
                try:
                    await func(*args, **kwargs)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in background task {func.__name__}: {e}")

        wrapper._is_task = True  # type: ignore[attr-defined]
        wrapper._task_interval = seconds  # type: ignore[attr-defined]
        return wrapper

    return decorator


def sync_slash_commands(
    target_or_guild_id: Optional[Union[str, List[str], Callable[..., Any], type]] = None,
    force_on_invoke: bool = False,
    *,
    guild_id: Optional[Union[str, List[str]]] = None,
) -> Any:
    """
    Marks a Bot class or command function for Slash Command synchronization (Global, Single Guild, or List of Guilds).
    Supports all invocation styles:
    - `@sync_slash_commands` (on a Bot subclass or command function, without parentheses)
    - `@sync_slash_commands()` (with empty parentheses)
    - `@sync_slash_commands("GUILD_ID")` or `@sync_slash_commands(guild_id="GUILD_ID")`
    """
    resolved_guild_id: Optional[Union[str, List[str]]] = guild_id
    direct_target: Optional[Any] = None

    if isinstance(target_or_guild_id, type) or callable(target_or_guild_id):
        direct_target = target_or_guild_id
    elif target_or_guild_id is not None and resolved_guild_id is None:
        resolved_guild_id = target_or_guild_id

    def decorator(obj: Any) -> Any:
        # Case 1: Decorating a Bot class (e.g. `@sync_slash_commands class ModerationBot(Bot):`)
        if isinstance(obj, type):
            obj._sync_slash_commands = True
            obj._sync_guild_id = resolved_guild_id
            return obj

        # Case 2: Decorating a command coroutine function
        @functools.wraps(obj)
        async def wrapper(ctx: Any, *args: Any, **kwargs: Any) -> Any:
            result = await obj(ctx, *args, **kwargs)

            should_sync = force_on_invoke or getattr(obj, "__name__", "").startswith("sync")
            if not should_sync:
                return result

            if resolved_guild_id is None:
                if "GLOBAL" not in _SYNCED_TARGETS or force_on_invoke:
                    try:
                        await ctx.bot.command_handler.sync_commands()
                        _SYNCED_TARGETS.add("GLOBAL")
                    except Exception as e:
                        logger.error(f"Global command sync error: {e}")
            elif isinstance(resolved_guild_id, str):
                if resolved_guild_id not in _SYNCED_TARGETS or force_on_invoke:
                    try:
                        await ctx.bot.command_handler.sync_commands(guild_id=resolved_guild_id)
                        _SYNCED_TARGETS.add(resolved_guild_id)
                    except Exception as e:
                        logger.error(f"Error syncing commands in guild {resolved_guild_id}: {e}")
            elif isinstance(resolved_guild_id, list):
                for gid in resolved_guild_id:
                    if gid not in _SYNCED_TARGETS or force_on_invoke:
                        try:
                            await ctx.bot.command_handler.sync_commands(guild_id=gid)
                            _SYNCED_TARGETS.add(gid)
                        except Exception as e:
                            logger.error(f"Error syncing commands in guild {gid}: {e}")
            return result

        wrapper._slash_command = True  # type: ignore[attr-defined]
        wrapper._guild_id = resolved_guild_id  # type: ignore[attr-defined]
        return wrapper

    if direct_target is not None:
        return decorator(direct_target)
    return decorator


def sync_commands(guilds: Optional[Union[str, List[str]]] = None) -> Callable[..., Any]:
    """Short alias for `sync_slash_commands`."""
    return sync_slash_commands(guild_id=guilds)


def sync_test_servers(guild_ids: List[str]) -> Callable[..., Any]:
    """Synchronizes slash commands across a list of test guilds."""
    return sync_slash_commands(guild_id=guild_ids)


def describe(**descriptions: str) -> Callable[..., Any]:
    """Attaches parameter descriptions to a Slash Command."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        if not hasattr(func, "parameter_descriptions"):
            func.parameter_descriptions = {}  # type: ignore[attr-defined]
        func.parameter_descriptions.update(descriptions)  # type: ignore[attr-defined]
        return func

    return decorator


async def _fetch_cached_guild_info(bot: Any, guild_id: str) -> Dict[str, Any]:
    guild_info = cache.get(f"guild_info_{guild_id}")
    if not guild_info:
        guild_info = await bot.http.request("GET", f"/guilds/{guild_id}", raise_on_error=False) or {}
        if guild_info:
            cache.set(f"guild_info_{guild_id}", guild_info, ttl=300)
    return guild_info


async def _fetch_cached_guild_roles(bot: Any, guild_id: str) -> List[Dict[str, Any]]:
    guild_roles = cache.get(f"guild_roles_{guild_id}")
    if not guild_roles:
        guild_roles = (
            await bot.http.request("GET", f"/guilds/{guild_id}/roles", raise_on_error=False) or []
        )
        if guild_roles:
            cache.set(f"guild_roles_{guild_id}", guild_roles, ttl=300)
    return guild_roles


def is_admin() -> Callable[..., Any]:
    """Restricts command execution to Guild Administrators or the Guild Owner."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(ctx: Any, *args: Any, **kwargs: Any) -> Any:
            guild_id = ctx.guild_id
            author_id = str(ctx.author["id"]) if ctx.author else ""

            if guild_id:
                guild_info = await _fetch_cached_guild_info(ctx.bot, guild_id)
                if str(guild_info.get("owner_id")) == author_id:
                    return await func(ctx, *args, **kwargs)

                roles = ctx.member["roles"] if ctx.member and "roles" in ctx.member else []
                guild_roles = await _fetch_cached_guild_roles(ctx.bot, guild_id)
                admin_role_ids = [
                    str(r["id"]) for r in guild_roles if int(r.get("permissions", 0)) & 0x8
                ]
                if any(str(rid) in admin_role_ids for rid in roles):
                    return await func(ctx, *args, **kwargs)

            await ctx.bot.event_handler.handle_event(
                {
                    "t": "on_error",
                    "d": {
                        "message": "You must be an administrator or the server owner to use this command.",
                        "channel_id": ctx.channel_id,
                    },
                }
            )
            return None

        return wrapper

    return decorator


def is_owner() -> Callable[..., Any]:
    """Restricts command execution to the Guild Owner."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(ctx: Any, *args: Any, **kwargs: Any) -> Any:
            guild_id = ctx.guild_id
            author_id = str(ctx.author["id"]) if ctx.author else ""

            if guild_id:
                guild_info = await _fetch_cached_guild_info(ctx.bot, guild_id)
                if str(guild_info.get("owner_id")) == author_id:
                    return await func(ctx, *args, **kwargs)

            await ctx.bot.event_handler.handle_event(
                {
                    "t": "on_error",
                    "d": {
                        "message": "You must be the server owner to use this command.",
                        "channel_id": ctx.channel_id,
                    },
                }
            )
            return None

        return wrapper

    return decorator


def has_role(role_name_or_id: str) -> Callable[..., Any]:
    """Restricts command execution to members who hold a specific role (by name or ID)."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(ctx: Any, *args: Any, **kwargs: Any) -> Any:
            roles = [str(r) for r in (ctx.member["roles"] if ctx.member and "roles" in ctx.member else [])]
            guild_id = ctx.guild_id

            if str(role_name_or_id) in roles:
                return await func(ctx, *args, **kwargs)

            if guild_id:
                guild_roles = await _fetch_cached_guild_roles(ctx.bot, guild_id)
                role_ids = [
                    str(r["id"])
                    for r in guild_roles
                    if r.get("name") == role_name_or_id or str(r.get("id")) == str(role_name_or_id)
                ]
                if any(rid in roles for rid in role_ids):
                    return await func(ctx, *args, **kwargs)

            await ctx.bot.event_handler.handle_event(
                {
                    "t": "on_error",
                    "d": {
                        "message": f"You need the '{role_name_or_id}' role to use this command.",
                        "channel_id": ctx.channel_id,
                    },
                }
            )
            return None

        return wrapper

    return decorator


def has_permissions(**required_perms: bool) -> Callable[..., Any]:
    """
    Verifies that the command author holds all specified Discord API v10 permissions
    (e.g., `@has_permissions(ban_members=True, manage_messages=True)`).
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(ctx: Any, *args: Any, **kwargs: Any) -> Any:
            guild_id = ctx.guild_id
            if not guild_id:
                await ctx.reply("❌ This command can only be executed inside a server.", ephemeral=True)
                return None

            author_id = str(ctx.author["id"]) if ctx.author else ""
            guild_info = await _fetch_cached_guild_info(ctx.bot, guild_id)
            if str(guild_info.get("owner_id")) == author_id:
                return await func(ctx, *args, **kwargs)

            if ctx.member and ctx.member.get("permissions"):
                perm_obj = Permissions(ctx.member["permissions"])
            else:
                roles = [str(r) for r in (ctx.member["roles"] if ctx.member and "roles" in ctx.member else [])]
                guild_roles = await _fetch_cached_guild_roles(ctx.bot, guild_id)
                total_bits = 0
                for r in guild_roles:
                    if str(r.get("id")) == str(guild_id) or str(r.get("id")) in roles:
                        total_bits |= int(r.get("permissions", 0))
                perm_obj = Permissions(total_bits)

            missing = perm_obj.missing(**required_perms)
            if not missing:
                return await func(ctx, *args, **kwargs)

            missing_str = ", ".join(missing)
            await ctx.bot.event_handler.handle_event(
                {
                    "t": "on_error",
                    "d": {
                        "message": f"Insufficient permissions. Required: {missing_str}",
                        "channel_id": ctx.channel_id,
                    },
                }
            )
            return None

        return wrapper

    return decorator


def guild_only() -> Callable[..., Any]:
    """Ensures the command can only be executed inside a server (not in DMs)."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(ctx: Any, *args: Any, **kwargs: Any) -> Any:
            if not ctx.guild_id:
                await ctx.reply("❌ This command can only be used inside a server.", ephemeral=True)
                return None
            return await func(ctx, *args, **kwargs)

        return wrapper

    return decorator


def in_voice_channel() -> Callable[..., Any]:
    """Ensures the invoking user is currently connected to a voice channel."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(ctx: Any, *args: Any, **kwargs: Any) -> Any:
            if not ctx.author or not getattr(ctx.author, "voice", None) or not ctx.author.voice.channel:
                await ctx.reply(
                    "❌ You must be connected to a voice channel to use this command!",
                    ephemeral=True,
                )
                return None
            return await func(ctx, *args, **kwargs)

        return wrapper

    return decorator


def rate_limit(limit: int, per: float, scope: str = "user") -> Callable[..., Any]:
    """
    Applies a command cooldown per user (`user`), channel (`channel`), or server (`guild`).
    Reports the exact remaining time when the cooldown limit is reached.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(ctx: Any, *args: Any, **kwargs: Any) -> Any:
            target_id = (
                ctx.guild_id
                if scope == "guild"
                else ctx.channel_id
                if scope == "channel"
                else (ctx.author["id"] if ctx.author else "anon")
            )
            key = f"rate_limit:{func.__name__}:{scope}:{target_id}"
            current = cache.get(key) or 0
            if current >= limit:
                time_left = cache.get_remaining_ttl(key) or float(per)
                await ctx.bot.event_handler.handle_event(
                    {
                        "t": "on_error",
                        "d": {
                            "message": "You have reached the rate limit for this command.",
                            "time_left": time_left,
                            "channel_id": ctx.channel_id,
                        },
                    }
                )
                return None

            rem_ttl = cache.get_remaining_ttl(key)
            cache.set(key, current + 1, ttl=rem_ttl if rem_ttl > 0 else float(per))
            return await func(ctx, *args, **kwargs)

        return wrapper

    return decorator


cooldown = rate_limit


def command(
    name: Optional[str] = None,
    description: Optional[str] = None,
    aliases: Optional[List[str]] = None,
) -> Callable[..., Any]:
    """Standalone decorator to mark a function as a command (for use in Cogs or scripts)."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        func._command = {  # type: ignore[attr-defined]
            "name": name or func.__name__,
            "description": description or func.__doc__ or "No description provided",
            "aliases": aliases or [],
            "options": [],
        }
        return func

    return decorator
