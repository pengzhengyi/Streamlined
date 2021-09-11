from streamlined import TAGS
from streamlined.component.capabilities import WithTag


def test_tag_set_and_get_tag(faker, minimum_manager):
    # Setup
    tags = faker.words()
    tag_capability = WithTag(**{TAGS: tags})
    tag_capability._execute_for_tags(minimum_manager)

    for tag in tags:
        assert minimum_manager.has_tag(tag_capability, tag)
