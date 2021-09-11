from __future__ import annotations

import re
from configparser import ExtendedInterpolation
from re import Pattern
from typing import Any, ClassVar, Dict

from .configuration_parser import ConfigurationParser


class ConfigurationLoader:
    """
    Loading values from a configuration file using configuration parser.

    This class should not be instantiated directly, rather user should
    create a derived dataclass class with proper data fields.

    For example:

    ```Python
    @dataclass
    class FooConfig(ConfigurationLoader):
        bar: str
    ```

    After invoking `FooConfig.from_config_file(<config_filepath>, <section>)`, an instance of
    FooConfig will be created with all values loaded according to their annotation types.
    """

    INITVAR_ANNOTATION_REGEX: ClassVar[Pattern[str]] = re.compile(
        r"(?:dataclasses\.)?InitVar\[([a-z]+)\]"
    )

    @staticmethod
    def _convert_annotation_to_string(annotation: Any) -> str:
        """
        Convert an annotation to string.

        >>> ConfigurationLoader._convert_annotation_to_string(str)
        'str'
        >>> ConfigurationLoader._convert_annotation_to_string(int)
        'int'
        >>> ConfigurationLoader._convert_annotation_to_string('float')
        'float'
        >>> 'ClassVar' in ConfigurationLoader._convert_annotation_to_string(ClassVar[str])
        True
        """
        if isinstance(annotation, str):
            return annotation
        elif isinstance(annotation, type):
            return annotation.__name__
        else:
            return str(annotation)

    @classmethod
    def _should_skip_field(cls, annotation: Any) -> bool:
        """
        Determine whether a field should be skipped.

        >>> ConfigurationLoader._should_skip_field(str)
        False
        >>> ConfigurationLoader._should_skip_field('int')
        False
        >>> ConfigurationLoader._should_skip_field('ClassVar[str]')
        True
        >>> ConfigurationLoader._should_skip_field(ClassVar[float])
        True
        """
        annotation_str = cls._convert_annotation_to_string(annotation)
        return "ClassVar" in annotation_str

    @classmethod
    def _cleanse_annotation(cls, annotation: Any) -> str:
        """
        Extract type from InitVar[<type>].

        >>> ConfigurationLoader._cleanse_annotation("InitVar[float]")
        'float'
        >>> from dataclasses import InitVar
        >>> ConfigurationLoader._cleanse_annotation(InitVar[float])
        'float'
        """
        annotation_str = cls._convert_annotation_to_string(annotation)
        match = re.fullmatch(cls.INITVAR_ANNOTATION_REGEX, annotation_str)
        if match:
            # option = InitVar[<type>]
            return match[1]
        else:
            return annotation_str

    @classmethod
    def from_config_file(
        cls,
        config_path: str,
        section: str = ConfigurationParser.DEFAULTSECT,
        **config_parser_kwargs: Any
    ) -> ConfigurationLoader:
        """
        Initialize a concrete ConfigurationLoader instance from config file.

        :param config_path: A path to config file -- a INI file.
        :param section: A section to load from config file. Default to DEFAULTSECT.
        :param config_parser_kwargs: Keyword arguments used to initialize the ConfigurationParser.
        :returns: A ConfigurationLoader instance with all values
            loaded according to their annotation types.
        """
        config_parser_kwargs.setdefault("interpolation", ExtendedInterpolation())

        parser = ConfigurationParser(**config_parser_kwargs)
        parser.read(config_path)

        values: Dict[str, Any] = dict(
            (
                option,
                parser.get_with_type(section, option, cls._cleanse_annotation(annotation)),
            )
            for option, annotation in cls.__annotations__.items()
            if not cls._should_skip_field(annotation)
        )

        return cls(**values)


if __name__ == "__main__":
    import doctest

    doctest.testmod()
