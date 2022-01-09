"""
Illustrate a simple pipeline that can get size/md5sum of files in a directory in parallel.
"""

from __future__ import annotations

import asyncio
import csv
import logging
import os
import sys
from enum import Enum, auto
from pathlib import Path
from typing import (
    Any,
    ClassVar,
    Dict,
    Generic,
    Iterable,
    List,
    Mapping,
    Optional,
    Tuple,
    TypeVar,
    Union,
)

from streamlined import (
    ACTION,
    ARGPARSE,
    ARGUMENT,
    ARGUMENTS,
    CHOICES,
    CLEANUP,
    HANDLERS,
    HELP,
    LEVEL,
    LOG,
    MESSAGE,
    NAME,
    PARALLEL,
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
HAS_SOURCE_DIR = "has_source_dir"
HAS_TARGET_DIR = "has_target_dir"
SOURCE_FILEPATHS = "source_filepaths"
TARGET_FILEPATHS = "target_filepaths"
SOURCE_FILESIZE_FILEPATH = "source_filesize_filepath"
TARGET_FILESIZE_FILEPATH = "target_filesize_filepath"

SOURCE_DIR = "source_dir"
TARGET_DIR = "target_dir"
SOURCE_LOGNAME = "源"
TARGET_LOGNAME = "目标"

K = TypeVar("K")
V = TypeVar("V")


class AbstractReport(Generic[K, V], Mapping[K, V]):
    report: Dict[K, V]
    DELIMITER: ClassVar[str] = "\t"

    @property
    def KEY_NAME(self) -> str:
        raise NotImplementedError()

    @property
    def VALUE_NAME(self) -> str:
        raise NotImplementedError()

    @property
    def FIELD_NAMES(self) -> List[str]:
        return [self.KEY_NAME, self.VALUE_NAME]

    @classmethod
    def convert_key(self, key: str) -> K:
        return key

    @classmethod
    def convert_value(self, value: str) -> V:
        return value

    @classmethod
    def empty(cls) -> AbstractReport[K, V]:
        return cls()

    def __init__(self) -> None:
        super().__init__()
        self.report = dict()

    def __getitem__(self, key: K) -> V:
        return self.report[key]

    def __setitem__(self, key: K, value: V) -> None:
        self.report[key] = value

    def __str__(self) -> str:
        return "\n".join(":".join(str(part) for part in line) for line in self.to_list())

    def to_list(self, key_first: bool = True) -> Union[List[Tuple[K, V]], List[Tuple[V, K]]]:
        if key_first:
            return list(self.report.items())
        else:
            return [(value, key) for key, value in self.report.items()]

    def write(self, filepath: str, key_first: bool = True) -> None:
        if key_first:
            fieldnames = self.FIELD_NAMES
        else:
            fieldnames = list(reversed(self.FIELD_NAMES))

        with open(filepath, "w", newline="") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=self.DELIMITER)
            for key, value in self.report.items():
                writer.writerow({self.KEY_NAME: key, self.VALUE_NAME: value})

    def load(self, filepath: str, key_first: bool = True) -> None:
        if key_first:
            fieldnames = self.FIELD_NAMES
        else:
            fieldnames = list(reversed(self.FIELD_NAMES))

        with open(filepath, newline="") as csvfile:
            reader = csv.DictReader(csvfile, fieldnames=fieldnames, delimiter=self.DELIMITER)
            for row in reader:
                key = self.convert_key(row[self.KEY_NAME])
                value = self.convert_value(row[self.VALUE_NAME])
                self[key] = value


class FileSizeReport(AbstractReport[str, int]):
    @property
    def KEY_NAME(self) -> str:
        return FILENAME

    @property
    def VALUE_NAME(self) -> str:
        return FILESIZE

    @classmethod
    def convert_key(self, key: str) -> str:
        return key

    @classmethod
    def convert_value(self, value: str) -> int:
        return int(value)


