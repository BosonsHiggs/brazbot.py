"""
Cliente de Voz nativo da biblioteca brazbot.py (Discord Voice Gateway v8 + UDP RTP AEAD).
Implementa:
- Handshake completo (Opcode 4 Gateway -> VOICE_STATE_UPDATE + VOICE_SERVER_UPDATE)
- Voice WebSocket v8 (?v=8) com Heartbeat numerado (seq_ack), Buffered Resume (Op 7 / Op 9) e loop contínuo
- IP Discovery de 74 bytes Big-Endian (Type=1, Length=70, SSRC, Address, Port)
- Criptografia de transporte moderna exigida pelo Discord:
  * aead_aes256_gcm_rtpsize (preferencial, via cryptography AESGCM)
  * aead_xchacha20_poly1305_rtpsize (obrigatório, via PyNaCl nacl.bindings)
- Codificação e Decodificação Opus nativa via ctypes (libopus) + Demuxer Ogg/Opus puro em Python (fallback via FFmpeg)
- Controle real de volume em PCM 16-bit, busca (seek), filtros de áudio FFmpeg e recepção/bridge de pacotes de voz
"""

import array
import asyncio
import ctypes
import ctypes.util
import json
import logging
import socket
import struct
import time
from subprocess import PIPE
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple, Union

import aiohttp

from brazbot.errors import OpusError, VoiceConnectionError

logger = logging.getLogger(__name__)

# Constantes de Áudio Opus / RTP do Discord
SAMPLE_RATE = 48000
CHANNELS = 2
FRAME_LENGTH_MS = 20
SAMPLES_PER_FRAME = int(SAMPLE_RATE / 1000 * FRAME_LENGTH_MS)  # 960 amostras por canal
SAMPLE_SIZE = 2 * CHANNELS  # 4 bytes (16-bit stereo)
PCM_FRAME_SIZE = SAMPLES_PER_FRAME * SAMPLE_SIZE  # 3840 bytes por quadro de 20ms
OPUS_SILENCE_FRAME = b"\xf8\xff\xfe"

# Constantes da libopus
OPUS_OK = 0
OPUS_APPLICATION_AUDIO = 2049
OPUS_APPLICATION_VOIP = 2048
OPUS_SET_BITRATE_REQUEST = 4002
OPUS_SET_FEC_REQUEST = 4012
OPUS_SET_PACKET_LOSS_PERC_REQUEST = 4014
OPUS_SET_SIGNAL_REQUEST = 4024
OPUS_SIGNAL_MUSIC = 3002

SUPPORTED_ENCRYPTION_MODES = (
    "aead_aes256_gcm_rtpsize",
    "aead_xchacha20_poly1305_rtpsize",
)


def _load_opus_lib() -> Optional[ctypes.CDLL]:
    """Localiza e carrega dinamicamente a biblioteca C libopus no sistema operacional."""
    candidates = [
        ctypes.util.find_library("opus"),
        "libopus.so.0",
        "libopus.so",
        "libopus.0.dylib",
        "opus.dll",
        "libopus-0.dll",
    ]
    for name in candidates:
        if not name:
            continue
        try:
            return ctypes.cdll.LoadLibrary(name)
        except OSError:
            continue
    return None


_OPUS_LIB = _load_opus_lib()


class OpusEncoder:
    """
    Codificador Opus nativo via ctypes (48kHz, 2 canais, 20ms -> pacotes Opus para o Discord).
    """

    def __init__(
        self,
        sample_rate: int = SAMPLE_RATE,
        channels: int = CHANNELS,
        application: int = OPUS_APPLICATION_AUDIO,
        bitrate: int = 128000,
    ):
        if _OPUS_LIB is None:
            raise OpusError(
                "Biblioteca nativa 'libopus' não encontrada no sistema. "
                "Instale 'libopus0' / 'ffmpeg' ou utilize FFmpegOpusAudioSource."
            )
        self.sample_rate = sample_rate
        self.channels = channels
        self._lib = _OPUS_LIB

        self._lib.opus_encoder_create.argtypes = [
            ctypes.c_int32,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_int),
        ]
        self._lib.opus_encoder_create.restype = ctypes.c_void_p

        self._lib.opus_encode.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_int16),
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int32,
        ]
        self._lib.opus_encode.restype = ctypes.c_int32

        self._lib.opus_encoder_ctl.restype = ctypes.c_int32
        self._lib.opus_encoder_destroy.argtypes = [ctypes.c_void_p]
        self._lib.opus_encoder_destroy.restype = None

        err = ctypes.c_int()
        self._state = self._lib.opus_encoder_create(
            sample_rate, channels, application, ctypes.byref(err)
        )
        if err.value != OPUS_OK or not self._state:
            raise OpusError(f"Falha ao inicializar OpusEncoder (código {err.value})")

        self.set_bitrate(bitrate)
        self.set_fec(True)
        self.set_packet_loss_percent(15)

    def set_bitrate(self, kbps_or_bps: int) -> None:
        bps = kbps_or_bps * 1000 if kbps_or_bps <= 512 else kbps_or_bps
        bps = min(512000, max(16000, int(bps)))
        self._lib.opus_encoder_ctl(self._state, OPUS_SET_BITRATE_REQUEST, ctypes.c_int32(bps))

    def set_fec(self, enabled: bool = True) -> None:
        self._lib.opus_encoder_ctl(
            self._state, OPUS_SET_FEC_REQUEST, ctypes.c_int32(1 if enabled else 0)
        )

    def set_packet_loss_percent(self, percentage: int = 15) -> None:
        pct = min(100, max(0, int(percentage)))
        self._lib.opus_encoder_ctl(
            self._state, OPUS_SET_PACKET_LOSS_PERC_REQUEST, ctypes.c_int32(pct)
        )

    def encode(self, pcm_data: bytes, frame_size: int = SAMPLES_PER_FRAME) -> bytes:
        """Codifica um quadro PCM s16le (3840 bytes) em um quadro Opus."""
        if len(pcm_data) < PCM_FRAME_SIZE:
            pcm_data = pcm_data + b"\x00" * (PCM_FRAME_SIZE - len(pcm_data))
        max_data_bytes = 4000
        out_buf = ctypes.create_string_buffer(max_data_bytes)
        pcm_ptr = ctypes.cast(pcm_data, ctypes.POINTER(ctypes.c_int16))
        length = self._lib.opus_encode(
            self._state, pcm_ptr, frame_size, out_buf, max_data_bytes
        )
        if length < 0:
            raise OpusError(f"Erro ao codificar quadro Opus (código {length})")
        return out_buf.raw[:length]

    def destroy(self) -> None:
        if getattr(self, "_state", None):
            self._lib.opus_encoder_destroy(self._state)
            self._state = None

    def __del__(self) -> None:
        self.destroy()


