"""
Grupos de Subcomandos (`SubCommandGroup`) compatíveis tanto com comandos de prefixo
quanto com a árvore de Application Commands (SUB_COMMAND type=1 e SUB_COMMAND_GROUP type=2) da API v10.
"""

from typing import Any, Callable, Dict, List, Optional


class SubCommandGroup:
    """
    Representa um grupo ou subgrupo de comandos (ex.: `/fun sorrir alto` ou `!fun sorrir alto`).
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
        self.description = description or f"Grupo de comandos {self.group_name}"
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
