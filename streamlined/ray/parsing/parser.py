from typing import Any, Dict

from .simplification import Simplification


class Parser(Simplification):
    """
    Represents abstract parsing of config.
    """

    def parse(self, value: Any) -> Dict:
        simplified_value = self.simplify(value)
        return self._do_parse(simplified_value)

    def _do_parse(self, value: Any) -> Dict:
        raise NotImplementedError()
