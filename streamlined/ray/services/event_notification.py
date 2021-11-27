from __future__ import annotations

from typing import Any, Callable, List

from .service import Service


class EventNotification(Service):
    """
    EventNotification implements basic [Event-driven messaging](https://en.wikipedia.org/wiki/Event-driven_messaging).

    >>> meeting = EventNotification()
    >>> attendees = []
    >>> meeting += lambda: attendees.append("Alice")
    >>> meeting += lambda: attendees.append("Bob")
    >>> meeting()
    >>> attendees
    ['Alice', 'Bob']
    """

    listeners: List[Callable]

    def __init__(
        self,
        *args: Any,
        **kwargs: Any,
    ):
        super().__init__(*args, **kwargs)
        self.listeners = list()

    def __call__(self, *args: Any, **kwargs: Any) -> None:
        for listener in self.listeners:
            self.notify(listener, *args, **kwargs)

    def __add__(self, other: Callable) -> EventNotification:
        self.register(other)
        return self

    def __iadd__(self, other: Callable) -> EventNotification:
        return self.__add__(other)

    def __sub__(self, other: Callable) -> EventNotification:
        self.unregister(other)
        return self

    def __isub__(self, other: Callable) -> EventNotification:
        return self.__sub__(other)

    def register(self, _callable: Callable) -> None:
        """
        Register an event listener.

        This event listener will be called after all other registered event listeners (if any).
        """
        self.listeners.append(_callable)

    def unregister(self, _callable: Callable) -> None:
        """
        Unregister an event listener.
        """
        self.listeners.remove(_callable)

    def notify(self, listener: Callable, *args: Any, **kwargs: Any) -> None:
        listener(*args, **kwargs)


if __name__ == "__main__":
    import doctest

    doctest.testmod()
