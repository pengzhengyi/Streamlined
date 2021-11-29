from __future__ import annotations

from concurrent.futures import Executor
from typing import Any, Iterable

from streamlined.ray.execution import ExecutionSchedule
from streamlined.ray.services import EventNotification, after


class Authentication:
    def __init__(self, username: str, password: str):
        super().__init__()
        self.username = username
        self.password = password

    def __call__(self) -> bool:
        return True


class Download:
    """
    Abstract interface for a downloading task.

    The following methods should be implemented:

    - `download`: downloading from src to dest
    - `validate`: validate whether download succeeds
    - `reset`: reset the environment at download failure, so that download can be restarted
    """

    def __init__(self, src: Any, dest: Any, retry_limit: int = 3):
        self.src = src
        self.dest = dest
        self.retry_limit = retry_limit
        self.__init_events()

    def __init_events(self):
        self.on_success = EventNotification()
        self.on_failure = EventNotification()

    def __call__(self) -> bool:
        retry_limit = self.retry_limit

        for which_attempt in range(retry_limit):
            self.download()

            if self.validate():
                break
            else:
                if not self.reset():
                    self.on_failure()
                    return False
        else:
            self.on_failure()
            return False

        self.on_success()
        return True

    def download(self) -> None:
        """Download src to dest"""
        pass

    def validate(self) -> bool:
        """Determines whether download succeeds"""
        return True

    def reset(self) -> bool:
        """Determines whether cleanup succeeds"""
        return False


class DownloadManager:
    is_authenticated: bool
    can_enumerate: bool

    def __init__(
        self, authentication: Authentication, enumeration: Enumeration, executor: Executor
    ):
        super().__init__()
        self.__init_authentication(authentication)
        self.__init_enumeration(enumeration)
        self.__init_events()
        self.__init_execution_schedule()
        self.executor = executor

    def __init_events(self) -> None:
        self.on_authentication_failed = EventNotification()
        self.on_enumeration_failed = EventNotification()

    def create_download_tasks(self, result: Iterable[Download]) -> None:
        if result is None:
            self.can_enumerate = False

        self.can_enumerate = True
        self.downloads = []
        self.download_eus = []

        for download in result:
            self.downloads.append(download)
            download_eu = self.execution_schedule.push(download, has_prerequisites=True)
            download_eu.require(self.enumeration_eu)
            self.download_eus.append(download_eu)

    def __init_authentication(self, authentication: Authentication) -> None:
        self.is_authenticated = False
        self.authentication = authentication

    def __init_enumeration(self, enumeration: Enumeration) -> None:
        self.can_enumerate = False
        self.enumeration = enumeration

    def __init_execution_schedule(self) -> None:
        self.execution_schedule = ExecutionSchedule()

        self.authentication_eu = self.execution_schedule.push(self.authentication)
        self.authentication_eu.on_complete.listeners.insert(
            0, lambda auth_result: setattr(self, "is_authenticated", auth_result)
        )

        self.on_authentication_failed_eu = self.execution_schedule.push(
            self.on_authentication_failed
        )
        self.on_authentication_failed_eu.require(
            self.authentication_eu, condition=lambda: not self.is_authenticated
        )

        self.enumeration_eu = self.execution_schedule.push(self.enumeration)
        self.enumeration_eu.require(
            self.authentication_eu, condition=lambda: self.is_authenticated
        )
        self.enumeration_eu.on_complete.listeners.insert(0, self.create_download_tasks)

        self.on_enumeration_failed_eu = self.execution_schedule.push(self.on_enumeration_failed)
        self.on_enumeration_failed_eu.require(
            self.enumeration_eu, condition=lambda: not self.can_enumerate
        )

    def __call__(self):
        for execution_unit in self.execution_schedule:
            self.executor.submit(execution_unit)
        else:
            self.executor.shutdown()


class Enumeration:
    def __call__(self) -> Iterable[Download]:
        return []
