"""
Full Message, Reaction, Interaction, Modal, Poll, and Webhook Handler for Discord API v10.
"""

import logging
import urllib.parse
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Union

from brazbot.http import BASE_URL, HTTPClient
from brazbot.snowflake import Snowflake

logger = logging.getLogger(__name__)


def _serialize_embed(embed: Any) -> Dict[str, Any]:
    if hasattr(embed, "to_dict"):
        return embed.to_dict()
    if isinstance(embed, dict):
        return embed
    raise TypeError(f"Invalid embed type: {type(embed)}")


def _serialize_components(components: Any) -> List[Dict[str, Any]]:
    if components is None:
        return []
    if hasattr(components, "to_components"):
        return components.to_components()
    if hasattr(components, "to_component"):
        comp = components.to_component
        return [comp() if callable(comp) else comp]
    if isinstance(components, list):
        result: List[Dict[str, Any]] = []
        for item in components:
            if hasattr(item, "to_component"):
                comp = item.to_component
                result.append(comp() if callable(comp) else comp)
            elif hasattr(item, "to_dict"):
                d = item.to_dict()
                if d.get("type") == 1:
                    result.append(d)
                else:
                    result.append({"type": 1, "components": [d]})
            elif isinstance(item, dict):
                if item.get("type") == 1:
                    result.append(item)
                else:
                    result.append({"type": 1, "components": [item]})
        return result
    return []


