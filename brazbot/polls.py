"""
Suporte nativo a Enquetes (Polls) da API v10 do Discord.
"""

from typing import Any, Dict, List, Optional, Union


class PollMedia:
    """Objeto de mídia (texto e emoji opcional) para pergunta ou resposta de Enquete."""

    def __init__(
        self,
        text: str,
        emoji: Optional[Union[str, Dict[str, Any]]] = None,
    ):
        self.text = str(text)[:300]
        if isinstance(emoji, str):
            self.emoji: Optional[Dict[str, Any]] = {"name": emoji}
        else:
            self.emoji = emoji

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {"text": self.text}
        if self.emoji:
            data["emoji"] = self.emoji
        return data


class PollAnswer:
    """Opção de resposta individual para uma Enquete (`Poll`)."""

    def __init__(
        self,
        text: str,
        emoji: Optional[Union[str, Dict[str, Any]]] = None,
        answer_id: Optional[int] = None,
    ):
        self.answer_id = answer_id
        self.poll_media = PollMedia(text=text, emoji=emoji)

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {"poll_media": self.poll_media.to_dict()}
        if self.answer_id is not None:
            data["answer_id"] = int(self.answer_id)
        return data


class Poll:
    """
    Construtor de Enquetes nativas da API v10 do Discord.
    Pode ser passado em `ctx.send(..., poll=poll)` ou `channel.send(..., poll=poll)`.
    """

    def __init__(
        self,
        question: str,
        answers: Optional[List[Union[str, PollAnswer]]] = None,
        duration_hours: int = 24,
        allow_multiselect: bool = False,
        layout_type: int = 1,
    ):
        self.question = PollMedia(question)
        self.duration = max(1, min(768, int(duration_hours)))  # Até 32 dias (768h)
        self.allow_multiselect = bool(allow_multiselect)
        self.layout_type = int(layout_type)
        self.answers: List[PollAnswer] = []
        if answers:
            for item in answers:
                if isinstance(item, PollAnswer):
                    self.answers.append(item)
                else:
                    self.answers.append(PollAnswer(str(item)))

    def add_answer(
        self,
        text: str,
        emoji: Optional[Union[str, Dict[str, Any]]] = None,
    ) -> "Poll":
        self.answers.append(PollAnswer(text=text, emoji=emoji))
        return self

    def to_dict(self) -> Dict[str, Any]:
        return {
            "question": self.question.to_dict(),
            "answers": [a.to_dict() for a in self.answers[:10]],
            "duration": self.duration,
            "allow_multiselect": self.allow_multiselect,
            "layout_type": self.layout_type,
        }

    @staticmethod
    async def end_poll(bot: Any, channel_id: str, message_id: str) -> Dict[str, Any]:
        """Encerra imediatamente uma enquete ativa (`POST /channels/{channel.id}/polls/{message.id}/expire`)."""
        return await bot.http.request(
            "POST", f"/channels/{channel_id}/polls/{message_id}/expire"
        )

    @staticmethod
    async def get_answer_voters(
        bot: Any,
        channel_id: str,
        message_id: str,
        answer_id: int,
        limit: int = 25,
        after: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Lista os usuários que votaram em uma resposta específica da enquete."""
        params: Dict[str, Any] = {"limit": min(100, max(1, limit))}
        if after:
            params["after"] = after
        return await bot.http.request(
            "GET",
            f"/channels/{channel_id}/polls/{message_id}/answers/{answer_id}",
            params=params,
        )
