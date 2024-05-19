class SubCommandGroup:
    def __init__(self, bot, group_name, parent_group_name=None):
        self.bot = bot
        self.group_name = group_name
        self.parent_group_name = parent_group_name

    def command(self, name=None, description=None):
        def decorator(func):
            full_command_name = f"{self.parent_group_name} {self.group_name} {name}" if self.parent_group_name else f"{self.group_name} {name}"
            self.bot.command_handler.register_command(func, full_command_name, description)
            return func
        return decorator

    def subgroup(self, name):
        return SubCommandGroup(self.bot, name, f"{self.parent_group_name} {self.group_name}" if self.parent_group_name else self.group_name)
