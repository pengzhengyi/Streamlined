from collections import deque
from unittest.mock import Mock

from streamlined.ray.execution import ExecutionSchedule


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
    # assert len(queue) == 1
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
