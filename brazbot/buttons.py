"""
Componentes de Botão (`Button`, `ButtonStyle`, `ActionRow`, `View`) da API v10 do Discord.
"""

from enum import IntEnum
from typing import Any, Callable, Dict, List, Optional, Union


class ButtonStyle(IntEnum):
    """Estilos oficiais de botões da API v10 do Discord."""

    PRIMARY = 1
    BLURPLE = 1
    SECONDARY = 2
    GREY = 2
    SUCCESS = 3
    GREEN = 3
    DANGER = 4
    RED = 4
    LINK = 5
    PREMIUM = 6


class Button:
    """
    Representa um componente de Botão (Component Type 2) da API v10 do Discord.
    """

    Style = ButtonStyle

    def __init__(
        self,
        label: Optional[str] = None,
        style: int = ButtonStyle.PRIMARY,
        custom_id: Optional[str] = None,
        url: Optional[str] = None,
        disabled: bool = False,
        emoji: Optional[Union[str, Dict[str, Any]]] = None,
        sku_id: Optional[str] = None,
        callback: Optional[Callable[..., Any]] = None,
    ):
        self.label = label
        self.style = int(style)
        self.custom_id = custom_id
        self.url = url
        self.disabled = bool(disabled)
        self.sku_id = sku_id
        self.callback = callback
        if isinstance(emoji, str):
            self.emoji: Optional[Dict[str, Any]] = {"name": emoji}
        else:
            self.emoji = emoji

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "type": 2,
            "style": self.style,
            "disabled": self.disabled,
        }
        if self.label is not None:
            data["label"] = str(self.label)
        if self.style == ButtonStyle.LINK and self.url:
            data["url"] = self.url
        elif self.style == ButtonStyle.PREMIUM and self.sku_id:
            data["sku_id"] = str(self.sku_id)
        elif self.custom_id:
            data["custom_id"] = str(self.custom_id)
        if self.emoji:
            data["emoji"] = self.emoji
        return data

    @property
    def to_component(self) -> Dict[str, Any]:
        return {"type": 1, "components": [self.to_dict()]}


class ActionRow:
    """Agrupa até 5 botões ou 1 menu de seleção em uma linha (Component Type 1)."""

    def __init__(self, *components: Any):
        self.components = list(components)

    def add_component(self, component: Any) -> "ActionRow":
        self.components.append(component)
        return self

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": 1,
            "components": [
                c.to_dict() if hasattr(c, "to_dict") else c for c in self.components
            ],
        }

    @property
    def to_component(self) -> Dict[str, Any]:
        return self.to_dict()


class View:
    """
    Contêiner de múltiplos componentes interativos (Botões e Dropdowns) com suporte
    a callbacks automáticos registrados no bot.
    """

    def __init__(self, bot: Any = None, timeout: Optional[float] = 180.0):
        self.bot = bot
        self.timeout = timeout
        self.items: List[Any] = []

    def add_item(self, item: Any) -> "View":
        self.items.append(item)
        if self.bot and getattr(item, "custom_id", None) and getattr(item, "callback", None):
            self.bot.register_component_callback(item.custom_id, item.callback)
        return self

    def to_components(self) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        current_buttons: List[Dict[str, Any]] = []

        for item in self.items:
            if isinstance(item, ActionRow):
                if current_buttons:
                    rows.append({"type": 1, "components": current_buttons})
                    current_buttons = []
                rows.append(item.to_dict())
            else:
                d = item.to_dict() if hasattr(item, "to_dict") else item
                if d.get("type") == 2:
                    current_buttons.append(d)
                    if len(current_buttons) == 5:
                        rows.append({"type": 1, "components": current_buttons})
                        current_buttons = []
                else:
                    if current_buttons:
                        rows.append({"type": 1, "components": current_buttons})
                        current_buttons = []
                    rows.append({"type": 1, "components": [d]})

        if current_buttons:
            rows.append({"type": 1, "components": current_buttons})
        return rows[:5]
