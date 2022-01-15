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
from functools import partial
from pathlib import Path
from typing import (
    Any,
    ClassVar,
    Dict,
    Generic,
    Iterable,
    Iterator,
    List,
    Mapping,
    MutableMapping,
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
    IDENTITY_FACTORY,
    LEVEL,
    LOG,
    MESSAGE,
    NAME,
    PARALLEL,
    REQUIRED,
    RUNSTAGES,
    RUNSTEP,
    RUNSTEPS,
    SCHEDULING,
    TYPE,
    VALIDATOR,
    VALIDATOR_AFTER_STAGE,
    VALUE,
    Pipeline,
    Scoped,
    Template,
    TemplateParameter,
    TemplateParameterDefault,
)
from streamlined.utils import (
    EqualValueFormatter,
    ItemPair,
    MissingInSourceFormatter,
    MissingInTargetFormatter,
    UnequalValueFormatter,
    crash,
    dict_cmp,
    getsize,
    md5,
    walk,
)

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

FILESIZE = "filesize"
FILENAME = "filename"
FILEHASH = "filehash"
HAS_SOURCE_DIR = "has_source_dir"
HAS_TARGET_DIR = "has_target_dir"
SOURCE_FILEPATHS = "source_filepaths"
TARGET_FILEPATHS = "target_filepaths"
SOURCE_FILESIZE_FILEPATH = "source_filesize_filepath"
SOURCE_FILEHASH_FILEPATH = "source_filehash_filepath"
TARGET_FILESIZE_FILEPATH = "target_filesize_filepath"
TARGET_FILEHASH_FILEPATH = "target_filehash_filepath"
SOURCE_FILESIZE_REPORT = "source_filesize_report"
SOURCE_FILEHASH_REPORT = "source_filehash_report"
TARGET_FILESIZE_REPORT = "target_filesize_report"
TARGET_FILEHASH_REPORT = "target_filehash_report"

SOURCE = "source"
TARGET = "target"


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

    def __len__(self) -> int:
        return len(self.report)

    def __iter__(self) -> Iterator[K]:
        yield from self.report.keys()

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
        if not os.path.isfile(filepath):
            raise FileNotFoundError(f"cannot find project to load {filepath}")

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


# Common


# Arguments


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
    dirpath: Optional[str], name: str, dictionary: MutableMapping[str, Any]
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


def set_dirfiles(dirpath: str, name: str, dictionary: MutableMapping[str, Any]) -> List[str]:
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


def is_not_dir(filepath: str) -> bool:
    if not filepath:
        return True
    return not os.path.isdir(filepath)


def is_source_filesize_filepath_not_dir(source_filesize_filepath: str) -> bool:
    return is_not_dir(source_filesize_filepath)


def crash_when_filesize_filepath_is_dir(logname: str) -> None:
    reason = f"{logname}文件大小报告储存位置不应该为文件夹"
    crash(reason)


def crash_when_filehash_filepath_is_dir(logname: str) -> None:
    reason = f"{logname}文件md5报告储存位置不应该为文件夹"
    crash(reason)


SOURCE_FILESIZE_FILEPATH_ARGUMENT = {
    NAME: SOURCE_FILESIZE_FILEPATH,
    VALUE: {
        TYPE: ARGPARSE,
        NAME: ["--ss", "--source-filesize"],
        HELP: create_help_for_filesize_filepath(SOURCE_DIR, SOURCE_LOGNAME),
    },
    VALIDATOR: {
        VALIDATOR_AFTER_STAGE: {
            ACTION: is_source_filesize_filepath_not_dir,
            HANDLERS: {
                True: {
                    LOG: {
                        LEVEL: logging.INFO,
                        MESSAGE: report_source_filesize_filepath,
                    },
                },
                False: {ACTION: partial(crash_when_filesize_filepath_is_dir, SOURCE_LOGNAME)},
            },
        }
    },
}


def determine_source_filesize_report_type(
    has_source_dir: bool, source_filesize_filepath: str
) -> ReportCreationType:
    return ReportCreationType.determine_report_type(has_source_dir, source_filesize_filepath)


