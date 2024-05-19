import aiohttp
import functools
from brazbot.cache import Cache

cache = Cache()

def sync_slash_commands(guild_id=None):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(ctx, *args, **kwargs):
            await func(ctx, *args, **kwargs)
            await ctx.bot.command_handler.sync_commands(guild_id)
        return wrapper
    return decorator

def is_admin():
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(ctx, *args, **kwargs):
            guild_id = ctx.guild_id
            author_id = ctx.author['id']
            
            guild_info = cache.get(f"guild_info_{guild_id}")
            if not guild_info:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"https://discord.com/api/v10/guilds/{guild_id}", headers=ctx.bot.headers) as response:
                        guild_info = await response.json()
                cache.set(f"guild_info_{guild_id}", guild_info)
            if guild_info.get('owner_id') == author_id:
                return await func(ctx, *args, **kwargs)
            
            roles = ctx.member['roles']
            guild_roles = cache.get(f"guild_roles_{guild_id}")
            if not guild_roles:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"https://discord.com/api/v10/guilds/{guild_id}/roles", headers=ctx.bot.headers) as response:
                        guild_roles = await response.json()
                cache.set(f"guild_roles_{guild_id}", guild_roles)
            admin_role_ids = [role['id'] for role in guild_roles if int(role['permissions']) & 0x8]
            if any(role_id in roles for role_id in admin_role_ids):
                return await func(ctx, *args, **kwargs)
            else:
                await ctx.bot.event_handler.handle_event({
                    't': 'on_error',
                    'd': {'message': 'Você precisa ser um administrador ou o dono do servidor para usar este comando.', 'channel_id': ctx.channel_id}
                })
        return wrapper
    return decorator

def is_owner():
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(ctx, *args, **kwargs):
            guild_id = ctx.guild_id
            author_id = ctx.author['id']
            
            guild_info = cache.get(f"guild_info_{guild_id}")
            if not guild_info:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"https://discord.com/api/v10/guilds/{guild_id}", headers=ctx.bot.headers) as response:
                        guild_info = await response.json()
                cache.set(f"guild_info_{guild_id}", guild_info)
            if guild_info.get('owner_id') == author_id:
                return await func(ctx, *args, **kwargs)
            await ctx.bot.event_handler.handle_event({
                't': 'on_error',
                'd': {'message': 'Você precisa ser o dono do servidor para usar este comando.', 'channel_id': ctx.channel_id}
            })
        return wrapper
    return decorator

def has_role(role_name):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(ctx, *args, **kwargs):
            roles = ctx.member['roles']
            guild_id = ctx.guild_id
            
            guild_roles = cache.get(f"guild_roles_{guild_id}")
            if not guild_roles:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"https://discord.com/api/v10/guilds/{guild_id}/roles", headers=ctx.bot.headers) as response:
                        guild_roles = await response.json()
                cache.set(f"guild_roles_{guild_id}", guild_roles)
            role_ids = [role['id'] for role in guild_roles if role['name'] == role_name]
            if any(role_id in roles for role_id in role_ids):
                return await func(ctx, *args, **kwargs)
            else:
                await ctx.bot.event_handler.handle_event({
                    't': 'on_error',
                    'd': {'message': f'Você precisa do papel {role_name} para usar este comando.', 'channel_id': ctx.channel_id}
                })
        return wrapper
    return decorator
    
def rate_limit(limit, per, scope="user"):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(ctx, *args, **kwargs):
            key = f"rate_limit:{scope}:{ctx.guild_id if scope == 'guild' else ctx.channel_id if scope == 'channel' else ctx.author['id']}"
            current = cache.get(key) or 0  # Ajuste aqui
            if current >= limit:
                await ctx.bot.event_handler.handle_event({
                    't': 'on_error',
                    'd': {'message': 'Você atingiu o limite de uso deste comando.', 'time_left': per, 'channel_id': ctx.channel_id}
                })
            else:
                cache.set(key, current + 1, ttl=per)
                return await func(ctx, *args, **kwargs)
        return wrapper
    return decorator