class FileHashReport(AbstractReport[str, str]):
    @property
    def KEY_NAME(self) -> str:
        return FILENAME

    @property
    def VALUE_NAME(self) -> str:
        return FILEHASH


# Arguments


def crash(reason: Union[str, int] = 1) -> None:
    sys.exit(reason)


class ReportCreationType(Enum):
    Generate = auto()
    Load = auto()
    Skip = auto()

    @classmethod
    def determine_report_type(cls, has_dir: bool, load_filepath: str) -> ReportCreationType:
        if has_dir:
            return cls.Generate
        else:
            if load_filepath is None:
                return cls.Skip
            else:
                return cls.Load


def is_dir(dirpath: Optional[str]) -> bool:
    return dirpath is not None and os.path.isdir(dirpath)


def check_and_set_dir_exists(
    dirpath: Optional[str], name: str, dictionary: Dict[str, Any]
) -> bool:
    dir_exists = is_dir(dirpath)
    dictionary[name] = dir_exists
    return dir_exists


def check_source_dir_exists(source_dir: Optional[str], _scoped_: Scoped) -> bool:
    return check_and_set_dir_exists(source_dir, HAS_SOURCE_DIR, _scoped_.global_scope)


def listfiles(directory: Path) -> Iterable[str]:
    for filepath in walk(directory):
        if filepath.is_file():
            yield str(filepath)


def set_dirfiles(dirpath: str, name: str, dictionary: Dict[str, Any]) -> List[str]:
    filepaths = list(listfiles(Path(dirpath)))
    dictionary[name] = filepaths
    return filepaths


def set_source_filepaths(source_dir: str, _scoped_: Scoped) -> List[str]:
    return set_dirfiles(source_dir, SOURCE_FILEPATHS, _scoped_.global_scope)


def report_dirpath(dirpath: str, logname: str = "") -> str:
    return f"操作的{logname}文件夹为{dirpath}"


def report_nonexisting_dirpath(dirpath: Optional[str], logname: str = "") -> str:
    if dirpath is None:
        dirpath = ""
    return f"{logname}文件夹{dirpath}未提供或没有指向合理位置"


def report_source_dir(source_dir: str) -> str:
    return report_dirpath(source_dir, SOURCE_LOGNAME)


def report_nonexisting_source_dir(source_dir: Optional[str]) -> str:
    return report_nonexisting_dirpath(source_dir, SOURCE_LOGNAME)


def create_help_for_dir(logname: str) -> str:
    return f"请提供操作的{logname}文件夹"


SOURCE_DIR_ARGUMENT: Dict[str, Any] = {
    NAME: "source_dir",
    VALUE: {TYPE: ARGPARSE, NAME: ["-s", "--src"], HELP: create_help_for_dir(SOURCE_LOGNAME)},
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
                False: {
                    LOG: {LEVEL: logging.WARNING, MESSAGE: report_nonexisting_source_dir},
                },
            },
        }
    },
}


def report_filesize_filepath(has_dir: bool, filesize_filepath: Optional[str], logname: str) -> str:
    if filesize_filepath is None:
        return f"{logname}文件大小报告储存位置未提供"

    if has_dir:
        return f"{logname}文件大小报告将保存在{filesize_filepath}"
    else:
        return f"{logname}文件大小报告将从{filesize_filepath}读取"


def report_source_filesize_filepath(
    has_source_dir: bool, source_filesize_filepath: Optional[str]
) -> str:
    return report_filesize_filepath(has_source_dir, source_filesize_filepath, SOURCE_LOGNAME)


def create_help_for_filesize_filepath(dirname: str, logname: str) -> str:
    return f"请提供{logname}文件大小报告储存位置。当提供{dirname}时，报告会被写入此位置；当{dirname}未提供时，报告会从此位置读取。"


