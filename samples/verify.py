"""
Illustrate a simple pipeline that can get size/md5sum of files in a directory in parallel.
"""

from __future__ import annotations

import asyncio
import csv
import logging
import os
import sys
from enum import Enum
from pathlib import Path
from typing import Any, ClassVar, Dict, Iterable, List, Optional, Tuple, Union

from streamlined import (
    ACTION,
    ARGPARSE,
    ARGUMENT,
    ARGUMENTS,
    CHOICES,
    CLEANUP,
    DEFAULT,
    HANDLERS,
    HELP,
    LEVEL,
    LOG,
    MESSAGE,
    NAME,
    PARALLEL,
    RUNSTAGE,
    RUNSTAGES,
    RUNSTEP,
    RUNSTEPS,
    SCHEDULING,
    TYPE,
    VALIDATOR,
    VALIDATOR_AFTER_STAGE,
    VALUE,
    Context,
    Pipeline,
    Scoped,
    SimpleExecutor,
)
from streamlined.utils import getsize, md5, walk

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

FILESIZE = "filesize"
FILENAME = "filename"
FILEHASH = "filehash"


class FileSizeReport:
    filesizes: Dict[str, int]

    FIELD_NAMES: ClassVar[List[str]] = [FILESIZE, FILENAME]
    DELIMITER: ClassVar[str] = "\t"
    DEFAULT_OUTPUT_FILENAME = "checksize.csv"

    @staticmethod
    def filesize_adapter(filesize: str) -> int:
        return int(filesize)

    @staticmethod
    def filesize_converter(filesize: int) -> str:
        return str(filesize)

    @classmethod
    def empty(cls) -> FileSizeReport:
        return cls()

    @classmethod
    def load(cls, filepath: Optional[str] = None) -> FileSizeReport:
        if filepath is None:
            filepath = cls.DEFAULT_OUTPUT_FILENAME

        report = cls()
        with open(filepath, newline="") as csvfile:
            reader = csv.DictReader(csvfile, fieldnames=cls.FIELD_NAMES, delimiter=cls.DELIMITER)
            for row in reader:
                filesize: int = cls.filesize_adapter(row[FILESIZE])
                filename = row[FILENAME]
                report.add(filename, filesize)
        return report

    def __init__(self, filesizes: Optional[Dict[str, int]] = None) -> None:
        if filesizes is None:
            filesizes = dict()
        self.filesizes = filesizes

    def add(self, filename: str, filesize: int) -> None:
        self.filesizes[filename] = filesize

    def write(self, filepath: Optional[str] = None) -> None:
        if filepath is None:
            filepath = self.DEFAULT_OUTPUT_FILENAME

        with open(filepath, "w", newline="") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=self.FIELD_NAMES, delimiter=self.DELIMITER)
            for filename, filesize in self.filesizes.items():
                writer.writerow({FILENAME: filename, FILESIZE: filesize})

    def to_list(
        self, show_filename_first: bool = True
    ) -> Union[List[Tuple[str, int]], List[Tuple[int, str]]]:
        if show_filename_first:
            return list(self.filesizes.items())
        else:
            return [(filesize, filename) for filename, filesize in self.filesizes.items()]

    def __str__(self) -> str:
        return "\n".join(
            ":".join(str(segment) for segment in filename_and_filesize)
            for filename_and_filesize in self.to_list()
        )


