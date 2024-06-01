import datetime
import json

class Embed:
    def __init__(self, title=None, description=None, url=None, color=None):
        self.title = title
        self.description = description
        self.url = url
        self.color = color
        self.timestamp = None
        self.footer = {}
        self.image = {}
        self.thumbnail = {}
        self.author = {}
        self.fields = []

    def set_title(self, title):
        self.title = title
        return self

    def set_description(self, description):
        self.description = description
        return self

    def set_url(self, url):
        self.url = url
        return self

    def set_color(self, color):
        self.color = color
        return self

    def set_timestamp(self, timestamp=None):
        if timestamp is None:
            timestamp = datetime.datetime.utcnow()
        self.timestamp = timestamp.isoformat()
        return self

    def set_footer(self, text, icon_url=None):
        self.footer = {"text": text}
        if icon_url:
            self.footer["icon_url"] = icon_url
        return self

    def set_image(self, url):
        self.image = {"url": url}
        return self

    def set_thumbnail(self, url):
        self.thumbnail = {"url": url}
        return self

    def set_author(self, name, url=None, icon_url=None):
        self.author = {"name": name}
        if url:
            self.author["url"] = url
        if icon_url:
            self.author["icon_url"] = icon_url
        return self

    def add_field(self, name, value, inline=True):
        self.fields.append({"name": name, "value": value, "inline": inline})
        return self

    def to_dict(self):
        embed = {}
        if self.title:
            embed["title"] = self.title
        if self.description:
            embed["description"] = self.description
        if self.url:
            embed["url"] = self.url
        if self.color:
            embed["color"] = self.color
        if self.timestamp:
            embed["timestamp"] = self.timestamp
        if self.footer:
            embed["footer"] = self.footer
        if self.image:
            embed["image"] = self.image
        if self.thumbnail:
            embed["thumbnail"] = self.thumbnail
        if self.author:
            embed["author"] = self.author
        if self.fields:
            embed["fields"] = self.fields
        return embed

    def to_json(self):
        return json.dumps(self.to_dict(), indent=4)

