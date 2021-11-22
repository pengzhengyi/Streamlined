from unittest.mock import Mock

from streamlined.ray.execution.execution_plan import DependencyRequirements


def test_dependency_requirements_on_new_requirement():
    mock = Mock()

    todos = DependencyRequirements()
    todos.on_new_requirement += mock

    todos["buy milk"] = False
    mock.assert_called_once_with(prerequisite="buy milk")

    todos["buy rice"] = False
    mock.assert_called_with(prerequisite="buy rice")


def test_dependency_requirements_on_all_requirements_satisfied():
    mock = Mock()

    todos = DependencyRequirements()
    todos.on_all_requirements_satisfied += mock

    todos["buy milk"] = False

    assert mock.call_count == 0
    todos["buy milk"] = True
    mock.assert_called_once_with()
