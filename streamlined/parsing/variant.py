from functools import cache, cached_property
from typing import Any, Callable, Iterable, List, Sequence, Tuple

from ..common import AND, IS_DICT, NOT, OR, TYPE, Predicate, Transform
from .simplification import Simplification


class Variant(Simplification):
    """
    A variant capture an extended config format.

    To reduce the parsing work, Variant will reduce this extended
    format to standard format.
    """

    __slots__ = ("_variant_simplifications",)

    def __init__(self) -> None:
        self._init_simplifications_for_variant()
        super().__init__()

    @classmethod
    def get_name(cls) -> str:
        return cls.__name__.lower()

    @classmethod
    def verify(cls, value: Any) -> None:
        """
        Verify is compliant variant config format.

        Should raise exception when not compliant.
        """

    @classmethod
    def reduce(cls, value: Any) -> Any:
        """
        Convert value from variant format to standard format.
        """
        cls.verify(value)

        return value

    @classmethod
    def is_variant(cls, value: Any) -> bool:
        return IS_DICT(value) and TYPE in value and value[TYPE] == cls.get_name()

    @classmethod
    def _get_simplifications_for_variant(cls) -> List[Tuple[Predicate, Transform]]:
        """
        When simplifications for variant can be statically computed (not varying
        per instance). This method should be implemented to compute the
        simplifications for this variant.
        """
        return []

    @classmethod
    @property
    @cache
    def _static_variant_simplifications(cls) -> List[Tuple[Predicate, Transform]]:
        return cls._get_simplifications_for_variant()

    @cached_property
    def is_simplified_variant(self) -> Callable[[Any], bool]:
        return AND(self.is_variant, NOT(OR(*self._variant_predicates)))

    @cached_property
    def is_not_simplified_variant(self) -> Callable[[Any], bool]:
        return AND(self.is_variant, OR(*self._variant_predicates))

    @cached_property
    def simplify_variant(self) -> Callable[[Any], Any]:
        return self.aggregate(self._variant_simplifications)

    @cached_property
    def name(self) -> str:
        return self.__class__.get_name()

    @property
    def _variant_predicates(self) -> Iterable[Predicate]:
        for predicate, _ in self._variant_simplifications:
            yield predicate

    def _init_simplifications_for_variant(self) -> None:
        """
        By default, it will use static computed (cached) simplifications for this
        variant. To use the default workflow, `_get_simplifications_for_variant`
        should be implemented to statically compute the simplifications.

        Otherwise, when the simplifications for this variant varies per instance.
        This method should be overridden to bind custom value for
        `_variant_simplifications`.
        """
        self._variant_simplifications: List[
            Tuple[Predicate, Transform]
        ] = self._static_variant_simplifications

    def _init_simplifications(self) -> None:
        super()._init_simplifications()

        self.simplifications.append((self.is_not_simplified_variant, self.simplify_variant))

        self.simplifications.append((self.is_simplified_variant, self.reduce))


class WithVariants(Simplification):
    __slots__ = ("variants",)

    @classmethod
    def _get_static_variants(cls) -> Sequence[Variant]:
        """
        When variants can be statically computed (not varying per instance).
        This method should be implemented to compute the variants.
        """
        return []

    @classmethod
    @property
    @cache
    def _static_variants(cls) -> Sequence[Variant]:
        return cls._get_static_variants()

    @classmethod
    def _get_simplifications(cls) -> List[Tuple[Predicate, Transform]]:
        simplifications = super()._get_simplifications()

        for variant in cls._get_static_variants():
            simplifications.extend(variant.simplifications)

        return simplifications

    def __init__(self) -> None:
        self._init_variants()
        super().__init__()

    def _init_variants(self) -> None:
        """
        By default, it will use static computed (cached) variants. To use the default workflow, `_get_static_variants` should be implemented to
        statically compute the simplifications.

        Otherwise, when the list of variants varies per instance.
        This method should be overridden to bind custom value for `variants`.
        """
        self.variants: Sequence[Variant] = self._static_variants
