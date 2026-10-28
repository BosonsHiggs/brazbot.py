"""
Núcleo principal do Bot e Cliente Gateway v10 da biblioteca brazbot.py (`DiscordBot` / `Bot`).
Implementa:
- Conexão WebSocket Gateway v10 (`wss://gateway.discord.gg/?v=10&encoding=json`) com suporte a Zlib-stream opcional
- Suporte completo a RESUME (Opcode 6), RECONNECT (Opcode 7), INVALID_SESSION (Opcode 9), HEARTBEAT (Opcode 1/11)
  com cálculo de latência (`bot.latency`) e reconexão inteligente usando `resume_gateway_url`
- Rastreamento automático de `voice_states` em `GUILD_CREATE` e `VOICE_STATE_UPDATE` para que `ctx.author.voice.channel`
  esteja sempre disponível nos comandos de voz e música
- Roteamento preciso de `INTERACTION_CREATE` (Slash Commands type=2, Buttons/Dropdowns type=3, Autocomplete type=4, Modals type=5)
- Compatibilidade total com `DiscordBot` e `Bot`, `await bot.start()` e `bot.run()`.
"""

import asyncio
import json
import logging
import random
import sys
import time
import zlib
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Union

import aiohttp
from aiohttp import ClientResponseError

from brazbot.audit_log_entry import AuditLogEntry
from brazbot.cache import Cache
from brazbot.channels import Channel, VoiceChannel, channel_factory
from brazbot.commands import CommandContext, CommandHandler
from brazbot.decorators import tasks
from brazbot.events import EventHandler
from brazbot.eventstype import EventTypes
from brazbot.guilds import Guild
from brazbot.http import BASE_URL, HTTPClient
from brazbot.member import Member, VoiceState
from brazbot.message_handler import MessageHandler
from brazbot.music import GuildMusicPlayer
from brazbot.permissions import INTENTS, Intents

logger = logging.getLogger(__name__)


