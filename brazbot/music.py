"""
Motor completo de Música e Extração de Áudio (`yt-dlp`) nativo da biblioteca brazbot.py.
Suporta:
- Extração assíncrona via `yt-dlp` (YouTube, Playlists, SoundCloud, Twitch, links diretos HTTP)
- Busca inteligente por nome (`ytsearch:`)
- Fila de reprodução por servidor (GuildMusicPlayer), Loop (off, track, queue), Histórico, Shuffle, Move, Remove, SkipTo
- Controle real de Volume (0% a 200%), Seek (avançar/retroceder para posição em segundos) e Filtros de Áudio FFmpeg
  (bassboost, nightcore, vaporwave, 8d, treble, karaoke, normal)
"""

import asyncio
import os
import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from brazbot.errors import VoiceConnectionError
from brazbot.voiceclient import FFmpegAudioSource, VoiceClient

# Presets de filtros de áudio FFmpeg para comandos de música
AUDIO_FILTERS: Dict[str, Optional[str]] = {
    "off": None,
    "normal": None,
    "bassboost": "bass=g=12:f=110:w=0.6",
    "nightcore": "aresample=48000,asetrate=48000*1.25",
    "vaporwave": "aresample=48000,asetrate=48000*0.8",
    "8d": "apulsator=hz=0.125",
    "treble": "treble=g=8",
    "karaoke": "stereotools=mlev=0.03",
    "echo": "aecho=0.8:0.88:60:0.4",
}

YTDL_DEFAULT_OPTIONS: Dict[str, Any] = {
    "format": "bestaudio/best",
    "noplaylist": False,
    "nocheckcertificate": True,
    "ignoreerrors": False,
    "logtostderr": False,
    "quiet": True,
    "no_warnings": True,
    "default_search": "ytsearch",
    "source_address": "0.0.0.0",
    "extract_flat": False,
}


@dataclass
class Track:
    """Representa uma faixa de áudio na fila ou em reprodução."""

    title: str
    url: str  # URL original ou página
    stream_url: str  # URL direta da stream de áudio para o FFmpeg
    requester: str = "Unknown"
    duration: int = 0  # Duração em segundos (0 = desconhecida/live)
    thumbnail: Optional[str] = None
    uploader: Optional[str] = None
    is_live: bool = False
    started_at: Optional[str] = None
    seek_offset: float = 0.0
    audio_filter: str = "off"
    source: Optional[FFmpegAudioSource] = field(default=None, repr=False)

    @property
    def formatted_duration(self) -> str:
        if self.is_live:
            return "🔴 AO VIVO"
        if not self.duration or self.duration <= 0:
            return "Desconhecida"
        mins, secs = divmod(int(self.duration), 60)
        hours, mins = divmod(mins, 60)
        if hours > 0:
            return f"{hours}:{mins:02d}:{secs:02d}"
        return f"{mins}:{secs:02d}"

    @property
    def elapsed_seconds(self) -> float:
        if self.source:
            return self.seek_offset + self.source.elapsed_seconds
        if self.started_at:
            delta = datetime.now() - datetime.fromisoformat(self.started_at)
            return self.seek_offset + delta.total_seconds()
        return self.seek_offset

    def progress_bar(self, length: int = 16) -> str:
        elapsed = int(self.elapsed_seconds)
        e_min, e_sec = divmod(elapsed, 60)
        elapsed_str = f"{e_min}:{e_sec:02d}"
        if not self.duration or self.duration <= 0:
            return f"`▶ {elapsed_str}`"
        ratio = min(1.0, max(0.0, elapsed / float(self.duration)))
        pos = int(ratio * length)
        bar = "▬" * pos + "🔘" + "▬" * max(0, length - pos - 1)
        return f"`{elapsed_str}` {bar} `{self.formatted_duration}`"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "stream_url": self.stream_url,
            "requester": self.requester,
            "duration": self.duration,
            "thumbnail": self.thumbnail,
            "uploader": self.uploader,
            "is_live": self.is_live,
            "started_at": self.started_at,
            "audio_filter": self.audio_filter,
        }


