"""
Motor de Comandos Híbridos (Prefixo + Slash Commands + Context Menus + Autocomplete) da brazbot.py.
"""

import inspect
import logging
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple, Union, get_args, get_origin

from brazbot.attachments import Attachment
from brazbot.channels import Channel, ForumChannel, StageChannel, TextChannel, VoiceChannel
from brazbot.guilds import Guild
from brazbot.greedy_union import Greedy
from brazbot.member import Member, VoiceState
from brazbot.roles import Role
from brazbot.snowflake import Snowflake
from brazbot.threads import Thread

logger = logging.getLogger(__name__)


class CommandContext:
    """
    Contexto unificado de execução de comando (funciona de forma idêntica para comandos
    de Prefixo `!cmd`, Slash Commands `/cmd` e Context Menus).
    """

    def __init__(
        self,
        bot: Any,
        message: Dict[str, Any],
        interaction: Optional[Dict[str, Any]] = None,
    ):
        self.bot = bot
        self.message = message or {}
        self.interaction = interaction
        self.deferred: bool = False
        self.responded: bool = False

        self.channel_id: Optional[str] = str(
            self.message.get("channel_id")
            or (interaction.get("channel_id") if interaction else "")
            or ""
        ) or None
        self.guild_id: Optional[str] = str(
            self.message.get("guild_id")
            or (interaction.get("guild_id") if interaction else "")
            or ""
        ) or None
        self.content: str = self.message.get("content", "")

        # Constrói objetos Member ricos (com `.voice` e suporte a `ctx.author['id']`)
        raw_member = (
            (interaction.get("member") if interaction else None)
            or self.message.get("member")
            or {}
        )
        raw_user = (
            self.message.get("author")
            or (raw_member.get("user") if isinstance(raw_member, dict) else None)
            or (interaction.get("user") if interaction else None)
            or {}
        )

        merged_member_data: Dict[str, Any] = {}
        if isinstance(raw_member, dict):
            merged_member_data.update(raw_member)
        if isinstance(raw_user, dict):
            merged_member_data["user"] = raw_user
            for k, v in raw_user.items():
                merged_member_data.setdefault(k, v)

        user_id = str(raw_user.get("id") or merged_member_data.get("id") or "")
        voice_state: Optional[VoiceState] = None
        if self.guild_id and user_id and hasattr(bot, "get_member_voice_state"):
            voice_state = bot.get_member_voice_state(self.guild_id, user_id)

        if merged_member_data:
            self.author: Optional[Member] = Member(
                merged_member_data,
                bot=bot,
                guild_id=self.guild_id,
                voice_state=voice_state,
            )
            self.member: Optional[Member] = self.author
        else:
            self.author = None
            self.member = None

        # Extração de opções de Slash Command (incluindo subcomandos)
        self.options: Dict[str, Any] = {}
        if interaction and "data" in interaction:
            self._extract_options(interaction["data"].get("options", []))

    def _extract_options(self, options_list: List[Dict[str, Any]]) -> None:
        for opt in options_list:
            if opt.get("type") in (1, 2):  # SUB_COMMAND ou SUB_COMMAND_GROUP
                self._extract_options(opt.get("options", []))
            elif "name" in opt and "value" in opt:
                self.options[opt["name"]] = opt["value"]

    @property
    def voice_client(self) -> Any:
        """Retorna o `VoiceClient` ativo do bot neste servidor, se houver."""
        if self.guild_id and hasattr(self.bot, "voice_clients"):
            return self.bot.voice_clients.get(self.guild_id)
        return None

    async def defer(self, ephemeral: bool = False) -> None:
        """
        Adia a resposta da interação (Type 5 DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE).
        Em comandos de prefixo, aciona o indicador 'digitando...' no canal.
        """
        self.deferred = True
        if self.interaction:
            self.interaction["_deferred"] = True
            payload: Dict[str, Any] = {"type": 5}
            if ephemeral:
                payload["data"] = {"flags": 64}
            await self.bot.http.request(
                "POST",
                f"/interactions/{self.interaction['id']}/{self.interaction['token']}/callback",
                json_data=payload,
                auth=False,
                raise_on_error=False,
            )
        elif self.channel_id:
            await self.bot.http.request(
                "POST", f"/channels/{self.channel_id}/typing", raise_on_error=False
            )

    async def send_modal(self, title: str, custom_id: str, data: Any) -> Any:
        """Abre um formulário Modal em resposta à interação."""
        if not self.interaction:
            raise RuntimeError("Modals can only be sent in response to an interaction.")
        self.responded = True
        return await self.bot.message_handler.send_modal(
            self.interaction, title, custom_id, data
        )

    async def send_followup_message(
        self,
        content: Optional[str] = None,
        embed: Any = None,
        embeds: Optional[List[Any]] = None,
        files: Optional[List[Any]] = None,
        components: Optional[Any] = None,
        ephemeral: bool = False,
        poll: Any = None,
    ) -> Any:
        """
        Envia uma mensagem de acompanhamento (follow-up) após `ctx.defer()`.
        Se o comando foi chamado via prefixo (`!cmd`), envia normalmente para o canal.
        """
        self.responded = True
        if self.interaction:
            if not self.deferred and not self.interaction.get("_deferred") and not self.interaction.get("_responded"):
                return await self.bot.message_handler.send_interaction(
                    self.interaction,
                    content=content,
                    embed=embed,
                    embeds=embeds,
                    files=files,
                    components=components,
                    ephemeral=ephemeral,
                    poll=poll,
                )
            return await self.bot.message_handler.send_followup_message(
                self.bot.application_id,
                self.interaction["token"],
                content=content,
                embed=embed,
                embeds=embeds,
                files=files,
                components=components,
                ephemeral=ephemeral,
                poll=poll,
            )
        if self.channel_id:
            return await self.bot.message_handler.send_message(
                self.channel_id,
                content=content,
                embed=embed,
                embeds=embeds,
                files=files,
                components=components,
                ephemeral=ephemeral,
                poll=poll,
            )
        return None

    async def send(
        self,
        content: Optional[str] = None,
        *,
        embed: Any = None,
        embeds: Optional[List[Any]] = None,
        files: Optional[List[Any]] = None,
        components: Optional[Any] = None,
        ephemeral: bool = False,
        poll: Any = None,
    ) -> Any:
        """
        Método universal de resposta: funciona automaticamente em Slash Commands (com ou sem defer)
        e em comandos de prefixo.
        """
        return await self.send_followup_message(
            content=content,
            embed=embed,
            embeds=embeds,
            files=files,
            components=components,
            ephemeral=ephemeral,
            poll=poll,
        )

    async def reply(
        self,
        content: Optional[str] = None,
        *,
        embed: Any = None,
        embeds: Optional[List[Any]] = None,
        files: Optional[List[Any]] = None,
        components: Optional[Any] = None,
        ephemeral: bool = False,
        poll: Any = None,
    ) -> Any:
        """Responde ao comando (alias semântico para `ctx.send`)."""
        if not self.interaction and self.channel_id and self.message.get("id"):
            return await self.bot.message_handler.send_message(
                self.channel_id,
                content=content,
                embed=embed,
                embeds=embeds,
                files=files,
                components=components,
                ephemeral=ephemeral,
                poll=poll,
                reply_to=self.message["id"],
            )
        return await self.send(
            content=content,
            embed=embed,
            embeds=embeds,
            files=files,
            components=components,
            ephemeral=ephemeral,
            poll=poll,
        )

    async def edit_original_response(
        self,
        content: Optional[str] = None,
        *,
        embed: Any = None,
        embeds: Optional[List[Any]] = None,
        components: Optional[Any] = None,
    ) -> Any:
        if not self.interaction:
            return None
        return await self.bot.message_handler.edit_interaction_response(
            self.bot.application_id,
            self.interaction["token"],
            content=content,
            embed=embed,
            embeds=embeds,
            components=components,
        )

    async def get_channel(self, id: Optional[str] = None) -> Channel:
        """Busca o objeto `Channel` do contexto atual ou pelo ID informado."""
        target_id = str(id if id is not None else self.channel_id)
        return await Channel.from_channel_id(self.bot, self.guild_id, target_id)

    async def get_guild(self) -> Optional[Guild]:
        if not self.guild_id:
            return None
        return await Guild.from_guild_id(self.bot, self.guild_id)


