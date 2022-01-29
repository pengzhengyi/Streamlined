from __future__ import annotations

import logging
import os
import sys
from enum import Enum
from functools import partial
from typing import Callable, Optional, Union

from aiofiles import os as aos

from streamlined import (
    ACTION,
    ARGPARSE,
    ARGS,
    ARGUMENTS,
    HANDLERS,
    HELP,
    LEVEL,
    LOG,
    MESSAGE,
    NAME,
    RUNSTAGES,
    RUNSTEPS,
    TYPE,
    VALIDATOR,
    VALIDATOR_AFTER_STAGE,
    VALUE,
    Pipeline,
    Scoped,
    create_identity_function,
    rewrite_function_parameters,
    use_basic_logging_config,
)
from streamlined.utils import append, copy, crash, samecontent

SOURCE = "source"
TARGET = "target"


SOURCE_LOGNAME = "源"
TARGET_LOGNAME = "目标"


class MergeStatus(str, Enum):
    Copy = "copy"
    Ignore = "ignore"
    Append = "append"
    Emulation = "emulation"


async def merge_by_copy(source: str, target: str) -> None:
    containing_dir = os.path.dirname(target)
    await aos.makedirs(containing_dir, exist_ok=True)

    if not await copy(source, target):
        raise OSError(f"Failed to copy {source} to {target}")


async def merge_by_append(source, target) -> None:
    await append(source, target)


async def merge(source: str, target: str) -> MergeStatus:
    if await aos.path.isfile(target):
        if await samecontent(source, target):
            return MergeStatus.Ignore
        else:
            await merge_by_append(source, target)
            return MergeStatus.Append
    else:
        await merge_by_copy(source, target)
        return MergeStatus.Copy


async def check_source_exists(source: Optional[str]) -> bool:
    return source is not None and await aos.path.isfile(source)


def report_filepath(filepath: str, logname: str = "") -> str:
    return f"合并的{logname}文件为{filepath}"


def report_nonexisting_filepath(filepath: Optional[str], logname: str = "") -> str:
    if filepath is None:
        filepath = ""
    return f"{logname}文件{filepath}未提供或没有指向合理位置"


report_source_filepath: Callable[[str], str] = rewrite_function_parameters(
    partial(report_filepath, logname=SOURCE_LOGNAME),
    "report_source_filepath",
    SOURCE,
)


def crash_when_is_not_file(filepath: Optional[str], logname: str) -> None:
    reason = report_nonexisting_filepath(filepath, logname)
    crash(reason)


crash_when_source_is_not_file: Callable[[str], None] = rewrite_function_parameters(
    partial(crash_when_is_not_file, logname=SOURCE_LOGNAME),
    "crash_when_source_is_not_file",
    SOURCE,
)


def report_should_remove(should_remove: bool) -> str:
    return f'合并的源文件将被{"删除" if should_remove else "保留"}'


SHOULD_REMOVE_ARGUMENT = {
    NAME: "should_remove",
    VALUE: {
        TYPE: ARGPARSE,
        NAME: ["--rm", "--remove"],
        HELP: "是否删除合并的源文件",
        ACTION: "store_true",
        ARGS: create_identity_function(ARGS),
    },
    LOG: {LEVEL: logging.INFO, MESSAGE: report_should_remove},
}

SOURCE_ARGUMENT = {
    NAME: SOURCE,
    VALUE: {
        TYPE: ARGPARSE,
        NAME: ["--src", "--source"],
        HELP: f"请提供合并的{SOURCE_LOGNAME}文件",
        ARGS: create_identity_function(ARGS),
    },
    VALIDATOR: {
        VALIDATOR_AFTER_STAGE: {
            ACTION: check_source_exists,
            HANDLERS: {
                True: {
                    LOG: {
                        LEVEL: logging.INFO,
                        MESSAGE: report_source_filepath,
                    },
                },
                False: {
                    ACTION: crash_when_source_is_not_file,
                },
            },
        }
    },
}


def check_target_provided(target: Optional[str]) -> None:
    return target is not None


report_target_filepath: Callable[[str], str] = rewrite_function_parameters(
    partial(report_filepath, logname=TARGET_LOGNAME),
    "report_target_filepath",
    TARGET,
)


def crash_when_target_is_not_provided() -> None:
    crash(f"{TARGET_LOGNAME}文件未提供")


TARGET_ARGUMENT = {
    NAME: TARGET,
    VALUE: {
        TYPE: ARGPARSE,
        NAME: ["--dest", "--target"],
        HELP: f"请提供合并的{TARGET_LOGNAME}文件",
        ARGS: create_identity_function(ARGS),
    },
    VALIDATOR: {
        VALIDATOR_AFTER_STAGE: {
            ACTION: check_target_provided,
            HANDLERS: {
                True: {
                    LOG: {
                        LEVEL: logging.INFO,
                        MESSAGE: report_target_filepath,
                    },
                },
                False: {
                    ACTION: crash_when_target_is_not_provided,
                },
            },
        }
    },
}


async def checked_merge(
    _scoped_: Scoped, source: str, target: str, should_remove: bool
) -> Union[MergeStatus, Exception]:
    dry_run = False
    if dry_run:
        result = MergeStatus.Emulation
    else:
        try:
            result = await merge(source, target)
            if should_remove:
                await aos.remove(source)
        except Exception as error:
            result = error
    _scoped_.set("merge_result", result, 1)
    return result


def get_merge_log_level(merge_result: Union[MergeStatus, Exception]) -> int:
    if isinstance(merge_result, Exception):
        return logging.ERROR
    else:
        return logging.INFO


def get_merge_log_message(
    source: str, target: str, merge_result: Union[MergeStatus, Exception]
) -> str:
    if isinstance(merge_result, Exception):
        return "[⨯]" + str(merge_result)
    elif merge_result == MergeStatus.Ignore:
        return f"[✓] {source}未移动，因为相同文件已存在于{target}"
    elif merge_result == MergeStatus.Append:
        return f"[✓] {source}被增加到{target}"
    elif merge_result == MergeStatus.Copy:
        return f"[✓] {source}被复制到{target}"
    else:  # merge_result == MergeStatus.Emulation:
        return f"[DRY_RUN] {source}应该被复制到{target}"


# Runsteps
MERGEFILE_RUNSTEP = {
    ACTION: checked_merge,
    LOG: {LEVEL: get_merge_log_level, MESSAGE: get_merge_log_message},
}

# Pipeline
MERGEFILE_PIPELINE = {
    NAME: "合并文件",
    RUNSTAGES: [{RUNSTEPS: [MERGEFILE_RUNSTEP]}],
    ARGUMENTS: [
        SOURCE_ARGUMENT,
        TARGET_ARGUMENT,
        SHOULD_REMOVE_ARGUMENT,
    ],
}


def main() -> None:
    use_basic_logging_config()
    pipeline = Pipeline(MERGEFILE_PIPELINE)

    pipeline.print_help(
        dict(
            prog="合并文件",
            description="该程序会将源文件合并至目标位置",
            epilog="© Timing Biology",
        )
    )
    scoped = pipeline.run_as_main(**{ARGS: sys.argv})


if __name__ == "__main__":
    main()