class FileHashReport:
    filehashes: Dict[str, str]

    FIELD_NAMES: ClassVar[List[str]] = [FILEHASH, FILENAME]
    DELIMITER: ClassVar[str] = "\t"
    DEFAULT_OUTPUT_FILENAME = "MD5.csv"

    @classmethod
    def empty(cls) -> FileHashReport:
        return cls()

    @classmethod
    def load(cls, filepath: Optional[str] = None) -> FileHashReport:
        if filepath is None:
            filepath = cls.DEFAULT_OUTPUT_FILENAME

        report = cls()
        with open(filepath, newline="") as csvfile:
            reader = csv.DictReader(csvfile, fieldnames=cls.FIELD_NAMES, delimiter=cls.DELIMITER)
            for row in reader:
                filehash = row[FILEHASH]
                filename = row[FILENAME]
                report.add(filename, filehash)
        return report

    def __init__(self, filehashes: Optional[Dict[str, str]] = None) -> None:
        if filehashes is None:
            filehashes = dict()
        self.filehashes = filehashes

    def add(self, filename: str, filehash: str) -> None:
        self.filehashes[filename] = filehash

    def write(self, filepath: Optional[str] = None) -> None:
        if filepath is None:
            filepath = self.DEFAULT_OUTPUT_FILENAME

        with open(filepath, "w", newline="") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=self.FIELD_NAMES, delimiter=self.DELIMITER)
            for filename, filehash in self.filehashes.items():
                writer.writerow({FILENAME: filename, FILEHASH: filehash})

    def to_list(
        self, show_filename_first: bool = True
    ) -> Union[List[Tuple[str, str]], List[Tuple[str, str]]]:
        if show_filename_first:
            return list(self.filehashes.items())
        else:
            return [(filehash, filename) for filename, filehash in self.filehashes.items()]

    def __str__(self) -> str:
        return "\n".join(
            ":".join(str(segment) for segment in filename_and_filehash)
            for filename_and_filehash in self.to_list()
        )


# Arguments


def get_current_dir() -> Path:
    return Path(os.getcwd())


def check_source_dir_exists(source_dir: str) -> bool:
    return os.path.isdir(source_dir)


def report_source_dir(source_dir: str) -> str:
    return f"操作的源文件夹为{source_dir}"


def report_nonexisting_source_dir(source_dir: str) -> str:
    return f"源文件夹{source_dir}不存在"


def crash(reason: Union[str, int] = 1) -> None:
    sys.exit(reason)


SOURCE_DIR_ARGUMENT: Dict[str, Any] = {
    NAME: "source_dir",
    VALUE: {
        TYPE: ARGPARSE,
        NAME: ["-s", "--src"],
        DEFAULT: "",
        HELP: "请提供操作的源文件夹",
    },
    VALIDATOR: {
        VALIDATOR_AFTER_STAGE: {
            ACTION: check_source_dir_exists,
            HANDLERS: {
                True: {LOG: {LEVEL: logging.INFO, MESSAGE: report_source_dir}},
                False: {
                    LOG: {LEVEL: logging.WARNING, MESSAGE: report_nonexisting_source_dir},
                },
            },
        }
    },
}


def report_source_filesize_output_filepath(source_filesize_output_filepath: str) -> str:
    return f"源文件大小报告将保存在{source_filesize_output_filepath}"


def report_source_filehash_output_filepath(source_filehash_output_filepath: str) -> str:
    return f"源文件md5报告将保存在{source_filehash_output_filepath}"


WRITE_SOURCE_FILESIZES_ARGUMENT: Dict[str, Any] = {
    NAME: "source_filesize_output_filepath",
    VALUE: {
        TYPE: ARGPARSE,
        NAME: ["-wss", "--write-source-filesize"],
        DEFAULT: ".checksize.source.csv",
        HELP: "请提供源文件大小报告储存位置",
    },
    LOG: {LEVEL: logging.INFO, MESSAGE: report_source_filesize_output_filepath},
}

WRITE_SOURCE_FILEHASHES_ARGUMENT: Dict[str, Any] = {
    NAME: "source_filehash_output_filepath",
    VALUE: {
        TYPE: ARGPARSE,
        NAME: ["-wsh", "--write-source-filehash"],
        DEFAULT: ".md5.source.csv",
        HELP: "请提供源文件md5报告储存位置",
    },
    LOG: {LEVEL: logging.INFO, MESSAGE: report_source_filehash_output_filepath},
}


def listfiles(directory: Path) -> Iterable[str]:
    for filepath in walk(directory):
        if filepath.is_file():
            yield str(filepath)


def check_target_dir_exists(target_dir: str) -> bool:
    return os.path.isdir(target_dir)


def report_target_dir(target_dir: str) -> str:
    return f"操作的目标文件夹为{target_dir}"


def report_nonexisting_target_dir(target_dir: str) -> str:
    return f"目标文件夹{target_dir}不存在"


