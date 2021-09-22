from __future__ import annotations

from dataclasses import _MISSING_TYPE, Field, InitVar
from typing import Any, ClassVar, Dict, List, Optional, Union, get_origin

from .argument_parser import ArgumentParser
from .configuration_loader import ConfigurationLoader


class ArgumentLoader(ConfigurationLoader):
    """
    ArgumentParser can be seen as a mixin trait to be applied to a dataclass
    so that both an argument parser can be created based off defined fields
    and an instance of dataclass can be initialized based off parsed arguments.

    This class should not be instantiated directly, rather user should
    create a derived dataclass class with proper data fields.

    For example:

    ```Python
    @dataclass
    class DatabaseConfig(ArgumentLoader):
        username: str = field(
            metadata={"name": ["-u", "--username"], "help": "supply username", "default": "admin"}
        )
        password: str = field(
            metadata={"name": ["-p"], "help": "supply password", "dest": "password"}
        )
        database: InitVar[str] = field(
            metadata={"help": "supply value for database", "choices": ["mysql", "sqlite", "mongodb"]}
        )

        def __post_init__(self, database):
            pass
    ```

    After invoking `DatabaseConfig.from_arguments(<args>)`, an instance of
    DatabaseConfig will be created with all values loaded based on parsed arguments.
    """

    @staticmethod
    def _add_field_to_argument_parser(field: Field, argument_parser: ArgumentParser) -> None:
        name_or_flags: Union[str, List[str]] = field.metadata.get(
            "name", field.metadata.get("flags", field.metadata.get("name_or_flags", field.name))
        )
        if isinstance(name_or_flags, str):
            name_or_flags = [name_or_flags]

        kwarg_names = [
            "action",
            "nargs",
            "const",
            "choices",
            "required",
            "help",
            "metavar",
            "dest",
        ]
        kwargs: Dict[str, Any] = {
            kwarg_name: field.metadata.get(kwarg_name)
            for kwarg_name in kwarg_names
            if kwarg_name in field.metadata
        }
        kwargs["type"] = field.metadata.get(
            "type", field.type.type if isinstance(field.type, InitVar) else field.type
        )

        if "default" in field.metadata:
            kwargs["default"] = field.metadata.get("default")
        elif not isinstance(field.default, _MISSING_TYPE):
            kwargs["default"] = field.default
        elif not isinstance(field.default_factory, _MISSING_TYPE):
            kwargs["default"] = field.default_factory()

        argument_parser.add_argument(*name_or_flags, **kwargs)

    @classmethod
    def _is_annotation_classvar(cls, fieldname: str) -> bool:
        return get_origin(cls.__annotations__[fieldname]) is ClassVar

    @classmethod
    def parse_args(
        cls, argument_parser: ArgumentParser, args: Optional[List[str]] = None
    ) -> ArgumentLoader:
        """
        Call `parse_args` on the specified `argument_parser` with provided `args`.
        Use the parsed arguments to create an instance of this class.
        """
        namespace = argument_parser.parse_args(args=args)
        return cls(**vars(namespace))

    @classmethod
    def create_argument_parser(cls, add_help: bool = True, **kwargs: Any) -> ArgumentParser:
        """
        Create an argument parser based on the fields defined in this dataclass.

        InitVar will be added as argument while ClassVar will be ignored.

        For example, this example argument parser in argparse

        ```Python
        parser = argparse.ArgumentParser(description='Process some integers.')
        parser.add_argument('integers', metavar='N', type=int, nargs='+',
                            help='an integer for the accumulator')
        parser.add_argument('--sum', dest='accumulate', action='store_const',
                            const=sum, default=max,
                            help='sum the integers (default: find the max)')
        ```

        is roughly equivalent to

        ```Python
        @dataclass
        class IntegerProcessingArguments(ArgumentLoader):
            integers: int = field(metadata={'metavar': 'N', 'nargs': '+', 'help': 'an integer for the accumulator'})
            accumulate: Callable[..., int] = field(metadata={'name': '--sum', 'action': 'store_const', 'const': sum, 'default': max, 'help': 'sum the integers (default: find the max)'})


        IntegerProcessingArguments.create_argument_parser(description='Process some integers.')
        ```
        """
        argument_parser = ArgumentParser(add_help=add_help, **kwargs)

        for name, field in cls.__dataclass_fields__.items():
            if not cls._is_annotation_classvar(name):
                cls._add_field_to_argument_parser(field, argument_parser)

        return argument_parser

    @classmethod
    def from_arguments(cls, args: Optional[List[str]] = None, **kwargs: Any) -> ArgumentLoader:
        """
        Create an argument parser based on the defined fields in this dataclass
        and use this argument parser to parse args to initialize this dataclass.
        """
        argument_parser = cls.create_argument_parser(**kwargs)
        return cls.parse_args(argument_parser, args=args)
