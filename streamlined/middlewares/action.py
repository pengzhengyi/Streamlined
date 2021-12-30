from subprocess import DEVNULL, PIPE
from typing import Any, Callable, ClassVar, Dict, List

from decorator import FunctionMaker

from ..common import (
    AND,
    ASYNC_VOID,
    DEFAULT_KEYERROR,
    IDENTITY_FACTORY,
    IS_CALLABLE,
    IS_LIST,
    IS_NOT_CALLABLE,
    IS_NOT_LIST,
    IS_NOT_LIST_OF_CALLABLE,
    IS_STR,
    VALUE,
    StdinStream,
    Stream,
    SubprocessResult,
)
from ..common import run as run_
from ..parsing import Variant, WithVariants
from .middleware import Context, Middleware
from .parser import Parser

ARGS = "args"
STDIN = "stdin"
STDOUT = "stdout"
STDERR = "stderr"
KWARGS = "kwargs"


def _IS_ARGS_NOT_CALLABLE(value: Dict[str, Any]) -> bool:
    return IS_NOT_CALLABLE(value[ARGS])


def _TRANSFORM_WHEN_ARGS_NOT_CALLABLE(value: Dict[str, Any]) -> Dict[str, Any]:
    value[ARGS] = IDENTITY_FACTORY(value[ARGS])
    return value


def _MISSING_STDIN(value: Dict[str, Any]) -> bool:
    return STDIN not in value


def _TRANSFORM_WHEN_MISSING_STDIN(value: Dict[str, Any]) -> Dict[str, Any]:
    value[STDIN] = DEVNULL
    return value


def _IS_STDIN_STR(value: Dict[str, Any]) -> bool:
    return IS_STR(value[STDIN])


def _TRANSFORM_WHEN_STDIN_IS_STR(value: Dict[str, Any]) -> Dict[str, Any]:
    string: str = value[STDIN]
    value[STDIN] = string.encode("utf-8")
    return value


def _MISSING_ARGS(value: Dict[str, Any]) -> bool:
    return ARGS not in value


def _IS_STDIN_NOT_CALLABLE(value: Dict[str, Any]) -> bool:
    return IS_NOT_CALLABLE(value[STDIN])


def _TRANSFORM_WHEN_STDIN_NOT_CALLABLE(value: Dict[str, Any]) -> Dict[str, Any]:
    value[STDIN] = IDENTITY_FACTORY(value[STDIN])
    return value


def _MISSING_STDOUT(value: Dict[str, Any]) -> bool:
    return STDOUT not in value


def _TRANSFORM_WHEN_MISSING_STDOUT(value: Dict[str, Any]) -> Dict[str, Any]:
    value[STDOUT] = PIPE
    return value


def _IS_STDOUT_NOT_CALLABLE(value: Dict[str, Any]) -> bool:
    return IS_NOT_CALLABLE(value[STDOUT])


def _TRANSFORM_WHEN_STDOUT_NOT_CALLABLE(value: Dict[str, Any]) -> Dict[str, Any]:
    value[STDOUT] = IDENTITY_FACTORY(value[STDOUT])
    return value


def _MISSING_STDERR(value: Dict[str, Any]) -> bool:
    return STDERR not in value


def _TRANSFORM_WHEN_MISSING_STDERR(value: Dict[str, Any]) -> Dict[str, Any]:
    value[STDERR] = PIPE
    return value


def _IS_STDERR_NOT_CALLABLE(value: Dict[str, Any]) -> bool:
    return IS_NOT_CALLABLE(value[STDERR])


def _TRANSFORM_WHEN_STDERR_NOT_CALLABLE(value: Dict[str, Any]) -> Dict[str, Any]:
    value[STDERR] = IDENTITY_FACTORY(value[STDERR])
    return value


def _MISSING_KWARGS(value: Dict[str, Any]) -> bool:
    return KWARGS not in value


def _TRANSFORM_WHEN_MISSING_KWARGS(value: Dict[str, Any]) -> Dict[str, Any]:
    value[KWARGS] = dict()
    return value


def _IS_KWARGS_NOT_CALLABLE(value: Dict[str, Any]) -> bool:
    return IS_NOT_CALLABLE(value[KWARGS])


def _TRANSFORM_WHEN_KWARGS_NOT_CALLABLE(value: Dict[str, Any]) -> Dict[str, Any]:
    value[KWARGS] = IDENTITY_FACTORY(value[KWARGS])
    return value


