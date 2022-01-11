from unittest.mock import Mock

from streamlined.utils import dict_cmp


def test_dict_cmp_simple():
    source = {"a": 1}
    key_unequal_target = {"aaa": 1}
    value_unequal_target = {"a": 10}
    for itempair in dict_cmp(source, source):
        assert itempair.is_present_and_equal

    for itempair in dict_cmp(source, key_unequal_target, lambda key: key * 3):
        assert itempair.is_present_and_equal

    for itempair in dict_cmp(source, value_unequal_target):
        assert itempair.is_present_in_both and not itempair.are_equal


def test_dict_cmp_diff():
    source = {"a": 1, "b": 2, "d": 0}
    target = {"c": 3, "b": 2, "d": -1}

    itempairs = list(dict_cmp(source, target))
    assert len(itempairs) == 4

    missing_in_source_formatter = Mock()
    missing_in_target_formatter = Mock()
    unequal_value_formatter = Mock()
    equal_value_formatter = Mock()

    for itempair in itempairs:
        itempair.format(
            missing_in_source_formatter,
            missing_in_target_formatter,
            unequal_value_formatter,
            equal_value_formatter,
        )

    missing_in_source_formatter.assert_called_once_with("c", 3)
    missing_in_target_formatter.assert_called_once_with("a", 1)
    unequal_value_formatter.assert_called_once_with("d", 0, "d", -1)
    equal_value_formatter.assert_called_once_with("b", 2, "b", 2)
