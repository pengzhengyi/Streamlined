from typing import ClassVar, TypeVar

from ..constants import CLEANUP
from .execution_component import ExecutionComponent

T = TypeVar("T")


class CleanupComponent(ExecutionComponent[T]):
    """
    Execute cleanup action before exiting execution scope.

    A typical scenario is to close file descriptor.
    """

    KEY_NAME: ClassVar[str] = CLEANUP