class OpusDecoder:
    """
    Decodificador Opus nativo via ctypes (pacotes Opus -> PCM s16le 48kHz stereo).
    Usado para recepção de voz e bridge de chamadas entre servidores.
    """

    def __init__(self, sample_rate: int = SAMPLE_RATE, channels: int = CHANNELS):
        if _OPUS_LIB is None:
            raise OpusError("Biblioteca nativa 'libopus' não encontrada no sistema.")
        self.sample_rate = sample_rate
        self.channels = channels
        self._lib = _OPUS_LIB

        self._lib.opus_decoder_create.argtypes = [
            ctypes.c_int32,
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_int),
        ]
        self._lib.opus_decoder_create.restype = ctypes.c_void_p

        self._lib.opus_decode.argtypes = [
            ctypes.c_void_p,
            ctypes.c_char_p,
            ctypes.c_int32,
            ctypes.POINTER(ctypes.c_int16),
            ctypes.c_int,
            ctypes.c_int,
        ]
        self._lib.opus_decode.restype = ctypes.c_int

        self._lib.opus_decoder_destroy.argtypes = [ctypes.c_void_p]
        self._lib.opus_decoder_destroy.restype = None

        err = ctypes.c_int()
        self._state = self._lib.opus_decoder_create(sample_rate, channels, ctypes.byref(err))
        if err.value != OPUS_OK or not self._state:
            raise OpusError(f"Falha ao inicializar OpusDecoder (código {err.value})")

    def decode(self, opus_data: Optional[bytes], fec: bool = False) -> bytes:
        """Decodifica um pacote Opus em 3840 bytes de áudio PCM s16le."""
        out_samples = SAMPLES_PER_FRAME * self.channels
        pcm_buf = (ctypes.c_int16 * out_samples)()
        data_ptr = ctypes.c_char_p(opus_data) if opus_data else None
        data_len = len(opus_data) if opus_data else 0
        decoded_samples = self._lib.opus_decode(
            self._state,
            data_ptr,
            data_len,
            pcm_buf,
            SAMPLES_PER_FRAME,
            1 if fec else 0,
        )
        if decoded_samples < 0:
            raise OpusError(f"Erro ao decodificar pacote Opus (código {decoded_samples})")
        return ctypes.string_at(pcm_buf, decoded_samples * self.channels * 2)

    def destroy(self) -> None:
        if getattr(self, "_state", None):
            self._lib.opus_decoder_destroy(self._state)
            self._state = None

    def __del__(self) -> None:
        self.destroy()


class OggOpusDemuxer:
    """
    Demuxer Ogg/Opus puro em Python para extrair pacotes Opus diretamente do stdout do FFmpeg
    quando a libopus não está acessível via ctypes ou quando o modo Opus direto é utilizado.
    """

    def __init__(self, stream: asyncio.StreamReader):
        self.stream = stream
        self._packet_queue: List[bytes] = []
        self._partial_packet = bytearray()

    async def read_packet(self) -> Optional[bytes]:
        """Lê o próximo pacote de áudio Opus válido do fluxo Ogg."""
        while not self._packet_queue:
            header = await self.stream.readexactly(27) if hasattr(self.stream, "readexactly") else await self.stream.read(27)
            if not header or len(header) < 27:
                return None
            if header[:4] != b"OggS":
                return None
            page_segments = header[26]
            segment_table = await self.stream.read(page_segments)
            if len(segment_table) < page_segments:
                return None

            body_size = sum(segment_table)
            body = await self.stream.read(body_size)
            if len(body) < body_size:
                return None

            offset = 0
            for seg_len in segment_table:
                self._partial_packet.extend(body[offset : offset + seg_len])
                offset += seg_len
                if seg_len < 255:
                    pkt = bytes(self._partial_packet)
                    self._partial_packet.clear()
                    # Ignora cabeçalhos Ogg OpusHead e OpusTags
                    if pkt.startswith(b"OpusHead") or pkt.startswith(b"OpusTags"):
                        continue
                    if pkt:
                        self._packet_queue.append(pkt)

        return self._packet_queue.pop(0)


def scale_pcm16_volume(pcm_data: bytes, volume: float) -> bytes:
    """Aplica ganho de volume (0.0 a 2.0) em amostras PCM 16-bit signed little-endian."""
    if abs(volume - 1.0) < 1e-4:
        return pcm_data
    if volume <= 0.0:
        return b"\x00" * len(pcm_data)
    samples = array.array("h")
    # Garante alinhamento par de bytes
    valid_len = len(pcm_data) - (len(pcm_data) % 2)
    samples.frombytes(pcm_data[:valid_len])
    for i in range(len(samples)):
        val = int(samples[i] * volume)
        if val > 32767:
            val = 32767
        elif val < -32768:
            val = -32768
        samples[i] = val
    return samples.tobytes()


class AudioSource:
    """Classe base para fontes de áudio reproduzíveis pelo VoiceClient."""

    def __init__(self, volume: float = 1.0):
        self.volume: float = float(volume)
        self.paused: bool = False
        self.position: int = 0
        self._closed: bool = False

    async def read(self) -> Optional[bytes]:
        """Lê 20ms de áudio (3840 bytes se PCM ou 1 quadro se Opus). Retorna None ao terminar."""
        raise NotImplementedError

    def is_opus(self) -> bool:
        """Retorna True se `read()` já entrega quadros codificados em Opus."""
        return False

    @property
    def elapsed_seconds(self) -> float:
        """Retorna o tempo reproduzido em segundos."""
        return self.position / float(SAMPLE_RATE * SAMPLE_SIZE)

    async def cleanup(self) -> None:
        """Libera recursos associados à fonte de áudio."""
        self._closed = True


