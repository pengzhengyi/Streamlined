from __future__ import annotations

from inspect import Parameter, _ParameterKind
from typing import Any, ClassVar, Dict, Iterable, Mapping, Optional, Tuple

from .predicates import IS_DICT, IS_SEQUENCE


class TemplateParameter:
    kind: ClassVar[_ParameterKind] = Parameter.POSITIONAL_OR_KEYWORD

    def __init__(
        self, name: str, default: Any = Parameter.empty, annotation: Any = Parameter.empty
    ) -> None:
        self.name = name
        self.default = default
        self.annotation = annotation

    def substitute_name(self, substitutions: Optional[Mapping[str, Any]]) -> str:
        if substitutions is None:
            return self.name
        return self.name.format_map(substitutions)

    def substitute(
        self, value: Any, name_substitutions: Optional[Mapping[str, Any]]
    ) -> Tuple[Parameter, Any]:
        substituted_name = self.substitute_name(name_substitutions)
        parameter = Parameter(
            name=substituted_name, kind=self.kind, default=self.default, annotation=self.annotation
        )
        return (parameter, value)

    def substitute_from(
        self, values: Mapping[str, Any], name_substitutions: Optional[Mapping[str, Any]]
    ) -> Tuple[Parameter, Any]:
        substituted_name = self.substitute_name(name_substitutions)
        parameter = Parameter(
            name=substituted_name, kind=self.kind, default=self.default, annotation=self.annotation
        )
        value = values[substituted_name]
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
        values: Mapping[Any, Any],
        name_substitutions: Optional[Mapping[str, Any]] = None,
    ) -> Template:
        parameters = self.get_parameters(self.template)
        parameter_substitutions = self.substitute_parameters(
            parameters, values, name_substitutions
        )
        return self.substitute_template(self.template, parameter_substitutions)