SOURCE_FILESIZE_FILEPATH_ARGUMENT: Dict[str, Any] = {
    NAME: SOURCE_FILESIZE_FILEPATH,
    VALUE: {
        TYPE: ARGPARSE,
        NAME: ["-ss", "--source-filesize"],
        HELP: create_help_for_filesize_filepath(SOURCE_DIR, SOURCE_LOGNAME),
    },
    LOG: {LEVEL: logging.INFO, MESSAGE: report_source_filesize_filepath},
}


def determine_source_filesize_report_type(
    has_source_dir: bool, source_filesize_filepath: str
) -> ReportCreationType:
    return ReportCreationType.determine_report_type(has_source_dir, source_filesize_filepath)


SOURCE_FILESIZE_REPORT_TYPE: Dict[str, Any] = {
    NAME: "source_filesize_report_type",
    VALUE: determine_source_filesize_report_type,
}


def report_filehash_filepath(has_dir: bool, filepath: str, logname: str) -> str:
    if filepath is None:
        return f"{logname}文件md5报告储存位置未提供"

    if has_dir:
        return f"{logname}文件md5报告将保存在{filepath}"
    else:
        return f"{logname}文件md5报告将从{filepath}读取"


def report_source_filehash_filepath(has_source_dir: bool, source_filehash_filepath: str) -> str:
    return report_filehash_filepath(has_source_dir, source_filehash_filepath, SOURCE_LOGNAME)


def create_help_for_filehash_filepath(dirname: str, logname: str) -> str:
    return f"请提供{logname}文件md5报告储存位置。当提供{dirname}时，报告会被写入此位置；当{dirname}未提供时，报告会从此位置读取。"


SOURCE_FILEHASH_FILEPATH_ARGUMENT: Dict[str, Any] = {
    NAME: "source_filehash_filepath",
    VALUE: {
        TYPE: ARGPARSE,
        NAME: ["-sh", "--source-filehash"],
        HELP: create_help_for_filehash_filepath(SOURCE_DIR, SOURCE_LOGNAME),
    },
    LOG: {LEVEL: logging.INFO, MESSAGE: report_source_filehash_filepath},
}


def determine_source_filehash_report_type(
    has_source_dir: bool, source_filehash_filepath: str
) -> ReportCreationType:
    return ReportCreationType.determine_report_type(has_source_dir, source_filehash_filepath)


SOURCE_FILEHASH_REPORT_TYPE: Dict[str, Any] = {
    NAME: "source_filehash_report_type",
    VALUE: determine_source_filehash_report_type,
}


def check_target_dir_exists(target_dir: Optional[str], _scoped_: Scoped) -> bool:
    return check_and_set_dir_exists(target_dir, HAS_TARGET_DIR, _scoped_.global_scope)


def set_target_filepaths(target_dir: str, _scoped_: Scoped) -> List[str]:
    return set_dirfiles(target_dir, TARGET_FILEPATHS, _scoped_.global_scope)


def report_target_dir(target_dir: str) -> str:
    return report_dirpath(target_dir, TARGET_LOGNAME)


def report_nonexisting_target_dir(target_dir: str) -> str:
    return report_nonexisting_dirpath(target_dir, SOURCE_LOGNAME)


TARGET_DIR_ARGUMENT: Dict[str, Any] = {
    NAME: "target_dir",
    VALUE: {TYPE: ARGPARSE, NAME: ["-t", "--target"], HELP: create_help_for_dir(TARGET_LOGNAME)},
    VALIDATOR: {
        VALIDATOR_AFTER_STAGE: {
            ACTION: check_target_dir_exists,
            HANDLERS: {
                True: {
                    LOG: {LEVEL: logging.INFO, MESSAGE: report_target_dir},
                    ACTION: set_target_filepaths,
                },
                False: {
                    LOG: {LEVEL: logging.WARNING, MESSAGE: report_nonexisting_target_dir},
                },
            },
        }
    },
}