class FFmpegAudioSource(AudioSource):
    """
    Fonte de áudio baseada em FFmpeg (suporta URLs HTTP/HTTPS, streams extraídos via yt-dlp,
    arquivos locais, filtros de áudio, busca/seek e reconexão automática).
    Se `use_opus_pipe=True` (ou se a libopus não estiver disponível via ctypes), faz o FFmpeg
    codificar diretamente em Opus (`-c:a libopus -f ogg`).
    """

    def __init__(
        self,
        source: str,
        *,
        pipe: bool = False,
        before_options: str = "",
        options: str = "",
        volume: float = 1.0,
        seek_seconds: float = 0.0,
        audio_filter: Optional[str] = None,
        use_opus_pipe: Optional[bool] = None,
        **kwargs: Any,
    ):
        super().__init__(volume=volume)
        self.source = source
        self.pipe = pipe
        self.before_options = before_options
        self.options = options
        self.seek_seconds = float(seek_seconds or 0.0)
        self.audio_filter = audio_filter
        self.process: Optional[asyncio.subprocess.Process] = None
        self._stderr_reader: Optional[asyncio.Task] = None
        self._ogg_demuxer: Optional[OggOpusDemuxer] = None
        self._use_opus_pipe = (
            use_opus_pipe if use_opus_pipe is not None else (_OPUS_LIB is None)
        )

        # Reconexão automática padrão para URLs HTTP(S)
        if not self.pipe and self.source.startswith(("http://", "https://")) and not self.before_options:
            self.before_options = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"

        self.args = self._build_args()

    def _build_args(self) -> List[str]:
        args = ["ffmpeg", "-hide_banner"]
        if self.seek_seconds > 0:
            args.extend(["-ss", f"{self.seek_seconds:.2f}"])
        if self.before_options:
            args.extend(self.before_options.split())

        args.extend(["-i", "pipe:0" if self.pipe else self.source, "-vn"])

        if self.audio_filter:
            args.extend(["-af", self.audio_filter])

        if self._use_opus_pipe:
            args.extend(
                [
                    "-c:a",
                    "libopus",
                    "-b:a",
                    "128k",
                    "-vbr",
                    "on",
                    "-application",
                    "audio",
                    "-frame_duration",
                    "20",
                    "-page_duration",
                    "20000",
                    "-ar",
                    str(SAMPLE_RATE),
                    "-ac",
                    str(CHANNELS),
                    "-loglevel",
                    "warning",
                ]
            )
            if self.options:
                args.extend(self.options.split())
            args.extend(["-f", "ogg", "pipe:1"])
        else:
            args.extend(
                [
                    "-f",
                    "s16le",
                    "-ar",
                    str(SAMPLE_RATE),
                    "-ac",
                    str(CHANNELS),
                    "-loglevel",
                    "warning",
                ]
            )
            if self.options:
                args.extend(self.options.split())
            args.append("pipe:1")
        return args

    def is_opus(self) -> bool:
        return self._use_opus_pipe

    async def create_process(self) -> None:
        """Inicia o subprocesso FFmpeg."""
        if self.process is not None:
            return
        try:
            self.process = await asyncio.create_subprocess_exec(
                *self.args,
                stdin=PIPE if self.pipe else None,
                stdout=PIPE,
                stderr=PIPE,
            )
            if self._use_opus_pipe and self.process.stdout:
                self._ogg_demuxer = OggOpusDemuxer(self.process.stdout)
            self._stderr_reader = asyncio.create_task(self._read_stderr())
            logger.debug(f"Processo FFmpeg iniciado (PID={self.process.pid})")
        except Exception as e:
            logger.error(f"Falha ao iniciar processo FFmpeg: {e}")
            raise VoiceConnectionError(f"Falha ao iniciar FFmpeg: {e}") from e

    async def _read_stderr(self) -> None:
        while self.process and self.process.stderr and not self._closed:
            try:
                line = await self.process.stderr.readline()
                if not line:
                    break
                decoded = line.decode(errors="ignore").strip()
                if decoded and "warning" not in decoded.lower():
                    logger.debug(f"FFmpeg: {decoded}")
            except Exception:
                break

    async def read(self) -> Optional[bytes]:
        if self._closed or self.paused:
            return None
        if self.process is None:
            await self.create_process()
        if not self.process or not self.process.stdout:
            return None

        try:
            if self._use_opus_pipe and self._ogg_demuxer:
                pkt = await self._ogg_demuxer.read_packet()
                if not pkt:
                    await self.cleanup()
                    return None
                self.position += PCM_FRAME_SIZE
                return pkt

            # Lê exatamente 3840 bytes (20ms de PCM s16le stereo 48kHz)
            buf = bytearray()
            while len(buf) < PCM_FRAME_SIZE:
                chunk = await self.process.stdout.read(PCM_FRAME_SIZE - len(buf))
                if not chunk:
                    break
                buf.extend(chunk)

            if not buf:
                await self.cleanup()
                return None

            if len(buf) < PCM_FRAME_SIZE:
                buf.extend(b"\x00" * (PCM_FRAME_SIZE - len(buf)))

            self.position += len(buf)
            pcm_bytes = bytes(buf)
            if abs(self.volume - 1.0) > 1e-4:
                pcm_bytes = scale_pcm16_volume(pcm_bytes, self.volume)
            return pcm_bytes

        except asyncio.IncompleteReadError:
            await self.cleanup()
            return None
        except Exception as e:
            logger.error(f"Erro ao ler fluxo do FFmpeg: {e}")
            await self.cleanup()
            return None

    async def write_pipe(self, data: bytes) -> None:
        """Escreve bytes no stdin do FFmpeg quando em modo pipe."""
        if self._closed or not self.process or not self.process.stdin:
            return
        try:
            self.process.stdin.write(data)
            await self.process.stdin.drain()
        except Exception as e:
            logger.error(f"Erro ao escrever no pipe do FFmpeg: {e}")

    async def cleanup(self) -> None:
        self._closed = True
        if self._stderr_reader:
            self._stderr_reader.cancel()
            try:
                await self._stderr_reader
            except (asyncio.CancelledError, Exception):
                pass
            self._stderr_reader = None

        if self.process:
            try:
                self.process.terminate()
                await asyncio.wait_for(self.process.wait(), timeout=3.0)
            except asyncio.TimeoutError:
                try:
                    self.process.kill()
                    await self.process.wait()
                except (asyncio.CancelledError, Exception):
                    pass
            except (asyncio.CancelledError, Exception):
                pass
            self.process = None


