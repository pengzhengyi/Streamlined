from treelib import Node, Tree

from streamlined.common import update


def test_update_insert():
    """
    Harry
    ├── Bill
    └── Jane
        ├── Diane
        │   └── Mary
        └── Mark
    """
    original = Tree()
    original.create_node("Harry", "harry")
    original.create_node("Jane", "jane", parent="harry")
    original.create_node("Bill", "bill", parent="harry")
    original.create_node("Diane", "diane", parent="jane")
    original.create_node("Mary", "mary", parent="diane")
    original.create_node("Mark", "mark", parent="jane")

    """
    Harry
    └── Jane
        └── Mark
            ├── Alice
            └── Bob
                └── Jerry
    """
    hierarchy_of_mark = Tree()
    hierarchy_of_mark.create_node("Harry", "harry")
    hierarchy_of_mark.create_node("Jane", "jane", parent="harry")
    hierarchy_of_mark.create_node("Mark", "mark", parent="jane")
    hierarchy_of_mark.create_node("Alice", "alice", parent="mark")
    hierarchy_of_mark.create_node("Bob", "bob", parent="mark")
    hierarchy_of_mark.create_node("Jerry", "jerry", parent="bob")

    update(
        original,
        hierarchy_of_mark,
        are_equal=lambda source, target: source.identifier == target.identifier,
    )

    """
    Harry
    ├── Bill
    └── Jane
        ├── Diane
        │   └── Mary
        └── Mark
            ├── Alice
            └── Bob
                └── Jerry
    """

    assert len(original.children("mark")) == 2
    assert "alice" in original
    assert "bob" in original
    assert "jerry" in original


def test_update_update_equal():
    """
    Harry
    ├── Bill
    └── Jane
        ├── Diane
        │   └── Mary
        └── Mark
    """
    original = Tree()
    original.create_node("Harry", "harry")
    original.create_node("Jane", "jane", parent="harry")
    original.create_node("Bill", "bill", parent="harry")
    original.create_node("Diane", "diane", parent="jane")
    original.create_node("Mary", "mary", parent="diane")
    original.create_node("Mark", "mark", parent="jane")

    """
    Harry
    └── Jane
        └── Mark
    """
    hierarchy_of_mark = Tree()
    hierarchy_of_mark.create_node("Harry", "harry")
    hierarchy_of_mark.create_node("Jane", "jane", parent="harry")
    hierarchy_of_mark.create_node("Mark", "mark", parent="jane")

    update(
        original,
        hierarchy_of_mark,
        are_equal=lambda source, target: source.identifier == target.identifier,
        update_equal=lambda source, target: setattr(source, "tag", f"[M] {source.identifier}"),
    )

    """
    [M] harry
    ├── Bill
    └── [M] jane
        ├── Diane
        │   └── Mary
        └── [M] mark
    """

    assert original["harry"].tag == "[M] harry"
    assert original["jane"].tag == "[M] jane"
