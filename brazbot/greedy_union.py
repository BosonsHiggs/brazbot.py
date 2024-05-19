from typing import TypeVar, Generic, List

T = TypeVar('T')

class Greedy(Generic[T]):
    def __init__(self, values: List[T]):
        self.values = values

    def __iter__(self):
        return iter(self.values)

    def __repr__(self):
        return f"Greedy({self.values})"
