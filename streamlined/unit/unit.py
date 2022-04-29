from __future__ import annotations

from enum import Enum, auto
from typing import Any, Callable, List, Mapping, Optional, Protocol, Sequence, TypeVar

import wrapt

from ..common import TAUTOLOGY
from .types import (
    BoundFunction,
    EnvironmentType,
    ExceptionPredicate,
    Exceptions,
    ExecutableType,
    KeyType,
    ValueType,
)


class Callback(Protocol):
    """Notify an unit is ready to execute."""

    def __call__(self, unit: Unit, **kwargs: Any) -> ValueType:
        ...


class OnCompleteCallback(Protocol):
    """Notify when an unit has finished its execution."""

    def __call__(self, unit: Unit, result: ValueType, **kwargs: Any) -> ValueType:
        ...


OnSetupCallback = OnCleanupCallback = OnLogCallback = OnReadyCallback = Callback
ValueGetter = OnCompleteCallback


class OnExceptionCallback(Protocol):
    """Handle when an unit suppresses an exception."""

    def __call__(self, unit: Unit, exception: BaseException, **kwargs: Any) -> ValueType:
        ...


class ThenCondition(Protocol):
    """An additionally condition to require for whether the unit as prerequisite
    is satisfied for the unit as dependent.
    """

    def __call__(self, prerequisite: Unit, dependent: Unit, **kwargs: Any) -> bool:
        ...


T = TypeVar("T")


@wrapt.decorator
def non_terminal(
    wrapped: Callable[..., Any], instance: T, args: List[Any], kwargs: Mapping[str, Any]
) -> T:
    """Make a class instance method non-terminal. That is, it will return the
    instance it was invoked on."""
    wrapped(*args, **kwargs)
    return instance


class Moment(Enum):
    """Different moment during the lifetime of an Unit."""

    ON_READY = auto()
    ON_COMPLETE = auto()
    ON_EXCEPTION = auto()


class Unit:
    """
    A unit is a piece of work in a task.

    Consider a hypothetical example of revenue calculating unit:
    ```
    from operator import sub
    unit = Unit(sub).name("calculate revenue")                               \
                    .parameters("profit", "cost")                            \
                    .receive({"profit": 1000, "cost": 100})                  \
                    .output("revenue")                                       \
                    .output("monthly_revenue", lambda revenue: revenue / 12) \
                    .output("daily_revenue", lambda revenue: revenue / 365)  \
                    .on_complete(save_revenue_in_database)

    unit() == {'__result__': ..., 'revenue': ..., 'monthly_revenue': ..., 'daily_revenue': ..., }
    ```

    Recommended Order:

    + on_exception
    + name
    + parameters
    + receive
    + output
    + setup
    + on_ready
    + on_complete
    + validate
    + log
    + cleanup
    """

    @property
    def is_ready(self) -> bool:
        # TODO
        ...

    def __init__(self, func: ExecutableType) -> None:
        self._func = func
        # TODO

    def __call__(self) -> Any:
        # TODO
        pass

    def bound(self, **kwargs: Any) -> BoundFunction:
        assert self.is_ready
        # TODO

    def then(
        self,
        unit: Unit,
        when: ThenCondition = TAUTOLOGY,
        dnf_conjunction: Optional[KeyType] = None,
    ) -> Unit:
        # TODO
        pass

    @non_terminal
    def name(self, name: KeyType, **kwargs: Any) -> Unit:
        # TODO
        pass

    @non_terminal
    def parameters(
        self,
        args: Optional[Sequence[KeyType]] = None,
        kwargs: Optional[Mapping[str, KeyType]] = None,
    ) -> Unit:
        # TODO
        pass

    @non_terminal
    def output(self, name: KeyType, value: Optional[ValueGetter] = None, **kwargs: Any) -> Unit:
        # TODO
        pass

    @non_terminal
    def receive(self, environment: EnvironmentType, **kwargs: Any) -> Unit:
        # TODO
        pass

    @non_terminal
    def on_ready(self, on_ready: OnReadyCallback, **kwargs: Any) -> Unit:
        # TODO
        pass

    @non_terminal
    def on_complete(self, on_complete: OnCompleteCallback, **kwargs: Any) -> Unit:
        # TODO
        pass

    @non_terminal
    def on_exception(
        self,
        exceptions: Exceptions,
        when: ExceptionPredicate,
        then: OnExceptionCallback,
        **kwargs: Any,
    ) -> Unit:
        # TODO
        pass

    @non_terminal
    def setup(
        self, setup: OnSetupCallback, moment: Moment = Moment.ON_READY, **kwargs: Any
    ) -> Unit:
        pass

    @non_terminal
    def log(self, log: OnLogCallback, moment: Moment = Moment.ON_COMPLETE, **kwargs: Any) -> Unit:
        # TODO
        pass

    @non_terminal
    def cleanup(
        self, cleanup: OnCleanupCallback, moment: Moment = Moment.ON_COMPLETE, **kwargs: Any
    ) -> Unit:
        pass

    @non_terminal
    def validate(
        self, log: OnLogCallback, moment: Moment = Moment.ON_COMPLETE, **kwargs: Any
    ) -> Unit:
        # TODO
        pass

    def _require(self, name: KeyType) -> Unit:
        # TODO add prerequisite
        pass

    def _output(self, name: KeyType, value: ValueType) -> Unit:
        # TODO register name with value
        pass
