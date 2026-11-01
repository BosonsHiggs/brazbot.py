"""
Modal Forms (`Form`, `FormField`) for Discord API v10 (Interaction Callback Type 9).
"""

from typing import Any, Callable, Dict, List, Optional


class FormField:
    """
    Text Input field (`TEXT_INPUT` - Component Type 4) for a Modal (`Form`).
    `style=1` for single-line Short input, `style=2` for multi-line Paragraph input.
    """

    def __init__(
        self,
        label: str,
        placeholder: Optional[str] = None,
        custom_id: str = "field",
        style: int = 1,
        type: str = "SHORT",
        options: Optional[List[Any]] = None,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        required: bool = True,
        value: Optional[str] = None,
    ):
        self.label = str(label)[:45]
        self.placeholder = placeholder
        self.custom_id = str(custom_id)
        self.style = 2 if str(type).upper() == "PARAGRAPH" else int(style)
        self.type = type
        self.options = options
        self.min_length = min_length
        self.max_length = max_length
        self.required = bool(required)
        self.value = value

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "type": 4,
            "label": self.label,
            "custom_id": self.custom_id,
            "style": self.style,
            "required": self.required,
        }
        if self.type == "DROPDOWN" and self.options:
            data["type"] = 3
            data["options"] = self.options
        if self.placeholder is not None:
            data["placeholder"] = str(self.placeholder)[:100]
        if self.min_length is not None:
            data["min_length"] = int(self.min_length)
        if self.max_length is not None:
            data["max_length"] = int(self.max_length)
        if self.value is not None:
            data["value"] = str(self.value)
        return data


class Form:
    """
    Represents an interactive Modal in Discord API v10 (Interaction Callback Type 9).
    """

    def __init__(
        self,
        title: str,
        custom_id: str,
        fields: List[FormField],
        callback: Optional[Callable[..., Any]] = None,
    ):
        self.title = str(title)[:45]
        self.custom_id = str(custom_id)
        self.fields = fields[:5]
        self.callback = callback

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "custom_id": self.custom_id,
            "components": [
                {"type": 1, "components": [field.to_dict()]} for field in self.fields
            ],
        }

    @property
    def to_component(self) -> Dict[str, Any]:
        return {
            "type": 9,
            "data": self.to_dict(),
        }
