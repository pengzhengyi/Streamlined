from __future__ import annotations

from enum import Enum, auto
from inspect import Parameter, _ParameterKind
from typing import Any, ClassVar, Dict, Iterable, Mapping, Optional, Tuple, Union

from .dictionary import update_with_callable
from .predicates import IS_DICT, IS_SEQUENCE


class TemplateParameterDefault(Enum):
    EMPTY = Parameter.empty
    USE_NAME = auto()
    USE_DEFAULT = auto()

    @classmethod
    def of(cls, value: Any) -> TemplateParameterDefault:
        if isinstance(value, cls):
            return value
        else:
            return TemplateParameterDefault.USE_DEFAULT

    def evaluate(self, **kwargs: Any) -> Any:
        if self is TemplateParameterDefault.EMPTY:
            return self.value
        elif self is TemplateParameterDefault.USE_NAME:
            return kwargs["name"]
        else:
            return kwargs["default"]


class TemplateParameter:
    kind: ClassVar[_ParameterKind] = Parameter.POSITIONAL_OR_KEYWORD

    def __init__(
        self,
        name: str,
        default: Union[Any, TemplateParameterDefault] = TemplateParameterDefault.EMPTY,
        annotation: Any = Parameter.empty,
    ) -> None:
        self.name = name
        self.default = default
        self.annotation = annotation

    def substitute_name(self, substitutions: Optional[Mapping[str, Any]]) -> str:
        if substitutions is None:
            return self.name
        return self.name.format_map(substitutions)

    def to_parameter(self, **overrides: Any) -> Parameter:
        parameter_kwargs = dict(
            name=self.name, kind=self.kind, default=self.default, annotation=self.annotation
        )
        parameter_kwargs.update(overrides)

        update_with_callable(
            parameter_kwargs,
            "default",
            lambda parameter_default: TemplateParameterDefault.of(parameter_default).evaluate(
                **parameter_kwargs
            ),
        )

        return Parameter(**parameter_kwargs)

    def substitute(
        self, value: Any, name_substitutions: Optional[Mapping[str, Any]]
    ) -> Tuple[Parameter, Any]:
        substituted_name = self.substitute_name(name_substitutions)
        parameter = self.to_parameter(name=substituted_name)
        return (parameter, value)

    def substitute_from(
        self, values: Mapping[str, Any], name_substitutions: Optional[Mapping[str, Any]]
    ) -> Tuple[Parameter, Any]:
        substituted_name = self.substitute_name(name_substitutions)
        parameter = self.to_parameter(name=substituted_name)
        value = values.get(substituted_name, parameter.default)
        return (parameter, value)


class Template:
    @staticmethod
    def is_parameter(value: Any) -> bool:
        return isinstance(value, TemplateParameter)

    @staticmethod
    def substitute_parameters(
        parameters: Iterable[TemplateParameter],
        values: Mapping[Any, Any],
        name_substitutions: Optional[Mapping[str, Any]] = None,
    ) -> Dict[TemplateParameter, Any]:
        substituted_parameters: Dict[TemplateParameter, Any] = dict()

        for parameter in parameters:
            try:
                _, value = parameter.substitute_from(values, name_substitutions)
            except (KeyError, ValueError):
                value = parameter
            substituted_parameters[parameter] = value

        return substituted_parameters

    @classmethod
    def get_parameters(cls, template: Any) -> Iterable[TemplateParameter]:
        if IS_DICT(template):
            for k, v in template.items():
                yield from cls.get_parameters(k)
                yield from cls.get_parameters(v)
        elif IS_SEQUENCE(template):
            for item in template:
                yield from cls.get_parameters(item)
        elif isinstance(template, TemplateParameter):
            yield template

    @classmethod
    def substitute_template(
        cls, template: Any, parameter_substitutions: Mapping[TemplateParameter, Any]
    ) -> Any:
        if IS_DICT(template):
            return {
                cls.substitute_template(k, parameter_substitutions): cls.substitute_template(
                    v, parameter_substitutions
                )
                for k, v in template.items()
            }
        elif IS_SEQUENCE(template):
            return [cls.substitute_template(item, parameter_substitutions) for item in template]
        else:
            return parameter_substitutions.get(template, template)

    def __init__(self, template: Any) -> None:
        self._init_template(template)

    def _init_template(self, template: Any) -> None:
        self.template = template
        self._init_parameters()

    def _init_parameters(self) -> None:
        self.parameters = list(self.get_parameters(self.template))

    def substitute(
        self,
        values: Optional[Mapping[str, Any]] = None,
        name_substitutions: Optional[Mapping[str, Any]] = None,
    ) -> Template:
        if values is None:
            values = dict()

        parameters = self.get_parameters(self.template)
        parameter_substitutions = self.substitute_parameters(
            parameters, values, name_substitutions
        )
        return self.substitute_template(self.template, parameter_substitutions)