class PCMAudioSource(AudioSource):
    """
    Fonte de áudio para dados PCM s16le em memória (48kHz).
    Suporta conversão automática de mono (1 canal) para estéreo (2 canais).
    """

    def __init__(
        self,
        data: bytes,
        chunk_size: int = PCM_FRAME_SIZE,
        channels: int = 2,
        volume: float = 1.0,
    ):
        super().__init__(volume=volume)
        if channels == 1:
            # Duplica amostras mono de 16 bits para estéreo
            mono = array.array("h")
            mono.frombytes(data[: len(data) - (len(data) % 2)])
            stereo = array.array("h")
            for sample in mono:
                stereo.append(sample)
                stereo.append(sample)
            self.data = stereo.tobytes()
        else:
            self.data = data
        self.chunk_size = chunk_size
        self.pos = 0

    async def read(self) -> Optional[bytes]:
        if self._closed or self.paused or self.pos >= len(self.data):
            return None
        chunk = self.data[self.pos : self.pos + self.chunk_size]
        self.pos += len(chunk)
        self.position = self.pos
        if not chunk:
            return None
        if len(chunk) < self.chunk_size:
            chunk = chunk + b"\x00" * (self.chunk_size - len(chunk))
        if abs(self.volume - 1.0) > 1e-4:
            chunk = scale_pcm16_volume(chunk, self.volume)
        return chunk


class VoiceWebSocket:
    """
    Gerencia a conexão WebSocket com o Discord Voice Gateway v8 (`?v=8`).
    """

    def __init__(self, voice_client: "VoiceClient"):
        self.voice_client = voice_client
        self._session: Optional[aiohttp.ClientSession] = None
        self.ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.receive_task: Optional[asyncio.Task] = None
        self.heartbeat_interval: float = 41.25
        self.ssrc: int = 0
        self.secret_key: Optional[List[int]] = None
        self.mode: Optional[str] = None
        self.modes: List[str] = []
        self.ip: Optional[str] = None
        self.port: Optional[int] = None
        self.seq_ack: int = -1
        self.ssrc_user_map: Dict[int, str] = {}
        self._ready_event = asyncio.Event()
        self._session_desc_event = asyncio.Event()
        self._closed = False

    async def connect(self, endpoint: str, resume: bool = False) -> aiohttp.ClientWebSocketResponse:
        """Conecta ao Voice Gateway v8 e realiza o handshake Identify (Op 0) ou Resume (Op 7)."""
        clean_endpoint = endpoint.replace("wss://", "").replace("https://", "").split(":")[0]
        ws_url = f"wss://{clean_endpoint}/?v=8"

        self._closed = False
        self._ready_event.clear()
        self._session_desc_event.clear()

        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()

        self.ws = await self._session.ws_connect(ws_url, heartbeat=None, autoping=True)
        self.receive_task = asyncio.create_task(self._receive_loop())

        if resume:
            await self.send_resume()
        else:
            await self.identify()
            try:
                await asyncio.wait_for(self._ready_event.wait(), timeout=20.0)
            except asyncio.TimeoutError as e:
                raise VoiceConnectionError("Timeout aguardando Opcode 2 READY do Voice Gateway") from e

        return self.ws

    async def identify(self) -> None:
        """Envia o payload Opcode 0 Identify para o Voice Gateway v8."""
        payload = {
            "op": 0,
            "d": {
                "server_id": str(self.voice_client.guild_id),
                "user_id": str(self.voice_client.bot.application_id),
                "session_id": str(self.voice_client.session_id),
                "token": str(self.voice_client.token),
                "max_dave_protocol_version": 0,
            },
        }
        await self.send_json(payload)

    async def send_resume(self) -> None:
        """Envia o payload Opcode 7 Resume para o Voice Gateway v8."""
        payload = {
            "op": 7,
            "d": {
                "server_id": str(self.voice_client.guild_id),
                "session_id": str(self.voice_client.session_id),
                "token": str(self.voice_client.token),
                "seq_ack": self.seq_ack,
            },
        }
        await self.send_json(payload)

    async def send_json(self, payload: Dict[str, Any]) -> None:
        if self.ws and not self.ws.closed:
            await self.ws.send_str(json.dumps(payload))

    async def _receive_loop(self) -> None:
        """Loop contínuo de recepção de eventos do Voice Gateway v8."""
        if not self.ws:
            return
        try:
            async for msg in self.ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    if "seq" in data and isinstance(data["seq"], int):
                        self.seq_ack = data["seq"]

                    op = data.get("op")
                    d = data.get("d") or {}

                    if op == 8:  # HELLO
                        self.heartbeat_interval = float(d.get("heartbeat_interval", 41250)) / 1000.0
                        if self.heartbeat_task:
                            self.heartbeat_task.cancel()
                        self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())

                    elif op == 2:  # READY
                        self.ssrc = int(d["ssrc"])
                        self.ip = d["ip"]
                        self.port = int(d["port"])
                        self.modes = d.get("modes", [])
                        self._ready_event.set()

                    elif op == 4:  # SESSION_DESCRIPTION
                        self.secret_key = d.get("secret_key")
                        self.mode = d.get("mode")
                        self._session_desc_event.set()

                    elif op == 5:  # SPEAKING
                        user_id = d.get("user_id")
                        user_ssrc = d.get("ssrc")
                        if user_id and user_ssrc is not None:
                            self.ssrc_user_map[int(user_ssrc)] = str(user_id)

                    elif op == 3:  # Server-requested immediate heartbeat
                        await self._send_heartbeat_once()

                    elif op == 6:  # HEARTBEAT_ACK
                        pass

                    elif op == 9:  # RESUMED
                        logger.info(f"Sessão de voz retomada (guild={self.voice_client.guild_id})")

                    elif op == 13:  # CLIENT_DISCONNECT
                        disc_user = d.get("user_id")
                        if disc_user:
                            for k, v in list(self.ssrc_user_map.items()):
                                if v == str(disc_user):
                                    self.ssrc_user_map.pop(k, None)

                    elif op == 21:  # DAVE_PROTOCOL_PREPARE_TRANSITION
                        transition_id = d.get("transition_id", 0)
                        await self.send_json(
                            {"op": 23, "d": {"transition_id": transition_id}}
                        )

                elif msg.type == aiohttp.WSMsgType.BINARY:
                    # Mensagens binárias no Voice Gateway v8 trazem 2 bytes big-endian de seq no início
                    if len(msg.data) >= 3:
                        self.seq_ack = struct.unpack_from(">H", msg.data, 0)[0]

                elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                    break
        except asyncio.CancelledError:
            pass
        except Exception as e:
            if not self._closed:
                logger.error(f"Erro no loop do VoiceWebSocket: {e}")

    async def _send_heartbeat_once(self) -> None:
        nonce = int(time.time() * 1000)
        payload = {
            "op": 3,
            "d": {
                "t": nonce,
                "seq_ack": self.seq_ack,
            },
        }
        await self.send_json(payload)

    async def _heartbeat_loop(self) -> None:
        while not self._closed:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                if self.ws and not self.ws.closed:
                    await self._send_heartbeat_once()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Erro no heartbeat de voz: {e}")
                break

    async def select_protocol(self, ip: str, port: int, mode: str) -> None:
        """Envia Opcode 1 Select Protocol e aguarda Opcode 4 Session Description."""
        payload = {
            "op": 1,
            "d": {
                "protocol": "udp",
                "data": {
                    "address": ip,
                    "port": int(port),
                    "mode": mode,
                },
            },
        }
        await self.send_json(payload)
        try:
            await asyncio.wait_for(self._session_desc_event.wait(), timeout=20.0)
        except asyncio.TimeoutError as e:
            raise VoiceConnectionError(
                "Timeout aguardando Opcode 4 SESSION_DESCRIPTION do Voice Gateway"
            ) from e

    async def set_speaking(self, speaking: Union[bool, int]) -> None:
        """Envia Opcode 5 Speaking (1 = Microphone, 0 = Stop)."""
        if self._closed or not self.ws or self.ws.closed:
            return
        flag = int(speaking) if not isinstance(speaking, bool) else (1 if speaking else 0)
        payload = {
            "op": 5,
            "d": {
                "speaking": flag,
                "delay": 0,
                "ssrc": self.ssrc,
            },
        }
        try:
            await self.send_json(payload)
        except Exception as e:
            logger.error(f"Falha ao enviar estado speaking: {e}")

    async def close(self) -> None:
        self._closed = True
        for task in (self.heartbeat_task, self.receive_task):
            if task:
                task.cancel()
                try:
                    await task
                except (asyncio.CancelledError, Exception):
                    pass
        self.heartbeat_task = None
        self.receive_task = None
        if self.ws and not self.ws.closed:
            await self.ws.close()
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None