class YTDLSource:
    """
    Extrator assíncrono de faixas e pesquisas usando a última versão do `yt-dlp`.
    Também suporta links diretos para arquivos de áudio (.mp3, .wav, .ogg, .flac, .m4a).
    """

    DIRECT_EXTENSIONS = (".mp3", ".wav", ".ogg", ".flac", ".m4a", ".opus", ".webm", ".aac")

    @classmethod
    def _is_direct_audio_url(cls, query: str) -> bool:
        if not query.startswith(("http://", "https://")):
            return False
        path = query.split("?")[0].lower()
        return path.endswith(cls.DIRECT_EXTENSIONS)

    @classmethod
    async def extract_tracks(
        cls,
        query: str,
        requester: str = "Unknown",
        max_playlist_items: int = 50,
    ) -> List[Track]:
        """
        Extrai uma ou mais faixas a partir de uma URL (YouTube, Playlist, SoundCloud, link direto)
        ou termo de busca textual.
        """
        query = query.strip()

        # Se for arquivo local existente ou link direto de áudio (.mp3, .wav, etc.)
        if os.path.isfile(query) or cls._is_direct_audio_url(query):
            base = os.path.basename(query.split("?")[0]) or "Audio Track"
            for ext in cls.DIRECT_EXTENSIONS:
                if base.lower().endswith(ext):
                    base = base[: -len(ext)]
                    break
            return [
                Track(
                    title=base,
                    url=query,
                    stream_url=query,
                    requester=requester,
                )
            ]

        try:
            import yt_dlp
        except ImportError:
            # Fallback caso yt-dlp não esteja instalado e seja uma URL direta
            if query.startswith(("http://", "https://")):
                title = os.path.basename(query.split("?")[0]) or query
                return [Track(title=title, url=query, stream_url=query, requester=requester)]
            raise VoiceConnectionError(
                "O pacote 'yt-dlp' é necessário para pesquisar ou reproduzir links do YouTube. "
                "Instale com: pip install -U yt-dlp"
            )

        opts = dict(YTDL_DEFAULT_OPTIONS)
        opts["playlistend"] = max_playlist_items
        search_target = query if query.startswith(("http://", "https://")) else f"ytsearch1:{query}"

        def _extract() -> Dict[str, Any]:
            with yt_dlp.YoutubeDL(opts) as ydl:
                return ydl.extract_info(search_target, download=False)

        info = await asyncio.to_thread(_extract)
        if not info:
            return []

        entries = info.get("entries") if "entries" in info else [info]
        tracks: List[Track] = []
        for entry in entries:
            if not entry:
                continue
            stream_url = entry.get("url") or entry.get("webpage_url") or query
            webpage_url = entry.get("webpage_url") or entry.get("original_url") or query
            title = entry.get("title") or "Faixa Desconhecida"
            duration = int(entry.get("duration") or 0)
            thumbnail = entry.get("thumbnail")
            uploader = entry.get("uploader") or entry.get("channel")
            is_live = bool(entry.get("is_live", False))
            tracks.append(
                Track(
                    title=title,
                    url=webpage_url,
                    stream_url=stream_url,
                    requester=requester,
                    duration=duration,
                    thumbnail=thumbnail,
                    uploader=uploader,
                    is_live=is_live,
                )
            )
        return tracks

    @classmethod
    async def search(cls, query: str, limit: int = 5, requester: str = "Unknown") -> List[Track]:
        """Pesquisa até `limit` resultados no YouTube para seleção ou autocomplete."""
        try:
            import yt_dlp
        except ImportError:
            return []

        opts = dict(YTDL_DEFAULT_OPTIONS)
        opts["noplaylist"] = True

        def _search() -> Dict[str, Any]:
            with yt_dlp.YoutubeDL(opts) as ydl:
                return ydl.extract_info(f"ytsearch{limit}:{query}", download=False)

        info = await asyncio.to_thread(_search)
        if not info or "entries" not in info:
            return []

        results: List[Track] = []
        for entry in info["entries"]:
            if not entry:
                continue
            results.append(
                Track(
                    title=entry.get("title") or "Sem título",
                    url=entry.get("webpage_url") or entry.get("url") or "",
                    stream_url=entry.get("url") or "",
                    requester=requester,
                    duration=int(entry.get("duration") or 0),
                    thumbnail=entry.get("thumbnail"),
                    uploader=entry.get("uploader"),
                    is_live=bool(entry.get("is_live", False)),
                )
            )
        return results