class MessageHandler:
    """
    Central handler for messages, interaction callbacks, follow-ups, reactions, and webhooks in Discord API v10.
    """

    def __init__(self, token: str, http_client: Optional[HTTPClient] = None):
        self.token = token
        self.base_url = BASE_URL
        self.headers = {
            "Authorization": f"Bot {self.token}",
            "Content-Type": "application/json",
        }
        self.http = http_client or HTTPClient(token)

    def _build_message_payload(
        self,
        content: Optional[str] = None,
        embed: Any = None,
        embeds: Optional[List[Any]] = None,
        components: Optional[Any] = None,
        ephemeral: bool = False,
        poll: Any = None,
        tts: bool = False,
        allowed_mentions: Optional[Dict[str, Any]] = None,
        message_reference: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        data: Dict[str, Any] = {}
        if content is not None:
            data["content"] = str(content)
        embed_list: List[Dict[str, Any]] = []
        if embed is not None:
            embed_list.append(_serialize_embed(embed))
        if embeds:
            embed_list.extend(_serialize_embed(e) for e in embeds)
        if embed_list:
            data["embeds"] = embed_list
        if components is not None:
            serialized_comps = _serialize_components(components)
            if serialized_comps:
                data["components"] = serialized_comps
        if poll is not None:
            data["poll"] = poll.to_dict() if hasattr(poll, "to_dict") else poll
        if tts:
            data["tts"] = True
        if allowed_mentions is not None:
            data["allowed_mentions"] = allowed_mentions
        if message_reference is not None:
            data["message_reference"] = message_reference
        if ephemeral:
            data["flags"] = 64
        return data

    async def send_message(
        self,
        channel_id: Union[str, int],
        content: Optional[str] = None,
        embed: Any = None,
        embeds: Optional[List[Any]] = None,
        files: Optional[List[Any]] = None,
        components: Optional[Any] = None,
        ephemeral: bool = False,
        poll: Any = None,
        tts: bool = False,
        reply_to: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Sends a message to a text, voice, or thread channel."""
        ref = {"message_id": str(reply_to)} if reply_to else None
        payload = self._build_message_payload(
            content=content,
            embed=embed,
            embeds=embeds,
            components=components,
            ephemeral=ephemeral,
            poll=poll,
            tts=tts,
            message_reference=ref,
        )
        return await self.http.request(
            "POST",
            f"/channels/{channel_id}/messages",
            json_data=payload,
            files=files,
            raise_on_error=False,
        )

    async def send_embed(
        self,
        channel_id: Union[str, int],
        embed: Any,
        content: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Sends an embed to a channel (compatible with examples/simple_example.py)."""
        return await self.send_message(channel_id, content=content, embed=embed)

    async def send_file(
        self,
        channel_id: Union[str, int],
        file_path: str,
        content: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Uploads a local file from disk to a channel."""
        return await self.send_message(channel_id, content=content, files=[file_path])

    async def send_image(
        self,
        channel_id: Union[str, int],
        image_url: str,
        content: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Sends an image embedded via URL."""
        return await self.send_message(
            channel_id, content=content, embed={"image": {"url": image_url}}
        )

    async def edit_message(
        self,
        channel_id: Union[str, int],
        message_id: Union[str, int],
        content: Optional[str] = None,
        embed: Any = None,
        embeds: Optional[List[Any]] = None,
        files: Optional[List[Any]] = None,
        components: Optional[Any] = None,
    ) -> Optional[Dict[str, Any]]:
        """Edits an existing message."""
        payload = self._build_message_payload(
            content=content, embed=embed, embeds=embeds, components=components
        )
        return await self.http.request(
            "PATCH",
            f"/channels/{channel_id}/messages/{message_id}",
            json_data=payload,
            files=files,
            raise_on_error=False,
        )

    async def send_interaction(
        self,
        interaction: Dict[str, Any],
        content: Optional[str] = None,
        embed: Any = None,
        embeds: Optional[List[Any]] = None,
        files: Optional[List[Any]] = None,
        components: Optional[Any] = None,
        ephemeral: bool = False,
        poll: Any = None,
        response_type: int = 4,
    ) -> Any:
        """
        Responds directly to an Interaction (`POST /interactions/{id}/{token}/callback`).
        If the interaction has already been deferred (`_deferred`), automatically routes to
        `send_followup_message` to prevent Discord error 40060 (Interaction has already been acknowledged).
        """
        if interaction.get("_deferred"):
            app_id = interaction.get("application_id")
            if app_id:
                return await self.send_followup_message(
                    app_id,
                    interaction["token"],
                    content=content,
                    embed=embed,
                    embeds=embeds,
                    files=files,
                    components=components,
                    ephemeral=ephemeral,
                    poll=poll,
                )

        inner_data = self._build_message_payload(
            content=content,
            embed=embed,
            embeds=embeds,
            components=components,
            ephemeral=ephemeral,
            poll=poll,
        )
        payload = {"type": response_type, "data": inner_data}
        interaction["_responded"] = True
        return await self.http.request(
            "POST",
            f"/interactions/{interaction['id']}/{interaction['token']}/callback",
            json_data=payload,
            files=files,
            auth=False,
            raise_on_error=False,
        )

    async def send_followup_message(
        self,
        application_id: Union[str, int],
        interaction_token: str,
        content: Optional[str] = None,
        embed: Any = None,
        embeds: Optional[List[Any]] = None,
        files: Optional[List[Any]] = None,
        components: Optional[Any] = None,
        ephemeral: bool = False,
        poll: Any = None,
    ) -> Optional[Dict[str, Any]]:
        """Sends a follow-up message after `ctx.defer()`."""
        payload = self._build_message_payload(
            content=content,
            embed=embed,
            embeds=embeds,
            components=components,
            ephemeral=ephemeral,
            poll=poll,
        )
        return await self.http.request(
            "POST",
            f"/webhooks/{application_id}/{interaction_token}",
            json_data=payload,
            files=files,
            auth=False,
            raise_on_error=False,
        )

    async def edit_interaction_response(
        self,
        application_id: Union[str, int],
        interaction_token: str,
        content: Optional[str] = None,
        embed: Any = None,
        embeds: Optional[List[Any]] = None,
        files: Optional[List[Any]] = None,
        components: Optional[Any] = None,
        message_id: str = "@original",
    ) -> Optional[Dict[str, Any]]:
        """Edits the original (or follow-up) response of an interaction."""
        payload = self._build_message_payload(
            content=content, embed=embed, embeds=embeds, components=components
        )
        return await self.http.request(
            "PATCH",
            f"/webhooks/{application_id}/{interaction_token}/messages/{message_id}",
            json_data=payload,
            files=files,
            auth=False,
            raise_on_error=False,
        )

    async def delete_interaction_response(
        self,
        application_id: Union[str, int],
        interaction_token: str,
        message_id: str = "@original",
    ) -> bool:
        """Deletes the original (or follow-up) response of an interaction."""
        res = await self.http.request(
            "DELETE",
            f"/webhooks/{application_id}/{interaction_token}/messages/{message_id}",
            auth=False,
            raise_on_error=False,
        )
        return bool(res)

    async def send_modal(
        self,
        interaction: Dict[str, Any],
        title: str,
        custom_id: str,
        data: Any,
    ) -> Any:
        """Sends a Modal form response (Interaction Callback Type 9)."""
        if isinstance(data, dict) and data.get("type") == 9:
            payload = data
        elif hasattr(data, "to_component"):
            comp = data.to_component
            payload = comp() if callable(comp) else comp
        else:
            payload = {
                "type": 9,
                "data": {
                    "title": title,
                    "custom_id": custom_id,
                    "components": data if isinstance(data, list) else [],
                },
            }
        interaction["_responded"] = True
        return await self.http.request(
            "POST",
            f"/interactions/{interaction['id']}/{interaction['token']}/callback",
            json_data=payload,
            auth=False,
            raise_on_error=False,
        )

    async def delete_message(
        self,
        channel_id: Union[str, int],
        message_id: Union[str, int],
        reason: Optional[str] = None,
    ) -> bool:
        res = await self.http.request(
            "DELETE",
            f"/channels/{channel_id}/messages/{message_id}",
            reason=reason,
            raise_on_error=False,
        )
        return bool(res)

    async def add_reaction(
        self, channel_id: Union[str, int], message_id: Union[str, int], emoji: str
    ) -> bool:
        encoded_emoji = urllib.parse.quote(emoji.strip("<>"))
        res = await self.http.request(
            "PUT",
            f"/channels/{channel_id}/messages/{message_id}/reactions/{encoded_emoji}/@me",
            raise_on_error=False,
        )
        return bool(res)

    async def remove_reaction(
        self,
        channel_id: Union[str, int],
        message_id: Union[str, int],
        emoji: str,
        user_id: str = "@me",
    ) -> bool:
        encoded_emoji = urllib.parse.quote(emoji.strip("<>"))
        res = await self.http.request(
            "DELETE",
            f"/channels/{channel_id}/messages/{message_id}/reactions/{encoded_emoji}/{user_id}",
            raise_on_error=False,
        )
        return bool(res)

    async def clear_reactions(
        self, channel_id: Union[str, int], message_id: Union[str, int]
    ) -> bool:
        res = await self.http.request(
            "DELETE",
            f"/channels/{channel_id}/messages/{message_id}/reactions",
            raise_on_error=False,
        )
        return bool(res)

    async def bulk_delete_messages(
        self,
        channel_id: Union[str, int],
        message_ids: List[str],
        reason: Optional[str] = None,
    ) -> bool:
        """
        Deletes between 2 and 100 messages in a single API call (`POST /channels/{id}/messages/bulk-delete`).
        Automatically filters out messages older than 14 days and falls back to single delete if 1 ID is passed.
        """
        cutoff = Snowflake.from_datetime(datetime.now(timezone.utc) - timedelta(days=14, seconds=-30))
        clean_ids = [
            str(m).strip()
            for m in message_ids
            if str(m).strip() and Snowflake.is_valid(str(m).strip()) and Snowflake.parse(str(m).strip()) > cutoff
        ]
        # Deduplicate while preserving order
        clean_ids = list(dict.fromkeys(clean_ids))
        if not clean_ids:
            return False
        if len(clean_ids) == 1:
            return await self.delete_message(channel_id, clean_ids[0], reason=reason)
        res = await self.http.request(
            "POST",
            f"/channels/{channel_id}/messages/bulk-delete",
            json_data={"messages": clean_ids[:100]},
            reason=reason,
            raise_on_error=False,
        )
        return bool(res)

    async def pin_message(
        self,
        channel_id: Union[str, int],
        message_id: Union[str, int],
        reason: Optional[str] = None,
    ) -> bool:
        res = await self.http.request(
            "PUT",
            f"/channels/{channel_id}/pins/{message_id}",
            reason=reason,
            raise_on_error=False,
        )
        return bool(res)

    async def unpin_message(
        self,
        channel_id: Union[str, int],
        message_id: Union[str, int],
        reason: Optional[str] = None,
    ) -> bool:
        res = await self.http.request(
            "DELETE",
            f"/channels/{channel_id}/pins/{message_id}",
            reason=reason,
            raise_on_error=False,
        )
        return bool(res)

    async def create_webhook(
        self,
        channel_id: Union[str, int],
        name: str,
        avatar: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        payload: Dict[str, Any] = {"name": name}
        if avatar:
            payload["avatar"] = avatar
        return await self.http.request(
            "POST",
            f"/channels/{channel_id}/webhooks",
            json_data=payload,
            reason=reason,
            raise_on_error=False,
        )

    async def send_webhook_message(
        self,
        webhook_url: str,
        content: Optional[str] = None,
        username: Optional[str] = None,
        avatar_url: Optional[str] = None,
        embeds: Optional[List[Any]] = None,
        wait: bool = True,
    ) -> Any:
        payload: Dict[str, Any] = {}
        if content is not None:
            payload["content"] = str(content)
        if username:
            payload["username"] = username
        if avatar_url:
            payload["avatar_url"] = avatar_url
        if embeds:
            payload["embeds"] = [_serialize_embed(e) for e in embeds]
        sep = "&" if "?" in webhook_url else "?"
        target_url = f"{webhook_url}{sep}wait={'true' if wait else 'false'}"
        return await self.http.request(
            "POST",
            "",
            full_url=target_url,
            json_data=payload,
            auth=False,
            raise_on_error=False,
        )
