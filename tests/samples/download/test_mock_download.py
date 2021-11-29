import random
from concurrent.futures import ProcessPoolExecutor
from unittest.mock import Mock

from faker import Faker

from .test_download import Authentication, Download, DownloadManager, Enumeration

fake = Faker()


class MockDownload(Download):
    def __init__(
        self,
        src,
        dest,
        retry_limit: int = 3,
        download_success_prob: float = 0.5,
        reset_success_prob: float = 1,
    ):
        super().__init__(src, dest, retry_limit=retry_limit)
        self.__init_mocks()
        self.download_success_prob = download_success_prob
        self.reset_success_prob = reset_success_prob

    def __init_mocks(self) -> None:
        self.download_mock = Mock()
        self.validate_mock = Mock()
        self.reset_mock = Mock()

    def download(self) -> None:
        self.download_mock(self.src, self.dest)

    def validate(self) -> bool:
        is_success = random.random() < self.download_success_prob
        self.validate_mock(is_success)
        return is_success

    def reset(self) -> bool:
        is_success = random.random() < self.reset_success_prob
        self.reset_mock(is_success)
        return is_success


def test_mock_download():
    success_callback = Mock()
    failure_callback = Mock()

    download_task = MockDownload("foo", "bar")
    download_task.on_success.register(success_callback)
    download_task.on_failure.register(failure_callback)
    download_task()

    download_task.download_mock.assert_called()
    download_task.validate_mock.assert_called()
    assert 1 == (success_callback.call_count + failure_callback.call_count)


class MockEnumeration(Enumeration):
    def __call__(self):
        for i in random.choice(range(2, 5)):
            url = fake.url()
            yield Download(src=url, dest=fake.file_path())


# def test_download_manger():
#     authentication = Authentication(fake.user_name(), fake.password())
#     breakpoint()
#     download_manager = DownloadManager(authentication, MockEnumeration(), ProcessPoolExecutor())

#     download_manager()

#     assert download_manager.is_authenticated
#     assert download_manager.can_enumerate
