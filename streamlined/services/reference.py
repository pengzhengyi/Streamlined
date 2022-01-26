from string import Formatter
from typing import Any, Mapping


class Reference(Formatter):
    def __init__(self, format_string: str) -> None:
        super().__init__()
        self.format_string = format_string

    def __call__(self, _scoped_: Mapping[str, Any]) -> Any:
        return self.resolve(_scoped_)

    def __str__(self) -> str:
        return f"{self.format_string}->?"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({str(self)})"

    def resolve(self, _scoped_: Mapping[str, Any]) -> Any:
        """
        Resolve this format string in provided scope.

        This method needs to be implemented by subclasses.

        To allow it to be used in middleware, its argument is deliberately set to
        `_scoped_`.
        """
        raise NotImplementedError()


class NameRef(Reference):
    """
    NameRef allows dynamic resolving a string by holding a format string as
    reference.

    Format String
    ------
    The format string should adhere to the
    [Format String Syntax](https://docs.python.org/3/library/string.html#format-string-syntax).

    In other words, the format string should be passable to `str.format` but with
    positional key like `{0}` disallowed.

    Middleware Compatibility
    ------
    `NameRef` can be used in middleware like the following:

    ```
    Argument({
        NAME: NameRef('{origin}_dir'),
        VALUE: '/tmp'
    })
    ```

    Suppose `origin` has value `source`, the above is equivalent to:

    ```
    Argument({
        NAME: 'source_dir',
        VALUE: '/tmp'
    })
    ```

    Example
    ------

    >>> reference = NameRef('document_version-{v}')
    >>> reference.resolve(dict(v=1))
    'document_version-1'
    >>> reference(dict(v='alpha'))
    'document_version-alpha'
    """

    _resolved_name: str

    def __str__(self) -> str:
        try:
            return f"{self.format_string}->{self._resolved_name}"
        except AttributeError:
            return super().__str__()

    def resolve(self, _scoped_: Mapping[str, Any]) -> str:
        self._resolved_name = self.vformat(self.format_string, [], _scoped_)
        return self._resolved_name


class ValueRef(NameRef):
    """
    NameRef allows dynamic resolving a value by holding a format string as
    reference.

    Format String
    ------
    The format string should adhere to the
    [Format String Syntax](https://docs.python.org/3/library/string.html#format-string-syntax).

    In other words, the format string should be passable to `str.format` but with
    positional key like `{0}` disallowed.

    Differences from `NameRef`
    ------
    As implied by name, `NameRef` resolves to a string while `ValueRef` goes one
    step beyond -- it resolves to the value referred by that resolved string.

    Middleware Compatibility
    ------
    `ValueRef` can be used in middleware like the following:

    ```
    Argument({
        NAME: NameRef('{origin}_dir'),
        VALUE: ValueRef('{origin}_dir')
    })
    ```

    Suppose `origin` has value `source` and `source_dir` has value `/tmp`, the above is equivalent to:

    ```
    Argument({
        NAME: 'source_dir',
        VALUE: '/tmp'
    })
    ```

    Example
    ------

    >>> smallest_prime = ValueRef('smallest_prime')
    >>> smallest_prime.resolve(dict(smallest_prime=2))
    2
    >>> smallest_what = ValueRef('smallest_{what}')
    >>> smallest_what(dict(smallest_positive_integer=1, what='positive_integer'))
    1
    """

    _resolved_value: Any

    def __str__(self) -> str:
        try:
            return f"{self.format_string}|{self._resolved_name}->{self._resolved_value}"
        except AttributeError:
            return super().__str__()

    def resolve(self, _scoped_: Mapping[str, Any]) -> Any:
        resolved_name = super().resolve(_scoped_)
        self._resolved_value = _scoped_[resolved_name]
        return self._resolved_value


if __name__ == "__main__":
    import doctest

    doctest.testmod()
