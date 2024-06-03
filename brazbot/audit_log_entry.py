import aiohttp
from datetime import datetime

class AuditLogEntry:
    def __init__(self, *, users, integrations, app_commands, automod_rules, webhooks, data, guild, bot):

        self.action = data.get('action_type') if data.get('action_type') else -10000
        self.after = data.get('changes', {})[0].get('after') if type(data.get('changes', {})) == list else {}
        self.before = data.get('changes', {})[0].get('before')  if type(data.get('changes', {})) == list else {}
        self.category = data.get('target_type')
        self.changes = data.get('changes')
        self.created_at = datetime.fromtimestamp(((int(data['id']) >> 22) + 1420070400000) / 1000)
        self.extra = data.get('options')
        self.guild = guild
        self.id = data.get('id')
        self.reason = data.get('reason')
        self.target = data.get('target_id')
        self.user = users.get(data.get('user_id'))
        self.user_id = data.get('user_id')
        self.bot = bot

    @classmethod
    async def from_guild_id(cls, bot, guild_id):
        cache_key = f"audit_log_{guild_id}"
        data = bot.get_cache_data(cache_key)

        if data:
            users = {user['id']: user for user in data['users']}
            return [
                        cls(
                            users=users,
                            integrations=data.get('integrations', {}),
                            app_commands=data.get('application_commands', {}),
                            automod_rules=data.get('auto_moderation_rules', {}),
                            webhooks=data.get('webhooks', {}),
                            data=entry,
                            guild=guild_id,
                            bot=bot
                        ) for entry in data['audit_log_entries']
                    ]

        url = f"https://discord.com/api/v10/guilds/{guild_id}/audit-logs"
        headers = {
            "Authorization": f"Bot {bot.token}"
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    bot.set_cache_data(cache_key, data, seconds=10)
                    users = {user['id']: user for user in data['users']}  # Convert list to dictionary
                    return [
                        cls(
                            users=users,
                            integrations=data.get('integrations', {}),
                            app_commands=data.get('application_commands', {}),
                            automod_rules=data.get('auto_moderation_rules', {}),
                            webhooks=data.get('webhooks', {}),
                            data=entry,
                            guild=guild_id,
                            bot=bot
                        ) for entry in data['audit_log_entries']
                    ]
                else:
                    raise Exception(f"Failed to fetch audit log data: {response.status}")

    def __str__(self):
        return f"AuditLogEntry(action={self.action}, user={self.user}, target={self.target})"
