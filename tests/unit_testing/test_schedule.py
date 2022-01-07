import asyncio
from typing import List

import pytest

from streamlined.scheduling import Schedule, Unit


@pytest.mark.asyncio
async def test_scheduling_async_iter():
    schedule = Schedule()
    schedule.push(
        primary_school := Unit("primary school"), has_prerequisites=False, has_dependents=True
    )

    schedule.push(
        middle_school := Unit("middle school"), has_prerequisites=True, has_dependents=True
    )
    middle_school.require(primary_school)

    schedule.push(high_school := Unit("high school"), has_prerequisites=True, has_dependents=True)
    high_school.require(middle_school)

    schedule.push(university := Unit("university"), has_prerequisites=True, has_dependents=False)
    university.require(high_school)

    order: List[str] = []
    async for unit in schedule:
        order.append(unit.value)
        await asyncio.sleep(0.1)
        schedule.notify(unit)

    assert order == ["primary school", "middle school", "high school", "university"]


@pytest.mark.asyncio
async def test_scheduling_walk_greedy():
    schedule = Schedule()
    schedule.push(task1 := Unit("task 1"), has_prerequisites=False, has_dependents=False)
    schedule.push(task2 := Unit("task 2"), has_prerequisites=False, has_dependents=False)

    iteration = 0

    async for units in schedule.walk_greedy():
        if iteration == 0:
            assert len(units) == 2
            assert task1 in units
            assert task2 in units
        elif iteration == 1:
            assert len(units) == 0
            schedule.notify(task1)
            schedule.notify(task2)
        iteration += 1