class UDPVoiceConnection:
    """
    Gerencia o socket UDP de voz, IP Discovery de 74 bytes e criptografia/descriptografia RTP AEAD:
    - `aead_aes256_gcm_rtpsize`
    - `aead_xchacha20_poly1305_rtpsize`
    """

    def __init__(self, voice_client: "VoiceClient"):
        self.voice_client = voice_client
        self.socket: Optional[socket.socket] = None
        self.endpoint_ip: Optional[str] = None
        self.endpoint_port: Optional[int] = None
        self.external_ip: Optional[str] = None
        self.external_port: Optional[int] = None
        self.sequence: int = 0
        self.timestamp: int = 0
        self.encrypt_nonce: int = 0
        self.ssrc: int = 0
        self.secret_key: Optional[bytes] = None
        self.mode: str = "aead_xchacha20_poly1305_rtpsize"
        self._closed: bool = False

    @staticmethod
    def choose_encryption_mode(server_modes: List[str]) -> str:
        """Seleciona o melhor modo AEAD suportado pelo servidor e pelo ambiente."""
        if "aead_aes256_gcm_rtpsize" in server_modes:
            try:
                from cryptography.hazmat.primitives.ciphers.aead import AESGCM  # noqa: F401
                return "aead_aes256_gcm_rtpsize"
            except ImportError:
                pass
        if "aead_xchacha20_poly1305_rtpsize" in server_modes:
            return "aead_xchacha20_poly1305_rtpsize"
        raise VoiceConnectionError(
            f"Nenhum modo de criptografia AEAD compatível encontrado em: {server_modes}"
        )

    async def connect(self, ip: str, port: int, ssrc: int) -> Tuple[str, int]:
        """Conecta o socket UDP ao servidor de voz e realiza o IP Discovery de 74 bytes."""
        self.ssrc = int(ssrc)
        self.endpoint_ip = ip
        self.endpoint_port = int(port)
        self._closed = False

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setblocking(False)
        self.socket.connect((self.endpoint_ip, self.endpoint_port))

        # Pacote oficial de IP Discovery do Discord (74 bytes Big-Endian):
        # [0..1] Type = 0x0001 (Request)
        # [2..3] Length = 70 (0x0046)
        # [4..7] SSRC (uint32)
        # [8..71] Address (64 bytes nulos)
        # [72..73] Port (2 bytes nulos)
        packet = bytearray(74)
        struct.pack_into(">HHI", packet, 0, 1, 70, self.ssrc)

        loop = asyncio.get_running_loop()
        await loop.sock_sendall(self.socket, packet)

        data = await asyncio.wait_for(loop.sock_recv(self.socket, 74), timeout=10.0)
        if len(data) < 74:
            raise VoiceConnectionError(
                f"Resposta de IP Discovery inválida ({len(data)} bytes, esperado 74 bytes)"
            )

        ip_start = 8
        ip_end = data.index(b"\x00", ip_start)
        self.external_ip = data[ip_start:ip_end].decode("ascii")
        self.external_port = struct.unpack_from(">H", data, 72)[0]
        return self.external_ip, self.external_port

    def _encrypt_aead_aes256_gcm_rtpsize(self, header: bytes, data: bytes) -> bytes:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        if not self.secret_key:
            raise VoiceConnectionError("Chave secreta de voz não definida.")
        self.encrypt_nonce = (self.encrypt_nonce + 1) & 0xFFFFFFFF
        nonce_suffix = struct.pack(">I", self.encrypt_nonce)
        nonce = bytearray(12)
        nonce[:4] = nonce_suffix
        aesgcm = AESGCM(bytes(self.secret_key))
        ciphertext = aesgcm.encrypt(bytes(nonce), bytes(data), bytes(header))
        return bytes(header) + ciphertext + nonce_suffix

    def _encrypt_aead_xchacha20_poly1305_rtpsize(self, header: bytes, data: bytes) -> bytes:
        import nacl.bindings

        if not self.secret_key:
            raise VoiceConnectionError("Chave secreta de voz não definida.")
        self.encrypt_nonce = (self.encrypt_nonce + 1) & 0xFFFFFFFF
        nonce_suffix = struct.pack(">I", self.encrypt_nonce)
        nonce = bytearray(24)
        nonce[:4] = nonce_suffix
        ciphertext = nacl.bindings.crypto_aead_xchacha20poly1305_ietf_encrypt(
            bytes(data),
            bytes(header),
            bytes(nonce),
            bytes(self.secret_key),
        )
        return bytes(header) + ciphertext + nonce_suffix

    def create_packet(self, opus_frame: bytes) -> bytes:
        """Cria um pacote RTP criptografado com o modo AEAD negociado."""
        header = bytearray(12)
        header[0] = 0x80
        header[1] = 0x78
        struct.pack_into(">H", header, 2, self.sequence & 0xFFFF)
        struct.pack_into(">I", header, 4, self.timestamp & 0xFFFFFFFF)
        struct.pack_into(">I", header, 8, self.ssrc & 0xFFFFFFFF)

        self.sequence = (self.sequence + 1) & 0xFFFF
        self.timestamp = (self.timestamp + SAMPLES_PER_FRAME) & 0xFFFFFFFF

        if self.mode == "aead_aes256_gcm_rtpsize":
            return self._encrypt_aead_aes256_gcm_rtpsize(bytes(header), opus_frame)
        return self._encrypt_aead_xchacha20_poly1305_rtpsize(bytes(header), opus_frame)

    def decrypt_packet(self, packet: bytes) -> Optional[Tuple[int, int, int, bytes]]:
        """
        Descriptografa um pacote RTP recebido no modo `rtpsize`.
        Retorna `(ssrc, sequence, timestamp, opus_payload)` ou `None` se for pacote RTCP/controle.
        """
        if len(packet) < 28 or not self.secret_key:
            return None

        first_byte = packet[0]
        payload_type = packet[1] & 0x7F
        # Filtra pacotes RTCP (200..206) ou pacotes de ping/descoberta
        if payload_type != 0x78:
            return None

        csrc_count = first_byte & 0x0F
        has_extension = bool(first_byte & 0x10)
        seq, ts, ssrc = struct.unpack_from(">HII", packet, 2)

        header_len = 12 + (csrc_count * 4)
        ext_len_words = 0
        if has_extension:
            if len(packet) < header_len + 4:
                return None
            _, ext_len_words = struct.unpack_from(">HH", packet, header_len)
            header_len += 4  # O preâmbulo de 4 bytes da extensão faz parte do cabeçalho claro (AAD)

        header = packet[:header_len]
        nonce_suffix = packet[-4:]
        ciphertext = packet[header_len:-4]

        try:
            if self.mode == "aead_aes256_gcm_rtpsize":
                from cryptography.hazmat.primitives.ciphers.aead import AESGCM

                nonce = bytearray(12)
                nonce[:4] = nonce_suffix
                plaintext = AESGCM(bytes(self.secret_key)).decrypt(
                    bytes(nonce), ciphertext, header
                )
            else:
                import nacl.bindings

                nonce = bytearray(24)
                nonce[:4] = nonce_suffix
                plaintext = nacl.bindings.crypto_aead_xchacha20poly1305_ietf_decrypt(
                    ciphertext,
                    header,
                    bytes(nonce),
                    bytes(self.secret_key),
                )
        except Exception:
            return None

        # Remove corpo da extensão RTP descriptografada, se presente
        if has_extension and ext_len_words > 0:
            ext_bytes = ext_len_words * 4
            if len(plaintext) <= ext_bytes:
                return None
            plaintext = plaintext[ext_bytes:]

        return ssrc, seq, ts, plaintext

    async def send_audio(self, opus_data: bytes) -> None:
        """Envia um quadro Opus criptografado pelo socket UDP."""
        if self._closed or not self.socket:
            return
        packet = self.create_packet(opus_data)
        try:
            await asyncio.get_running_loop().sock_sendall(self.socket, packet)
        except Exception as e:
            logger.error(f"Erro ao enviar pacote UDP de voz: {e}")

    def close(self) -> None:
        self._closed = True
        if self.socket:
            try:
                self.socket.close()
            except (asyncio.CancelledError, Exception):
                pass
            self.socket = None


