"""
Subcommand Groups (`SubCommandGroup`) compatible with both prefix commands
and Discord API v10 Application Command trees (SUB_COMMAND type=1 and SUB_COMMAND_GROUP type=2).
"""

from typing import Any, Callable, Dict, Optional


class SubCommandGroup:
    """
    Represents a command group or subgroup (e.g., `/fun smile loud` or `!fun smile loud`).
    """

    def __init__(
        self,
        bot: Any,
        group_name: str,
        parent_group_name: Optional[str] = None,
        description: Optional[str] = None,
    ):
        self.bot = bot
        self.group_name = group_name.strip().lower()
        self.parent_group_name = (
            parent_group_name.strip().lower() if parent_group_name else None
        )
        self.description = description or f"Command group {self.group_name}"
        self.subcommands: Dict[str, Callable[..., Any]] = {}
        self.subgroups: Dict[str, "SubCommandGroup"] = {}

    def command(
        self, name: Optional[str] = None, description: Optional[str] = None
    ) -> Callable[..., Any]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            sub_name = (name or func.__name__).strip().lower()
            full_command_name = (
                f"{self.parent_group_name} {self.group_name} {sub_name}"
                if self.parent_group_name
                else f"{self.group_name} {sub_name}"
            )
            self.subcommands[sub_name] = func
            self.bot.command_handler.register_command(
                func,
                full_command_name,
                description,
                group_path=full_command_name.split(),
            )
            return func

        return decorator

    def subgroup(
        self, name: str, description: Optional[str] = None
    ) -> "SubCommandGroup":
        parent = (
            f"{self.parent_group_name} {self.group_name}"
            if self.parent_group_name
            else self.group_name
        )
        sub = SubCommandGroup(
            self.bot, name, parent_group_name=parent, description=description
        )
        self.subgroups[name.strip().lower()] = sub
        return sub
