from streamlined.component import ExecutionComponent


def test_minimum_execution_component(faker, minimum_manager):
    # Execution
    value = faker.text()
    execution_component = ExecutionComponent(lambda: value)
    result = execution_component(minimum_manager)

    # Result Validation
    assert value == result
