class FormField:
    def __init__(self, label, placeholder, custom_id, style=1, min_length=None, max_length=None, required=True):
        self.label = label
        self.placeholder = placeholder
        self.custom_id = custom_id
        self.style = style
        self.min_length = min_length
        self.max_length = max_length
        self.required = required

    def to_dict(self):
        data = {
            "type": 4,
            "label": self.label,
            "style": self.style,
            "custom_id": self.custom_id,
            "placeholder": self.placeholder,
            "required": self.required
        }
        if self.min_length is not None:
            data["min_length"] = self.min_length
        if self.max_length is not None:
            data["max_length"] = self.max_length
        return data

class Form:
    def __init__(self, title, custom_id, fields):
        self.title = title
        self.custom_id = custom_id
        self.fields = fields

    def to_dict(self):
        return {
            "type": 1,
            "title": self.title,
            "custom_id": self.custom_id,
            "components": [{"type": 1, "components": [field.to_dict() for field in self.fields]}]
        }
