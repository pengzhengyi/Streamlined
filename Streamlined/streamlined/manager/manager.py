from __future__ import annotations

from typing import List, Type

from .service import (
    ExecutionWithDependencyInjection,
    Logging,
    NameTracking,
    ResultCollection,
    Scoping,
    Service,
    TagGrouping,
    add_services,
)

DEFAULT_SERVICES: List[Type[Service]] = [
    NameTracking,
    ResultCollection,
    ExecutionWithDependencyInjection,
    Scoping,
    Logging,
    TagGrouping,
]


def create_manager(*services: Type[Service]) -> Type[Service]:
    """
    Create a manager with specified services.

    Think a manager as a service provider who will recommend corresponding service to request.
    """
    return add_services("Manager", *services)


Manager = create_manager(*DEFAULT_SERVICES)