TARGET_DIR_ARGUMENT: Dict[str, Any] = {
    NAME: "target_dir",
    VALUE: {
        TYPE: ARGPARSE,
        NAME: ["-t", "--target"],
        DEFAULT: "",
        HELP: "请提供操作的目标文件夹",
    },
    VALIDATOR: {
        VALIDATOR_AFTER_STAGE: {
            ACTION: check_target_dir_exists,
            HANDLERS: {
                True: {LOG: {LEVEL: logging.INFO, MESSAGE: report_target_dir}},
                False: {
                    LOG: {LEVEL: logging.WARNING, MESSAGE: report_nonexisting_target_dir},
                },
            },
        }
    },
}


def report_target_filesize_output_filepath(target_filesize_output_filepath: str) -> str:
    return f"目标文件大小报告将保存在{target_filesize_output_filepath}"


def report_target_filehash_output_filepath(target_filehash_output_filepath: str) -> str:
    return f"目标文件md5报告将保存在{target_filehash_output_filepath}"


WRITE_TARGET_FILESIZES_ARGUMENT: Dict[str, Any] = {
    NAME: "target_filesize_output_filepath",
    VALUE: {
        TYPE: ARGPARSE,
        NAME: ["-wts", "--write-target-filesize"],
        DEFAULT: ".checksize.target.csv",
        HELP: "请提供目标文件大小报告储存位置",
    },
    LOG: {LEVEL: logging.INFO, MESSAGE: report_target_filesize_output_filepath},
}


WRITE_TARGET_FILEHASHES_ARGUMENT: Dict[str, Any] = {
    NAME: "target_filehash_output_filepath",
    VALUE: {
        TYPE: ARGPARSE,
        NAME: ["-wth", "--write-target-filehash"],
        DEFAULT: ".md5.target.csv",
        HELP: "请提供目标文件md5报告储存位置",
    },
    LOG: {LEVEL: logging.INFO, MESSAGE: report_target_filehash_output_filepath},
}


class Operation(str, Enum):
    @classmethod
    def get_all_operations(cls) -> List[str]:
        return [operation.value for operation in cls]

    Checksize: str = "checksize"
    Checksum: str = "checksum"


ALL_OPERATIONS = Operation.get_all_operations()


def report_operations(operations: List[str]) -> str:
    return f'将执行操作包括「{", ".join(operations)}」'


OPERATION_ARGUMENT: Dict[str, Any] = {
    NAME: "operations",
    VALUE: {
        TYPE: ARGPARSE,
        NAME: ["-op", "--operation"],
        ACTION: "append",
        CHOICES: ALL_OPERATIONS,
        HELP: "对源文件夹与目标文件夹的操作",
    },
    LOG: {LEVEL: logging.INFO, MESSAGE: report_operations},
}


def should_get_source_filesizes(operations: List[str], source_dir: str) -> bool:
    return bool(source_dir) and Operation.Checksize in operations


def should_get_source_filehashes(operations: List[str], source_dir: str) -> bool:
    return bool(source_dir) and Operation.Checksum in operations


def report_get_source_filesizes(get_source_filesizes: bool) -> str:
    if get_source_filesizes:
        return "会统计源文件夹文件大小"
    else:
        return "不会统计源文件夹文件大小"


def report_get_source_filehashes(get_source_filehashes: bool) -> str:
    if get_source_filehashes:
        return "会统计源文件夹文件md5"
    else:
        return "不会统计源文件夹文件md5"


GET_SOURCE_FILESIZES_ARGUMENT: Dict[str, Any] = {
    NAME: "get_source_filesizes",
    VALUE: should_get_source_filesizes,
    LOG: {LEVEL: logging.INFO, VALUE: report_get_source_filesizes},
}

GET_SOURCE_FILEHASHES_ARGUMENT: Dict[str, Any] = {
    NAME: "get_source_filehashes",
    VALUE: should_get_source_filehashes,
    LOG: {LEVEL: logging.INFO, VALUE: report_get_source_filehashes},
}


def should_get_target_filesizes(operations: List[str], target_dir: str) -> bool:
    return bool(target_dir) and Operation.Checksize in operations


def should_get_target_filehashes(operations: List[str], target_dir: str) -> bool:
    return bool(target_dir) and Operation.Checksum in operations


def report_get_target_filesizes(get_target_filesizes: bool) -> str:
    if get_target_filesizes:
        return "会统计目标文件夹文件大小"
    else:
        return "不会统计目标文件夹文件大小"


