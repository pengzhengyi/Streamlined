from unittest.mock import Mock

from streamlined.ray.execution import ExecutionStatus, ExecutionUnit


def test_execution_status():
    mock = Mock()
    execution_unit = ExecutionUnit(mock)

    assert execution_unit.status == ExecutionStatus.NotStarted
    execution_unit(1)

    mock.assert_called_once_with(1)
    assert execution_unit.status == ExecutionStatus.Completed


def test_on_complete_callable():
    mock = Mock()
    execution_unit = ExecutionUnit(mock)
    on_complete_mock = Mock()
    execution_unit.on_complete += on_complete_mock

    execution_unit()
    on_complete_mock.assert_called_once()
