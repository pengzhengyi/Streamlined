from typing import Any, List, Tuple

from ..common import Predicate, Transform


class Simplification:
    """Reduce multiple config formats to more standard formats."""

    simplifications: List[Tuple[Predicate, Transform]]

    def _init_simplifications(self) -> None:
        self.simplifications = []

    def simplify(self, value: Any):
        for predicate, transform in self.simplifications:
            if predicate(value):
                return self.simplify(transform(value))

        return value
