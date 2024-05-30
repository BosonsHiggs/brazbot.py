class Button:
    def __init__(self, label, style, custom_id, url=None, disabled=False, emoji=None):
        self.label = label
        self.style = style
        self.custom_id = custom_id
        self.url = url
        self.disabled = disabled
        self.emoji = emoji

    def to_dict(self):

        data = {
            "type": 2,
            "label": self.label,
            "style": self.style,
            "custom_id": self.custom_id,
            "disabled": self.disabled
        }

        if self.url:
            data["url"] = self.url
        if self.emoji:
            data["emoji"] = self.emoji
        
        components = [
            {
                "type": 1,
                "components": [
                    data
                ]
            }
        ]
        return components
