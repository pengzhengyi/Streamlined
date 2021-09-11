from __future__ import annotations

import argparse
from typing import Any, List, Optional


class ArgumentParser(argparse.ArgumentParser):
    """
    Same as [argparse.ArgumentParser](https://docs.python.org/3/library/argparse.html#argumentparser-objects) except with one enhanced functionality to add dynamic definition of an argument and parse its value in one invocation.
    """

    def __init__(self, *args: Any, add_help: bool = False, **kwargs: Any):
        super().__init__(*args, add_help=add_help, **kwargs)

    def parse_argument(self, *_args: Any, args: Optional[List[str]] = None, **kwargs: Any) -> Any:
        """
        This method is combination of [add_argument](https://docs.python.org/3/library/argparse.html#argparse.ArgumentParser.add_argument) and [parse_args](https://docs.python.org/3/library/argparse.html#argparse.ArgumentParser.parse_args).

        In short, it allows one argument definition to be added
        (through parameters for `add_arguments`) and then parsed argument
        value immediately interpreted against the provided `args` keyword
        argument (same as the `args` parameter for `parse_args`)

        >>> parser = ArgumentParser()
        >>> parser.parse_argument('foo', type=int, args=['123'])
        123
        """
        argument_definition = self.add_argument(*_args, **kwargs)
        namespace = self.parse_known_args(args)[0]
        return getattr(namespace, argument_definition.dest)

    def parse_help_argument(self, args: Optional[List[str]] = None) -> None:
        """
        Since this ArgumentParser allows argument to be defined incrementally
        with `parse_argument`, print help is disabled by default to avoid
        printing an incomplete usage.

        If displaying help message is desired, after adding all dynamic
        argument definition, this method can be called to add back help option.

        In other words, if `-h` is present in args, if will be captured in
        invocation to this method and cause a help message to be printed.
        """
        self.add_argument("-h", "--help", action="help", help="show this help message and exit")
        self.parse_known_args(args)


if __name__ == "__main__":
    import doctest

    doctest.testmod()