SOURCE_FILESIZE_REPORT_TYPE = {
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


def is_source_filehash_filepath_not_dir(source_filehash_filepath: str) -> bool:
    return is_not_dir(source_filehash_filepath)


SOURCE_FILEHASH_FILEPATH_ARGUMENT = {
    NAME: SOURCE_FILEHASH_FILEPATH,
    VALUE: {
        TYPE: ARGPARSE,
        NAME: ["--sh", "--source-filehash"],
        HELP: create_help_for_filehash_filepath(SOURCE_DIR, SOURCE_LOGNAME),
    },
    VALIDATOR: {
        VALIDATOR_AFTER_STAGE: {
            ACTION: is_source_filehash_filepath_not_dir,
            HANDLERS: {
                True: {
                    LOG: {
                        LEVEL: logging.INFO,
                        MESSAGE: report_source_filehash_filepath,
                    },
                },
                False: {ACTION: partial(crash_when_filehash_filepath_is_dir, SOURCE_LOGNAME)},
            },
        }
    },
}


def determine_source_filehash_report_type(
    has_source_dir: bool, source_filehash_filepath: str
) -> ReportCreationType:
    return ReportCreationType.determine_report_type(has_source_dir, source_filehash_filepath)


SOURCE_FILEHASH_REPORT_TYPE = {
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
    return report_nonexisting_dirpath(target_dir, TARGET_LOGNAME)


TARGET_DIR_ARGUMENT = {
    NAME: TARGET_DIR,
    VALUE: {TYPE: ARGPARSE, NAME: ["--target"], HELP: create_help_for_dir(TARGET_LOGNAME)},
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


def is_target_filesize_filepath_not_dir(target_filesize_filepath: str) -> bool:
    return is_not_dir(target_filesize_filepath)


TARGET_FILESIZE_FILEPATH_ARGUMENT = {
    NAME: TARGET_FILESIZE_FILEPATH,
    VALUE: {
        TYPE: ARGPARSE,
        NAME: ["--ts", "--target-filesize"],
        HELP: create_help_for_filesize_filepath(TARGET_DIR, TARGET_LOGNAME),
    },
    VALIDATOR: {
        VALIDATOR_AFTER_STAGE: {
            ACTION: is_target_filesize_filepath_not_dir,
            HANDLERS: {
                True: {
                    LOG: {
                        LEVEL: logging.INFO,
                        MESSAGE: report_target_filesize_filepath,
                    },
                },
                False: {ACTION: partial(crash_when_filesize_filepath_is_dir, TARGET_LOGNAME)},
            },
        }
    },
}


def determine_target_filesize_report_type(
    has_target_dir: bool, target_filesize_filepath: str
) -> ReportCreationType:
    return ReportCreationType.determine_report_type(has_target_dir, target_filesize_filepath)


TARGET_FILESIZE_REPORT_TYPE = {
    NAME: "target_filesize_report_type",
    VALUE: determine_target_filesize_report_type,
}


def report_target_filehash_filepath(has_target_dir: bool, target_filehash_filepath: str) -> str:
    return report_filehash_filepath(has_target_dir, target_filehash_filepath, TARGET_LOGNAME)


def is_target_filehash_filepath_not_dir(target_filehash_filepath: str) -> bool:
    return is_not_dir(target_filehash_filepath)


TARGET_FILEHASH_FILEPATH_ARGUMENT = {
    NAME: TARGET_FILEHASH_FILEPATH,
    VALUE: {
        TYPE: ARGPARSE,
        NAME: ["--th", "--target-filehash"],
        HELP: create_help_for_filehash_filepath(TARGET_DIR, TARGET_LOGNAME),
    },
    VALIDATOR: {
        VALIDATOR_AFTER_STAGE: {
            ACTION: is_target_filehash_filepath_not_dir,
            HANDLERS: {
                True: {
                    LOG: {
                        LEVEL: logging.INFO,
                        MESSAGE: report_target_filehash_filepath,
                    },
                },
                False: {ACTION: partial(crash_when_filehash_filepath_is_dir, TARGET_LOGNAME)},
            },
        }
    },
}


def determine_target_filehash_report_type(
    has_target_dir: bool, target_filehash_filepath: str
) -> ReportCreationType:
    return ReportCreationType.determine_report_type(has_target_dir, target_filehash_filepath)


TARGET_FILEHASH_REPORT_TYPE = {
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


OPERATION_ARGUMENT = {
    NAME: "operations",
    VALUE: {
        TYPE: ARGPARSE,
        NAME: ["--op", "--operation"],
        REQUIRED: True,
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


def save_report(
    report: AbstractReport[K, V],
    filepath: Optional[str],
    dictionary: MutableMapping[str, Any],
    keyname: str,
    key_first: bool = False,
) -> None:
    if filepath is not None:
        report.write(filepath, key_first=key_first)
    dictionary[keyname] = report


def load_report(
    report: AbstractReport[K, V],
    filepath: str,
    dictionary: MutableMapping[str, Any],
    keyname: str,
    key_first: bool = False,
) -> AbstractReport[K, V]:
    report.load(filepath, key_first=key_first)
    dictionary[keyname] = report
    return report


def load_source_filesize_report(
    _scoped_: Scoped, source_filesize_filepath: str
) -> AbstractReport[str, int]:
    return load_report(
        FileSizeReport.empty(),
        source_filesize_filepath,
        _scoped_.global_scope,
        SOURCE_FILESIZE_REPORT,
    )


GENERATE_REPORT_TEMPLATE = Template(
    {
        NAME: TemplateParameter(
            name="create {type} report for {origin} files",
            default=TemplateParameterDefault.USE_NAME,
        ),
        ARGUMENTS: [
            {
                NAME: TemplateParameter(
                    name="{type}_report",
                    default=TemplateParameterDefault.USE_NAME,
                ),
                VALUE: FileSizeReport.empty,
            },
            {
                NAME: "filepaths",
                VALUE: TemplateParameter(name="get_{origin}_filepaths"),
            },
        ],
        RUNSTEPS: {
            VALUE: TemplateParameter(
                name="create_{type}_report_runsteps",
            ),
            SCHEDULING: PARALLEL,
        },
        LOG: {
            LEVEL: logging.DEBUG,
            MESSAGE: TemplateParameter(
                name="log_{type}_report",
            ),
        },
        CLEANUP: TemplateParameter(
            name="save_{origin}_{type}_report",
        ),
    }
)


def get_source_filepaths(source_filepaths: List[str]) -> List[str]:
    return source_filepaths


def get_target_filepaths(target_filepaths: List[str]) -> List[str]:
    return target_filepaths


def save_source_filesize_report(
    _scoped_: Scoped, filesize_report: FileSizeReport, source_filesize_filepath: Optional[str]
) -> None:
    return save_report(
        filesize_report, source_filesize_filepath, _scoped_.global_scope, SOURCE_FILESIZE_REPORT
    )


def save_source_filehash_report(
    _scoped_: Scoped, filehash_report: FileHashReport, source_filehash_filepath: Optional[str]
) -> None:
    return save_report(
        filehash_report, source_filehash_filepath, _scoped_.global_scope, SOURCE_FILEHASH_REPORT
    )


def save_target_filesize_report(
    _scoped_: Scoped, filesize_report: FileSizeReport, target_filesize_filepath: Optional[str]
) -> None:
    return save_report(
        filesize_report, target_filesize_filepath, _scoped_.global_scope, TARGET_FILESIZE_REPORT
    )


def save_target_filehash_report(
    _scoped_: Scoped, filehash_report: FileHashReport, target_filehash_filepath: Optional[str]
) -> None:
    return save_report(
        filehash_report, target_filehash_filepath, _scoped_.global_scope, TARGET_FILEHASH_REPORT
    )


GENERATE_REPORT_VALUES = {
    "get_source_filepaths": get_source_filepaths,
    "get_target_filepaths": get_target_filepaths,
    "create_filesize_report_runsteps": create_filesize_report_runsteps,
    "create_filehash_report_runsteps": create_filehash_report_runsteps,
    "log_filesize_report": log_filesize_report,
    "log_filehash_report": log_filehash_report,
    "save_source_filesize_report": save_source_filesize_report,
    "save_source_filehash_report": save_source_filehash_report,
    "save_target_filesize_report": save_target_filesize_report,
    "save_target_filehash_report": save_target_filehash_report,
}
GENERATE_SOURCE_FILESIZE_REPORT_RUNSTAGE = GENERATE_REPORT_TEMPLATE.substitute(
    GENERATE_REPORT_VALUES,
    name_substitutions={"type": FILESIZE, "origin": SOURCE},
)

GENERATE_SOURCE_FILEHASH_REPORT_RUNSTAGE = GENERATE_REPORT_TEMPLATE.substitute(
    GENERATE_REPORT_VALUES,
    name_substitutions={"type": FILEHASH, "origin": SOURCE},
)
GENERATE_TARGET_FILESIZE_REPORT_RUNSTAGE = GENERATE_REPORT_TEMPLATE.substitute(
    GENERATE_REPORT_VALUES,
    name_substitutions={"type": FILESIZE, "origin": TARGET},
)
GENERATE_TARGET_FILEHASH_REPORT_RUNSTAGE = GENERATE_REPORT_TEMPLATE.substitute(
    GENERATE_REPORT_VALUES,
    name_substitutions={"type": FILEHASH, "origin": TARGET},
)

LOAD_SOURCE_FILESIZE_REPORT_RUNSTAGE = {RUNSTEPS: [{ACTION: load_source_filesize_report}]}


def load_source_filehash_report(
    _scoped_: Scoped, source_filehash_filepath: str
) -> AbstractReport[str, str]:
    return load_report(
        FileHashReport.empty(),
        source_filehash_filepath,
        _scoped_.global_scope,
        SOURCE_FILEHASH_REPORT,
    )


LOAD_SOURCE_FILEHASH_REPORT_RUNSTAGE = {RUNSTEPS: [{ACTION: load_source_filehash_report}]}


def load_target_filesize_report(
    _scoped_: Scoped, target_filesize_filepath: str
) -> AbstractReport[str, int]:
    return load_report(
        FileSizeReport.empty(),
        target_filesize_filepath,
        _scoped_.global_scope,
        TARGET_FILESIZE_REPORT,
    )


LOAD_TARGET_FILESIZE_REPORT_RUNSTAGE = {RUNSTEPS: [{ACTION: load_target_filesize_report}]}


def load_target_filehash_report(
    _scoped_: Scoped, target_filehash_filepath: str
) -> AbstractReport[str, str]:
    return load_report(
        FileHashReport.empty(),
        target_filehash_filepath,
        _scoped_.global_scope,
        TARGET_FILEHASH_REPORT,
    )


LOAD_TARGET_FILEHASH_REPORT_RUNSTAGE = {RUNSTEPS: [{ACTION: load_target_filehash_report}]}


def compare_filesize_report(
    source_filesize_report: FileSizeReport, target_filesize_report: FileSizeReport
) -> List[ItemPair[str, int]]:
    return list(dict_cmp(source_filesize_report.report, target_filesize_report.report))


def filesize_missing_in_source_formatter(filename: str, filesize: int) -> str:
    return f"[错误] {filename}只存在于{TARGET_LOGNAME}文件夹"


def filesize_missing_in_target_formatter(filename: str, filesize: int) -> str:
    return f"[错误] {filename}只存在于{SOURCE_LOGNAME}文件夹"


def filesize_equal_value_formatter(
    source_filename: str, source_filesize: int, target_filename: str, target_filesize: int
) -> str:
    return f"[正确] {source_filename}和{target_filename}文件大小均为{source_filesize}"


def filesize_unequal_value_formatter(
    source_filename: str, source_filesize: int, target_filename: str, target_filesize: int
) -> str:
    return f"[错误] {source_filename}文件大小为{source_filesize}而{target_filename}文件大小为{target_filesize}"


def create_report_diff(
    itempairs: List[ItemPair[str, int]],
    missing_in_source_formatter: MissingInSourceFormatter[str, int],
    missing_in_target_formatter: MissingInTargetFormatter[str, int],
    unequal_value_formatter: UnequalValueFormatter[str, int],
    equal_value_formatter: EqualValueFormatter[str, int],
) -> List[str]:
    return [
        itempair.format(
            missing_in_source_formatter,
            missing_in_target_formatter,
            unequal_value_formatter,
            equal_value_formatter,
        )
        for itempair in itempairs
    ]


def create_logdiff_runstep(diff: List[str]) -> List[Dict[str, Any]]:
    return [
        {LOG: {LEVEL: logging.INFO if "正确" in diff_item else logging.ERROR, VALUE: diff_item}}
        for diff_item in diff
    ]


FILESIZE_DIFF = "filesize_diff"
COMPARE_FILESIZE_REPORT_RUNSTAGE = {
    ARGUMENTS: [
        {
            NAME: "missing_in_source_formatter",
            VALUE: IDENTITY_FACTORY(filesize_missing_in_source_formatter),
        },
        {
            NAME: "missing_in_target_formatter",
            VALUE: IDENTITY_FACTORY(filesize_missing_in_target_formatter),
        },
        {
            NAME: "unequal_value_formatter",
            VALUE: IDENTITY_FACTORY(filesize_unequal_value_formatter),
        },
        {NAME: "equal_value_formatter", VALUE: IDENTITY_FACTORY(filesize_equal_value_formatter)},
        {NAME: "itempairs", VALUE: compare_filesize_report},
        {NAME: "diff", VALUE: create_report_diff},
    ],
    RUNSTEPS: create_logdiff_runstep,
}


def compare_filehash_report(
    source_filehash_report: FileHashReport, target_filehash_report: FileHashReport
) -> List[ItemPair[str, str]]:
    return list(dict_cmp(source_filehash_report.report, target_filehash_report.report))


def filehash_missing_in_source_formatter(filename: str, filehash: int) -> str:
    return f"[错误] {filename}只存在于{TARGET_LOGNAME}文件夹"


def filehash_missing_in_target_formatter(filename: str, filehash: int) -> str:
    return f"[错误] {filename}只存在于{SOURCE_LOGNAME}文件夹"


def filehash_equal_value_formatter(
    source_filename: str, source_filehash: int, target_filename: str, target_filehash: int
) -> str:
    return f"[正确] {source_filename}和{target_filename}文件md5均为{source_filehash}"


def filehash_unequal_value_formatter(
    source_filename: str, source_filehash: int, target_filename: str, target_filehash: int
) -> str:
    return (
        f"[错误] {source_filename}文件md5为{source_filehash}而{target_filename}文件md5为{target_filehash}"
    )


FILEHASH_DIFF = "filehash_diff"
COMPARE_FILEHASH_REPORT_RUNSTAGE = {
    ARGUMENTS: [
        {
            NAME: "missing_in_source_formatter",
            VALUE: IDENTITY_FACTORY(filehash_missing_in_source_formatter),
        },
        {
            NAME: "missing_in_target_formatter",
            VALUE: IDENTITY_FACTORY(filehash_missing_in_target_formatter),
        },
        {
            NAME: "unequal_value_formatter",
            VALUE: IDENTITY_FACTORY(filehash_unequal_value_formatter),
        },
        {NAME: "equal_value_formatter", VALUE: IDENTITY_FACTORY(filehash_equal_value_formatter)},
        {NAME: "itempairs", VALUE: compare_filehash_report},
        {NAME: "diff", VALUE: create_report_diff},
    ],
    RUNSTEPS: create_logdiff_runstep,
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
    runstages: List[Dict[str, Any]] = []

    if will_checksize:
        has_source_filesize_report = True
        if source_filesize_report_type is ReportCreationType.Generate:
            runstages.append(GENERATE_SOURCE_FILESIZE_REPORT_RUNSTAGE)
        elif source_filesize_report_type is ReportCreationType.Load:
            runstages.append(LOAD_SOURCE_FILESIZE_REPORT_RUNSTAGE)
        else:
            has_source_filesize_report = False

        has_target_filesize_report = True
        if target_filesize_report_type is ReportCreationType.Generate:
            runstages.append(GENERATE_TARGET_FILESIZE_REPORT_RUNSTAGE)
        elif target_filesize_report_type is ReportCreationType.Load:
            runstages.append(LOAD_TARGET_FILESIZE_REPORT_RUNSTAGE)
        else:
            has_target_filesize_report = False

        if has_source_filesize_report and has_target_filesize_report:
            runstages.append(COMPARE_FILESIZE_REPORT_RUNSTAGE)

    if will_checksum:
        has_source_filehash_report = True
        if source_filehash_report_type is ReportCreationType.Generate:
            runstages.append(GENERATE_SOURCE_FILEHASH_REPORT_RUNSTAGE)
        elif source_filehash_report_type is ReportCreationType.Load:
            runstages.append(LOAD_SOURCE_FILEHASH_REPORT_RUNSTAGE)
        else:
            has_source_filehash_report = False

        has_target_filehash_report = True
        if target_filehash_report_type is ReportCreationType.Generate:
            runstages.append(GENERATE_TARGET_FILEHASH_REPORT_RUNSTAGE)
        elif target_filehash_report_type is ReportCreationType.Load:
            runstages.append(LOAD_TARGET_FILEHASH_REPORT_RUNSTAGE)
        else:
            has_target_filehash_report = False

        if has_source_filehash_report and has_target_filehash_report:
            runstages.append(COMPARE_FILEHASH_REPORT_RUNSTAGE)

    return runstages


PIPELINE = {
    ARGUMENTS: [
        SOURCE_DIR_ARGUMENT,
        SOURCE_FILESIZE_FILEPATH_ARGUMENT,
        SOURCE_FILESIZE_REPORT_TYPE,
        SOURCE_FILEHASH_FILEPATH_ARGUMENT,
        SOURCE_FILEHASH_REPORT_TYPE,
        TARGET_DIR_ARGUMENT,
        TARGET_FILESIZE_FILEPATH_ARGUMENT,
        TARGET_FILESIZE_REPORT_TYPE,
        TARGET_FILEHASH_FILEPATH_ARGUMENT,
        TARGET_FILEHASH_REPORT_TYPE,
        OPERATION_ARGUMENT,
    ],
    RUNSTAGES: {VALUE: create_runstages},
}


async def main() -> None:
    pipeline = Pipeline(PIPELINE)

    pipeline.print_help()
    scoping = pipeline.run()


if __name__ == "__main__":
    asyncio.run(main())
