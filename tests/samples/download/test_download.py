from typing import Any

from streamlined.ray.services import EventNotification


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