def report_target_filesize_filepath(has_target_dir: bool, target_filesize_filepath: str) -> str:
    return report_filesize_filepath(has_target_dir, target_filesize_filepath, TARGET_LOGNAME)


TARGET_FILESIZE_FILEPATH_ARGUMENT: Dict[str, Any] = {
    NAME: "target_filesize_filepath",
    VALUE: {
        TYPE: ARGPARSE,
        NAME: ["-ts", "--target-filesize"],
        HELP: create_help_for_filesize_filepath(TARGET_DIR, TARGET_LOGNAME),
    },
    LOG: {LEVEL: logging.INFO, MESSAGE: report_target_filesize_filepath},
}


def determine_target_filesize_report_type(
    has_source_dir: bool, target_filesize_report_type: str
) -> ReportCreationType:
    return ReportCreationType.determine_report_type(has_source_dir, target_filesize_report_type)


TARGET_FILESIZE_REPORT_TYPE: Dict[str, Any] = {
    NAME: "target_filesize_report_type",
    VALUE: determine_target_filesize_report_type,
}


def report_target_filehash_filepath(has_target_dir: bool, target_filehash_filepath: str) -> str:
    return report_filehash_filepath(has_target_dir, target_filehash_filepath, TARGET_LOGNAME)


TARGET_FILEHASH_FILEPATH_ARGUMENT: Dict[str, Any] = {
    NAME: "target_filehash_filepath",
    VALUE: {
        TYPE: ARGPARSE,
        NAME: ["-th", "--target-filehash"],
        HELP: create_help_for_filehash_filepath(TARGET_DIR, TARGET_LOGNAME),
    },
    LOG: {LEVEL: logging.INFO, MESSAGE: report_target_filehash_filepath},
}


def determine_target_filehash_report_type(
    has_source_dir: bool, target_filehash_report_type: str
) -> ReportCreationType:
    return ReportCreationType.determine_report_type(has_source_dir, target_filehash_report_type)


TARGET_FILEHASH_REPORT_TYPE: Dict[str, Any] = {
    NAME: "target_filehash_report_type",
    VALUE: determine_target_filehash_report_type,
}


class Operation(str, Enum):
    @classmethod
    def get_all_operations(cls) -> List[str]:
        return [operation.value for operation in cls]

    Checksize: str = "checksize"
    Checksum: str = "checksum"


ALL_OPERATIONS = Operation.get_all_operations()


def report_operations(operations: List[str], _scoped_: Scoped) -> str:
    for operation in ALL_OPERATIONS:
        has_operation = operation in operations
        _scoped_.global_scope[f"will_{operation}"] = has_operation

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


# Runstage


async def estimate_filesize(filepath: str) -> int:
    return await getsize(filepath)


async def estimate_filehash(filepath: str) -> str:
    return await md5(filepath)


def add_filesize_to_report(filesize_report: FileSizeReport, filepath: str, filesize: int) -> None:
    filesize_report[filepath] = filesize


def add_filehash_to_report(filehash_report: FileHashReport, filepath: str, filehash: str) -> None:
    filehash_report[filepath] = filehash


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


def log_report(report: AbstractReport[K, V]) -> str:
    return "\n" + str(report) + "\n"


def log_filesize_report(filesize_report: FileSizeReport) -> str:
    return log_report(filesize_report)


def log_filehash_report(filehash_report: FileHashReport) -> str:
    return log_report(filehash_report)


def get_source_filepaths(source_filepaths: List[str]) -> List[str]:
    return source_filepaths


def save_source_filesize_report(
    _scoped_: Scoped, filesize_report: FileSizeReport, source_filesize_filepath: str
) -> None:
    filesize_report.write(source_filesize_filepath)
    _scoped_.global_scope["source_filesize_report"] = filesize_report


