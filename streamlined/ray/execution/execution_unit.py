from __future__ import annotations

from enum import Enum, auto
from typing import Any, Callable

from decorator import decorate

from ..common import ASYNC_VOID, VOID
from ..services import EventNotification


class ExecutionStatus(Enum):
    NotStarted = auto()
    Started = auto()
    Completed = auto()


class ExecutionUnit:
    """
    Execution unit holds a callable and is responsible for its execution.

    It can be seen as a wrapper around a normal callable offering status and completion notification.

    When ExecutionUnit is called, the wrapped function will be called and at its completion, registered listeners will be notified.

    Initialization
    --------
    ExecutionUnit can be instantiated in three ways:

    1. In this approach, the callable is transformed into an ExecutionUnit while the original callable is now `ExecutionUnit.callable`. Invoking the name of callable will actually invoke the ExecutionUnit.

    ```Python
    @ExecutionUnit
    def add(x, y):
        return x + y
    ```

    2. In this approach, callable and ExecutionUnit are two distinct entities.
    Invoking callable will not simultaneously start the instantiated ExecutionUnit.

    ```Python
    def add(x, y):
        return x + y

    execution_unit = ExecutionUnit(add)
    ```

    3. In this approach, callable and ExecutionUnit are "interweaved".
    After callable being embedded into an existing ExecutionUnit, invoking callable will instruct the associated ExecutionUnit to run which will eventually run the code of callable.
    ! An important advantage of this approach is that signature of callable is preserved while invoking the callable will invoke the ExecutionUnit.

    ```Python
    execution_unit = ExecutionUnit.empty()

    @ExecutionUnit.bind(execution_unit)
    def add(x, y):
        return x + y
    ```
    """

    @classmethod
    def empty(cls):
        return cls()

    @staticmethod
    def bind(execution_unit: ExecutionUnit):
        def _decorate(_callable: Callable):
            execution_unit.callable = _callable

            def wrapper(_callable: Callable, *args: Any, **kwargs: Any):
                return execution_unit(*args, **kwargs)

            return decorate(_callable, wrapper)

        return _decorate

    def __init__(self, _callable: Callable = VOID):
        self.__init_task(_callable)

    def __init_task(self, _callable: Callable) -> None:
        self.callable = _callable
        self.__init_task_on_complete()
        self.status = ExecutionStatus.NotStarted

    def __init_task_on_complete(self) -> None:
        self.on_complete = EventNotification()

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        self.status = ExecutionStatus.Started

        result = self.callable(*args, **kwargs)

        self.set_complete(result, *args, **kwargs)
        return result

    def set_complete(self, result: Any, *args: Any, **kwargs: Any) -> None:
        """
        Mark the status as Completed and trigger on_complete event notification.

        This method will be called automatically when ExecutionUnit is called. It can also be called explicitly to set a result.
        """
        self.status = ExecutionStatus.Completed
        self.on_complete(result)


class AsyncExecutionUnit(ExecutionUnit):
    """
    Similar as ExecutionUnit, but work specifically for coroutines.
    """

    @staticmethod
    def bind(execution_unit: ExecutionUnit):
        def _decorate(_callable: Callable):
            execution_unit.callable = _callable

            async def wrapper(_callable: Callable, *args: Any, **kwargs: Any):
                return await execution_unit(*args, **kwargs)

            return decorate(_callable, wrapper)

        return _decorate

    def __init__(self, _callable=ASYNC_VOID):
        super().__init__(_callable=_callable)

    async def __call__(self, *args: Any, **kwargs: Any) -> Any:
        self.status = ExecutionStatus.Started

        result = await self.callable(*args, **kwargs)

        self.set_complete(result, *args, **kwargs)
        return result


if __name__ == "__main__":
    import doctest

    doctest.testmod()
