from functools import cached_property
from operator import methodcaller

from ..common import TAUTOLOGY
from ..parsing import Parser as AbstractParser


class Parser(AbstractParser):
    @cached_property
    def name(self) -> str:
        return self.__class__.__name__.lower()

    def __init__(self) -> None:
        super().__init__()
        self._init_simplifications()

    def _init_simplifications(self) -> None:
        self.simplifications.insert(0, (TAUTOLOGY, methodcaller("get", self.name, None)))
