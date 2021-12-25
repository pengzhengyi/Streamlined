from __future__ import annotations

from dataclasses import replace
from typing import Any, Awaitable, Callable, ClassVar, Dict, List, Type

from ..common import (
    ACTION,
    AND,
    ASYNC_VOID,
    DEFAULT,
    DEFAULT_KEYERROR,
    HANDLERS,
    IDENTITY_FACTORY,
    IS_CALLABLE,
    IS_DICT,
    IS_NONE,
    IS_NOT_CALLABLE,
    IS_NOT_DICT,
    IS_STR,
    NOOP,
    VALUE,
    get_or_raise,
)
from ..services import Scoped
from .action import Action
from .cleanup import Cleanup
from .log import LOG, Log
from .middleware import Middleware, MiddlewareContext, WithMiddlewares
from .name import Name
from .parser import AbstractParser, Parser


class ValidationError(Exception):
    pass


def _TRANSFORM_WHEN_HANDLER_IS_STR(value: str) -> Dict[str, str]:
    return {LOG: value}


def _TRANSFORM_WHEN_HANDLER_IS_CALLABLE(value: Callable) -> Dict[str, Callable]:
    return {ACTION: value}


def _MISSING_HANDLER_ACTION(value: Dict) -> bool:
    return ACTION not in value


def _TRANSFORM_WHEN_HANDLER_MISSING_ACTION(value: Dict) -> Dict:
    value[ACTION] = NOOP
    return value


class ValidatorHandler(Parser, Middleware, WithMiddlewares):
    @classmethod
    def verify(self, value: Any) -> None:
        super().verify(value)

        if IS_NOT_DICT(value):
            raise TypeError(f"{value} should be dict")

        if _MISSING_HANDLER_ACTION(value):
            raise DEFAULT_KEYERROR(value, ACTION)

    def _init_middleware_types(self):
        super()._init_middleware_types()
        self.middleware_types.extend([Action, Log])

    def _init_simplifications(self) -> None:
        super()._init_simplifications()

        # `{<name>: None}` -> `{<name>: NOOP}`
        self.simplifications.append((IS_NONE, IDENTITY_FACTORY(NOOP)))

        # `{<name>: <str>}` -> `{<name>: {LOG: <str>}}}`
        self.simplifications.append((IS_STR, _TRANSFORM_WHEN_HANDLER_IS_STR))

        # `{<name>: <callable>}` -> `{<name>: {ACTION: <callable>}}}`
        self.simplifications.append((IS_CALLABLE, _TRANSFORM_WHEN_HANDLER_IS_CALLABLE))

        # `{<name>: {LOG: ...}}}` -> `{<name>: {LOG: ..., ACTION: NOOP}}}`
        self.simplifications.append(
            (AND(IS_DICT, _MISSING_HANDLER_ACTION), _TRANSFORM_WHEN_HANDLER_MISSING_ACTION)
        )

    def parse(self, value: Any) -> Dict:
        return AbstractParser.parse(self, value)

    def _do_parse(self, value: Any) -> Dict:
        self.verify(value)

        return {"middlewares": list(self.create_middlewares_from(value))}

    async def _do_apply(self, context: MiddlewareContext):
        coroutine = WithMiddlewares.apply(self, context)
        return await coroutine()


def _MISSING_HANDLERS(value: Dict) -> bool:
    return HANDLERS not in value


def _TRANSFORM_WHEN_MISSING_HANDLERS(value: Dict) -> Dict:
    value[HANDLERS] = dict()
    return value


def _MISSING_DEFAULT_HANDLER(value: Dict) -> bool:
    return DEFAULT not in value[HANDLERS]


def _TRANSFORM_WHEN_MISSING_DEFAULT_HANDLER(value: Dict) -> Dict:
    value[HANDLERS][DEFAULT] = NOOP
    return value


def _TRANSFORM_WHEN_IS_CALLABLE(value: Callable) -> Dict[str, Callable]:
    return {ACTION: value}


