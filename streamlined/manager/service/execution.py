import inspect
from typing import Any, Callable, Iterable, List, TypeVar

from .service import Service

T = TypeVar("T")


class ExecutionWithDependencyInjection(Service):
    """
    Provides a execute method that executes an action by providing all arguments
    using dependency injection.
    """

    @staticmethod
    def __prepare_argument(scope: Any, argname: str) -> Any:
        return scope.get_value(name=argname)

    @classmethod
    def __prepare_arguments(cls, scope: Any, argnames: Iterable[str]) -> List[str]:
        return [cls.__prepare_argument(scope, argname) for argname in argnames]

    @classmethod
    def __prepare_arguments_for_action(cls, scope: Any, action: Callable[..., Any]) -> List[str]:
        argspec = inspect.getfullargspec(action)
        return cls.__prepare_arguments(scope, argnames=argspec.args)

    def execute(self, action: Callable[..., T]) -> T:
        """
        Execute an action using depndency injection.
        """
        arguments = ExecutionWithDependencyInjection.__prepare_arguments_for_action(
            scope=self, action=action
        )
        return action(*arguments)
