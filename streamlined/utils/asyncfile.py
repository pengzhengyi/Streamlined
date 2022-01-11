import hashlib

from aiofile import async_open

DEFAULT_BUFFER_SIZE = 10 * 1024 * 1024


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


async def copy(source: str, dest: str, chunk_size: int = DEFAULT_BUFFER_SIZE) -> int:
    bytes_count = 0
    async with async_open(source, "rb") as reader, async_open(dest, "wb") as writer:
        async for chunk in reader.iter_chunked(chunk_size):
            bytes_count += await writer.write(chunk)
    return bytes_count
