import aiohttp
from datetime import datetime
from brazbot.member import Member

class Guild:
	def __init__(self, data, bot=None):
		self.bot = bot
		self.id = data.get('id')
		self.name = data.get('name')
		self.icon = data.get('icon')
		self.splash = data.get('splash')
		self.discovery_splash = data.get('discovery_splash')
		self.owner_id = data.get('owner_id')
		self.owner = data.get('owner')
		self.permissions = data.get('permissions')
		self.region = data.get('region')
		self.afk_channel = data.get('afk_channel')
		self.afk_timeout = data.get('afk_timeout')
		self.widget_enabled = data.get('widget_enabled')
		self.widget_channel = data.get('widget_channel')
		self.verification_level = data.get('verification_level')
		self.default_notifications = data.get('default_notifications')
		self.explicit_content_filter = data.get('explicit_content_filter')
		self.roles = data.get('roles', [])
		self.emojis = data.get('emojis', [])
		self.features = data.get('features', [])
		self.mfa_level = data.get('mfa_level')
		self.application_id = data.get('application_id')
		self.system_channel = data.get('system_channel')
		self.system_channel_flags = data.get('system_channel_flags')
		self.rules_channel = data.get('rules_channel')
		self.max_presences = data.get('max_presences')
		self.max_members = data.get('max_members')
		self.vanity_url_code = data.get('vanity_url_code')
		self.description = data.get('description')
		self.banner = data.get('banner')
		self.premium_tier = data.get('premium_tier')
		self.premium_subscription_count = data.get('premium_subscription_count')
		self.preferred_locale = data.get('preferred_locale')
		self.public_updates_channel = data.get('public_updates_channel')
		self.max_video_channel_users = data.get('max_video_channel_users')
		self.approximate_member_count = data.get('approximate_member_count')
		self.approximate_presence_count = data.get('approximate_presence_count')
		self.welcome_screen = data.get('welcome_screen')
		self.nsfw_level = data.get('nsfw_level')
		self.premium_progress_bar_enabled = data.get('premium_progress_bar_enabled')
		self.large = data.get('large')
		self.member_count = data.get('member_count')
		self.members = data.get('members', [])
		self.channels = data.get('channels', [])
		self.threads = data.get('threads', [])
		self.stage_channels = data.get('stage_channels', [])
		self.voice_channels = data.get('voice_channels', [])
		self.categories = data.get('categories', [])
		self.shard_id = data.get('shard_id')
		self.unavailable = data.get('unavailable')
		self.invites_paused_until = data.get('invites_paused_until')
		self.dms_paused_until = data.get('dms_paused_until')
		self.filesize_limit = data.get('filesize_limit')
		self.emoji_limit = data.get('emoji_limit')
		self.sticker_limit = data.get('sticker_limit')
		self.stage_instances = data.get('stage_instances', [])
		self.scheduled_events = data.get('scheduled_events', [])
		self.default_role = data.get('default_role')
		self.self_role = data.get('self_role')
		self.public_updates_channel_id = data.get('public_updates_channel_id')
		self.created_at = datetime.fromtimestamp(((int(self.id) >> 22) + 1420070400000) / 1000)

	@classmethod
	async def from_guild_id(cls, bot, guild_id):
		url = f"https://discord.com/api/v10/guilds/{guild_id}"
		headers = {
			"Authorization": f"Bot {bot.token}"
		}

		async with aiohttp.ClientSession() as session:
			async with session.get(url, headers=headers) as response:
				if response.status == 200:
					data = await response.json()
					return cls(data, bot)
				else:
					raise Exception(f"Failed to fetch guild data: {response.status}")

	def __str__(self):
		return self.name

	# Method to count roles using lambda and yield
	def roles_count(self):
		count = lambda: (yield from (role for role in self.roles))
		return sum(1 for _ in count())

	# Method to fetch all members with pagination and concurrency
	async def fetch_all_members(self):
		members = []
		limit = 1000
		after = None
		try:
			async def fetch_page(after):
				params = {'limit': limit}
				if after:
					params['after'] = after

				url = f"https://discord.com/api/v10/guilds/{self.id}/members"
				headers = {
					"Authorization": f"Bot {self.bot.token}"
				}

				async with aiohttp.ClientSession() as session:
					async with session.get(url, headers=headers, params=params) as response:
						if response.status == 429:
							retry_after = int(response.headers.get('Retry-After', 1))
							await asyncio.sleep(retry_after)
							return await fetch_page(after)
						elif response.status != 200:
							raise Exception(f"Failed to fetch members: {response.status}")
						
						data = await response.json()
						return data

			while True:
				data = await fetch_page(after)
				if not data:
					break

				for member_data in data:
					member = Member(member_data, self.bot)
					members.append(member)

				after = data[-1]['user']['id']
				if len(data) < limit:
					break

				# Sleep to respect rate limits
				await asyncio.sleep(1)
		except Exception as e:
			print(e)

		return members


	# Methods to interact with the Discord API
	async def active_threads(self):
		url = f"https://discord.com/api/v10/guilds/{self.id}/threads/active"
		headers = {
			"Authorization": f"Bot {self.bot.token}"
		}
		async with aiohttp.ClientSession() as session:
			async with session.get(url, headers=headers) as response:
				if response.status == 200:
					return await response.json()
				else:
					raise Exception(f"Failed to fetch active threads: {response.status}")

	async def audit_logs(self):
		url = f"https://discord.com/api/v10/guilds/{self.id}/audit-logs"
		headers = {
			"Authorization": f"Bot {self.bot.token}"
		}
		async with aiohttp.ClientSession() as session:
			async with session.get(url, headers=headers) as response:
				if response.status == 200:
					return await response.json()
				else:
					raise Exception(f"Failed to fetch audit logs: {response.status}")

	async def ban(self, user_id, delete_message_days=0, reason=None):
		url = f"https://discord.com/api/v10/guilds/{self.id}/bans/{user_id}"
		headers = {
			"Authorization": f"Bot {self.bot.token}",
			"Content-Type": "application/json"
		}
		json_data = {
			"delete_message_days": delete_message_days,
			"reason": reason
		}
		async with aiohttp.ClientSession() as session:
			async with session.put(url, headers=headers, json=json_data) as response:
				if response.status != 204:
					raise Exception(f"Failed to ban user {user_id}: {response.status}")

	async def bans(self):
		url = f"https://discord.com/api/v10/guilds/{self.id}/bans"
		headers = {
			"Authorization": f"Bot {self.bot.token}"
		}
		async with aiohttp.ClientSession() as session:
			async with session.get(url, headers=headers) as response:
				if response.status == 200:
					return await response.json()
				else:
					raise Exception(f"Failed to fetch bans: {response.status}")

	async def bulk_ban(self, user_ids, delete_message_days=0, reason=None):
		for user_id in user_ids:
			await self.ban(user_id, delete_message_days, reason)

	async def by_category(self):
		url = f"https://discord.com/api/v10/guilds/{self.id}/channels"
		headers = {
			"Authorization": f"Bot {self.bot.token}"
		}
		async with aiohttp.ClientSession() as session:
			async with session.get(url, headers=headers) as response:
				if response.status == 200:
					channels = await response.json()
					categories = {}
					for channel in channels:
						category_id = channel.get('parent_id')
						if category_id not in categories:
							categories[category_id] = []
						categories[category_id].append(channel)
					return categories
				else:
					raise Exception(f"Failed to fetch channels by category: {response.status}")

	async def change_voice_state(self, channel_id, self_mute=False, self_deaf=False):
		url = f"https://discord.com/api/v10/guilds/{self.id}/voice-states/@me"
		headers = {
			"Authorization": f"Bot {self.bot.token}",
			"Content-Type": "application/json"
		}
		json_data = {
			"channel_id": channel_id,
			"self_mute": self_mute,
			"self_deaf": self_deaf
		}
		async with aiohttp.ClientSession() as session:
			async with session.patch(url, headers=headers, json=json_data) as response:
				if response.status != 204:
					raise Exception(f"Failed to change voice state: {response.status}")

	async def chunk(self):
		url = f"https://discord.com/api/v10/guilds/{self.id}/members?limit=1000"
		headers = {
			"Authorization": f"Bot {self.bot.token}"
		}
		async with aiohttp.ClientSession() as session:
			async with session.get(url, headers=headers) as response:
				if response.status == 200:
					return await response.json()
				else:
					raise Exception(f"Failed to chunk members: {response.status}")

	async def create_automod_rule(self, data):
		url = f"https://discord.com/api/v10/guilds/{self.id}/auto-moderation/rules"
		headers = {
			"Authorization": f"Bot {self.bot.token}",
			"Content-Type": "application/json"
		}
		async with aiohttp.ClientSession() as session:
			async with session.post(url, headers=headers, json=data) as response:
				if response.status != 201:
					raise Exception(f"Failed to create automod rule: {response.status}")

	async def create_category(self, name, reason=None):
		return await self.create_channel(name, 4, reason=reason)

	async def create_channel(self, name, type, reason=None):
		url = f"https://discord.com/api/v10/guilds/{self.id}/channels"
		headers = {
			"Authorization": f"Bot {self.bot.token}",
			"Content-Type": "application/json"
		}
		json_data = {
			"name": name,
			"type": type,
			"reason": reason
		}
		async with aiohttp.ClientSession() as session:
			async with session.post(url, headers=headers, json=json_data) as response:
				if response.status == 201:
					return await response.json()
				else:
					raise Exception(f"Failed to create channel: {response.status}")

	async def create_custom_emoji(self, name, image, roles=None, reason=None):
		url = f"https://discord.com/api/v10/guilds/{self.id}/emojis"
		headers = {
			"Authorization": f"Bot {self.bot.token}",
			"Content-Type": "application/json"
		}
		json_data = {
			"name": name,
			"image": image,
			"roles": roles,
			"reason": reason
		}
		async with aiohttp.ClientSession() as session:
			async with session.post(url, headers=headers, json=json_data) as response:
				if response.status == 201:
					return await response.json()
				else:
					raise Exception(f"Failed to create custom emoji: {response.status}")

	async def create_forum(self, name, reason=None):
		return await self.create_channel(name, 15, reason=reason)

	async def create_integration(self, type, id):
		url = f"https://discord.com/api/v10/guilds/{self.id}/integrations"
		headers = {
			"Authorization": f"Bot {self.bot.token}",
			"Content-Type": "application/json"
		}
		json_data = {
			"type": type,
			"id": id
		}
		async with aiohttp.ClientSession() as session:
			async with session.post(url, headers=headers, json=json_data) as response:
				if response.status != 204:
					raise Exception(f"Failed to create integration: {response.status}")

	async def create_role(self, data):
		url = f"https://discord.com/api/v10/guilds/{self.id}/roles"
		headers = {
			"Authorization": f"Bot {self.bot.token}",
			"Content-Type": "application/json"
		}
		async with aiohttp.ClientSession() as session:
			async with session.post(url, headers=headers, json=data) as response:
				if response.status == 201:
					return await response.json()
				else:
					raise Exception(f"Failed to create role: {response.status}")

	async def create_scheduled_event(self, data):
		url = f"https://discord.com/api/v10/guilds/{self.id}/scheduled-events"
		headers = {
			"Authorization": f"Bot {self.bot.token}",
			"Content-Type": "application/json"
		}
		async with aiohttp.ClientSession() as session:
			async with session.post(url, headers=headers, json=data) as response:
				if response.status == 201:
					return await response.json()
				else:
					raise Exception(f"Failed to create scheduled event: {response.status}")

	async def create_stage_channel(self, name, reason=None):
		return await self.create_channel(name, 13, reason=reason)

	async def create_sticker(self, data):
		url = f"https://discord.com/api/v10/guilds/{self.id}/stickers"
		headers = {
			"Authorization": f"Bot {self.bot.token}",
			"Content-Type": "application/json"
		}
		async with aiohttp.ClientSession() as session:
			async with session.post(url, headers=headers, json=data) as response:
				if response.status == 201:
					return await response.json()
				else:
					raise Exception(f"Failed to create sticker: {response.status}")

	async def create_template(self, data):
		url = f"https://discord.com/api/v10/guilds/{self.id}/templates"
		headers = {
			"Authorization": f"Bot {self.bot.token}",
			"Content-Type": "application/json"
		}
		async with aiohttp.ClientSession() as session:
			async with session.post(url, headers=headers, json=data) as response:
				if response.status == 201:
					return await response.json()
				else:
					raise Exception(f"Failed to create template: {response.status}")

	async def create_text_channel(self, name, reason=None):
		return await self.create_channel(name, 0, reason=reason)

	async def create_voice_channel(self, name, reason=None):
		return await self.create_channel(name, 2, reason=reason)

	async def delete(self, reason=None):
		url = f"https://discord.com/api/v10/guilds/{self.id}"
		headers = {
			"Authorization": f"Bot {self.bot.token}"
		}
		async with aiohttp.ClientSession() as session:
			async with session.delete(url, headers=headers) as response:
				if response.status != 204:
					raise Exception(f"Failed to delete guild: {response.status}")

	async def delete_emoji(self, emoji_id, reason=None):
		url = f"https://discord.com/api/v10/guilds/{self.id}/emojis/{emoji_id}"
		headers = {
			"Authorization": f"Bot {self.bot.token}"
		}
		async with aiohttp.ClientSession() as session:
			async with session.delete(url, headers=headers) as response:
				if response.status != 204:
					raise Exception(f"Failed to delete emoji: {response.status}")

	async def delete_sticker(self, sticker_id, reason=None):
		url = f"https://discord.com/api/v10/guilds/{self.id}/stickers/{sticker_id}"
		headers = {
			"Authorization": f"Bot {self.bot.token}"
		}
		async with aiohttp.ClientSession() as session:
			async with session.delete(url, headers=headers) as response:
				if response.status != 204:
					raise Exception(f"Failed to delete sticker: {response.status}")

	def dms_paused(self):
		return self.dms_paused_until is not None

	async def edit(self, **fields):
		url = f"https://discord.com/api/v10/guilds/{self.id}"
		headers = {
			"Authorization": f"Bot {self.bot.token}",
			"Content-Type": "application/json"
		}
		async with aiohttp.ClientSession() as session:
			async with session.patch(url, headers=headers, json=fields) as response:
				if response.status != 200:
					raise Exception(f"Failed to edit guild: {response.status}")

	async def edit_role_positions(self, roles):
		url = f"https://discord.com/api/v10/guilds/{self.id}/roles"
		headers = {
			"Authorization": f"Bot {self.bot.token}",
			"Content-Type": "application/json"
		}
		async with aiohttp.ClientSession() as session:
			async with session.patch(url, headers=headers, json=roles) as response:
				if response.status != 200:
					raise Exception(f"Failed to edit role positions: {response.status}")

	async def edit_welcome_screen(self, data):
		url = f"https://discord.com/api/v10/guilds/{self.id}/welcome-screen"
		headers = {
			"Authorization": f"Bot {self.bot.token}",
			"Content-Type": "application/json"
		}
		async with aiohttp.ClientSession() as session:
			async with session.patch(url, headers=headers, json=data) as response:
				if response.status != 200:
					raise Exception(f"Failed to edit welcome screen: {response.status}")

	async def edit_widget(self, data):
		url = f"https://discord.com/api/v10/guilds/{self.id}/widget"
		headers = {
			"Authorization": f"Bot {self.bot.token}",
			"Content-Type": "application/json"
		}
		async with aiohttp.ClientSession() as session:
			async with session.patch(url, headers=headers, json=data) as response:
				if response.status != 200:
					raise Exception(f"Failed to edit widget: {response.status}")

	async def estimate_pruned_members(self, days):
		url = f"https://discord.com/api/v10/guilds/{self.id}/prune"
		headers = {
			"Authorization": f"Bot {self.bot.token}"
		}
		async with aiohttp.ClientSession() as session:
			async with session.get(url, headers=headers, params={'days': days}) as response:
				if response.status == 200:
					return await response.json()
				else:
					raise Exception(f"Failed to estimate pruned members: {response.status}")

	async def fetch_automod_rule(self, rule_id):
		url = f"https://discord.com/api/v10/guilds/{self.id}/auto-moderation/rules/{rule_id}"
		headers = {
			"Authorization": f"Bot {self.bot.token}"
		}
		async with aiohttp.ClientSession() as session:
			async with session.get(url, headers=headers) as response:
				if response.status == 200:
					return await response.json()
				else:
					raise Exception(f"Failed to fetch automod rule: {response.status}")

	async def fetch_automod_rules(self):
		url = f"https://discord.com/api/v10/guilds/{self.id}/auto-moderation/rules"
		headers = {
			"Authorization": f"Bot {self.bot.token}"
		}
		async with aiohttp.ClientSession() as session:
			async with session.get(url, headers=headers) as response:
				if response.status == 200:
					return await response.json()
				else:
					raise Exception(f"Failed to fetch automod rules: {response.status}")

	async def fetch_ban(self, user_id):
		url = f"https://discord.com/api/v10/guilds/{self.id}/bans/{user_id}"
		headers = {
			"Authorization": f"Bot {self.bot.token}"
		}
		async with aiohttp.ClientSession() as session:
			async with session.get(url, headers=headers) as response:
				if response.status == 200:
					return await response.json()
				else:
					raise Exception(f"Failed to fetch ban: {response.status}")

	async def fetch_channel(self, channel_id):
		url = f"https://discord.com/api/v10/channels/{channel_id}"
		headers = {
			"Authorization": f"Bot {self.bot.token}"
		}
		async with aiohttp.ClientSession() as session:
			async with session.get(url, headers=headers) as response:
				if response.status == 200:
					return await response.json()
				else:
					raise Exception(f"Failed to fetch channel: {response.status}")

	async def fetch_channels(self):
		url = f"https://discord.com/api/v10/guilds/{self.id}/channels"
		headers = {
			"Authorization": f"Bot {self.bot.token}"
		}
		async with aiohttp.ClientSession() as session:
			async with session.get(url, headers=headers) as response:
				if response.status == 200:
					return await response.json()
				else:
					raise Exception(f"Failed to fetch channels: {response.status}")

	async def fetch_emoji(self, emoji_id):
		url = f"https://discord.com/api/v10/guilds/{self.id}/emojis/{emoji_id}"
		headers = {
			"Authorization": f"Bot {self.bot.token}"
		}
		async with aiohttp.ClientSession() as session:
			async with session.get(url, headers=headers) as response:
				if response.status == 200:
					return await response.json()
				else:
					raise Exception(f"Failed to fetch emoji: {response.status}")

	async def fetch_emojis(self):
		url = f"https://discord.com/api/v10/guilds/{self.id}/emojis"
		headers = {
			"Authorization": f"Bot {self.bot.token}"
		}
		async with aiohttp.ClientSession() as session:
			async with session.get(url, headers=headers) as response:
				if response.status == 200:
					return await response.json()
				else:
					raise Exception(f"Failed to fetch emojis: {response.status}")

	async def fetch_member(self, user_id):
		url = f"https://discord.com/api/v10/guilds/{self.id}/members/{user_id}"
		headers = {
			"Authorization": f"Bot {self.bot.token}"
		}
		async with aiohttp.ClientSession() as session:
			async with session.get(url, headers=headers) as response:
				if response.status == 200:
					return await response.json()
				else:
					raise Exception(f"Failed to fetch member: {response.status}")

	async def fetch_members(self):
		url = f"https://discord.com/api/v10/guilds/{self.id}/members"
		headers = {
			"Authorization": f"Bot {self.bot.token}"
		}
		async with aiohttp.ClientSession() as session:
			async with session.get(url, headers=headers) as response:
				if response.status == 200:
					return await response.json()
				else:
					raise Exception(f"Failed to fetch members: {response.status}")

	async def fetch_roles(self):
		url = f"https://discord.com/api/v10/guilds/{self.id}/roles"
		headers = {
			"Authorization": f"Bot {self.bot.token}"
		}
		async with aiohttp.ClientSession() as session:
			async with session.get(url, headers=headers) as response:
				if response.status == 200:
					return await response.json()
				else:
					raise Exception(f"Failed to fetch roles: {response.status}")

	async def fetch_scheduled_event(self, event_id):
		url = f"https://discord.com/api/v10/guilds/{self.id}/scheduled-events/{event_id}"
		headers = {
			"Authorization": f"Bot {self.bot.token}"
		}
		async with aiohttp.ClientSession() as session:
			async with session.get(url, headers=headers) as response:
				if response.status == 200:
					return await response.json()
				else:
					raise Exception(f"Failed to fetch scheduled event: {response.status}")

	async def fetch_scheduled_events(self):
		url = f"https://discord.com/api/v10/guilds/{self.id}/scheduled-events"
		headers = {
			"Authorization": f"Bot {self.bot.token}"
		}
		async with aiohttp.ClientSession() as session:
			async with session.get(url, headers=headers) as response:
				if response.status == 200:
					return await response.json()
				else:
					raise Exception(f"Failed to fetch scheduled events: {response.status}")

	async def fetch_sticker(self, sticker_id):
		url = f"https://discord.com/api/v10/guilds/{self.id}/stickers/{sticker_id}"
		headers = {
			"Authorization": f"Bot {self.bot.token}"
		}
		async with aiohttp.ClientSession() as session:
			async with session.get(url, headers=headers) as response:
				if response.status == 200:
					return await response.json()
				else:
					raise Exception(f"Failed to fetch sticker: {response.status}")

	async def fetch_stickers(self):
		url = f"https://discord.com/api/v10/guilds/{self.id}/stickers"
		headers = {
			"Authorization": f"Bot {self.bot.token}"
		}
		async with aiohttp.ClientSession() as session:
			async with session.get(url, headers=headers) as response:
				if response.status == 200:
					return await response.json()
				else:
					raise Exception(f"Failed to fetch stickers: {response.status}")

	def get_channel(self, channel_id):
		return next((channel for channel in self.channels if channel['id'] == channel_id), None)

	def get_channel_or_thread(self, channel_id):
		for collection in [self.channels, self.threads]:
			for item in collection:
				if item['id'] == channel_id:
					return item
		return None

	def get_emoji(self, emoji_id):
		return next((emoji for emoji in self.emojis if emoji['id'] == emoji_id), None)

	def get_member(self, user_id):
		return next((member for member in self.members if member['id'] == user_id), None)

	def get_member_named(self, name):
		return next((member for member in self.members if member['username'] == name), None)

	def get_role(self, role_id):
		return next((role for role in self.roles if role['id'] == role_id), None)

	def get_scheduled_event(self, event_id):
		return next((event for event in self.scheduled_events if event['id'] == event_id), None)

	def get_stage_instance(self, stage_id):
		return next((instance for instance in self.stage_instances if instance['id'] == stage_id), None)

	def get_thread(self, thread_id):
		return next((thread for thread in self.threads if thread['id'] == thread_id), None)

	async def integrations(self):
		url = f"https://discord.com/api/v10/guilds/{self.id}/integrations"
		headers = {
			"Authorization": f"Bot {self.bot.token}"
		}
		async with aiohttp.ClientSession() as session:
			async with session.get(url, headers=headers) as response:
				if response.status == 200:
					return await response.json()
				else:
					raise Exception(f"Failed to fetch integrations: {response.status}")

	async def invites(self):
		url = f"https://discord.com/api/v10/guilds/{self.id}/invites"
		headers = {
			"Authorization": f"Bot {self.bot.token}"
		}
		async with aiohttp.ClientSession() as session:
			async with session.get(url, headers=headers) as response:
				if response.status == 200:
					return await response.json()
				else:
					raise Exception(f"Failed to fetch invites: {response.status}")

	def invites_paused(self):
		return self.invites_paused_until is not None

	async def kick(self, user_id, reason=None):
		url = f"https://discord.com/api/v10/guilds/{self.id}/members/{user_id}"
		headers = {
			"Authorization": f"Bot {self.bot.token}"
		}
		async with aiohttp.ClientSession() as session:
			async with session.delete(url, headers=headers) as response:
				if response.status != 204:
					raise Exception(f"Failed to kick member {user_id}: {response.status}")

	async def leave(self):
		url = f"https://discord.com/api/v10/users/@me/guilds/{self.id}"
		headers = {
			"Authorization": f"Bot {self.bot.token}"
		}
		async with aiohttp.ClientSession() as session:
			async with session.delete(url, headers=headers) as response:
				if response.status != 204:
					raise Exception(f"Failed to leave guild: {response.status}")

	async def prune_members(self, days, reason=None):
		url = f"https://discord.com/api/v10/guilds/{self.id}/prune"
		headers = {
			"Authorization": f"Bot {self.bot.token}",
			"Content-Type": "application/json"
		}
		json_data = {
			"days": days,
			"reason": reason
		}
		async with aiohttp.ClientSession() as session:
			async with session.post(url, headers=headers, json=json_data) as response:
				if response.status != 204:
					raise Exception(f"Failed to prune members: {response.status}")

	async def query_members(self, query, limit=10):
		url = f"https://discord.com/api/v10/guilds/{self.id}/members/search"
		headers = {
			"Authorization": f"Bot {self.bot.token}",
			"Content-Type": "application/json"
		}
		params = {
			"query": query,
			"limit": limit
		}
		async with aiohttp.ClientSession() as session:
			async with session.get(url, headers=headers, params=params) as response:
				if response.status == 200:
					return await response.json()
				else:
					raise Exception(f"Failed to query members: {response.status}")

	async def templates(self):
		url = f"https://discord.com/api/v10/guilds/{self.id}/templates"
		headers = {
			"Authorization": f"Bot {self.bot.token}"
		}
		async with aiohttp.ClientSession() as session:
			async with session.get(url, headers=headers) as response:
				if response.status == 200:
					return await response.json()
				else:
					raise Exception(f"Failed to fetch templates: {response.status}")

	async def unban(self, user_id, reason=None):
		url = f"https://discord.com/api/v10/guilds/{self.id}/bans/{user_id}"
		headers = {
			"Authorization": f"Bot {self.bot.token}"
		}
		async with aiohttp.ClientSession() as session:
			async with session.delete(url, headers=headers) as response:
				if response.status != 204:
					raise Exception(f"Failed to unban user {user_id}: {response.status}")

	async def vanity_invite(self):
		url = f"https://discord.com/api/v10/guilds/{self.id}/vanity-url"
		headers = {
			"Authorization": f"Bot {self.bot.token}"
		}
		async with aiohttp.ClientSession() as session:
			async with session.get(url, headers=headers) as response:
				if response.status == 200:
					return await response.json()
				else:
					raise Exception(f"Failed to fetch vanity invite: {response.status}")

	async def webhooks(self):
		url = f"https://discord.com/api/v10/guilds/{self.id}/webhooks"
		headers = {
			"Authorization": f"Bot {self.bot.token}"
		}
		async with aiohttp.ClientSession() as session:
			async with session.get(url, headers=headers) as response:
				if response.status == 200:
					return await response.json()
				else:
					raise Exception(f"Failed to fetch webhooks: {response.status}")

	async def welcome_screen(self):
		url = f"https://discord.com/api/v10/guilds/{self.id}/welcome-screen"
		headers = {
			"Authorization": f"Bot {self.bot.token}"
		}
		async with aiohttp.ClientSession() as session:
			async with session.get(url, headers=headers) as response:
				if response.status == 200:
					return await response.json()
				else:
					raise Exception(f"Failed to fetch welcome screen: {response.status}")

	async def widget(self):
		url = f"https://discord.com/api/v10/guilds/{self.id}/widget.json"
		headers = {
			"Authorization": f"Bot {self.bot.token}"
		}
		async with aiohttp.ClientSession() as session:
			async with session.get(url, headers=headers) as response:
				if response.status == 200:
					return await response.json()
				else:
					raise Exception(f"Failed to fetch widget: {response.status}")