class DiscordBot:
    """
    Cliente principal para criação de bots na API v10 do Discord.
    Conecta-se diretamente ao Gateway v10 e à API REST v10 do Discord sem depender de bibliotecas terceiras de bots.
    """

    def __init__(
        self,
        token: Optional[str] = None,
        command_prefix: Optional[str] = "!",
        intents: Optional[Union[int, Intents, Iterable[str]]] = None,
        num_shards: int = 1,
        shard_id: int = 0,
        compress: bool = False,
    ):
        self.token = token or ""
        self.default_endpoint = "wss://gateway.discord.gg/?v=10"
        self.endpoint = self.default_endpoint
        self.resume_gateway_url: Optional[str] = None
        self.session_id: Optional[str] = None
        self.voice_server_endpoint: Optional[str] = None
        self.command_prefix = command_prefix
        self.intents = self.calculate_intents(
            intents
            if intents is not None
            else ["GUILDS", "GUILD_VOICE_STATES", "GUILD_MESSAGES", "MESSAGE_CONTENT"]
        )

        self.num_shards = int(num_shards)
        self.shard_id = int(shard_id)
        self.compress = bool(compress)
        self.base_url = BASE_URL
        self.headers = {
            "Authorization": f"Bot {self.token}",
            "Content-Type": "application/json",
        }

        self.http = HTTPClient(self.token, base_url=self.base_url)
        self.event_handler = EventHandler(self)
        self.command_handler = CommandHandler(self)
        self.message_handler = MessageHandler(self.token, http_client=self.http)
        self._ttl_cache = Cache()
        self.cache: Dict[str, Dict[str, Any]] = {}

        self.application_id: Optional[str] = None
        self.user: Optional[Dict[str, Any]] = None
        self.heartbeat_interval: Optional[float] = None
        self.heartbeat_task: Optional[asyncio.Task] = None
        self._last_heartbeat_sent: float = 0.0
        self.latency: float = 0.0
        self.sequence: Optional[int] = None
        self.cogs: List[Any] = []
        self.eventtypes = tuple(event_type.name for event_type in EventTypes)
        self.wait_for_futures: List[Tuple[asyncio.Future, Callable[[Dict[str, Any]], bool]]] = []

        # Estado em tempo real de servidores, canais, estados de voz e players de música
        self.guilds_data: Dict[str, Dict[str, Any]] = {}
        self.voice_states: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self.voice_clients: Dict[str, Any] = {}
        self.music_players: Dict[str, GuildMusicPlayer] = {}
        self.component_callbacks: Dict[str, Callable[..., Any]] = {}
        self.modal_callbacks: Dict[str, Callable[..., Any]] = {}
        self.interaction: Optional[Dict[str, Any]] = None

        self._ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self._listener_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        self._closing: bool = False
        self.message_queue: asyncio.Queue = asyncio.Queue()

        self.auto_register_events()

    # ==================== GERENCIAMENTO DE CACHE ====================

    def get_cache_data(self, key: str) -> Any:
        if key in self.cache:
            entry = self.cache[key]
            if entry["expiry"] > datetime.now():
                return entry["data"]
            self.delete_cache_data(key)
        return None

    def set_cache_data(
        self,
        key: str,
        data: Any,
        seconds: int = 60,
        ttl: Optional[int] = None,
    ) -> None:
        duration = ttl if ttl is not None else seconds
        self.cache[key] = {
            "data": data,
            "expiry": datetime.now() + timedelta(seconds=float(duration)),
        }

    def delete_cache_data(self, key: str) -> None:
        self.cache.pop(key, None)

    def update_cache_data(self, key: str, data: Any) -> None:
        if key in self.cache:
            self.cache[key]["data"] = data

    @tasks(seconds=120)
    async def _cache_cleanup_task(self) -> None:
        now = datetime.now()
        keys_to_delete = [
            key for key, entry in list(self.cache.items()) if entry["expiry"] <= now
        ]
        for key in keys_to_delete:
            self.delete_cache_data(key)
        self._ttl_cache.cleanup()

    # ==================== INTENTS, EVENTOS, COMANDOS E COGS ====================

    def calculate_intents(self, intents: Union[None, int, Intents, Iterable[str]]) -> int:
        return Intents.resolve(intents)

    def event(self, func: Callable[..., Any]) -> Callable[..., Any]:
        event_name = func.__name__
        self.event_handler.register(event_name, func)
        return func

    def command(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        aliases: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> Callable[..., Any]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self.command_handler.register_command(
                func, name=name, description=description, aliases=aliases, **kwargs
            )
            return func

        return decorator

    def user_command(self, name: Optional[str] = None) -> Callable[..., Any]:
        """Registra um comando de Menu de Contexto de Usuário (`type=2` USER)."""

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self.command_handler.register_command(func, name=name, cmd_type=2)
            return func

        return decorator

    def message_command(self, name: Optional[str] = None) -> Callable[..., Any]:
        """Registra um comando de Menu de Contexto de Mensagem (`type=3` MESSAGE)."""

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self.command_handler.register_command(func, name=name, cmd_type=3)
            return func

        return decorator

    def register_component_callback(
        self, custom_id: str, callback: Callable[..., Any]
    ) -> None:
        """Registra um callback automático para um `Button` ou `Dropdown` pelo `custom_id`."""
        self.component_callbacks[str(custom_id)] = callback

    def register_modal_callback(
        self, custom_id: str, callback: Callable[..., Any]
    ) -> None:
        """Registra um callback automático para submissão de um `Form` (Modal) pelo `custom_id`."""
        self.modal_callbacks[str(custom_id)] = callback

    def auto_register_events(self) -> None:
        for attr_name in dir(self):
            if attr_name.startswith("on_"):
                attr = getattr(self, attr_name)
                if callable(attr):
                    self.event(attr)

    def add_cog(self, cog: Any) -> None:
        if getattr(cog, "bot", None) is None:
            cog.bot = self
        self.cogs.append(cog)
        for attr_name in dir(cog):
            if attr_name.startswith("__"):
                continue
            attr = getattr(cog, attr_name)
            if callable(attr):
                if attr_name.startswith("on_") or hasattr(attr, "_cog_listener"):
                    ev_name = getattr(attr, "_cog_listener", attr_name)
                    self.event_handler.register(ev_name, attr)
                if hasattr(attr, "_command"):
                    cmd_info = attr._command
                    self.command_handler.register_command(
                        attr,
                        name=cmd_info["name"],
                        description=cmd_info["description"],
                        aliases=cmd_info.get("aliases"),
                    )

    def remove_cog(self, cog_or_name: Union[str, Any]) -> bool:
        for c in list(self.cogs):
            if c is cog_or_name or c.__class__.__name__ == cog_or_name:
                self.cogs.remove(c)
                return True
        return False

    # ==================== HELPERS DE VOZ, MÚSICA E RECURSOS ====================

    def get_member_voice_state(self, guild_id: str, user_id: str) -> Optional[VoiceState]:
        """Obtém o `VoiceState` em cache de um membro em um servidor."""
        g_states = self.voice_states.get(str(guild_id), {})
        vs_data = g_states.get(str(user_id))
        if vs_data and vs_data.get("channel_id"):
            return VoiceState(vs_data, bot=self, guild_id=str(guild_id))
        return None

    def get_music_player(self, guild_id: str) -> GuildMusicPlayer:
        """Obtém ou cria o reprodutor de música (`GuildMusicPlayer`) de um servidor."""
        gid = str(guild_id)
        if gid not in self.music_players:
            self.music_players[gid] = GuildMusicPlayer(self, gid)
        return self.music_players[gid]

    async def get_guild(self, guild_id: str) -> Guild:
        return await Guild.from_guild_id(self, str(guild_id))

    async def get_channel(self, channel_id: str, guild_id: Optional[str] = None) -> Channel:
        return await Channel.from_channel_id(self, guild_id, str(channel_id))

    async def setup_hook(self) -> None:
        """Hook assíncrono executado antes de conectar ao Gateway."""
        pass

    # ==================== GATEWAY v10 HEARTBEAT, PRESENCE E EVENTOS ====================

    async def send_heartbeat(self, ws: aiohttp.ClientWebSocketResponse) -> None:
        if not self.heartbeat_interval:
            return
        # Jitter inicial recomendado pela documentação do Gateway v10
        await asyncio.sleep( (self.heartbeat_interval / 1000.0) * random.uniform(0.1, 0.5) )
        while not ws.closed and not self._closing:
            try:
                self._last_heartbeat_sent = time.perf_counter()
                await ws.send_json({"op": 1, "d": self.sequence})
                await asyncio.sleep(self.heartbeat_interval / 1000.0)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug(f"Erro ao enviar heartbeat: {e}")
                break

    async def handle_rate_limit(self, response: Any) -> None:
        if response and getattr(response, "status", None) == 429:
            retry_after = float(response.headers.get("Retry-After", 1))
            is_global = response.headers.get("X-RateLimit-Global", False)
            rate_limit_scope = response.headers.get("X-RateLimit-Scope", "unknown")
            logger.error(
                f"Rate limited. Retry after {retry_after}s. Scope: {rate_limit_scope}. Global: {is_global}"
            )
            await asyncio.sleep(retry_after)

    async def change_presence(
        self,
        activity_name: str,
        activity_type: int = 0,
        status: str = "online",
        url: Optional[str] = None,
        afk: bool = False,
    ) -> None:
        """
        Atualiza a presença/status do bot pelo WebSocket ativo do Gateway (Opcode 3).
        """
        activity: Dict[str, Any] = {
            "name": str(activity_name),
            "type": int(activity_type),
        }
        if url and int(activity_type) == 1:
            activity["url"] = str(url)

        presence_payload = {
            "op": 3,
            "d": {
                "since": int(time.time() * 1000) if status == "idle" else None,
                "activities": [activity],
                "status": status,
                "afk": bool(afk),
            },
        }
        if self._ws and not self._ws.closed:
            await self._ws.send_json(presence_payload)

    async def wait_for(
        self,
        event_type: str,
        check: Optional[Callable[[Dict[str, Any]], bool]] = None,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Aguarda a chegada de um evento do Gateway que satisfaça a condição `check`."""
        loop = asyncio.get_running_loop()
        future: asyncio.Future = loop.create_future()

        def _full_check(msg: Dict[str, Any]) -> bool:
            if event_type and msg.get("t") != event_type:
                return False
            return True if check is None else bool(check(msg))

        entry = (future, _full_check)
        self.wait_for_futures.append(entry)
        try:
            return await asyncio.wait_for(future, timeout=timeout)
        finally:
            if entry in self.wait_for_futures:
                self.wait_for_futures.remove(entry)

    async def message_listener(self) -> None:
        while not self._closing:
            try:
                message = await self.message_queue.get()
                await self.process_message(message)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Erro ao processar mensagem do Gateway: {e}", exc_info=True)

    async def process_message(self, raw_message: Union[str, Dict[str, Any]]) -> None:
        message = json.loads(raw_message) if isinstance(raw_message, str) else raw_message
        if message.get("s") is not None:
            self.sequence = message["s"]

        op = message.get("op")
        t = message.get("t")
        d = message.get("d")

        # Opcode 10: HELLO
        if op == 10 and isinstance(d, dict):
            self.heartbeat_interval = d["heartbeat_interval"]
            if self.heartbeat_task:
                self.heartbeat_task.cancel()
            if self._ws:
                self.heartbeat_task = asyncio.create_task(self.send_heartbeat(self._ws))

        # Opcode 11: HEARTBEAT_ACK
        elif op == 11:
            if self._last_heartbeat_sent > 0:
                self.latency = time.perf_counter() - self._last_heartbeat_sent

        # Opcode 1: Server-requested Heartbeat
        elif op == 1:
            if self._ws and not self._ws.closed:
                await self._ws.send_json({"op": 1, "d": self.sequence})

        # Opcode 7: RECONNECT
        elif op == 7:
            logger.info("Gateway solicitou RECONNECT (Opcode 7). Reconectando com RESUME...")
            if self._ws and not self._ws.closed:
                await self._ws.close()

        # Opcode 9: INVALID_SESSION
        elif op == 9:
            resumable = bool(d)
            logger.warning(f"Gateway enviou INVALID_SESSION (resumable={resumable}).")
            if not resumable:
                self.session_id = None
                self.sequence = None
                self.endpoint = self.default_endpoint
            await asyncio.sleep(random.uniform(1.0, 5.0))
            if self._ws and not self._ws.closed:
                await self._ws.close()

        # Eventos de Dispatch (op == 0)
        if t == "READY" and isinstance(d, dict):
            self.resume_gateway_url = d.get("resume_gateway_url")
            if self.resume_gateway_url:
                self.endpoint = f"{self.resume_gateway_url}/?v=10"
            self.session_id = d.get("session_id")
            self.user = d.get("user")
            self.application_id = d.get("application", {}).get("id") or (
                self.user.get("id") if self.user else None
            )
            await self.event_handler.handle_event({"t": "on_ready", "d": d})

        elif t == "RESUMED":
            logger.info("Sessão do Gateway retomada com sucesso (RESUMED).")
            await self.event_handler.handle_event({"t": "on_resumed", "d": d})

        elif t == "GUILD_CREATE" and isinstance(d, dict):
            gid = str(d.get("id"))
            self.guilds_data[gid] = d
            self.set_cache_data(f"guild_{gid}", d, seconds=300)
            for ch in d.get("channels", []):
                if "id" in ch:
                    ch.setdefault("guild_id", gid)
                    self.set_cache_data(f"channel_{ch['id']}", ch, seconds=300)
            g_vs = self.voice_states.setdefault(gid, {})
            g_vs.clear()
            for vs in d.get("voice_states", []):
                uid = str(vs.get("user_id", ""))
                if uid and vs.get("channel_id"):
                    vs["guild_id"] = gid
                    g_vs[uid] = vs
            asyncio.create_task(
                self.event_handler.handle_event({"t": "on_guild_create", "d": d})
            )

        elif t == "MESSAGE_CREATE" and isinstance(d, dict):
            asyncio.create_task(self.event_handler.handle_event(message))
            asyncio.create_task(
                self.event_handler.handle_event({"t": "on_message_create", "d": d})
            )
            asyncio.create_task(self.command_handler.handle_command(message))

        elif t == "VOICE_SERVER_UPDATE" and isinstance(d, dict):
            self.voice_server_endpoint = d.get("endpoint")
            asyncio.create_task(
                self.event_handler.handle_event({"t": "on_voice_server_update", "d": d})
            )

        elif t == "VOICE_STATE_UPDATE" and isinstance(d, dict):
            gid = str(d.get("guild_id") or "")
            uid = str(d.get("user_id") or "")
            if gid and uid:
                g_vs = self.voice_states.setdefault(gid, {})
                if d.get("channel_id"):
                    g_vs[uid] = d
                else:
                    g_vs.pop(uid, None)
            if "endpoint" in d:
                self.voice_server_endpoint = d["endpoint"]
            asyncio.create_task(
                self.event_handler.handle_event({"t": "on_voice_state_update", "d": d})
            )

        elif t == "INTERACTION_CREATE" and isinstance(d, dict):
            interaction_type = d.get("type")
            data_field = d.get("data") or {}
            custom_id = data_field.get("custom_id")

            # Type 3: Message Component (Button / Select Menu)
            if interaction_type == 3:
                if custom_id and custom_id in self.component_callbacks:
                    asyncio.create_task(self.component_callbacks[custom_id](d))
                await self.event_handler.handle_event(
                    {"t": "on_interaction_create", "d": d}
                )
            # Type 4: Autocomplete
            elif interaction_type == 4:
                asyncio.create_task(self.command_handler.handle_autocomplete(d))
                await self.event_handler.handle_event(
                    {"t": "on_interaction_create", "d": d}
                )
            # Type 5: Modal Submit
            elif interaction_type == 5:
                if custom_id and custom_id in self.modal_callbacks:
                    asyncio.create_task(self.modal_callbacks[custom_id](d))
                await self.event_handler.handle_event(
                    {"t": "on_interaction_create", "d": d}
                )
            # Type 2: Application Command (Slash / Context Menu)
            else:
                asyncio.create_task(self.event_handler.handle_event(message))
                asyncio.create_task(
                    self.event_handler.handle_event({"t": "on_interaction_create", "d": d})
                )
                asyncio.create_task(self.command_handler.handle_command(message))

        elif t == "GUILD_AUDIT_LOG_ENTRY_CREATE" and isinstance(d, dict):
            action_type = d.get("action_type")
            matched_enum = next(
                (ev for ev in EventTypes if ev.value == action_type), None
            )
            asyncio.create_task(
                self.event_handler.handle_event(
                    {
                        "t": "on_audit_log_entry",
                        "d": {
                            "eventtype": matched_enum,
                            "guild_id": d.get("guild_id"),
                            "data": d,
                        },
                    }
                )
            )

        elif t in self.eventtypes and isinstance(d, dict):
            asyncio.create_task(
                self.event_handler.handle_event(
                    {
                        "t": "on_audit_log_entry",
                        "d": {
                            "eventtype": EventTypes[t],
                            "guild_id": d.get("guild_id"),
                            "data": d,
                        },
                    }
                )
            )

        elif t == "ERROR":
            await self.event_handler.handle_event({"t": "on_error", "d": d})

        elif t:
            # Despacha qualquer outro evento documentado da API v10 (ex.: on_guild_member_add, on_message_delete)
            asyncio.create_task(self.event_handler.handle_event(message))

        # Notifica aguardadores de `wait_for`
        for future, check in list(self.wait_for_futures):
            if not future.done() and check(message):
                future.set_result(message)
                if (future, check) in self.wait_for_futures:
                    self.wait_for_futures.remove((future, check))

    # ==================== CICLO DE VIDA DA CONEXÃO ====================

    async def start(self, token: Optional[str] = None) -> None:
        """Inicia o loop principal assíncrono do bot no Gateway v10."""
        if token:
            self.token = token
            self.http.token = token
            self.message_handler.token = token
            self.headers["Authorization"] = f"Bot {token}"

        self._closing = False
        self._cleanup_task = asyncio.create_task(self._cache_cleanup_task())
        await self.setup_hook()

        self._listener_task = asyncio.create_task(self.message_listener())

        while not self._closing:
            try:
                ws_url = f"{self.endpoint}&encoding=json"
                if self.compress:
                    ws_url += "&compress=zlib-stream"
                    inflater = zlib.decompressobj()
                    buffer = bytearray()

                async with aiohttp.ClientSession() as session:
                    async with session.ws_connect(ws_url, max_msg_size=0) as ws:
                        self._ws = ws

                        if self.session_id and self.sequence is not None:
                            await ws.send_json(
                                {
                                    "op": 6,
                                    "d": {
                                        "token": self.token,
                                        "session_id": self.session_id,
                                        "seq": self.sequence,
                                    },
                                }
                            )
                            logger.info(f"Enviando RESUME (session_id={self.session_id}, seq={self.sequence})")
                        else:
                            identify_payload = {
                                "op": 2,
                                "d": {
                                    "token": self.token,
                                    "intents": self.intents,
                                    "properties": {
                                        "os": sys.platform,
                                        "browser": "brazbot.py",
                                        "device": "brazbot.py",
                                    },
                                    "shard": [self.shard_id, self.num_shards],
                                },
                            }
                            await ws.send_json(identify_payload)

                        async for msg in ws:
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                await self.message_queue.put(msg.data)
                            elif msg.type == aiohttp.WSMsgType.BINARY and self.compress:
                                buffer.extend(msg.data)
                                if len(msg.data) >= 4 and msg.data[-4:] == b"\x00\x00\xff\xff":
                                    decompressed = inflater.decompress(buffer).decode("utf-8")
                                    buffer.clear()
                                    await self.message_queue.put(decompressed)
                            elif msg.type in {aiohttp.WSMsgType.ERROR, aiohttp.WSMsgType.CLOSED}:
                                break

                        if self.heartbeat_task:
                            self.heartbeat_task.cancel()

                        # Códigos fatais do Gateway do Discord que não devem reconectar
                        if ws.close_code in (4004, 4010, 4011, 4012, 4013, 4014):
                            raise RuntimeError(
                                f"Conexão encerrada pelo Discord com código fatal {ws.close_code} "
                                "(verifique seu DISCORD_TOKEN e as Privileged Intents no Developer Portal)."
                            )

            except ClientResponseError as e:
                await self.handle_rate_limit(e)
            except RuntimeError:
                raise
            except Exception as e:
                logger.error(f"Exceção na conexão com o Gateway: {e}")

            if not self._closing:
                logger.info("Reconectando ao Gateway em 5 segundos...")
                await asyncio.sleep(5)

    async def close(self) -> None:
        """Encerra todas as conexões de voz, Gateway e sessões HTTP limpamente."""
        self._closing = True
        for vc in list(self.voice_clients.values()):
            try:
                await vc.disconnect()
            except Exception:
                pass
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
        if self._listener_task:
            self._listener_task.cancel()
        if self._cleanup_task:
            self._cleanup_task.cancel()
        if self._ws and not self._ws.closed:
            await self._ws.close()
        await self.http.close()

    def run(self, token: Optional[str] = None) -> None:
        """Executa o bot de forma síncrona (compatível com `bot.run('TOKEN')` do README.md)."""
        try:
            asyncio.run(self.start(token=token))
        except KeyboardInterrupt:
            logger.info("Bot encerrado pelo usuário.")


# Alias oficial para `from brazbot.bot import Bot`
Bot = DiscordBot


def main() -> None:
    """Entrypoint de console para o comando `brazbot`."""
    from brazbot.cli import main as cli_main

    cli_main()
