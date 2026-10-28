"""
Funções utilitárias para criação rápida de Embeds, IDs únicos, formatação de tempo e paginação.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Generator, Iterable, List, Optional


def create_embed(
    title: str,
    description: str,
    color: int = 0x5865F2,
    footer: Optional[str] = None,
    thumbnail: Optional[str] = None,
) -> Dict[str, Any]:
    """Cria um dicionário de embed pronto para envio na API do Discord."""
    embed: Dict[str, Any] = {
        "title": title,
        "description": description,
        "color": color,
    }
    if footer:
        embed["footer"] = {"text": footer}
    if thumbnail:
        embed["thumbnail"] = {"url": thumbnail}
    return embed


def format_command_response(response_text: str, is_error: bool = False) -> Dict[str, Any]:
    """Formata uma resposta de comando como embed de sucesso (verde) ou erro (vermelho)."""
    color = 0xED4245 if is_error else 0x57F287
    return create_embed("Resposta do Comando", str(response_text), color)


def create_error_embed(error_message: str, title: str = "❌ Erro") -> Dict[str, Any]:
    """Cria um embed padronizado de erro."""
    return {
        "title": title,
        "description": str(error_message),
        "color": 0xED4245,
    }


def create_success_embed(message: str, title: str = "✅ Sucesso") -> Dict[str, Any]:
    """Cria um embed padronizado de sucesso."""
    return {
        "title": title,
        "description": str(message),
        "color": 0x57F287,
    }


def generate_unique_id(max_length: int = 8) -> int:
    """Gera um ID inteiro pseudoaleatório único com base em UUID4."""
    unique_id = uuid.uuid4()
    shortened_hex = unique_id.hex[: max(1, min(32, max_length))]
    return int(shortened_hex, 16)


def generate_list(items: Optional[Iterable[Any]] = None) -> Generator[Any, None, None]:
    """Gerador simples sobre uma coleção de itens."""
    if items:
        for item in items:
            yield item


def format_discord_timestamp(dt: Optional[datetime] = None, style: str = "R") -> str:
    """
    Formata um `datetime` na sintaxe nativa de timestamp do Discord (`<t:UNIX:STYLE>`).
    Estilos: 't' (hora curta), 'T' (hora longa), 'd' (data curta), 'D' (data longa),
    'f' (data/hora curta), 'F' (data/hora longa), 'R' (relativo).
    """
    if dt is None:
        dt = datetime.now(timezone.utc)
    return f"<t:{int(dt.timestamp())}:{style}>"


def chunk_list(items: List[Any], chunk_size: int = 10) -> List[List[Any]]:
    """Divide uma lista em páginas/blocos de tamanho `chunk_size`."""
    return [items[i : i + chunk_size] for i in range(0, len(items), max(1, chunk_size))]
