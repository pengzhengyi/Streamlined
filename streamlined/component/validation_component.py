from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    ClassVar,
    Dict,
    Generator,
    Iterable,
    Optional,
    Union,
)

from ..constants import (
    ACTION,
    VALIDATION_AFTER_STAGE,
    VALIDATION_BEFORE_STAGE,
    VALIDATION_RESULT,
    VALIDATOR,
)
from .component import Component
from .execution_component import ExecutionComponent
from .logging_component import LoggingComponent, TLogConfig, TLogDictConfig

if TYPE_CHECKING:
    from ..manager.manager import Manager
    from ..manager.service.scoping import Scope


TValidatorAction = Callable[..., bool]
TValidatorStageConfig = Dict[str, Union[TValidatorAction, TLogConfig]]
TValidatorConfig = Union[TValidatorStageConfig, TValidatorAction]
TValidator = Union[TValidatorConfig, TValidatorAction]


class ValidationError(Exception):
    """
    A custom error for validation.
    """

    def __init__(self, message, component: Component, manager: Manager):
        # Call the base class constructor with the parameters it needs
        super().__init__(message)

        self.component = component
        self.manager = manager


class ValidationStageComponent(Component):
    """
    A component represents a validation stage where a predicate will be executed in current scope.
    """

    VALIATION_RESULT_KEYNAME: ClassVar[str] = VALIDATION_RESULT
    ACTION_KEYNAME: ClassVar[str] = ACTION

    def __init__(self, action: TValidatorAction, log: Any = None, **kwargs: Any):
        super().__init__(**kwargs)
        self._action_runner = ExecutionComponent(action)
        self.__set_log(log)

    @classmethod
    def of(cls, config: Union[TValidatorAction]) -> ValidationStageComponent:
        if isinstance(config, dict):
            return cls(**config)
        else:
            return cls(action=config)

    @staticmethod
    def __get_default_log_config_for_validation_sucess() -> TLogDictConfig:
        return {"value": lambda _runstep_: f"validation suceeds for {_runstep_.name}"}

    @staticmethod
    def __get_default_log_config_for_validation_failure() -> TLogDictConfig:
        return {"value": lambda _runstep_: f"validation failed for {_runstep_.name}"}

    def __set_log_with_configs(self, success_config, failure_config) -> None:
        self._sucess_logging_component = LoggingComponent.of(success_config)
        self._failure_logging_component = LoggingComponent.of(failure_config)

    def __set_log(self, log: Any) -> None:
        if log is None:
            validation_success_log_config = self.__get_default_log_config_for_validation_sucess()
            validation_failure_log_config = self.__get_default_log_config_for_validation_failure()
        elif isinstance(log, dict):
            if True in log:
                validation_success_log_config = log[True]
                validation_failure_log_config = (
                    log[False] if False in log else validation_success_log_config
                )
            elif False in log:
                validation_success_log_config = validation_failure_log_config = log[False]
            else:
                validation_success_log_config = validation_failure_log_config = log
        else:
            validation_success_log_config = validation_failure_log_config = {"value": log}

        self.__set_log_with_configs(
            success_config=validation_success_log_config,
            failure_config=validation_failure_log_config,
        )

    def _execute_for_action(self, manager: Manager, scope: Scope) -> bool:
        result: bool = self._action_runner.execute(manager)
        scope.set_magic_value(self.VALIATION_RESULT_KEYNAME, result)
        scope.set_magic_value(self.ACTION_KEYNAME, result)
        return result

    def _execute_for_log(self, manager: Manager, validation_result: bool) -> None:
        if validation_result:
            self._sucess_logging_component.execute(manager)
        else:
            self._failure_logging_component.execute(manager)

    def execute(self, manager: Manager) -> bool:
        with manager.scoped() as scope:
            validation_result = self._execute_for_action(manager, scope)
            self._execute_for_log(manager, validation_result)
            return validation_result


class ValidationBeforeStageComponent(ValidationStageComponent):
    """
    A component represents validation before execution of certain action.

    It is typically used to verify that environment is set up properly.
    """

    STAGE_NAME: ClassVar[str] = VALIDATION_BEFORE_STAGE
    ERROR_MESSAGE: ClassVar[str] = "Pre-execution validation failed"


class ValidationAfterStageComponent(ValidationStageComponent):
    """
    A component represents validation after execution is finished.

    It is typically used to check the side-effect of executed action.
    """

    STAGE_NAME: ClassVar[str] = VALIDATION_AFTER_STAGE
    ERROR_MESSAGE: ClassVar[str] = "Post-execution validation failed"


class ValidatorComponent(Component):
    """
    A component represents the validation of a certain action.

    It could consist of two stages: before execution and post execution.
    """

    KEY_NAME: ClassVar[str] = VALIDATOR

    def __init__(
        self,
        before: Optional[TValidatorConfig] = None,
        after: Optional[TValidatorConfig] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.__set_before_validator_stage(before)
        self.__set_after_validator_stage(after)

    @classmethod
    def of(cls, config: TValidator) -> ValidatorComponent:
        if isinstance(config, dict):
            return cls(**config)
        else:  # callable(config)
            return cls(after=config)

    def __set_before_validator_stage(self, config: Optional[TValidatorConfig]) -> None:
        if config is None:
            self._before_stage = None
        else:
            self._before_stage = ValidationBeforeStageComponent.of(config)

    def __set_after_validator_stage(self, config: Optional[TValidatorConfig]) -> None:
        if config is None:
            self._after_stage = None
        else:
            self._after_stage = ValidationAfterStageComponent.of(config)

    def __create_validation_error(self, message: str, manager: Manager) -> Exception:
        return ValidationError(
            message,
            component=self,
            manager=manager,
        )

    def _execute_stage_validation(self, manager: Manager, stage_name: str) -> None:
        stage = (
            self._after_stage
            if stage_name == ValidationAfterStageComponent.STAGE_NAME
            else self._before_stage
        )

        if stage is not None:
            try:
                validation_result = stage.execute(manager)
            except Exception as exception:
                raise self.__create_validation_error(stage.ERROR_MESSAGE, manager) from exception

            if not validation_result:
                raise self.__create_validation_error(stage.ERROR_MESSAGE, manager)

    def _execute_before_stage_validation(self, manager: Manager) -> None:
        self._execute_stage_validation(manager, ValidationBeforeStageComponent.STAGE_NAME)

    def _execute_after_stage_validation(self, manager: Manager) -> None:
        self._execute_stage_validation(manager, ValidationAfterStageComponent.STAGE_NAME)

    def execute(self, manager: Manager) -> Iterable[None]:
        yield self._execute_before_stage_validation(manager)
        yield self._execute_after_stage_validation(manager)


class Validatable(Component):
    """
    A mixin encapsulates validation component.
    """

    VALIDATOR_KEYNAME: ClassVar[str] = VALIDATOR
    __validator_component: ValidatorComponent

    def __init__(self, **kwargs: Any):
        self.__set_validator(kwargs.pop(self.VALIDATOR_KEYNAME, None))
        super().__init__(**kwargs)

    def __set_validator(self, validator: Optional[TValidator]) -> None:
        if validator is not None:
            self.__validator_component = ValidatorComponent.of(validator)

    def __execute(self, manager: Manager) -> Generator[None, None, None]:
        try:
            validator_component = self.__validator_component
            executor = validator_component.execute(manager)
            yield next(executor)
            yield next(executor)
        except AttributeError:
            yield from [None, None]

    def execute(self, manager: Manager) -> Generator[None, None, None]:
        yield from self.__execute(manager)
