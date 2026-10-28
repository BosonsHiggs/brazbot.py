"""
Menus de Seleção (Select Menus / Dropdowns) da API v10 do Discord:
- `Dropdown` / `StringSelect` (Type 3)
- `UserSelect` (Type 5)
- `RoleSelect` (Type 6)
- `MentionableSelect` (Type 7)
- `ChannelSelect` (Type 8)
"""

from typing import Any, Callable, Dict, List, Optional, Union


class DropdownOption:
    """Opção individual para um `Dropdown` / `StringSelect` (Type 3)."""

    def __init__(
        self,
        label: str,
        value: str,
        description: Optional[str] = None,
        emoji: Optional[Union[str, Dict[str, Any]]] = None,
        default: bool = False,
    ):
        self.label = str(label)
        self.value = str(value)
        self.description = description
        if isinstance(emoji, str):
            self.emoji: Optional[Dict[str, Any]] = {"name": emoji}
        else:
            self.emoji = emoji
        self.default = bool(default)

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "label": self.label,
            "value": self.value,
            "default": self.default,
        }
        if self.description:
            data["description"] = str(self.description)
        if self.emoji:
            data["emoji"] = self.emoji
        return data


class Dropdown:
    """
    Menu de seleção de texto (`STRING_SELECT` - Component Type 3) da API v10 do Discord.
    """

    def __init__(
        self,
        custom_id: str,
        options: Optional[List[DropdownOption]] = None,
        placeholder: Optional[str] = None,
        min_values: int = 1,
        max_values: int = 1,
        disabled: bool = False,
        select_type: int = 3,
        channel_types: Optional[List[int]] = None,
        callback: Optional[Callable[..., Any]] = None,
    ):
        self.custom_id = str(custom_id)
        self.options = options or []
        self.placeholder = placeholder
        self.min_values = int(min_values)
        self.max_values = int(max_values)
        self.disabled = bool(disabled)
        self.select_type = int(select_type)
        self.channel_types = channel_types
        self.callback = callback

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "type": self.select_type,
            "custom_id": self.custom_id,
            "min_values": self.min_values,
            "max_values": self.max_values,
            "disabled": self.disabled,
        }
        if self.select_type == 3:
            data["options"] = [
                opt.to_dict() if hasattr(opt, "to_dict") else opt for opt in self.options
            ]
        if self.placeholder:
            data["placeholder"] = str(self.placeholder)
        if self.channel_types and self.select_type == 8:
            data["channel_types"] = self.channel_types
        return data

    @property
    def to_component(self) -> Dict[str, Any]:
        return {"type": 1, "components": [self.to_dict()]}


class UserSelect(Dropdown):
    """Menu de seleção de Usuários (`USER_SELECT` - Component Type 5)."""

    def __init__(self, custom_id: str, placeholder: Optional[str] = None, **kwargs: Any):
        super().__init__(custom_id, placeholder=placeholder, select_type=5, **kwargs)


class RoleSelect(Dropdown):
    """Menu de seleção de Cargos (`ROLE_SELECT` - Component Type 6)."""

    def __init__(self, custom_id: str, placeholder: Optional[str] = None, **kwargs: Any):
        super().__init__(custom_id, placeholder=placeholder, select_type=6, **kwargs)


class MentionableSelect(Dropdown):
    """Menu de seleção de Usuários e Cargos (`MENTIONABLE_SELECT` - Component Type 7)."""

    def __init__(self, custom_id: str, placeholder: Optional[str] = None, **kwargs: Any):
        super().__init__(custom_id, placeholder=placeholder, select_type=7, **kwargs)


class ChannelSelect(Dropdown):
    """Menu de seleção de Canais (`CHANNEL_SELECT` - Component Type 8)."""

    def __init__(
        self,
        custom_id: str,
        placeholder: Optional[str] = None,
        channel_types: Optional[List[int]] = None,
        **kwargs: Any,
    ):
        super().__init__(
            custom_id,
            placeholder=placeholder,
            select_type=8,
            channel_types=channel_types,
            **kwargs,
        )