class CommandHandler:
    """
    Registra, sincroniza e despacha comandos de Prefixo, Slash Commands (`CHAT_INPUT`),
    Context Menus (`USER` / `MESSAGE`) e Autocomplete na API v10 do Discord.
    """

    def __init__(self, bot: Any):
        self.bot = bot
        self.commands: Dict[str, Dict[str, Any]] = {}
        self.aliases: Dict[str, str] = {}
        self.autocomplete_functions: Dict[ tuple, Callable[..., Any] ] = {}

    def _infer_option_schema(
        self, func: Callable[..., Any]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        options: List[Dict[str, Any]] = []
        param_types: Dict[str, Any] = {}
        sig = inspect.signature(func)
        annotations = getattr(func, "__annotations__", {})

        params = list(sig.parameters.values())
        # Ignora `self` (se método de Cog) e `ctx` (primeiro parâmetro de contexto)
        start_idx = 0
        if params and params[0].name == "self":
            start_idx = 1
        if len(params) > start_idx and params[start_idx].name in ("ctx", "context", "interaction"):
            start_idx += 1

        for param_obj in params[start_idx:]:
            if param_obj.kind in (param_obj.VAR_POSITIONAL, param_obj.VAR_KEYWORD):
                continue
            param_name = param_obj.name
            if param_name == "return":
                continue

            param = annotations.get(param_name, str)
            has_default = param_obj.default is not inspect.Parameter.empty
            option: Dict[str, Any] = {
                "name": param_name,
                "required": not has_default,
                "type": 3,  # Default STRING
            }
            param_types[param_name] = param

            origin = get_origin(param)
            args = get_args(param)

            # Desempacota Optional[T] / Union[T, None]
            if origin is Union and type(None) in args:
                option["required"] = False
                non_none = [a for a in args if a is not type(None)]
                if len(non_none) == 1:
                    param = non_none[0]
                    origin = get_origin(param)
                    args = get_args(param)
                    param_types[param_name] = param

            if param is str:
                option["type"] = 3
                if hasattr(func, "autocomplete_options") and param_name in func.autocomplete_options:
                    option["autocomplete"] = True
            elif param is int:
                option["type"] = 4
            elif param is bool:
                option["type"] = 5
            elif param is float:
                option["type"] = 10
            elif param is bytes or param is Attachment:
                option["type"] = 11
            elif isinstance(param, type) and issubclass(param, Member):
                option["type"] = 6
            elif isinstance(param, type) and issubclass(param, Role):
                option["type"] = 8
            elif isinstance(param, type) and issubclass(param, Guild):
                option["type"] = 3  # Guild ID ou resolvido do contexto
                option["required"] = False
            elif isinstance(param, type) and issubclass(param, Thread):
                option["type"] = 7
                option["channel_types"] = [10, 11, 12]
            elif isinstance(param, type) and issubclass(param, Channel):
                option["type"] = 7
                if issubclass(param, StageChannel):
                    option["channel_types"] = [13]
                elif issubclass(param, VoiceChannel):
                    option["channel_types"] = [2, 13]
                elif issubclass(param, ForumChannel):
                    option["channel_types"] = [15]
                elif issubclass(param, TextChannel):
                    option["channel_types"] = [0, 5]
            elif param is dict and "channel" in param_name:
                option["type"] = 7
            elif origin is Literal:
                option["type"] = 3
                option["choices"] = [{"name": str(v), "value": str(v)} for v in args[:25]]
            elif origin is Greedy:
                option["type"] = 3
                option["required"] = False
            elif origin is Union:
                if str in args:
                    option["type"] = 3
                elif int in args:
                    option["type"] = 4
                elif float in args:
                    option["type"] = 10

            if hasattr(func, "parameter_descriptions") and param_name in func.parameter_descriptions:
                option["description"] = str(func.parameter_descriptions[param_name])[:100]
            else:
                option["description"] = f"Parâmetro {param_name}"[:100]

            options.append(option)

        # Discord exige que opções required=True venham antes das required=False
        options.sort(key=lambda o: not o.get("required", False))
        return options, param_types

    def register_command(
        self,
        func: Callable[..., Any],
        name: Optional[str] = None,
        description: Optional[str] = None,
        aliases: Optional[List[str]] = None,
        cmd_type: int = 1,
        group_path: Optional[List[str]] = None,
    ) -> None:
        raw_name = (name or func.__name__).strip()
        cmd_name = raw_name.lower() if cmd_type == 1 else raw_name
        desc = (description or func.__doc__ or "No description provided").strip().split("\n")[0][:100]
        if cmd_type != 1:
            desc = ""

        options, param_types = self._infer_option_schema(func) if cmd_type == 1 else ([], {})

        self.commands[cmd_name] = {
            "func": func,
            "name": cmd_name,
            "description": desc,
            "options": options,
            "param_types": param_types,
            "type": cmd_type,
            "aliases": [a.lower() for a in (aliases or [])],
            "group_path": group_path,
        }

        for alias in aliases or []:
            self.aliases[alias.lower()] = cmd_name

        logger.debug(f"Comando registrado: '{cmd_name}' (type={cmd_type}, options={len(options)})")

    def register_autocomplete(
        self,
        func: Callable[..., Any],
        command_name: str,
        option_name: Optional[str] = None,
    ) -> None:
        if option_name is None:
            # Chamado via autocomplete_command
            option_name = command_name
            for cname, cdata in self.commands.items():
                for opt in cdata["options"]:
                    if opt["name"] == option_name:
                        opt["autocomplete"] = True
                        self.autocomplete_functions[(cname, option_name)] = func
            return

        if command_name not in self.commands:
            raise ValueError(f"Command '{command_name}' not found")
        for option in self.commands[command_name]["options"]:
            if option["name"] == option_name:
                option["autocomplete"] = True
                self.autocomplete_functions[(command_name, option_name)] = func
                return
        raise ValueError(f"Option '{option_name}' not found in command '{command_name}'")

    async def send_autocomplete_response(
        self, interaction: Dict[str, Any], suggestions: List[Dict[str, Any]]
    ) -> Any:
        response_data = {
            "type": 8,
            "data": {"choices": suggestions[:25]},
        }
        return await self.bot.http.request(
            "POST",
            f"/interactions/{interaction['id']}/{interaction['token']}/callback",
            json_data=response_data,
            auth=False,
            raise_on_error=False,
        )

    async def handle_autocomplete(self, interaction: Dict[str, Any]) -> None:
        command_name = interaction["data"]["name"]
        options = interaction["data"].get("options", [])
        focused_option = next((opt for opt in options if opt.get("focused")), None)
        if focused_option:
            option_name = focused_option["name"]
            handler = self.autocomplete_functions.get((command_name, option_name))
            if handler:
                await handler(interaction)
            else:
                logger.warning(
                    f"Nenhuma função de autocomplete registrada para ({command_name}, {option_name})"
                )

    async def _resolve_slash_arguments(
        self,
        cmd_meta: Dict[str, Any],
        ctx: CommandContext,
        options: List[Dict[str, Any]],
        resolved_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        args: Dict[str, Any] = {}
        param_types = cmd_meta.get("param_types", {})
        user_id = ctx.author.id if ctx.author else None

        for opt in options:
            if opt.get("type") in (1, 2):
                sub_args = await self._resolve_slash_arguments(
                    cmd_meta, ctx, opt.get("options", []), resolved_data
                )
                args.update(sub_args)
                continue

            opt_name = opt["name"]
            opt_type = opt["type"]
            opt_val = opt.get("value")
            expected_type = param_types.get(opt_name)
            origin = get_origin(expected_type)

            if origin is Greedy:
                raw_parts = str(opt_val).replace(",", " ").split()
                inner_args = get_args(expected_type)
                conv_list: List[Any] = []
                for p in raw_parts:
                    try:
                        conv_list.append(int(p) if "." not in p else float(p))
                    except ValueError:
                        conv_list.append(p)
                args[opt_name] = Greedy(conv_list)
            elif opt_type == 6:  # USER
                args[opt_name] = await Member.from_user_id(self.bot, str(opt_val), ctx.guild_id)
            elif opt_type == 8:  # ROLE
                args[opt_name] = await Role.from_role_id(self.bot, ctx.guild_id, str(opt_val))  # type: ignore[arg-type]
            elif opt_type == 7:  # CHANNEL / THREAD
                if isinstance(expected_type, type) and issubclass(expected_type, Thread):
                    args[opt_name] = await Thread.from_thread_id(self.bot, ctx.guild_id, str(opt_val))
                elif isinstance(expected_type, type) and issubclass(expected_type, VoiceChannel):
                    args[opt_name] = await VoiceChannel.from_channel_id(
                        self.bot, ctx.guild_id, str(opt_val), user_id
                    )
                elif isinstance(expected_type, type) and issubclass(expected_type, TextChannel):
                    args[opt_name] = await TextChannel.from_channel_id(
                        self.bot, ctx.guild_id, str(opt_val), user_id
                    )
                else:
                    args[opt_name] = await Channel.from_channel_id(
                        self.bot, ctx.guild_id, str(opt_val), user_id
                    )
            elif opt_type == 11:  # ATTACHMENT
                att_dict = (resolved_data.get("attachments") or {}).get(str(opt_val))
                if att_dict:
                    att_obj = Attachment(att_dict)
                    if expected_type is bytes:
                        args[opt_name] = await att_obj.read()
                    else:
                        args[opt_name] = att_obj
                else:
                    args[opt_name] = opt_val
            elif isinstance(expected_type, type) and issubclass(expected_type, Guild):
                target_gid = str(opt_val or ctx.guild_id)
                args[opt_name] = await Guild.from_guild_id(self.bot, target_gid)
            else:
                args[opt_name] = opt_val

        # Se o comando espera `guild: Guild` e o usuário não precisou informar como opção:
        for p_name, p_type in param_types.items():
            if p_name not in args and isinstance(p_type, type) and issubclass(p_type, Guild) and ctx.guild_id:
                args[p_name] = await Guild.from_guild_id(self.bot, ctx.guild_id)

        return args

    async def handle_command(self, message: Dict[str, Any]) -> None:
        d = message.get("d", message)

        # 1. Comandos por Prefixo (MESSAGE_CREATE)
        if "content" in d and "type" not in d.get("data", {}):
            # Ignora mensagens de bots
            if d.get("author", {}).get("bot"):
                return
            content = d.get("content", "")
            prefix = self.bot.command_prefix
            if prefix and content.startswith(prefix):
                without_prefix = content[len(prefix) :].strip()
                if not without_prefix:
                    return
                parts = without_prefix.split()

                # Verifica correspondência com subcomandos (3, 2 ou 1 palavras)
                matched_cmd = None
                cmd_args: List[str] = []
                for length in (3, 2, 1):
                    if len(parts) >= length:
                        candidate = " ".join(parts[:length]).lower()
                        resolved_name = self.aliases.get(candidate, candidate)
                        if resolved_name in self.commands:
                            matched_cmd = self.commands[resolved_name]
                            cmd_args = parts[length:]
                            break

                if matched_cmd:
                    ctx = CommandContext(self.bot, d)
                    await matched_cmd["func"](ctx, *cmd_args)
            return

        # 2. Application Commands (INTERACTION_CREATE type=2)
        if d.get("type") == 2:
            data = d.get("data", {})
            command_name = data.get("name", "")
            options = data.get("options", [])
            resolved_data = data.get("resolved", {})

            # Verifica se é um subcomando na árvore Slash
            lookup_path = [command_name.lower()]
            curr_opts = options
            while curr_opts and curr_opts[0].get("type") in (1, 2):
                lookup_path.append(curr_opts[0]["name"].lower())
                curr_opts = curr_opts[0].get("options", [])

            full_lookup = " ".join(lookup_path)
            resolved_cmd_name = self.aliases.get(
                full_lookup,
                self.aliases.get(command_name.lower(), command_name),
            )
            cmd_meta = self.commands.get(full_lookup) or self.commands.get(resolved_cmd_name)

            if cmd_meta:
                ctx = CommandContext(self.bot, d, interaction=d)
                self.bot.interaction = d
                args = await self._resolve_slash_arguments(
                    cmd_meta, ctx, options, resolved_data
                )
                await cmd_meta["func"](ctx, **args)

        # 3. Autocomplete (INTERACTION_CREATE type=4)
        elif d.get("type") == 4:
            await self.handle_autocomplete(d)

    def _build_slash_command_payloads(self) -> List[Dict[str, Any]]:
        """Constrói o payload de Application Commands da API v10 (incluindo grupos de subcomandos)."""
        payloads: List[Dict[str, Any]] = []
        root_groups: Dict[str, Dict[str, Any]] = {}

        for name, cmd in self.commands.items():
            group_path = cmd.get("group_path")
            if group_path and len(group_path) >= 2:
                root_name = group_path[0]
                root_group = root_groups.setdefault(
                    root_name,
                    {
                        "name": root_name,
                        "description": f"Grupo de comandos {root_name}",
                        "type": 1,
                        "options": [],
                    },
                )
                if len(group_path) == 2:
                    root_group["options"].append(
                        {
                            "name": group_path[1],
                            "description": cmd["description"],
                            "type": 1,  # SUB_COMMAND
                            "options": cmd["options"],
                        }
                    )
                elif len(group_path) == 3:
                    sub_group_name = group_path[1]
                    sub_group = next(
                        (
                            o
                            for o in root_group["options"]
                            if o["name"] == sub_group_name and o["type"] == 2
                        ),
                        None,
                    )
                    if not sub_group:
                        sub_group = {
                            "name": sub_group_name,
                            "description": f"Subgrupo {sub_group_name}",
                            "type": 2,  # SUB_COMMAND_GROUP
                            "options": [],
                        }
                        root_group["options"].append(sub_group)
                    sub_group["options"].append(
                        {
                            "name": group_path[2],
                            "description": cmd["description"],
                            "type": 1,  # SUB_COMMAND
                            "options": cmd["options"],
                        }
                    )
            elif " " not in name:
                entry: Dict[str, Any] = {
                    "name": name,
                    "type": cmd.get("type", 1),
                }
                if entry["type"] == 1:
                    entry["description"] = cmd["description"]
                    entry["options"] = cmd["options"]
                payloads.append(entry)

        payloads.extend(root_groups.values())
        return payloads

    async def get_existing_commands(self, guild_id: Optional[str] = None) -> Dict[str, Any]:
        endpoint = (
            f"/applications/{self.bot.application_id}/guilds/{guild_id}/commands"
            if guild_id
            else f"/applications/{self.bot.application_id}/commands"
        )
        res = await self.bot.http.request("GET", endpoint, raise_on_error=False)
        if isinstance(res, list):
            return {cmd["name"]: cmd for cmd in res if isinstance(cmd, dict) and "name" in cmd}
        return {}

    async def sync_commands(self, guild_id: Optional[str] = None) -> str:
        """Sincroniza de forma inteligente a árvore de Slash Commands com a API v10 do Discord."""
        try:
            if not Snowflake.is_valid(self.bot.application_id):
                raise ValueError(f"Invalid application_id: {self.bot.application_id}")

            current_commands = self._build_slash_command_payloads()
            existing_commands = await self.get_existing_commands(guild_id)
            transformed_existing = [
                {
                    "name": cmd["name"],
                    "description": cmd.get("description", ""),
                    "options": [
                        {
                            "name": opt["name"],
                            "description": opt.get("description", ""),
                            "type": opt["type"],
                            "required": opt.get("required", False),
                        }
                        for opt in cmd.get("options", [])
                    ],
                    "type": cmd.get("type", 1),
                }
                for cmd in existing_commands.values()
            ]

            if self.commands_changed(current_commands, transformed_existing):
                endpoint = (
                    f"/applications/{self.bot.application_id}/guilds/{guild_id}/commands"
                    if guild_id
                    else f"/applications/{self.bot.application_id}/commands"
                )
                res = await self.bot.http.request(
                    "PUT", endpoint, json_data=current_commands, raise_on_error=False
                )
                if res is not None:
                    logger.info(
                        f"Comandos Slash sincronizados com sucesso ({'guild ' + str(guild_id) if guild_id else 'global'})."
                    )
                    return f"Commands synced successfully: {len(current_commands)} commands"
                return "Failed to sync commands"
            else:
                logger.info("Nenhuma alteração nos comandos Slash. Sincronização ignorada.")
                return "No changes in commands. Sync skipped."
        except Exception as e:
            logger.error(f"Exceção ao sincronizar comandos: {e}")
            return f"Exception occurred while syncing commands: {e}"

    def commands_changed(
        self,
        current_commands: List[Dict[str, Any]],
        existing_commands: List[Dict[str, Any]],
    ) -> bool:
        if len(current_commands) != len(existing_commands):
            return True
        existing_by_name = {c["name"]: c for c in existing_commands}
        for current in current_commands:
            existing = existing_by_name.get(current["name"])
            if not existing:
                return True
            if current.get("description", "") != existing.get("description", ""):
                return True
            curr_opts = [
                {
                    "name": o["name"],
                    "description": o.get("description", ""),
                    "type": o["type"],
                    "required": o.get("required", False),
                }
                for o in current.get("options", [])
            ]
            if curr_opts != existing.get("options", []):
                return True
        return False

    async def check_rate_limits(self) -> List[Dict[str, Any]]:
        """Retorna informações de Rate Limit dos buckets ativos e do Gateway."""
        snapshot = self.bot.http.get_rate_limit_snapshot()
        if snapshot:
            return snapshot
        # Caso ainda não tenha havido chamadas, consulta /gateway/bot
        await self.bot.http.request("GET", "/gateway/bot", raise_on_error=False)
        return self.bot.http.get_rate_limit_snapshot()


def command(
    name: Optional[str] = None,
    description: Optional[str] = None,
    aliases: Optional[List[str]] = None,
) -> Callable[..., Any]:
    """Decorador standalone exportado em `brazbot.commands` (compatível com README.md)."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        func._command = {  # type: ignore[attr-defined]
            "name": name or func.__name__,
            "description": description or func.__doc__ or "No description provided",
            "aliases": aliases or [],
        }
        return func

    return decorator
