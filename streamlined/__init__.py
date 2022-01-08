import resource
import sys

import nest_asyncio
import uvloop

from .common import (
    ACTION,
    DEFAULT,
    HANDLERS,
    LEVEL,
    LOGGER,
    MESSAGE,
    TYPE,
    VALUE,
    SubprocessResult,
)
from .execution import SimpleExecutor
from .middlewares import (
    ACTION,
    ARGPARSE,
    ARGS,
    ARGTYPE,
    ARGUMENT,
    ARGUMENTS,
    CHOICES,
    CLEANUP,
    CONST,
    DEFAULT,
    DEST,
    HELP,
    KWARGS,
    LOG,
    METAVAR,
    NAME,
    NARGS,
    PARALLEL,
    PIPELINE,
    REQUIRED,
    RUNSTAGE,
    RUNSTAGES,
    RUNSTEP,
    RUNSTEPS,
    SCHEDULING,
    SEQUENTIAL,
    SETUP,
    SHELL,
    SKIP,
    STDERR,
    STDIN,
    STDOUT,
    VALIDATOR,
    VALIDATOR_AFTER_STAGE,
    VALIDATOR_BEFORE_STAGE,
    Action,
    Argument,
    Arguments,
    Cleanup,
    Context,
    Log,
    Name,
    Pipeline,
    Runstage,
    Runstages,
    Runstep,
    Runsteps,
    Setup,
    Skip,
    Validator,
)
from .services import Scoped, Scoping

resource.setrlimit(resource.RLIMIT_STACK, (resource.RLIM_INFINITY, resource.RLIM_INFINITY))
sys.setrecursionlimit(10 ** 5)

# Patching asyncio
nest_asyncio.apply()

uvloop.install()
