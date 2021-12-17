from functools import cached_property
from operator import methodcaller
from typing import Any

from ..common import IS_DICT, TAUTOLOGY
from ..parsing import Parser as AbstractParser


class Parser(AbstractParser):
    """
    Parser initializes itself by parsing the provided argument at initialization.

    During parsing, it will treat the value as a Dictionary and parse the property
    under a key same as the class name.

    The exact action for handling parsed value should be in `_do_parse`.

    Standardization of data format should be specified in `_init_simplifications`.
    """

    @cached_property
    def name(self) -> str:
        return self.__class__.__name__.lower()

    def __init__(self, value) -> None:
        super().__init__()
        self._init_simplifications()
        self.parse(value)

    def parse(self, value: Any) -> Any:
        if IS_DICT(value):
            value = value.get(self.name, None)
            return super().parse(value)
        else:
            raise TypeError(f"Expect {value} to be a Dictionary")
