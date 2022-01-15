from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, MutableMapping, Optional

from aiofiles import os as aio

from streamlined import (
    ACTION,
    ARGPARSE,
    ARGUMENTS,
    HANDLERS,
    HELP,
    LEVEL,
    LOG,
    MESSAGE,
    NAME,
    PARALLEL,
    RUNSTAGES,
    RUNSTEPS,
    SCHEDULING,
    TYPE,
    VALIDATOR,
    VALIDATOR_AFTER_STAGE,
    VALUE,
    Pipeline,
    Scoped,
)
from streamlined.utils import copy, crash, samecontent, walk

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
SOURCE_DIR = "source_dir"
TARGET_DIR = "target_dir"
SOURCE_LOGNAME = "源"
TARGET_LOGNAME = "目标"
SOURCE_FILEPATHS = "source_filepaths"


def recreate_folder_structure(source: str, target: str, exists_ok: bool = True) -> List[str]:
    """
    Recreate folder structure in `source` at `target`.

    Only folders are created, no files will be copied.
    """
    created_targetpaths: List[str] = []
    for dirpath, dirnames, _ in os.walk(source):
        for dirname in dirnames:
            fullpath = Path(os.path.join(dirpath, dirname))
            relativepath = fullpath.relative_to(source)
            targetfullpath = Path(target).joinpath(relativepath)
            targetfullpath.mkdir(parents=True, exist_ok=exists_ok)
            created_targetpaths.append(str(targetfullpath))

    return created_targetpaths


def is_dir(dirpath: Optional[str]) -> bool:
    return dirpath is not None and os.path.isdir(dirpath)


def check_source_dir_exists(source_dir: Optional[str]) -> bool:
    return is_dir(source_dir)


def check_target_dir_exists(target_dir: Optional[str]) -> bool:
    return is_dir(target_dir)


def create_target_dir(target_dir: Optional[str]) -> None:
    if target_dir is None or os.path.isfile(target_dir):
        reason = report_nonexisting_dirpath(target_dir, TARGET_LOGNAME)
        crash(reason)

    os.makedirs(target_dir, exist_ok=True)


def create_help_for_dir(logname: str) -> str:
    return f"请提供操作的{logname}文件夹"


def report_nonexisting_dirpath(dirpath: Optional[str], logname: str = "") -> str:
    if dirpath is None:
        dirpath = ""
    return f"{logname}文件夹{dirpath}未提供或没有指向合理位置"


def crash_when_source_is_not_dir(source_dir: Optional[str]) -> None:
    reason = report_nonexisting_dirpath(source_dir, SOURCE_LOGNAME)
    crash(reason)


def report_dirpath(dirpath: str, logname: str = "") -> str:
    return f"操作的{logname}文件夹为{dirpath}"


def report_source_dir(source_dir: str) -> str:
    return report_dirpath(source_dir, SOURCE_LOGNAME)


def report_target_dir(target_dir: str) -> str:
    return report_dirpath(target_dir, TARGET_LOGNAME)


def listfiles(directory: Path) -> Iterable[str]:
    for filepath in walk(directory):
        if filepath.is_file():
            yield str(filepath)


def set_dirfiles(dirpath: str, name: str, dictionary: MutableMapping[str, Any]) -> List[str]:
    filepaths = list(listfiles(Path(dirpath)))
    dictionary[name] = filepaths
    return filepaths


def set_source_filepaths(source_dir: str, _scoped_: Scoped) -> List[str]:
    return set_dirfiles(source_dir, SOURCE_FILEPATHS, _scoped_.global_scope)


SOURCE_DIR_ARGUMENT = {
    NAME: "source_dir",
    VALUE: {TYPE: ARGPARSE, NAME: ["--src"], HELP: create_help_for_dir(SOURCE_LOGNAME)},
    VALIDATOR: {
        VALIDATOR_AFTER_STAGE: {
            ACTION: check_source_dir_exists,
            HANDLERS: {
                True: {
                    LOG: {
                        LEVEL: logging.INFO,
                        MESSAGE: report_source_dir,
                    },
                    ACTION: set_source_filepaths,
                },
                False: {ACTION: crash_when_source_is_not_dir},
            },
        }
    },
}
TARGET_DIR_ARGUMENT = {
    NAME: TARGET_DIR,
    VALUE: {
        TYPE: ARGPARSE,
        NAME: ["--target", "--dest"],
        HELP: create_help_for_dir(TARGET_LOGNAME),
    },
    VALIDATOR: {
        VALIDATOR_AFTER_STAGE: {
            ACTION: check_target_dir_exists,
            HANDLERS: {
                False: {ACTION: create_target_dir},
            },
        }
    },
    LOG: {LEVEL: logging.INFO, MESSAGE: report_target_dir},
}


def create_folder_structure(source_dir: str, target_dir: str) -> List[str]:
    return recreate_folder_structure(source_dir, target_dir, exists_ok=True)


def report_folder_structure_creation(source_dir: str, target_dir: str) -> str:
    return f"{source_dir}文件架结构已成功在{target_dir}创建"


def report_copyfiles(source_dir: str, target_dir: str) -> str:
    return f"{source_dir}的文件已成功复制到{target_dir}"


CREATE_FOLDER_STRUCTURE_RUNSTAGE = {
    NAME: "create source folder structure in target",
    RUNSTEPS: [{ACTION: create_folder_structure}],
    LOG: {LEVEL: logging.DEBUG, MESSAGE: report_folder_structure_creation},
}


def get_corresponding_filepath(source: str, source_dir: str, target_dir: str) -> str:
    relativepath = Path(source).relative_to(source_dir)
    targetpath = Path(target_dir).joinpath(relativepath)
    return str(targetpath)


async def copyfile(source: str, dest: str) -> bool:
    if await aio.path.isfile(dest) and await samecontent(source, dest):
        return True

    return await copy(source, dest)


def get_copy_log_level(_value_: bool) -> int:
    if _value_:
        return logging.DEBUG
    else:
        return logging.ERROR


def report_copy_status(source: str, dest: str, _value_: bool) -> str:
    status = "成功" if _value_ else "失败"
    return f"{source}的文件{status}复制到{dest}"


def create_copyfile_runsteps(source_filepaths: List[str]) -> List[Dict[str, Any]]:
    return [
        {
            NAME: f"copy {source_filepath}",
            ARGUMENTS: [
                {NAME: "source", VALUE: source_filepath},
                {NAME: "dest", VALUE: get_corresponding_filepath},
            ],
            ACTION: copyfile,
            LOG: {LEVEL: get_copy_log_level, MESSAGE: report_copy_status},
        }
        for source_filepath in source_filepaths
    ]


COPY_FILES_RUNSTAGE = {
    NAME: "copy files from source folder to target folder",
    RUNSTEPS: {VALUE: create_copyfile_runsteps, SCHEDULING: PARALLEL},
}

PIPELINE = {
    NAME: "copy directory from source to dest",
    ARGUMENTS: [SOURCE_DIR_ARGUMENT, TARGET_DIR_ARGUMENT],
    RUNSTAGES: [CREATE_FOLDER_STRUCTURE_RUNSTAGE, COPY_FILES_RUNSTAGE],
}


async def main() -> None:
    pipeline = Pipeline(PIPELINE)

    pipeline.print_help()
    scoping = pipeline.run()


if __name__ == "__main__":
    asyncio.run(main())