class ValidatorStage(Parser, Middleware):
    @classmethod
    def verify(cls, value: Any) -> None:
        super().verify(value)

        if IS_NOT_DICT(value):
            raise TypeError(f"{value} should be dict")

        if IS_NOT_CALLABLE(action := get_or_raise(value, ACTION)):
            raise TypeError(f"{action} should be callable")

        if _MISSING_HANDLERS(value):
            raise DEFAULT_KEYERROR(value, HANDLERS)

        if _MISSING_DEFAULT_HANDLER(value):
            raise DEFAULT_KEYERROR(value[HANDLERS], DEFAULT)

    def _init_simplifications(self) -> None:
        super()._init_simplifications()

        # `{<stage_name>: <callable>}` -> `{<stage_name>: {ACTION: <callable>}}`
        self.simplifications.append((IS_CALLABLE, _TRANSFORM_WHEN_IS_CALLABLE))

        # `{<stage_name>: {ACTION: <callable>}}` -> `{<stage_name>: {ACTION: <callable>, HANDLERS: {}}}`
        self.simplifications.append(
            (AND(IS_DICT, _MISSING_HANDLERS), _TRANSFORM_WHEN_MISSING_HANDLERS)
        )

        # `{<stage_name>: {ACTION: <callable>, HANDLERS: {}}}` -> `{<stage_name>: {ACTION: <callable>, HANDLERS: {DEFAULT: NOOP}}}`
        self.simplifications.append(
            (AND(IS_DICT, _MISSING_DEFAULT_HANDLER), _TRANSFORM_WHEN_MISSING_DEFAULT_HANDLER)
        )

    def _do_parse(self, value: Any) -> Dict[str, Any]:
        self.verify(value)

        parsed = self.parse_with(value, [Action])
        parsed["_handlers"] = {
            handler_name: ValidatorHandler(handler)
            for handler_name, handler in value[HANDLERS].items()
        }

        return parsed

    async def validate(self, executor) -> Any:
        return await executor.submit(self._action)

    def get_handler(self, result: Any) -> ValidatorHandler:
        try:
            return self._handlers[result]
        except KeyError:
            return self._handlers[DEFAULT]

    async def _do_apply(self, context: MiddlewareContext):
        validation_result = await self.validate(context.executor)
        context.scoped.setmagic(VALUE, validation_result)

        handler = self.get_handler(validation_result)
        scoped = await handler.apply_to(context)

        return scoped


class Before(ValidatorStage):
    pass


class After(ValidatorStage):
    pass


def _MISSING_BEFORE_STAGE(value) -> bool:
    return VALIDATOR_BEFORE_STAGE not in value


def _MISSING_AFTER_STAGE(value) -> bool:
    return VALIDATOR_AFTER_STAGE not in value


def _TRANSFORM_WHEN_VALIDATOR_IS_CALLABLE(value: Callable) -> Dict:
    return {VALIDATOR_AFTER_STAGE: value}


class Validator(Parser, Middleware):
    @classmethod
    def verify(cls, value: Any) -> None:
        super().verify(value)

        if not IS_DICT(value):
            raise TypeError(f"{value} should be dict")

        if _MISSING_BEFORE_STAGE(value) and _MISSING_AFTER_STAGE(value):
            raise ValueError(
                f"{value} should specify either {VALIDATOR_BEFORE_STAGE} stage validator or {VALIDATOR_AFTER_STAGE} stage validator"
            )

    def _init_simplifications(self) -> None:
        super()._init_simplifications()

        # `{VALIDATOR: <callable>}` -> `{VALIDATOR: {VALIDATOR_AFTER_STAGE: <callable>}}`
        self.simplifications.append((IS_CALLABLE, _TRANSFORM_WHEN_VALIDATOR_IS_CALLABLE))

    def _do_parse(self, value: Any) -> Dict:
        self.verify(value)

        parsed = dict()

        if not _MISSING_BEFORE_STAGE(value):
            parsed["_before_validator"] = Before(value)

        if not _MISSING_AFTER_STAGE(value):
            parsed["_after_validator"] = After(value)

        return parsed

    async def _validate_stage(
        self, stage_name: str, context: MiddlewareContext
    ) -> Awaitable[Scoped]:
        try:
            validator: ValidatorStage = getattr(self, f"_{stage_name}_validator")
            return await validator.apply_to(replace(context, next=ASYNC_VOID))
        except AttributeError:
            return context.scoped

    async def validate_before(self, context: MiddlewareContext) -> Awaitable[Scoped]:
        return await self._validate_stage(VALIDATOR_BEFORE_STAGE, context)

    async def validate_after(self, context: MiddlewareContext) -> Awaitable[Scoped]:
        return await self._validate_stage(VALIDATOR_AFTER_STAGE, context)

    async def _do_apply(self, context: MiddlewareContext):
        context.scoped.update(await self.validate_before(context))

        await context.next()
        context.scoped.update(await self.validate_after(context))
        return context.scoped


VALIDATOR = Validator.get_name()
VALIDATOR_BEFORE_STAGE = Before.get_name()
VALIDATOR_AFTER_STAGE = After.get_name()
