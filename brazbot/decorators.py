"""
Decoradores para controle de permissões, sincronização de comandos Slash,
tarefas periódicas (tasks), rate limiting (cooldown) e metadados de parâmetros.
"""

import asyncio
import functools
import logging
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Set, Union

from brazbot.cache import Cache
from brazbot.permissions import PERMISSION_FLAGS, Permissions

logger = logging.getLogger(__name__)
cache = Cache()
_SYNCED_TARGETS: Set[str] = set()


def tasks(seconds: float = 120.0, run_immediately: bool = False) -> Callable[..., Any]:
    """Executa uma corrotina periodicamente a cada `seconds` segundos em background."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> None:
            if run_immediately:
                try:
                    await func(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Erro na tarefa periódica {func.__name__}: {e}")
            while True:
                await asyncio.sleep(seconds)
                try:
                    await func(*args, **kwargs)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Erro na tarefa periódica {func.__name__}: {e}")

        wrapper._is_task = True  # type: ignore[attr-defined]
        wrapper._task_interval = seconds  # type: ignore[attr-defined]
        return wrapper

    return decorator


def sync_slash_commands(
    guild_id: Optional[Union[str, List[str]]] = None,
    force_on_invoke: bool = False,
) -> Callable[..., Any]:
    """
    Marca o comando para sincronização de Slash Commands (Global, Servidor único ou Lista de servidores).
    Por padrão, registra os alvos de sincronização no bot para que sejam sincronizados na inicialização
    (evitando atingir rate limits da API em toda execução de comando).
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(ctx: Any, *args: Any, **kwargs: Any) -> Any:
            result = await func(ctx, *args, **kwargs)

            # Só sincroniza na invocação se explicitamente forçado ou se o comando for o próprio `/sync`
            should_sync = force_on_invoke or getattr(func, "__name__", "").startswith("sync")
            if not should_sync:
                return result

            if guild_id is None:
                if "GLOBAL" not in _SYNCED_TARGETS or force_on_invoke:
                    try:
                        await ctx.bot.command_handler.sync_commands()
                        _SYNCED_TARGETS.add("GLOBAL")
                    except Exception as e:
                        logger.error(f"Erro na sincronização global: {e}")
            elif isinstance(guild_id, str):
                if guild_id not in _SYNCED_TARGETS or force_on_invoke:
                    try:
                        await ctx.bot.command_handler.sync_commands(guild_id=guild_id)
                        _SYNCED_TARGETS.add(guild_id)
                    except Exception as e:
                        logger.error(f"Erro ao sincronizar servidor {guild_id}: {e}")
            elif isinstance(guild_id, list):
                for gid in guild_id:
                    if gid not in _SYNCED_TARGETS or force_on_invoke:
                        try:
                            await ctx.bot.command_handler.sync_commands(guild_id=gid)
                            _SYNCED_TARGETS.add(gid)
                        except Exception as e:
                            logger.error(f"Erro no servidor {gid}: {e}")
            return result

        wrapper._slash_command = True  # type: ignore[attr-defined]
        wrapper._guild_id = guild_id  # type: ignore[attr-defined]
        return wrapper

    return decorator


def sync_commands(guilds: Optional[Union[str, List[str]]] = None) -> Callable[..., Any]:
    """Alias curto para `sync_slash_commands`."""
    return sync_slash_commands(guild_id=guilds)


def sync_test_servers(guild_ids: List[str]) -> Callable[..., Any]:
    """Sincroniza comandos em uma lista de servidores de teste."""
    return sync_slash_commands(guild_id=guild_ids)


def describe(**descriptions: str) -> Callable[..., Any]:
    """Define descrições detalhadas para os parâmetros de um comando Slash."""

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
    """Restringe o comando a Administradores ou ao Dono do Servidor."""

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
                        "message": "Você precisa ser um administrador ou o dono do servidor para usar este comando.",
                        "channel_id": ctx.channel_id,
                    },
                }
            )
            return None

        return wrapper

    return decorator


def is_owner() -> Callable[..., Any]:
    """Restringe o comando ao Dono do Servidor."""

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
                        "message": "Você precisa ser o dono do servidor para usar este comando.",
                        "channel_id": ctx.channel_id,
                    },
                }
            )
            return None

        return wrapper

    return decorator


def has_role(role_name_or_id: str) -> Callable[..., Any]:
    """Restringe o comando a membros que possuam um cargo específico (por nome ou ID)."""

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
                        "message": f"Você precisa do cargo '{role_name_or_id}' para usar este comando.",
                        "channel_id": ctx.channel_id,
                    },
                }
            )
            return None

        return wrapper

    return decorator


def has_permissions(**required_perms: bool) -> Callable[..., Any]:
    """
    Verifica se o autor do comando possui todas as permissões da API v10 especificadas
    (ex.: `@has_permissions(ban_members=True, manage_messages=True)`).
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(ctx: Any, *args: Any, **kwargs: Any) -> Any:
            guild_id = ctx.guild_id
            if not guild_id:
                await ctx.reply("❌ Este comando só pode ser executado em um servidor.", ephemeral=True)
                return None

            author_id = str(ctx.author["id"]) if ctx.author else ""
            guild_info = await _fetch_cached_guild_info(ctx.bot, guild_id)
            if str(guild_info.get("owner_id")) == author_id:
                return await func(ctx, *args, **kwargs)

            # Se a interação já enviou resolved permissions
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
                        "message": f"Permissões insuficientes. Necessário: {missing_str}",
                        "channel_id": ctx.channel_id,
                    },
                }
            )
            return None

        return wrapper

    return decorator


def guild_only() -> Callable[..., Any]:
    """Garante que o comando só seja executado dentro de um servidor (não em DMs)."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(ctx: Any, *args: Any, **kwargs: Any) -> Any:
            if not ctx.guild_id:
                await ctx.reply("❌ Este comando só pode ser usado dentro de um servidor.", ephemeral=True)
                return None
            return await func(ctx, *args, **kwargs)

        return wrapper

    return decorator


def in_voice_channel() -> Callable[..., Any]:
    """Garante que o usuário que invocou o comando esteja conectado a um canal de voz."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(ctx: Any, *args: Any, **kwargs: Any) -> Any:
            if not ctx.author or not getattr(ctx.author, "voice", None) or not ctx.author.voice.channel:
                await ctx.reply(
                    "❌ Você precisa estar conectado a um canal de voz para usar este comando!",
                    ephemeral=True,
                )
                return None
            return await func(ctx, *args, **kwargs)

        return wrapper

    return decorator


def rate_limit(limit: int, per: float, scope: str = "user") -> Callable[..., Any]:
    """
    Aplica limite de uso (cooldown) por usuário (`user`), canal (`channel`) ou servidor (`guild`).
    Informa o tempo restante exato quando o limite é atingido.
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
                            "message": "Você atingiu o limite de uso deste comando.",
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
    """Decorador standalone para marcar uma função como comando (para uso em Cogs ou scripts)."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        func._command = {  # type: ignore[attr-defined]
            "name": name or func.__name__,
            "description": description or func.__doc__ or "No description provided",
            "aliases": aliases or [],
            "options": [],
        }
        return func

    return decorator
