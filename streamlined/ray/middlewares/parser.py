from __future__ import annotations

from functools import cached_property, partial
from typing import Any, Dict, List, Type

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
        self._init_from_parsed(self.parse(value))

    def _init_from_parsed(self, parsed: Dict):
        for name, value in parsed.items():
            setattr(self, f"_{name}", value)

    def parse(self, value: Any) -> Dict:
        if IS_DICT(value):
            value = value.get(self.name, None)
            return super().parse(value)
        else:
            raise TypeError(f"Expect {value} to be a Dictionary")


class NestedParser(Parser):
    subparsers: List[Type[Parser]]

    def __init__(self, value) -> None:
        self._init_subparsers()
        super().__init__(value)

    def _init_subparsers(self) -> None:
        self.subparsers = []

    def _do_parse(self, value: Any) -> Dict[str, Any]:
        parsed = dict()

        for subparser_class in self.subparsers:
            subparser = subparser_class(value)

            parsed.update(subparser.parse(value))

        return parsed
