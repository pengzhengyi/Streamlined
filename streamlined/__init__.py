import resource
import sys

import uvloop

from .common import (
    ACTION,
    ASYNC_NOOP,
    DEFAULT,
    HANDLERS,
    IDENTITY_FACTORY,
    LEVEL,
    LOGGER,
    MESSAGE,
    NOOP,
    TYPE,
    VALUE,
    WHEN,
    SubprocessResult,
    Template,
    TemplateParameter,
    TemplateParameterDefault,
    bound,
    create_identity_function,
    get_default_handler,
    rewrite_function_parameters,
    run,
    use_basic_logging_config,
)
from .execution import SimpleExecutor
from .middlewares import (
    ACTION,
    ARGPARSE,
    ARGS,
    ARGTYPE,
    ARGUMENT,
    ARGUMENTS,
    CAUGHT_EXCEPTION,
    CHOICES,
    CLEANUP,
    CONCURRENCY,
    CONST,
    DEFAULT,
    DEST,
    EXCEPTION,
    HELP,
    KWARGS,
    LOG,
    METAVAR,
    NAME,
    NARGS,
    PIPELINE,
    REQUIRED,
    RUNSTAGE,
    RUNSTAGES,
    RUNSTEP,
    RUNSTEPS,
    SCHEDULING,
    SETUP,
    SHELL,
    SKIP,
    STDERR,
    STDIN,
    STDOUT,
    SUBSTEPS,
    SUPPRESS,
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
    Suppress,
    Validator,
)
from .scheduling import PARALLEL, SEQUENTIAL, Parallel
from .services import EvalRef
from .services import HybridStorageOption as StorageOption
from .services import NameRef, Scope, Scoped, Scoping, ValueRef

resource.setrlimit(resource.RLIMIT_STACK, (resource.RLIM_INFINITY, resource.RLIM_INFINITY))
sys.setrecursionlimit(10**5)

uvloop.install()
