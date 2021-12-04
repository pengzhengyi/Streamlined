from streamlined.ray.common import Bag, BidirectionalIndex


def test_bag():
    names = Bag()
    names["Male"] = "John"
    names["Male"] = "Bob"
    names["Female"] = "Alice"

    assert len(names) == 2
    assert len(names["Male"]) == 2
    assert len(names["Female"]) == 1

    assert names["Female"] == {"Alice"}


def test_bidirectional_index():
    groups = BidirectionalIndex()
    groups["red"] = "John"
    groups["red"] = "Alice"
    groups["blue"] = "Bob"

    assert len(groups["red"]) == 2
    assert len(groups["blue"]) == 1
    assert len(groups["Alice"]) == 1
    assert "John" in groups["red"]
    assert "blue" in groups["Bob"]
