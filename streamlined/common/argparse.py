import sys
from argparse import ArgumentParser
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Type, Union

from .dictionary import set_if_not_none
from .predicates import IS_STR


@dataclass
class ArgparseResult:
    name: str
    value: Any
    remaining_args: List[str]
    args: List[str]
    kwargs: Dict[str, Any]

    def add_argument(self, argument_parser: ArgumentParser) -> None:
        argument_parser.add_argument(*self.args, **self.kwargs)


def parse_known_args(
    name: Union[str, List[str]],
    action: Optional[str] = None,
    nargs: Optional[Union[str, int]] = None,
    const: Optional[Any] = None,
    default: Optional[Any] = None,
    type: Optional[Type] = str,
    choices: Optional[Iterable[Any]] = None,
    required: Optional[bool] = None,
    help: Optional[str] = None,
    metavar: Optional[str] = None,
    dest: Optional[str] = None,
    args: List[str] = sys.argv,
    add_help: bool = False,
) -> ArgparseResult:
    """
    Combine `add_argument` and `parse_known_args` from argparse.

    Parameters
    ------
    add_help: bool
        Whether help argument will be parsed. Default to False to
        avoid influencing causing system exit and interrupting
        partial parsing. This should be the expected argument.
    """
    kwargs: Dict[str, Any] = {}
    parser = ArgumentParser(add_help=add_help)
    if IS_STR(name):
        name = [name]

    set_if_not_none(kwargs, "action", action)
    set_if_not_none(kwargs, "nargs", nargs)
    set_if_not_none(kwargs, "const", const)
    set_if_not_none(kwargs, "default", default)
    set_if_not_none(kwargs, "type", type)
    set_if_not_none(kwargs, "choices", choices)
    set_if_not_none(kwargs, "required", required)
    set_if_not_none(kwargs, "help", help)
    set_if_not_none(kwargs, "metavar", metavar)
    set_if_not_none(kwargs, "dest", dest)

    parser.add_argument(*name, **kwargs)
    namespace, remaining_args = parser.parse_known_args(args)
    parsed = vars(namespace)
    argname, argvalue = parsed.popitem()
    return ArgparseResult(argname, argvalue, remaining_args, name, kwargs)
