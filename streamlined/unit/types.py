from typing import Any, Callable, Hashable, Mapping, Sequence, Type, Union

KeyType = Hashable
ValueType = Any
ExecutableType = Callable[..., Any]
EnvironmentType = Mapping[KeyType, ValueType]
Exceptions = Union[Type[BaseException], Sequence[Type[BaseException]]]
BoundFunction = Callable[[], ValueType]
ExceptionPredicate = Callable[[BaseException], bool]
