class DropdownOption:
    def __init__(self, label, value, description=None, emoji=None, default=False):
        self.label = label
        self.value = value
        self.description = description
        self.emoji = emoji
        self.default = default

    def to_dict(self):
        data = {
            "label": self.label,
            "value": self.value,
            "default": self.default
        }
        if self.description:
            data["description"] = self.description
        if self.emoji:
            data["emoji"] = self.emoji
        return data

class Dropdown:
    def __init__(self, custom_id, options, placeholder=None, min_values=1, max_values=1, disabled=False):
        self.custom_id = custom_id
        self.options = options
        self.placeholder = placeholder
        self.min_values = min_values
        self.max_values = max_values
        self.disabled = disabled

    def to_dict(self):
        return {
            "type": 3,
            "custom_id": self.custom_id,
            "options": [option.to_dict() for option in self.options],
            "placeholder": self.placeholder,
            "min_values": self.min_values,
            "max_values": self.max_values,
            "disabled": self.disabled
        }

    @property
    def to_component(self):
        return {"type": 1, "components": [self.to_dict()]}