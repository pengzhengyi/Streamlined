from __future__ import annotations

from abc import ABC, abstractmethod
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Generator,
    Iterable,
    List,
    Optional,
    Type,
    Union,
)

if TYPE_CHECKING:
    from ..manager.manager import Manager


class Component(ABC):
    def __init__(self, **kwargs: Any):
        assert not kwargs
        super().__init__()

    @classmethod
    def of(cls, config: Dict[str, Any]) -> Component:
        return cls(**config)

    @abstractmethod
    def execute(self, manager: Manager) -> Any:
        raise NotImplementedError


def stack(component_class: Type[Component]) -> Type[Component]:
    class Stacked(Component):
        def __init__(self, configs: List[Any], **kwargs: Any):
            super().__init__(**kwargs)
            self.__set_components(configs)

        def __set_components(self, configs: List[Any]) -> None:
            self.__components = [component_class.of(config) for config in configs]

        def __execute(self, manager: Manager) -> Iterable[Any]:
            for component in self.__components:
                yield component.execute(manager)

        def execute(self, manager: Manager) -> List[Any]:
            result = list(self.__execute(manager))
            manager.set_result(self, result)
            return result

    return Stacked


def combine(*component_classes: Type[Component]) -> Type[Component]:
    class Combined(Component):
        __components: List[Component]
        __name_to_component: Dict[str, Component]
        __default_execution_order: List[str]

        def __init__(self, **kwargs: Any):
            self.__components = []
            self.__name_to_component = dict()
            self.__default_execution_order = []

            for component_class in component_classes:
                keyname = component_class.KEY_NAME
                self.__default_execution_order.append(keyname)
                try:
                    self.__set_component(component_class, kwargs.pop(keyname))
                except KeyError:
                    continue

            super().__init__(**kwargs)

        def __set_component(self, component_class: Type[Component], config: Any) -> None:
            component = component_class(config)
            self.__components.append(component)
            self.__name_to_component[component_class.KEY_NAME] = component

        def __get_component_by_name(self, name: str) -> Component:
            return self.__name_to_component[name]

        def __get_component_by_index(self, index: int) -> Component:
            return self.__components[index]

        def __get_component(self, identifier: Union[str, int]) -> Component:
            if isinstance(identifier, str):
                return self.__get_component_by_name(name=identifier)
            else:
                return self.__get_component_by_index(index=identifier)

        def __execute_component_by_name(self, name: str, manager: Manager) -> Any:
            return self.__get_component_by_name(name).execute(manager)

        def __execute_component_by_index(self, index: int, manager: Manager) -> Any:
            return self.__get_component_by_index(index).execute(manager)

        def __execute_component(
            self, identifier: Union[str, int], manager: Manager, headless: bool = True
        ) -> Any:
            try:
                return self.__get_component(identifier).execute(manager)
            except (IndexError, KeyError):
                if headless:
                    return
                else:
                    raise

        def __execute(
            self, manager: Manager, headless: bool = True
        ) -> Generator[Any, Union[str, int], None]:
            identifier = yield
            while identifier is not None:
                identifier = yield self.__execute_component(identifier, manager, headless)

        def execute(
            self,
            manager: Manager,
            order: Optional[Iterable[Union[str, int]]] = None,
            headless: bool = True,
        ) -> Generator[Any, None, None]:
            if order is None:
                order = self.__default_execution_order

            executor = self.__execute(manager, headless)
            # no-op
            next(executor)
            for identifier in order:
                yield executor.send(identifier)

    return Combined