def report_get_target_filehashes(get_target_filehashes: bool) -> str:
    if get_target_filehashes:
        return "会统计目标文件夹文件md5"
    else:
        return "不会统计目标文件夹文件md5"


GET_TARGET_FILESIZES_ARGUMENT: Dict[str, Any] = {
    NAME: "get_target_filesizes",
    VALUE: should_get_target_filesizes,
    LOG: {LEVEL: logging.INFO, VALUE: report_get_target_filesizes},
}

GET_TARGET_FILEHASHES_ARGUMENT: Dict[str, Any] = {
    NAME: "get_target_filehashes",
    VALUE: should_get_target_filehashes,
    LOG: {LEVEL: logging.INFO, VALUE: report_get_target_filehashes},
}

# Runstage


async def estimate_filesize(filepath: str) -> int:
    return await getsize(filepath)


async def estimate_filehash(filepath: str) -> str:
    return await md5(filepath)


def add_filesize_to_report(filesize_report: FileSizeReport, filepath: str, filesize: int) -> None:
    filesize_report.add(filepath, filesize)


def add_filehash_to_report(filehash_report: FileHashReport, filepath: str, filehash: str) -> None:
    filehash_report.add(filepath, filehash)


def create_filesize_report_runsteps(filepaths: List[str]) -> List[Dict[str, Any]]:
    return [
        {
            RUNSTEP: {
                NAME: f"get size for {filepath}",
                ARGUMENTS: [
                    {ARGUMENT: {NAME: "filepath", VALUE: filepath}},
                    {ARGUMENT: {NAME: FILESIZE, VALUE: estimate_filesize}},
                ],
                ACTION: add_filesize_to_report,
            },
        }
        for filepath in filepaths
    ]


def create_filehash_report_runsteps(filepaths: List[str]) -> List[Dict[str, Any]]:
    return [
        {
            RUNSTEP: {
                NAME: f"get hash for {filepath}",
                ARGUMENTS: [
                    {ARGUMENT: {NAME: "filepath", VALUE: filepath}},
                    {ARGUMENT: {NAME: FILEHASH, VALUE: estimate_filehash}},
                ],
                ACTION: add_filehash_to_report,
            },
        }
        for filepath in filepaths
    ]


def log_filesize_report(filesize_report: FileSizeReport) -> str:
    return "\n" + str(filesize_report) + "\n"


def log_filehash_report(filehash_report: FileHashReport) -> str:
    return "\n" + str(filehash_report) + "\n"


def get_source_filepaths(source_dir: str) -> List[str]:
    return list(listfiles(Path(source_dir)))


def get_target_filepaths(target_dir: str) -> List[str]:
    return list(listfiles(Path(target_dir)))


def save_source_filesize_report(
    _scoped_: Scoped, filesize_report: FileSizeReport, source_filesize_output_filepath: str
) -> None:
    filesize_report.write(source_filesize_output_filepath)
    _scoped_.global_scope["source_filesize_report"] = filesize_report


def save_source_filehash_report(
    _scoped_: Scoped, filehash_report: FileHashReport, source_filehash_output_filepath: str
) -> None:
    filehash_report.write(source_filehash_output_filepath)
    _scoped_.global_scope["source_filehash_report"] = filehash_report


SOURCE_DIR_FILESIZE_RUNSTAGE: Dict[str, Any] = {
    NAME: "create filesize report for source files",
    ARGUMENTS: [
        {NAME: "filesize_report", VALUE: FileSizeReport.empty},
        {NAME: "filepaths", VALUE: get_source_filepaths},
    ],
    RUNSTEPS: {VALUE: create_filesize_report_runsteps, SCHEDULING: PARALLEL},
    LOG: {LEVEL: logging.DEBUG, MESSAGE: log_filesize_report},
    CLEANUP: save_source_filesize_report,
}


SOURCE_DIR_FILEHASH_RUNSTAGE: Dict[str, Any] = {
    NAME: "create filehash report for source files",
    ARGUMENTS: [
        {NAME: "filehash_report", VALUE: FileHashReport.empty},
        {NAME: "filepaths", VALUE: get_source_filepaths},
    ],
    RUNSTEPS: {VALUE: create_filehash_report_runsteps, SCHEDULING: PARALLEL},
    LOG: {LEVEL: logging.DEBUG, MESSAGE: log_filehash_report},
    CLEANUP: save_source_filehash_report,
}


