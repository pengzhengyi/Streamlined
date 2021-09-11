from streamlined.component import ArgumentsComponent
from streamlined.component.argument_component import ArgumentComponent


def test_argument_component_registering_argument_values(faker, minimum_manager):
    # Setup
    text = faker.text()
    component = ArgumentsComponent(
        [{ArgumentComponent.NAME_KEYNAME: "text", ArgumentComponent.VALUE_KEYNAME: text}]
    )
    component.execute(minimum_manager)

    # Validation
    assert minimum_manager.get_value("text") == text
