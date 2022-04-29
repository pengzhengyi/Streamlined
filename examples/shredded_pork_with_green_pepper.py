from __future__ import annotations

import asyncio
from enum import Enum, auto
from types import TracebackType
from typing import Any, Awaitable, Callable, Optional, Type

from streamlined.ui import Console
from streamlined.unit import Function, Unit


class Ingredient:
    @classmethod
    def from_(cls, ingredient: Ingredient) -> Ingredient:
        return cls()


class Resource(Enum):
    VACANT = auto()
    OCCUPIED = auto()

    @property
    def is_vacant(self) -> bool:
        return self == Resource.VACANT

    @property
    def is_occupied(self) -> bool:
        return self == Resource.OCCUPIED

    @classmethod
    def new(cls) -> Resource:
        return cls.VACANT

    def __getattr__(self, name: str) -> Callable[..., Awaitable[None]]:
        async def use(*args: Any, duration: int, **kwargs: Any) -> None:
            with self:
                asyncio.sleep(duration)

        return use

    def __enter__(self) -> None:
        self.occupy()

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> Any:
        self.release()

    def occupy(self) -> Resource:
        if self.is_occupied:
            raise ResourceWarning("Already occupied!")
        return Resource.OCCUPIED

    def release(self) -> Resource:
        if self.is_vacant:
            raise ResourceWarning("Not occupied!")
        return Resource.VACANT


async def cut_ingredient(
    ingredient: Ingredient, cutting_board: Resource, knife: Resource
) -> Ingredient:
    with cutting_board:
        knife.cut(ingredient, duration=60)
        return Ingredient.from_(ingredient)


async def wash_pepper(pepper: Ingredient, kitchen_sink: Resource) -> Ingredient:
    await kitchen_sink.wash(pepper, duration=10)
    return Ingredient.from_(pepper)


async def mariate(bowl: Resource, ingredient: Ingredient, *sauces: Ingredient) -> Ingredient:
    bowl.mariate(ingredient, *sauces, duration=60)
    return Ingredient.from_(ingredient)


async def add_to_wak(wak: Resource, *ingredients: Ingredient) -> None:
    wak.add(ingredients, duration=1)


def main() -> None:
    ui = Console()  # Web
    cook_shredded_pork_with_green_pepper = Unit(
        Function(wash_pepper)
        .name("wash pepper")
        .require(lambda kitchen_sink: kitchen_sink.is_vacant)
        .output("washed_pepper"),
        Function(cut_ingredient)
        .name("cut pepper into shreds")
        .require(lambda knife: knife.is_vacant, lambda cutting_board: cutting_board.is_vacant)
        .parameters(ingredient="washed_pepper")
        .output("pepper_shreds"),
        Function(cut_ingredient)
        .name("cut ginger into shreds")
        .require(lambda knife: knife.is_vacant, lambda cutting_board: cutting_board.is_vacant)
        .parameters(ingredient="ginger")
        .output("ginger_shreds"),
        Function(cut_ingredient)
        .name("cut garlic into slices")
        .require(lambda knife: knife.is_vacant, lambda cutting_board: cutting_board.is_vacant)
        .parameters(ingredient="garlic")
        .output("garlic_slices"),
        Function(cut_ingredient)
        .name("cut pork into slices")
        .require(lambda knife: knife.is_vacant, lambda cutting_board: cutting_board.is_vacant)
        .parameters(ingredient="pork")
        .output("pork_slices"),
        Function(mariate)
        .name("marinate pork slices")
        .require(lambda bowl: bowl.is_vacant)
        .parameters(ingredient="pork_slices", sauces=["salt", "soy sauce", "oil"])
        .output("marinated_pork_slices"),
        Function(add_to_wak)
        .name("add oil to the wak")
        .require(lambda wak: wak.is_vacant)
        .parameters(ingredients=["oil"])
        .then(
            Function(add_to_wak)
            .name("add pork slices")
            .require(lambda wak: wak.is_vacant)
            .parameters(ingredients=["marinated_pork_slices"])
        )
        .then(
            Function(add_to_wak)
            .name("add garlic slices")
            .require(lambda wak: wak.is_vacant)
            .parameters(ingredients=["garlic_slices"])
        )
        .then(
            Function(add_to_wak)
            .name("add pepper slices")
            .require(lambda wak: wak.is_vacant)
            .parameters(ingredients=["pepper_slices"])
        )
        .then(
            Function(add_to_wak)
            .name("add salt")
            .require(lambda wak: wak.is_vacant)
            .parameters(ingredients=["pepper_salt"])
        )
        .then(
            Function(add_to_wak)
            .name("add sugar")
            .require(lambda wak: wak.is_vacant)
            .parameters(ingredients=["sugar"])
        )
        .then(
            Function(add_to_wak)
            .name("add vinegar")
            .require(lambda wak: wak.is_vacant)
            .parameters(ingredients=["vinegar"])
        )
        .then(
            Function(add_to_wak)
            .name("add soy sauce")
            .require(lambda wak: wak.is_vacant)
            .parameters(ingredients=["soy sauce"])
        ),
    ).receive(
        resource={
            "kitchen_sink": Resource.new(),
            "cutting_board": Resource.new(),
            "knife": Resource.new(),
            "bowl": Resource.new(),
            "wak": Resource.new(),
        },
        ingredients={
            "pork": Ingredient(),
            "pepper": Ingredient(),
            "ginger": Ingredient(),
            "garlic": Ingredient(),
            "salt": Ingredient(),
            "soy sauce": Ingredient(),
            "oil": Ingredient(),
            "sugar": Ingredient(),
            "vinegar": Ingredient(),
        },
    )
    ui.schedule(cook_shredded_pork_with_green_pepper)