def save_target_filesize_report(
    _scoped_: Scoped, filesize_report: FileSizeReport, target_filesize_output_filepath: str
) -> None:
    filesize_report.write(target_filesize_output_filepath)
    _scoped_.global_scope["target_filesize_report"] = filesize_report


def save_target_filehash_report(
    _scoped_: Scoped, filehash_report: FileHashReport, target_filehash_output_filepath: str
) -> None:
    filehash_report.write(target_filehash_output_filepath)
    _scoped_.global_scope["target_filehash_report"] = filehash_report


TARGET_DIR_FILESIZE_RUNSTAGE: Dict[str, Any] = {
    NAME: "create filesize report for target files",
    ARGUMENTS: [
        {NAME: "filesize_report", VALUE: FileSizeReport.empty},
        {NAME: "filepaths", VALUE: get_target_filepaths},
    ],
    RUNSTEPS: {VALUE: create_filesize_report_runsteps, SCHEDULING: PARALLEL},
    LOG: {LEVEL: logging.DEBUG, MESSAGE: log_filesize_report},
    CLEANUP: save_target_filesize_report,
}

TARGET_DIR_FILEHASH_RUNSTAGE: Dict[str, Any] = {
    NAME: "create filehash report for target files",
    ARGUMENTS: [
        {NAME: "filehash_report", VALUE: FileHashReport.empty},
        {NAME: "filepaths", VALUE: get_target_filepaths},
    ],
    RUNSTEPS: {VALUE: create_filehash_report_runsteps, SCHEDULING: PARALLEL},
    LOG: {LEVEL: logging.DEBUG, MESSAGE: log_filehash_report},
    CLEANUP: save_target_filehash_report,
}

# Pipeline


def create_runstages(
    get_source_filesizes: bool,
    get_target_filesizes: bool,
    get_source_filehashes: bool,
    get_target_filehashes: bool,
) -> List[Dict[str, Any]]:
    runstages = []

    if get_source_filesizes:
        runstages.append({RUNSTAGE: SOURCE_DIR_FILESIZE_RUNSTAGE})
    if get_target_filesizes:
        runstages.append({RUNSTAGE: TARGET_DIR_FILESIZE_RUNSTAGE})
    if get_source_filehashes:
        runstages.append({RUNSTAGE: SOURCE_DIR_FILEHASH_RUNSTAGE})
    if get_target_filehashes:
        runstages.append({RUNSTAGE: TARGET_DIR_FILEHASH_RUNSTAGE})

    return runstages


def PRINT_HELP_IF_REQUESTED(pipeline: Pipeline) -> None:
    args = sys.argv
    if "-h" in args or "--help" in args:
        pipeline.print_help()
        sys.exit(0)


PIPELINE = {
    ARGUMENTS: [
        {ARGUMENT: SOURCE_DIR_ARGUMENT},
        {ARGUMENT: TARGET_DIR_ARGUMENT},
        {ARGUMENT: OPERATION_ARGUMENT},
        {ARGUMENT: WRITE_SOURCE_FILESIZES_ARGUMENT},
        {ARGUMENT: WRITE_SOURCE_FILEHASHES_ARGUMENT},
        {ARGUMENT: WRITE_TARGET_FILESIZES_ARGUMENT},
        {ARGUMENT: WRITE_TARGET_FILEHASHES_ARGUMENT},
        {ARGUMENT: GET_SOURCE_FILESIZES_ARGUMENT},
        {ARGUMENT: GET_SOURCE_FILEHASHES_ARGUMENT},
        {ARGUMENT: GET_TARGET_FILESIZES_ARGUMENT},
        {ARGUMENT: GET_TARGET_FILEHASHES_ARGUMENT},
    ],
    RUNSTAGES: {VALUE: create_runstages},
}


async def main() -> None:
    context, scoping = Context.new(SimpleExecutor())

    pipeline = Pipeline(PIPELINE)

    PRINT_HELP_IF_REQUESTED(pipeline)
    scoped = await pipeline.apply_into(context)

    # Display scoping tree
    scoping.update(scoped)
    # scoping._tree.show()


if __name__ == "__main__":
    asyncio.run(main())
