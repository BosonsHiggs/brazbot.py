"""
Sistema de cache em memória com expiração por TTL (Time-To-Live) e limite opcional de entradas.
"""

import time
from typing import Any, Dict, Optional, List


class Cache:
    """
    Gerenciador de cache em memória com suporte a TTL (em segundos) e limpeza automática.
    Compatível tanto com `ttl=` quanto com `seconds=`.
    """

    def __init__(self, default_ttl: float = 300.0, max_size: int = 10000):
        self.default_ttl = float(default_ttl)
        self.max_size = max_size
        self.cache: Dict[str, Any] = {}
        self.expiry_times: Dict[str, float] = {}

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[float] = None,
        seconds: Optional[float] = None,
    ) -> None:
        """Armazena um valor no cache com tempo de expiração em segundos."""
        if len(self.cache) >= self.max_size and key not in self.cache:
            self.cleanup()
            if len(self.cache) >= self.max_size:
                oldest_key = min(self.expiry_times, key=self.expiry_times.get)  # type: ignore[arg-type]
                self.delete(oldest_key)

        effective_ttl = ttl if ttl is not None else (seconds if seconds is not None else self.default_ttl)
        self.cache[key] = value
        self.expiry_times[key] = time.time() + float(effective_ttl)

    def get(self, key: str, default: Any = None) -> Any:
        """Obtém um valor do cache se existir e não estiver expirado."""
        if key in self.cache:
            if time.time() < self.expiry_times.get(key, 0):
                return self.cache[key]
            self.delete(key)
        return default

    def get_remaining_ttl(self, key: str) -> float:
        """Retorna o tempo restante (em segundos) para a chave expirar, ou 0.0."""
        if key in self.cache:
            rem = self.expiry_times.get(key, 0) - time.time()
            if rem > 0:
                return rem
            self.delete(key)
        return 0.0

    def update(self, key: str, value: Any) -> bool:
        """Atualiza o valor de uma chave existente mantendo seu TTL atual."""
        if key in self.cache and time.time() < self.expiry_times.get(key, 0):
            self.cache[key] = value
            return True
        return False

    def delete(self, key: str) -> None:
        """Remove uma chave do cache."""
        self.cache.pop(key, None)
        self.expiry_times.pop(key, None)

    def clear(self) -> None:
        """Limpa todo o cache."""
        self.cache.clear()
        self.expiry_times.clear()

    def cleanup(self) -> int:
        """Remove todas as entradas expiradas e retorna a quantidade removida."""
        now = time.time()
        expired_keys: List[str] = [
            k for k, exp in list(self.expiry_times.items()) if exp <= now
        ]
        for k in expired_keys:
            self.delete(k)
        return len(expired_keys)

    def __contains__(self, key: str) -> bool:
        return self.get(key) is not None

    def __len__(self) -> int:
        self.cleanup()
        return len(self.cache)