def read_source_filesize_report(_scoped_: Scoped, source_filesize_filepath: str) -> FileSizeReport:
    source_filesize_report = FileSizeReport.load(source_filesize_filepath)
    _scoped_.global_scope["source_filesize_report"] = source_filesize_report
    return source_filesize_report


GENERATE_SOURCE_FILESIZE_REPORT_RUNSTAGE: Dict[str, Any] = {
    NAME: "create filesize report for source files",
    ARGUMENTS: [
        {NAME: "filesize_report", VALUE: FileSizeReport.empty},
        {NAME: "filepaths", VALUE: get_source_filepaths},
    ],
    RUNSTEPS: {VALUE: create_filesize_report_runsteps, SCHEDULING: PARALLEL},
    LOG: {LEVEL: logging.DEBUG, MESSAGE: log_filesize_report},
    CLEANUP: save_source_filesize_report,
}

LOAD_SOURCE_FILESIZE_REPORT_RUNSTAGE: Dict[str, Any] = {
    RUNSTEPS: [{ACTION: read_source_filesize_report}]
}


def save_source_filehash_report(
    _scoped_: Scoped, filehash_report: FileHashReport, source_filehash_filepath: str
) -> None:
    filehash_report.write(source_filehash_filepath)
    _scoped_.global_scope["source_filehash_report"] = filehash_report


GENERATE_SOURCE_FILEHASH_REPORT_RUNSTAGE: Dict[str, Any] = {
    NAME: "create filehash report for source files",
    ARGUMENTS: [
        {NAME: "filehash_report", VALUE: FileHashReport.empty},
        {NAME: "filepaths", VALUE: get_source_filepaths},
    ],
    RUNSTEPS: {VALUE: create_filehash_report_runsteps, SCHEDULING: PARALLEL},
    LOG: {LEVEL: logging.DEBUG, MESSAGE: log_filehash_report},
    CLEANUP: save_source_filehash_report,
}


def read_source_filehash_report(_scoped_: Scoped, source_filehash_filepath: str) -> FileHashReport:
    source_filehash_report = FileHashReport.load(source_filehash_filepath)
    _scoped_.global_scope["source_filehash_report"] = source_filehash_report
    return source_filehash_report


LOAD_SOURCE_FILEHASH_REPORT_RUNSTAGE: Dict[str, Any] = {
    RUNSTEPS: [{ACTION: read_source_filehash_report}]
}


def get_target_filepaths(target_filepaths: List[str]) -> List[str]:
    return target_filepaths


def save_target_filesize_report(
    _scoped_: Scoped, filesize_report: FileSizeReport, target_filesize_filepath: str
) -> None:
    filesize_report.write(target_filesize_filepath)
    _scoped_.global_scope["target_filesize_report"] = filesize_report


GENERATE_TARGET_FILESIZE_REPORT_RUNSTAGE: Dict[str, Any] = {
    NAME: "create filesize report for target files",
    ARGUMENTS: [
        {NAME: "filesize_report", VALUE: FileSizeReport.empty},
        {NAME: "filepaths", VALUE: get_target_filepaths},
    ],
    RUNSTEPS: {VALUE: create_filesize_report_runsteps, SCHEDULING: PARALLEL},
    LOG: {LEVEL: logging.DEBUG, MESSAGE: log_filesize_report},
    CLEANUP: save_target_filesize_report,
}


def read_target_filesize_report(_scoped_: Scoped, target_filesize_filepath: str) -> FileSizeReport:
    target_filesize_report = FileSizeReport.load(target_filesize_filepath)
    _scoped_.global_scope["target_filesize_report"] = target_filesize_report
    return target_filesize_report


LOAD_TARGET_FILESIZE_REPORT_RUNSTAGE: Dict[str, Any] = {
    RUNSTEPS: [{ACTION: read_target_filesize_report}]
}


def save_target_filehash_report(
    _scoped_: Scoped, filehash_report: FileHashReport, target_filehash_filepath: str
) -> None:
    filehash_report.write(target_filehash_filepath)
    _scoped_.global_scope["target_filehash_report"] = filehash_report


