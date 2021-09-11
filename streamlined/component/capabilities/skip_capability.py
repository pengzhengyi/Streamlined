from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, ClassVar, Dict, Optional, Union

from ...constants import ACTION, SKIP, VALUE
from ..execution_component import ExecutionComponent
from .capability import Capability

TSkipValue = Optional[Union[bool, Callable[..., bool]]]
TSkipAction = Optional[Callable[..., Any]]
TSkip = Optional[Union[TSkipValue, Dict[str, Union[TSkipAction, TSkipValue]]]]


if TYPE_CHECKING:
    from ...manager.manager import Manager


class Skippable(Capability):
    """
    A mixin that allows a component to conditionally skip its execution.

    It can be configured in any of the following ways:

    + Boolean Flag: `"skip": True` or `"skip": False`
    + An action (dependency injection applicable) that evaluates to boolean flag
      `"skip": lambda: True`
    + A dictionary:

      ```
      "skip": {
          "value": True,
          "action": lambda: print('skipped')
      }
      ```

    + Not specifying any, it will default to `"skip": False`
    """

    SKIP_KEYNAME: ClassVar[str] = SKIP

    def __init__(self, **kwargs: Any):
        self.__set_skip(kwargs.pop(self.SKIP_KEYNAME, None))
        super().__init__(**kwargs)

    def __getattribute__(self, name: str) -> Any:
        if name == "execute":
            target_execute_func = super().__getattribute__(name)
            return lambda manager, *args, **kwargs: self._skippable_execute(
                manager, *args, execute_func=target_execute_func, **kwargs
            )

        return super().__getattribute__(name)

    def __set_skip(self, skip: TSkip) -> None:
        skip_value = None
        skip_action = None

        if isinstance(skip, dict):
            skip_value = skip.get(VALUE)
            skip_action = skip.get(ACTION)
        else:
            skip_value = skip

        self.__set_skip_value(skip_value)
        self.__set_skip_action(skip_action)

    def __set_skip_value(self, value: TSkipValue) -> None:
        if value is None:
            # default not to skip
            value = False

        if isinstance(value, bool):
            self._should_skip = value
            self._should_skip_predicate = None
        else:
            assert callable(value)

            self._should_skip = None
            self._should_skip_predicate = ExecutionComponent(value)

    def __set_skip_action(self, action: TSkipAction) -> None:
        self._if_skip_action = None if action is None else ExecutionComponent(action)

    def __resolve_skip_value(self, manager: Manager) -> bool:
        if self._should_skip is not None:
            return self._should_skip
        else:
            return self._should_skip_predicate.execute(manager)

    def __execute_for_fallback_action(self, manager: Manager) -> Any:
        if self._if_skip_action is None:
            return None
        return self._if_skip_action.execute(manager)

    def _skippable_execute(
        self, manager: Manager, *args: Any, execute_func: Callable[..., Any], **kwargs: Any
    ) -> Callable[..., Any]:
        if self.__resolve_skip_value(manager):
            # should skip
            return self.__execute_for_fallback_action(manager)
        else:
            # should not skip
            return execute_func(manager, *args, **kwargs)
