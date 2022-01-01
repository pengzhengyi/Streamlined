from argparse import ArgumentParser
from typing import Any, Dict, List, Optional

from ..common import (
    AND,
    DEFAULT_KEYERROR,
    IS_DICT,
    IS_NOT_DICT,
    PIPELINE_ARGUMENT_PARSER,
)
from ..services import Scoped
from .argument import Arguments
from .cleanup import Cleanup
from .log import Log
from .middleware import APPLY_INTO, APPLY_ONTO, Context, Middleware, WithMiddlewares
from .name import NAME, Name
from .parser import AbstractParser
from .runstage import Runstages
from .runstep import _MISSING_RUNSTEP_NAME, _TRANSFORM_WHEN_MISSING_NAME
from .setup import Setup
from .skip import Skip
from .validator import Validator

_MISSING_PIPELINE_NAME = _MISSING_RUNSTEP_NAME


class Pipeline(Middleware, WithMiddlewares):
    def __init__(
        self, value: Any, argument_parser_kwargs: Optional[Dict[str, Any]] = None
    ) -> None:
        self._init_argument_parser(argument_parser_kwargs)
        super().__init__(value)

    @classmethod
    def verify(cls, value: Any) -> None:
        super().verify(value)

        if IS_NOT_DICT(value):
            raise TypeError(f"{value} should be dict")

        if _MISSING_PIPELINE_NAME(value):
            raise DEFAULT_KEYERROR(value, NAME)

    def _init_argument_parser(self, argument_parser_kwargs: Optional[Dict[str, Any]]) -> None:
        setattr(
            self,
            PIPELINE_ARGUMENT_PARSER,
            ArgumentParser()
            if argument_parser_kwargs is None
            else ArgumentParser(**argument_parser_kwargs),
        )

    def parse(self, value: Any) -> Dict[str, Any]:
        """
        Accept both `{...}` and `{PIPELINE: {...}}`
        """
        if PIPELINE in value:
            return super().parse(value)

        return AbstractParser.parse(self, value)

    def _init_middleware_types(self) -> None:
        super()._init_middleware_types()
        self.middleware_types.extend(
            [Name, Skip, Arguments, Setup, Validator, Runstages, Log, Cleanup]
        )

    def _init_middleware_apply_methods(self) -> None:
        super()._init_middleware_apply_methods()
        self.middleware_apply_methods.extend(
            [
                APPLY_ONTO,
                APPLY_ONTO,
                APPLY_INTO,
                APPLY_ONTO,
                APPLY_ONTO,
                APPLY_ONTO,
                APPLY_ONTO,
                APPLY_ONTO,
            ]
        )

    def _init_simplifications(self) -> None:
        super()._init_simplifications()

        # `{RUNSTAGE: {...}}` -> `{RUNSTAGE: {.., NAME: <uuid>}}`
        self.simplifications.append(
            (AND(IS_DICT, _MISSING_PIPELINE_NAME), _TRANSFORM_WHEN_MISSING_NAME)
        )

    def _do_parse(self, value: Any) -> Dict[str, List[Middleware]]:
        self.verify(value)
        return {"middlewares": list(self.create_middlewares_from(value))}

    def _prepare_context(self, context: Context) -> Context:
        context.scoped.setmagic(PIPELINE_ARGUMENT_PARSER, getattr(self, PIPELINE_ARGUMENT_PARSER))
        return context

    async def _do_apply(self, context: Context) -> Scoped:
        coroutine = WithMiddlewares.apply(self, self._prepare_context(context))
        return await coroutine()


PIPELINE = Pipeline.get_name()