GENERATE_TARGET_FILEHASH_REPORT_RUNSTAGE: Dict[str, Any] = {
    NAME: "create filehash report for target files",
    ARGUMENTS: [
        {NAME: "filehash_report", VALUE: FileHashReport.empty},
        {NAME: "filepaths", VALUE: get_target_filepaths},
    ],
    RUNSTEPS: {VALUE: create_filehash_report_runsteps, SCHEDULING: PARALLEL},
    LOG: {LEVEL: logging.DEBUG, MESSAGE: log_filehash_report},
    CLEANUP: save_target_filehash_report,
}


def read_target_filehash_report(_scoped_: Scoped, target_filehash_filepath: str) -> FileHashReport:
    target_filehash_report = FileHashReport.load(target_filehash_filepath)
    _scoped_.global_scope["target_filehash_report"] = target_filehash_report
    return target_filehash_report


LOAD_TARGET_FILEHASH_REPORT_RUNSTAGE: Dict[str, Any] = {
    RUNSTEPS: [{ACTION: read_target_filehash_report}]
}
# Pipeline


def create_runstages(
    will_checksize: bool,
    will_checksum: bool,
    source_filesize_report_type: ReportCreationType,
    target_filesize_report_type: ReportCreationType,
    source_filehash_report_type: ReportCreationType,
    target_filehash_report_type: ReportCreationType,
) -> List[Dict[str, Any]]:
    runstages = []

    if will_checksize:
        if source_filesize_report_type is ReportCreationType.Generate:
            runstages.append(GENERATE_SOURCE_FILESIZE_REPORT_RUNSTAGE)
        elif source_filesize_report_type is ReportCreationType.Load:
            runstages.append(LOAD_SOURCE_FILESIZE_REPORT_RUNSTAGE)

        if target_filesize_report_type is ReportCreationType.Generate:
            runstages.append(GENERATE_TARGET_FILESIZE_REPORT_RUNSTAGE)
        elif target_filesize_report_type is ReportCreationType.Load:
            runstages.append(LOAD_TARGET_FILESIZE_REPORT_RUNSTAGE)

    if will_checksum:
        if source_filehash_report_type is ReportCreationType.Generate:
            runstages.append(GENERATE_SOURCE_FILEHASH_REPORT_RUNSTAGE)
        elif source_filehash_report_type is ReportCreationType.Load:
            runstages.append(LOAD_SOURCE_FILEHASH_REPORT_RUNSTAGE)

        if target_filehash_report_type is ReportCreationType.Generate:
            runstages.append(GENERATE_TARGET_FILEHASH_REPORT_RUNSTAGE)
        elif target_filehash_report_type is ReportCreationType.Load:
            runstages.append(LOAD_TARGET_FILEHASH_REPORT_RUNSTAGE)

    return runstages


def PRINT_HELP_IF_REQUESTED(pipeline: Pipeline) -> None:
    args = sys.argv
    if "-h" in args or "--help" in args:
        pipeline.print_help()
        sys.exit(0)


PIPELINE = {
    ARGUMENTS: [
        SOURCE_DIR_ARGUMENT,
        SOURCE_FILESIZE_FILEPATH_ARGUMENT,
        SOURCE_FILESIZE_REPORT_TYPE,
        SOURCE_FILEHASH_FILEPATH_ARGUMENT,
        SOURCE_FILEHASH_FILEPATH_ARGUMENT,
        TARGET_DIR_ARGUMENT,
        TARGET_FILESIZE_FILEPATH_ARGUMENT,
        TARGET_FILESIZE_REPORT_TYPE,
        TARGET_FILEHASH_FILEPATH_ARGUMENT,
        TARGET_FILEHASH_FILEPATH_ARGUMENT,
        OPERATION_ARGUMENT,
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
