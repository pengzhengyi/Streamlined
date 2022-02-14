import pytest

from streamlined import Parallel
from streamlined.scheduling import Unit


@pytest.mark.asyncio
async def test_parallel_scheduler():
    units = [Unit(name) for name in ["A", "B", "C", "D", "E"]]
    scheduler = Parallel(max_concurrency=2)
    schedule = scheduler.create(units)

    iteration = 0
    async for units in schedule.walk_greedy():
        if iteration == 0 or iteration == 1:
            assert len(units) == 2
        else:
            assert len(units) == 1

        for unit in units:
            schedule.notify(unit)
        iteration += 1
