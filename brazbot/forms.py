class FormField:
    def __init__(self, label, placeholder, custom_id, style=1, type="SHORT", options=None, min_length=None, max_length=None, required=True):
        self.label = label
        self.placeholder = placeholder
        self.custom_id = custom_id
        self.style = style
        self.type = type
        self.options = options
        self.min_length = min_length
        self.max_length = max_length
        self.required = required

    def to_dict(self):
        data = {
            "label": self.label,
            "custom_id": self.custom_id,
            "style": self.style,
            "placeholder": self.placeholder,
            "required": self.required,
            "type": 4  # Default type for Text Input
        }
        if self.type == "DROPDOWN":
            data["type"] = 3  # Type for Select Menu
            data["options"] = self.options
        if self.min_length is not None:
            data["min_length"] = self.min_length
        if self.max_length is not None:
            data["max_length"] = self.max_length
        if self.placeholder is not None:
            data["placeholder"] = self.placeholder
        return data

class Form:
    def __init__(self, title, custom_id, fields):
        self.title = title
        self.custom_id = custom_id
        self.fields = fields

    def to_dict(self):
        return {
            "type": 1,  # Main Modal type
            "title": self.title,
            "custom_id": self.custom_id,
            "components": [
                {"type": 1, "components": [field.to_dict()]} for field in self.fields
            ]
        }

    @property
    def to_component(self):

        return {
            'type': 9, 
            'data': self.to_dict()
        }
