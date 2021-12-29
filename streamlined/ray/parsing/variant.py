from functools import cached_property
from typing import Any, Dict, Iterable, List, Tuple

from ..common import AND, IS_DICT, TYPE, Predicate, Transform
from .simplification import Simplification


class Variant(Simplification):
    """
    A variant capture an extended config format.

    To reduce the parsing work, Variant will reduce this extended
    format to standard format.
    """

    _variant_simplifications: List[Tuple[Predicate, Transform]]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._init_simplifications_for_variant()
        super().__init__(*args, **kwargs)

    @classmethod
    def verify(cls, value: Any) -> None:
        """
        Verify is compliant variant config format.

        Should raise exception when not compliant and return `value` when compliant.
        """
        return value

    @cached_property
    def name(self) -> str:
        return self.__class__.get_name()

    @classmethod
    def get_name(cls) -> str:
        return cls.__name__.lower()

    @classmethod
    def standardize(cls, value: Any) -> Any:
        """
        Convert value from variant format to standard format.
        """
        return value

    @classmethod
    def is_variant(cls, value: Any) -> bool:
        return IS_DICT(value) and value[TYPE] == cls.get_name()

    def _init_simplifications_for_variant(self) -> None:
        self._variant_simplifications = []

    def _init_simplifications(self) -> None:
        super()._init_simplifications()

        self.simplifications.append(
            (self.is_variant, self.aggregate(self._variant_simplifications))
        )

        self.simplifications.append((self.is_variant, self.verify))

        self.simplifications.append((self.is_variant, self.standardize))


class WithVariants(Simplification):
    variants: List[Variant]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._init_variants()
        super().__init__(*args, **kwargs)

    def _init_variants(self) -> None:
        self.variants = []

    def _init_simplifications(self) -> None:
        super()._init_simplifications()

        for variant in self.variants:
            self.simplifications.extend(variant.simplifications)