class GuildMusicPlayer:
    """
    Controlador de fila e reprodução de música para um servidor (Guild) específico.
    """

    def __init__(self, bot: Any, guild_id: str):
        self.bot = bot
        self.guild_id = str(guild_id)
        self.queue: List[Track] = []
        self.history: List[Track] = []
        self.current: Optional[Track] = None
        self.loop_mode: str = "off"  # "off", "track", "queue"
        self.volume: float = 1.0
        self.audio_filter: str = "off"
        self.text_channel_id: Optional[str] = None
        self.now_playing_message_id: Optional[str] = None
        self.on_track_start: Optional[Callable[[Track], Awaitable[None]]] = None

    @property
    def voice_client(self) -> Optional[VoiceClient]:
        if hasattr(self.bot, "voice_clients") and isinstance(self.bot.voice_clients, dict):
            return self.bot.voice_clients.get(self.guild_id)
        return None

    async def enqueue(
        self,
        query: str,
        requester: str = "Unknown",
        title: Optional[str] = None,
    ) -> List[Track]:
        """Extrai e adiciona uma ou mais faixas à fila; inicia a reprodução se ocioso."""
        tracks = await YTDLSource.extract_tracks(query, requester=requester)
        if title and len(tracks) == 1:
            tracks[0].title = title

        self.queue.extend(tracks)
        vc = self.voice_client
        if vc and vc.is_connected() and not vc.is_playing() and not vc.is_paused():
            await self.play_next()
        return tracks

    async def play_next(self, error: Optional[Exception] = None) -> Optional[Track]:
        """Avança para a próxima faixa respeitando o modo de loop."""
        if self.current:
            if self.loop_mode == "track":
                self.queue.insert(0, self.current)
            elif self.loop_mode == "queue":
                self.queue.append(self.current)

        if not self.queue:
            self.current = None
            return None

        next_track = self.queue.pop(0)
        next_track.started_at = datetime.now().isoformat()
        next_track.seek_offset = 0.0
        next_track.audio_filter = self.audio_filter

        # Se a stream_url expirou ou estava vazia, re-extrai
        if not next_track.stream_url or next_track.stream_url == next_track.url:
            if not YTDLSource._is_direct_audio_url(next_track.url) and not os.path.isfile(next_track.url):
                try:
                    refreshed = await YTDLSource.extract_tracks(
                        next_track.url, requester=next_track.requester, max_playlist_items=1
                    )
                    if refreshed:
                        next_track.stream_url = refreshed[0].stream_url
                except Exception:
                    pass

        self.current = next_track
        self.history.append(next_track)
        if len(self.history) > 50:
            self.history = self.history[-50:]

        vc = self.voice_client
        if vc and vc.is_connected():
            await self._start_track_source(vc, next_track, seek_seconds=0.0)
            if self.on_track_start:
                await self.on_track_start(next_track)
            return next_track
        return None

    async def _start_track_source(
        self,
        vc: VoiceClient,
        track: Track,
        seek_seconds: float = 0.0,
    ) -> None:
        filter_expr = AUDIO_FILTERS.get(self.audio_filter)
        source = FFmpegAudioSource(
            track.stream_url,
            volume=self.volume,
            seek_seconds=seek_seconds,
            audio_filter=filter_expr,
        )
        await source.create_process()
        track.source = source
        track.seek_offset = seek_seconds

        def _after_cb(err: Optional[Exception]) -> None:
            if self.current is track:
                asyncio.run_coroutine_threadsafe(self.play_next(err), asyncio.get_running_loop())

        await vc.play(source, after=_after_cb)

    async def seek(self, position_seconds: float) -> bool:
        """Reposiciona a reprodução da faixa atual para `position_seconds`."""
        vc = self.voice_client
        if not vc or not vc.is_connected() or not self.current:
            return False
        track = self.current
        # Evita disparar play_next durante o restart do seek
        vc._after_callback = None
        await vc.stop()
        self.current = track
        await self._start_track_source(vc, track, seek_seconds=max(0.0, float(position_seconds)))
        return True

    async def set_filter(self, filter_name: str) -> bool:
        """Aplica um filtro de áudio FFmpeg em tempo real."""
        key = filter_name.lower().strip()
        if key not in AUDIO_FILTERS:
            return False
        self.audio_filter = key
        if self.current and self.voice_client and self.voice_client.is_playing():
            await self.seek(self.current.elapsed_seconds)
        return True

    def set_volume(self, volume: float) -> bool:
        if 0.0 <= volume <= 2.0:
            self.volume = float(volume)
            if self.voice_client:
                self.voice_client.set_volume(self.volume)
            return True
        return False

    def shuffle(self) -> int:
        if len(self.queue) > 1:
            random.shuffle(self.queue)
        return len(self.queue)
