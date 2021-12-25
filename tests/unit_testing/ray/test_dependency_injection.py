from streamlined.ray.services import DependencyInjection


def test_dependency_injection_prepare():
    def add(a, b):
        return a + b

    assert add(1, 2) == 3

    argument_values = {"a": 10, "b": 20}
    prepared_add = DependencyInjection.prepare(add, argument_values)
    assert prepared_add() == 30
