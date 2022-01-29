from __future__ import annotations

from string import Formatter
from typing import TYPE_CHECKING, Any, Mapping, Optional

from ..common import ProxyDict

if TYPE_CHECKING:
    from ..middlewares import Context


class Reference(Formatter):
    def __init__(
        self,
        format_string: str,
        overrides: Optional[Mapping[str, Any]] = None,
        fallbacks: Optional[Mapping[str, Any]] = None,
    ) -> None:
        super().__init__()
        self.format_string = format_string
        self._init_overrides(overrides)
        self._init_fallbacks(fallbacks)

    def _init_overrides(self, overrides: Optional[Mapping[str, Any]]) -> None:
        self.overrides = dict() if overrides is None else overrides

    def _init_fallbacks(self, fallbacks: Optional[Mapping[str, Any]]) -> None:
        self.fallbacks = dict() if fallbacks is None else fallbacks

    def _create_proxy_dictionary(self, mapping: Mapping[str, Any]) -> ProxyDict:
        proxies = []
        if self.overrides:
            proxies.append(self.overrides)

        proxies.append(mapping)

        if self.fallbacks:
            proxies.append(self.fallbacks)

        return ProxyDict(*proxies)

    def __call__(self, _context_: Mapping[str, Any]) -> Any:
        return self.resolve(_context_)

    def __str__(self) -> str:
        return f"{self.format_string}->?"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({str(self)})"

    def resolve(self, _context_: Mapping[str, Any]) -> Any:
        """
        Resolve this format string in provided scope.

        This method needs to be implemented by subclasses.

        To allow it to be used in middleware, its argument is deliberately set to
        `_context_`.
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

    def resolve(self, _context_: Mapping[str, Any]) -> str:
        proxy_dict = self._create_proxy_dictionary(_context_)
        self._resolved_name = self.vformat(self.format_string, [], proxy_dict)
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

    def resolve(self, _context_: Mapping[str, Any]) -> Any:
        resolved_name = super().resolve(_context_)
        proxy_dict = self._create_proxy_dictionary(_context_)
        self._resolved_value = proxy_dict[resolved_name]
        return self._resolved_value


class EvalRef(ValueRef):
    """
    EvalRef allows dynamic resolving and evaluation of a callable value by holding a format string as reference.

    Format String
    ------
    The format string should adhere to the
    [Format String Syntax](https://docs.python.org/3/library/string.html#format-string-syntax).

    In other words, the format string should be passable to `str.format` but with
    positional key like `{0}` disallowed.

    Differences from `ValueRef`
    ------
    `EvalRef` takes one step further than ValueRef: in addition to assume the
    format string can resolve to a string that refers a value, `EvalRef` assumes
    this value is a callable and will invoke it by submitting it to the context.

    Due to the async nature of task execution for context, `resolve` and
    `__call__` are also async.


    Middleware Compatibility
    ------
    `ValueRef` should be primarily used in middleware like the following:

    ```
    import os


    def make_source_dir(source_dir: str) -> None:
        os.makedirs(source_dir, exists_ok=True)

    Argument({
        NAME: NameRef('{origin}_dir'),
        VALUE: ValueRef('{origin}_dir'),
        CLEANUP: EvalRef(`make_{origin}_dir`, overrides=dict(make_source_dir=make_source_dir))
    })
    ```

    Suppose `origin` has value `source` and `source_dir` has value `/tmp`, the above is equivalent to:

    ```
    Argument({
        NAME: 'source_dir',
        VALUE: '/tmp'
        CLEANUP: make_source_dir
    })
    ```
    """

    _evaluated_value: Any

    def __str__(self) -> str:
        try:
            return f"{self._resolved_value}={self.format_string}|{self._resolved_name}(...)->{self._evaluated_value}"
        except AttributeError:
            return super().__str__()

    async def __call__(self, _context_: Context) -> Any:
        return await self.resolve(_context_)

    async def resolve(self, _context_: Context) -> Any:
        resolved_func = super().resolve(_context_)
        if not callable(resolved_func):
            raise TypeError(f"{resolved_func} should be a callable")

        self._evaluated_value = await _context_.submit(resolved_func)
        return self._evaluated_value


if __name__ == "__main__":
    import doctest

    doctest.testmod()
