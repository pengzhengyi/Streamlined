import asyncio
from typing import List

import pytest

from streamlined.scheduling import Scheduling, Unit


@pytest.mark.asyncio
async def test_scheduling_async_iter():
    schedule = Scheduling()
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
