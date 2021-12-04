import asyncio
from collections import deque
from unittest.mock import Mock

import pytest

from streamlined.ray.execution import (
    DependencyTrackingAsyncExecutionUnit,
    ExecutionSchedule,
)


def test_execution_schedule_synchronous_execution():
    shopping_schedule = ExecutionSchedule()

    # Tasks
    go_shopping_eu = shopping_schedule.push(go_shopping := Mock(name="go shopping"))
    buy_milk_eu = shopping_schedule.push(buy_milk := Mock(name="buy milk"))
    buy_egg_eu = shopping_schedule.push(buy_egg := Mock(name="buy egg"))
    checkout_eu = shopping_schedule.push(checkout := Mock(name="checkout"))

    # Dependencies
    buy_milk_eu.require(go_shopping_eu)
    buy_egg_eu.require(go_shopping_eu)
    checkout_eu.require(buy_milk_eu)
    checkout_eu.require(buy_egg_eu)

    # run
    queue = deque()

    tasks = shopping_schedule.walk(queue, enqueue=queue.append, dequeue=queue.popleft)

    # execute first task -- go shopping
    assert go_shopping_eu == next(tasks)
    assert len(queue) == 0
    go_shopping_eu()
    assert buy_milk_eu.are_requirements_satisfied
    assert buy_egg_eu.are_requirements_satisfied

    # buy milk and buy egg
    assert len(queue) == 2
    next(tasks)()
    assert not checkout_eu.are_requirements_satisfied
    next(tasks)()
    assert checkout_eu.are_requirements_satisfied

    # checkout
    assert len(queue) == 1
    assert checkout_eu == next(tasks)
    assert len(queue) == 0
    checkout_eu()


def test_execution_schedule_circular_execution():
    """
    WeekStart ────── Day ────── Night ┰─── = day7 ─── WeekEnd
                      ┗━━━ < day 7 ━━━┛
    """

    # passing of a week
    week_schedule = ExecutionSchedule()

    # Tasks
    week_start_eu = week_schedule.push(
        week_start := Mock(name="week start"), has_prerequisites=False, has_dependents=True
    )
    day_eu = week_schedule.push(
        day := Mock(name="day"), has_prerequisites=True, has_dependents=True
    )
    night_eu = week_schedule.push(
        night := Mock(name="night"), has_prerequisites=True, has_dependents=True
    )
    week_end_eu = week_schedule.push(
        week_end := Mock(name="week end"), has_prerequisites=True, has_dependents=False
    )

    day_eu.require(week_start_eu, group="from week start")
    night_eu.require(day_eu)

    transition_from_night_to_day = Mock()
    transition_from_night_to_day.side_effect = [True, True, True, True, True, True, False]
    day_eu.require(night_eu, condition=transition_from_night_to_day, group="from night")
    transition_to_week_end = Mock()
    transition_to_week_end.side_effect = [False, False, False, False, False, False, True]
    week_end_eu.require(night_eu, transition_to_week_end)

    queue = deque()

    for task in week_schedule.walk(queue, enqueue=queue.append, dequeue=queue.popleft):
        task()

    week_start.assert_called_once()
    assert day.call_count == 7
    assert transition_from_night_to_day.call_count == 7
    assert night.call_count == 7
    assert transition_to_week_end.call_count == 7
    week_end.assert_called_once()


@pytest.mark.asyncio
async def test_execution_schedule_asynchronous_execution():
    prepare_mock = Mock()
    prepare_eu = DependencyTrackingAsyncExecutionUnit.empty()

    @DependencyTrackingAsyncExecutionUnit.bind(execution_unit=prepare_eu)
    async def prepare():
        await asyncio.sleep(0.1)
        prepare_mock()

    cook_mock = Mock()
    cook_eu = DependencyTrackingAsyncExecutionUnit.empty()

    @DependencyTrackingAsyncExecutionUnit.bind(execution_unit=cook_eu)
    async def cook():
        await asyncio.sleep(0.1)
        cook_mock()

    eat_mock = Mock()
    eat_eu = DependencyTrackingAsyncExecutionUnit.empty()

    @DependencyTrackingAsyncExecutionUnit.bind(execution_unit=eat_eu)
    async def eat():
        await asyncio.sleep(0.1)
        eat_mock()

    lunch_steps = ExecutionSchedule()
    assert prepare_eu == lunch_steps.push(prepare_eu)
    assert cook_eu == lunch_steps.push(cook_eu)
    assert eat_eu == lunch_steps.push(eat_eu)

    cook_eu.require(prepare_eu)
    eat_eu.require(cook_eu)

    async for task in lunch_steps:
        await task()

    prepare_mock.assert_called_once()
    cook_mock.assert_called_once()
    eat_mock.assert_called_once()
