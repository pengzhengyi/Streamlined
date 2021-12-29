import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from subprocess import PIPE
from typing import IO, Any, Dict, Literal, Optional, Union

Stream = Optional[Union[int, IO]]
StdinStream = Union[Stream, bytes]


@dataclass
class SubprocessResult:
    args: str
    stdin: StdinStream
    stdout: bytes
    stderr: bytes
    pid: int
    returncode: int
    kwargs: Dict[str, Any] = field(default_factory=dict)


async def subprocess(
    args: str, stdin: StdinStream, stdout: Stream, stderr: Stream, kwargs: Dict[str, Any]
) -> SubprocessResult:
    if isinstance(stdin, bytes):
        _stdin = PIPE
    else:
        _stdin = stdin
        stdin = None
    process = await asyncio.create_subprocess_exec(
        args, stdin=_stdin, stdout=stdout, stderr=stderr, **kwargs
    )
    stdout, stderr = await process.communicate(input=stdin)
    return SubprocessResult(
        args, stdin or _stdin, stdout, stderr, process.pid, process.returncode, kwargs
    )