class Shell(Variant):
    run: ClassVar[
        Callable[[str, StdinStream, Stream, Stream, Dict[str, Any]], SubprocessResult]
    ] = FunctionMaker.create(
        f"run(_{VALUE}0_: str, _{VALUE}1_: StdinStream, _{VALUE}2_: Stream, _{VALUE}3_: Stream, _{VALUE}4_: Dict[str, Any])",
        f"return run_(_{VALUE}0_, _{VALUE}1_, _{VALUE}2_, _{VALUE}3_, _{VALUE}4_)",
        dict(
            run_=run_,
            Stream=Stream,
            StdinStream=StdinStream,
            Dict=Dict,
            Any=Any,
            _call_=ASYNC_VOID,
        ),
        addsource=True,
    )

    @classmethod
    def reduce(cls, value: Any) -> Any:
        cls.verify(value)

        return [value[ARGS], value[STDIN], value[STDOUT], value[STDERR], value[KWARGS], cls.run]

    @classmethod
    def verify(cls, value: Any) -> None:
        if _MISSING_ARGS(value):
            raise DEFAULT_KEYERROR(value, ARGS)
        if _IS_ARGS_NOT_CALLABLE(value):
            raise TypeError(f"Expect {ARGS} to be a Callable, received {value[ARGS]}")

        if _MISSING_STDIN(value):
            raise DEFAULT_KEYERROR(value, STDIN)
        if _IS_STDIN_NOT_CALLABLE(value):
            raise TypeError(f"Expect {STDIN} to be a Callable, received {value[STDIN]}")

        if _MISSING_STDOUT(value):
            raise DEFAULT_KEYERROR(value, STDOUT)
        if _IS_STDOUT_NOT_CALLABLE(value):
            raise TypeError(f"Expect {STDOUT} to be a Callable, received {value[STDOUT]}")

        if _MISSING_STDERR(value):
            raise DEFAULT_KEYERROR(value, STDERR)
        if _IS_STDERR_NOT_CALLABLE(value):
            raise TypeError(f"Expect {STDERR} to be a Callable, received {value[STDERR]}")

        if _MISSING_KWARGS(value):
            raise DEFAULT_KEYERROR(value, KWARGS)
        if _IS_KWARGS_NOT_CALLABLE(value):
            raise TypeError(f"Expect {KWARGS} to be a Callable, received {value[KWARGS]}")

        return value

    def _init_simplifications_for_variant(self) -> None:
        super()._init_simplifications_for_variant()

        self._variant_simplifications.append(
            (_IS_ARGS_NOT_CALLABLE, _TRANSFORM_WHEN_ARGS_NOT_CALLABLE)
        )

        self._variant_simplifications.append((_MISSING_STDIN, _TRANSFORM_WHEN_MISSING_STDIN))

        self._variant_simplifications.append((_IS_STDIN_STR, _TRANSFORM_WHEN_STDIN_IS_STR))

        self._variant_simplifications.append(
            (_IS_STDIN_NOT_CALLABLE, _TRANSFORM_WHEN_STDIN_NOT_CALLABLE)
        )

        self._variant_simplifications.append((_MISSING_STDOUT, _TRANSFORM_WHEN_MISSING_STDOUT))

        self._variant_simplifications.append(
            (_IS_STDOUT_NOT_CALLABLE, _TRANSFORM_WHEN_STDOUT_NOT_CALLABLE)
        )

        self._variant_simplifications.append((_MISSING_STDERR, _TRANSFORM_WHEN_MISSING_STDERR))

        self._variant_simplifications.append(
            (_IS_STDERR_NOT_CALLABLE, _TRANSFORM_WHEN_STDERR_NOT_CALLABLE)
        )

        self._variant_simplifications.append((_MISSING_KWARGS, _TRANSFORM_WHEN_MISSING_KWARGS))

        self._variant_simplifications.append(
            (_IS_KWARGS_NOT_CALLABLE, _TRANSFORM_WHEN_KWARGS_NOT_CALLABLE)
        )


SHELL = Shell.get_name()


def _TRANSFORM_WHEN_NOT_LIST(value: Callable[..., Any]) -> List[Callable[..., Any]]:
    return [value]


class Action(WithVariants, Parser, Middleware):
    actions: List[Callable[..., Any]]

    @classmethod
    def verify(cls, value: Any) -> None:
        super().verify(value)

        if IS_NOT_LIST_OF_CALLABLE(value):
            raise TypeError(f"{value} should be a callable or a list of callable")

    def _init_variants(self) -> None:
        super()._init_variants()
        self.variants.append(Shell())

    def _init_simplifications(self) -> None:
        super()._init_simplifications()

        self.simplifications.append((AND(IS_NOT_LIST, IS_NOT_CALLABLE), IDENTITY_FACTORY))

        self.simplifications.append((AND(IS_LIST, IS_NOT_LIST_OF_CALLABLE), IDENTITY_FACTORY))

        self.simplifications.append((IS_NOT_LIST, _TRANSFORM_WHEN_NOT_LIST))

    def _do_parse(self, value: List[Callable[..., Any]]) -> Dict[str, Any]:
        self.verify(value)

        return {"actions": value}

    async def _do_apply(self, context: Context):
        for index, action in enumerate(self.actions):
            result = await context.submit(action)
            context.scoped.setmagic(f"{VALUE}{index}", result)
            context.scoped.setmagic(VALUE, result)

        await context.next()
        return context.scoped


ACTION = Action.get_name()