from unittest.mock import Mock

from streamlined.ray.execution import ExecutionRequirements


def test_execution_requirements_on_new_requirement():
    mock = Mock()

    todos = ExecutionRequirements()
    todos.on_new_requirement += mock

    todos["buy milk"] = False
    mock.assert_called_once_with(prerequisite="buy milk")

    todos["buy rice"] = False
    mock.assert_called_with(prerequisite="buy rice")


def test_execution_requirements_on_requirements_satisfied():
    mock = Mock()

    todos = ExecutionRequirements()
    todos.on_requirements_satisfied += mock

    todos["buy milk"] = False

    assert mock.call_count == 0
    todos["buy milk"] = True
    mock.assert_called_once_with()
