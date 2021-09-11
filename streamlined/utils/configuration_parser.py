from __future__ import annotations

import configparser
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, Optional, Type, Union

if TYPE_CHECKING:
    from io import StringIO


class ConfigurationParser(configparser.ConfigParser):
    """
    A configuration parser which wraps over
    [ConfigParser](https://docs.python.org/3/library/configparser.html).
    It can be initialized from multiple sources and supports convenient getter methods.

    >>> parser = ConfigurationParser()
    >>> parser.read_dict({'section1': {'sample': 'a'}})
    >>> parser.get(option='sample', section='section1')
    'a'
    """

    DEFAULTSECT: ClassVar[str] = configparser.DEFAULTSECT

    @classmethod
    def append_section(
        cls,
        section: str,
        filepath: str,
        space_around_delimiters: bool = False,
        **key_value_pairs: str
    ) -> None:
        """
        Append a section to the configuration file with specified key value pairs.
        """
        parser = cls()
        parser.read(filepath)

        parser.add_section(section)

        for option, value in key_value_pairs.items():
            parser.set(section, option, value)

        with open(filepath, "w") as fileobject:
            parser.write(fileobject, space_around_delimiters=space_around_delimiters)

    @classmethod
    def delete_section(cls, section: str, filepath: str) -> bool:
        """Remove a section from the configuration file"""
        parser = cls()
        parser.read(filepath)

        if parser.remove_section(section):
            with open(filepath, "w") as fileobject:
                parser.write(fileobject, space_around_delimiters=False)
            return True
        return False

    def get_with_type(
        self, section: str, option: str, _type: Union[str, Type[Any]]
    ) -> Optional[Any]:
        """
        Get a config option's value for the named section and convert to designated type.

        >>> parser = ConfigurationParser()
        >>> parser.read_dict({'section1': {'count': 123, 'ok': True}})
        >>> parser.get_with_type(section='section1', option='count', _type=int)
        123
        >>> parser.get_with_type(section='section1', option='ok', _type='bool')
        True
        """
        if _type == str.__name__ or _type == str:
            return self.get(section, option)
        elif _type == int.__name__ or _type == int:
            return self.getint(section, option)
        elif _type == float.__name__ or _type == float:
            return self.getfloat(section, option)
        elif _type == bool.__name__ or _type == bool:
            return self.getboolean(section, option)
        elif _type == Path.__name__ or _type == Path:
            return Path(self.get(section, option))
        else:
            if self.has_option(section, option):
                return self.get(section, option)
            else:
                return None


if __name__ == "__main__":
    import doctest

    doctest.testmod()