class VoiceClient:
    """
    Cliente principal para gerenciamento de conexões de voz, reprodução de música e recepção de áudio.
    """

    def __init__(self, bot: Any, channel: Any):
        self.bot = bot
        self.channel = channel
        self.guild_id = str(channel.guild_id)
        self.token: Optional[str] = None
        self.session_id: Optional[str] = getattr(bot, "session_id", None)
        self.endpoint: Optional[str] = None

        self.ws: Optional[VoiceWebSocket] = None
        self.udp: Optional[UDPVoiceConnection] = None
        self.current_source: Optional[AudioSource] = None
        self.audio_task: Optional[asyncio.Task] = None
        self.receive_udp_task: Optional[asyncio.Task] = None
        self.connected: bool = False
        self.speaking: bool = False
        self.volume: float = 1.0
        self._encoder: Optional[OpusEncoder] = None
        self._decoders: Dict[int, OpusDecoder] = {}
        self._after_callback: Optional[Callable[[Optional[Exception]], Any]] = None
        self._audio_listeners: List[Callable[[int, Optional[str], bytes], Any]] = []

    def _get_encoder(self) -> Optional[OpusEncoder]:
        if self._encoder is None and _OPUS_LIB is not None:
            try:
                self._encoder = OpusEncoder()
            except Exception as e:
                logger.warning(f"OpusEncoder via ctypes indisponível ({e}); usando FFmpeg Opus.")
        return self._encoder

    async def connect(self, self_mute: bool = False, self_deaf: bool = False) -> "VoiceClient":
        """Estabelece a conexão completa com o canal de voz (Gateway + Voice WS v8 + UDP AEAD)."""
        try:
            state_task = asyncio.create_task(self._wait_for_voice_state())
            server_task = asyncio.create_task(self._wait_for_voice_server())

            await self._update_voice_state(self.channel.id, self_mute=self_mute, self_deaf=self_deaf)

            await asyncio.gather(state_task, server_task)

            if not self.endpoint or not self.token or not self.session_id:
                raise VoiceConnectionError(
                    "Dados de handshake de voz incompletos (endpoint/token/session_id)."
                )

            self.ws = VoiceWebSocket(self)
            await self.ws.connect(self.endpoint)

            self.udp = UDPVoiceConnection(self)
            ip, port = await self.udp.connect(self.ws.ip, self.ws.port, self.ws.ssrc)  # type: ignore[arg-type]

            selected_mode = self.udp.choose_encryption_mode(self.ws.modes)
            self.udp.mode = selected_mode

            await self.ws.select_protocol(ip, port, selected_mode)
            if not self.ws.secret_key:
                raise VoiceConnectionError("Chave secreta (secret_key) não recebida na Session Description.")

            self.udp.secret_key = bytes(self.ws.secret_key)
            self.connected = True

            if hasattr(self.bot, "voice_clients") and isinstance(self.bot.voice_clients, dict):
                self.bot.voice_clients[self.guild_id] = self

            logger.info(
                f"Conectado ao canal de voz '{getattr(self.channel, 'name', self.channel.id)}' "
                f"(modo={selected_mode})"
            )
            return self

        except Exception as e:
            logger.error(f"Falha ao conectar ao canal de voz: {e}")
            await self.disconnect()
            raise

    async def disconnect(self) -> None:
        """Desconecta do canal de voz e limpa subprocessos e sockets."""
        self.connected = False

        await self.stop()
        await self.stop_listening()

        if self._encoder:
            self._encoder.destroy()
            self._encoder = None

        for dec in self._decoders.values():
            dec.destroy()
        self._decoders.clear()

        if self.udp:
            self.udp.close()
            self.udp = None

        if self.ws:
            await self.ws.close()
            self.ws = None

        await self._update_voice_state(None)

        if hasattr(self.bot, "voice_clients") and isinstance(self.bot.voice_clients, dict):
            self.bot.voice_clients.pop(self.guild_id, None)

        logger.info(f"Desconectado do canal de voz no servidor {self.guild_id}")

    async def _update_voice_state(
        self,
        channel_id: Optional[str],
        self_mute: bool = False,
        self_deaf: bool = False,
    ) -> None:
        payload = {
            "op": 4,
            "d": {
                "guild_id": str(self.guild_id),
                "channel_id": str(channel_id) if channel_id else None,
                "self_mute": bool(self_mute),
                "self_deaf": bool(self_deaf),
            },
        }
        if getattr(self.bot, "_ws", None) and not self.bot._ws.closed:
            await self.bot._ws.send_json(payload)

    async def _wait_for_voice_state(self) -> None:
        def check(event: Dict[str, Any]) -> bool:
            if event.get("t") != "VOICE_STATE_UPDATE":
                return False
            d = event.get("d") or {}
            return (
                str(d.get("guild_id")) == str(self.guild_id)
                and str(d.get("user_id")) == str(self.bot.application_id)
            )

        try:
            event = await self.bot.wait_for("VOICE_STATE_UPDATE", check=check, timeout=15.0)
            if event and "session_id" in event.get("d", {}):
                self.session_id = event["d"]["session_id"]
        except asyncio.TimeoutError:
            if not self.session_id:
                raise VoiceConnectionError("Timeout aguardando VOICE_STATE_UPDATE do Gateway.")

    async def _wait_for_voice_server(self) -> None:
        def check(event: Dict[str, Any]) -> bool:
            return (
                event.get("t") == "VOICE_SERVER_UPDATE"
                and str(event.get("d", {}).get("guild_id")) == str(self.guild_id)
            )

        event = await self.bot.wait_for("VOICE_SERVER_UPDATE", check=check, timeout=20.0)
        if not event or not event.get("d", {}).get("endpoint"):
            raise VoiceConnectionError("Timeout aguardando VOICE_SERVER_UPDATE do Gateway.")

        self.token = event["d"]["token"]
        self.endpoint = event["d"]["endpoint"]

    async def play(
        self,
        source: Union[str, AudioSource, bytes],
        *,
        after: Optional[Callable[[Optional[Exception]], Any]] = None,
        **kwargs: Any,
    ) -> None:
        """Inicia a reprodução de uma fonte de áudio (URL, arquivo, bytes PCM ou AudioSource)."""
        if self.audio_task and not self.audio_task.done():
            await self.stop()

        self._after_callback = after

        if isinstance(source, str):
            audio_source: AudioSource = FFmpegAudioSource(source, volume=self.volume, **kwargs)
            await audio_source.create_process()
            self.current_source = audio_source
        elif isinstance(source, bytes):
            self.current_source = PCMAudioSource(source, volume=self.volume)
        else:
            self.current_source = source
            if hasattr(self.current_source, "volume"):
                self.current_source.volume = self.volume
            if isinstance(self.current_source, FFmpegAudioSource) and self.current_source.process is None:
                await self.current_source.create_process()

        if self.ws:
            await self.ws.set_speaking(True)
        self.speaking = True
        self.audio_task = asyncio.create_task(self._audio_player())

    async def _audio_player(self) -> None:
        """Loop de transmissão de áudio com temporização precisa de 20ms (compensação de drift)."""
        player_error: Optional[Exception] = None
        encoder = self._get_encoder()
        frame_duration = FRAME_LENGTH_MS / 1000.0  # 0.02s
        next_time = time.perf_counter()

        try:
            while self.current_source and self.connected:
                if self.current_source.paused:
                    await asyncio.sleep(0.05)
                    next_time = time.perf_counter()
                    continue

                data = await self.current_source.read()
                if not data:
                    break

                if self.current_source.is_opus():
                    opus_packet = data
                elif encoder is not None:
                    opus_packet = encoder.encode(data, SAMPLES_PER_FRAME)
                else:
                    raise OpusError("Fonte PCM requer libopus instalada ou FFmpeg em modo Opus.")

                if self.udp:
                    await self.udp.send_audio(opus_packet)

                next_time += frame_duration
                delay = max(0.0, next_time - time.perf_counter())
                await asyncio.sleep(delay)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            player_error = e
            logger.error(f"Erro no reprodutor de áudio: {e}")
        finally:
            await self._on_track_end(player_error)

    async def _send_silence_frames(self, count: int = 5) -> None:
        """Envia 5 quadros de silêncio Opus (0xF8, 0xFF, 0xFE) conforme especificação do Discord."""
        if not self.udp or not self.connected:
            return
        for _ in range(count):
            await self.udp.send_audio(OPUS_SILENCE_FRAME)
            await asyncio.sleep(0.02)

    async def _on_track_end(self, error: Optional[Exception] = None) -> None:
        if self.speaking and self.ws:
            await self._send_silence_frames()
            await self.ws.set_speaking(False)
            self.speaking = False

        if self.current_source:
            await self.current_source.cleanup()
            self.current_source = None

        cb = self._after_callback
        self._after_callback = None
        if cb:
            try:
                res = cb(error)
                if asyncio.iscoroutine(res):
                    await res
            except Exception as e:
                logger.error(f"Erro no callback 'after' do VoiceClient: {e}")

    async def stop(self) -> None:
        """Interrompe a reprodução atual imediatamente."""
        self._after_callback = None
        if self.audio_task:
            self.audio_task.cancel()
            try:
                await self.audio_task
            except (asyncio.CancelledError, Exception):
                pass
            self.audio_task = None

        if self.speaking and self.ws:
            await self._send_silence_frames()
            await self.ws.set_speaking(False)
            self.speaking = False

        if self.current_source:
            await self.current_source.cleanup()
            self.current_source = None

    async def pause(self) -> None:
        """Pausa a reprodução atual."""
        if self.current_source and not self.current_source.paused:
            self.current_source.paused = True
            await self._send_silence_frames()
            if self.ws:
                await self.ws.set_speaking(False)
            self.speaking = False

    async def resume(self) -> None:
        """Retoma a reprodução pausada."""
        if self.current_source and self.current_source.paused:
            self.current_source.paused = False
            if self.ws:
                await self.ws.set_speaking(True)
            self.speaking = True

    def set_volume(self, volume: float) -> None:
        """Ajusta o volume (0.0 a 2.0) em tempo real."""
        self.volume = max(0.0, min(2.0, float(volume)))
        if self.current_source:
            self.current_source.volume = self.volume

    # ==================== RECEPÇÃO DE VOZ & BRIDGE ====================

    def add_audio_listener(self, callback: Callable[[int, Optional[str], bytes], Any]) -> None:
        """
        Registra um callback `(ssrc, user_id, opus_frame)` chamado a cada pacote de voz recebido.
        """
        self._audio_listeners.append(callback)
        if self.receive_udp_task is None or self.receive_udp_task.done():
            self.receive_udp_task = asyncio.create_task(self._udp_receive_loop())

    async def stop_listening(self) -> None:
        """Interrompe a escuta de pacotes UDP de entrada."""
        self._audio_listeners.clear()
        if self.receive_udp_task:
            self.receive_udp_task.cancel()
            try:
                await self.receive_udp_task
            except (asyncio.CancelledError, Exception):
                pass
            self.receive_udp_task = None

    async def _udp_receive_loop(self) -> None:
        """Recebe e descriptografa pacotes RTP de voz vindos do canal."""
        loop = asyncio.get_running_loop()
        while self.connected and self.udp and self.udp.socket and self._audio_listeners:
            try:
                raw_packet = await loop.sock_recv(self.udp.socket, 4096)
                if not raw_packet:
                    continue
                parsed = self.udp.decrypt_packet(raw_packet)
                if not parsed:
                    continue
                ssrc, _seq, _ts, opus_payload = parsed
                if opus_payload == OPUS_SILENCE_FRAME:
                    continue
                user_id = self.ws.ssrc_user_map.get(ssrc) if self.ws else None
                for listener in list(self._audio_listeners):
                    res = listener(ssrc, user_id, opus_payload)
                    if asyncio.iscoroutine(res):
                        asyncio.create_task(res)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug(f"Erro na recepção UDP de voz: {e}")
                await asyncio.sleep(0.01)

    def is_connected(self) -> bool:
        return bool(
            self.connected
            and self.ws is not None
            and self.ws.ws is not None
            and not self.ws.ws.closed
            and not self.ws._closed
        )

    def is_playing(self) -> bool:
        return bool(
            self.audio_task is not None
            and not self.audio_task.done()
            and self.current_source is not None
            and not self.current_source.paused
        )

    def is_paused(self) -> bool:
        return bool(self.current_source is not None and self.current_source.paused)
