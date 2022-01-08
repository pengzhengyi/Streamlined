import hashlib
from io import DEFAULT_BUFFER_SIZE

from aiofile import async_open


async def getsize(filepath: str, chunk_size: int = DEFAULT_BUFFER_SIZE) -> int:
    """
    Similar as `os.path.getsize`, get the filesize in bytes.
    """
    filesize = 0
    async with async_open(filepath, "rb") as reader:
        async for chunk in reader.iter_chunked(chunk_size):
            filesize += len(chunk)

    return filesize


async def md5(filepath: str, chunk_size: int = DEFAULT_BUFFER_SIZE) -> str:
    """
    Compute md5 of a filepath.
    """
    file_hash = hashlib.md5()
    async with async_open(filepath, "rb") as reader:
        async for chunk in reader.iter_chunked(chunk_size):
            file_hash.update(chunk)

    return file_hash.hexdigest()
