"""
Tipo genérico `Greedy[T]` para argumentos variáveis em comandos da biblioteca brazbot.py.
"""

from typing import Generic, Iterator, List, TypeVar

T = TypeVar("T")


class Greedy(Generic[T]):
    """Representa uma lista de argumentos consumidos de forma gulosa em comandos."""

    def __init__(self, values: List[T]):
        self.values = list(values)

    def __iter__(self) -> Iterator[T]:
        return iter(self.values)

    def __len__(self) -> int:
        return len(self.values)

    def __getitem__(self, idx: int) -> T:
        return self.values[idx]

    def __repr__(self) -> str:
        return f"Greedy({self.values})"
