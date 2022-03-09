import tempfile
from dataclasses import dataclass, field
from tempfile import gettempdir


@dataclass
class Settings:
    """
    Global settings for streamlined.

    It contains the following configurable options:

    + `use_diskcache` indicates whether temporary files will be used as cache.
    + `tempdir` determines where temporary cache files are saved.
    """

    use_diskcache: bool = field(default=False)

    @property
    def tempdir(self) -> str:
        """
        See [gettempdir](https://docs.python.org/3/library/tempfile.html#tempfile.gettempdir).
        """
        return gettempdir()

    @tempdir.setter
    def tempdir(self, value: str) -> None:
        tempfile.tempdir = value


SETTINGS = Settings()
