"""Tests for selection.py."""

import pytest

from performance_scheduling.models import InputError, Severity
from performance_scheduling.selection import Selection, parse_selection

# ---------------------------------------------------------------- what is accepted


@pytest.mark.parametrize(
    ("text", "expected_numbers"),
    [
        ("7", (7,)),
        ("1-5", (1, 2, 3, 4, 5)),
        ("1,4,9", (1, 4, 9)),
        ("1-3,7,20-22", (1, 2, 3, 7, 20, 21, 22)),
        ("3-3", (3,)),
    ],
)
def test_numbers_ranges_and_mixes(text, expected_numbers):
    assert parse_selection(text).numbers() == expected_numbers


@pytest.mark.parametrize("text", ["1-3, 7", " 1 - 3 ,7 ", "1 -3,  7", "\t1-3,7\n"])
def test_spaces_do_not_matter(text):
    assert parse_selection(text).numbers() == (1, 2, 3, 7)


@pytest.mark.parametrize("text", ["9,1,4", "4,4,1,9", "1,4,9,1"])
def test_order_and_repeats_do_not_matter(text):
    assert parse_selection(text).numbers() == (1, 4, 9)


def test_overlapping_and_touching_ranges_are_joined():
    assert parse_selection("1-5,3-8").ranges == ((1, 8),)
    assert parse_selection("1-3,4-6").ranges == ((1, 6),)
    assert parse_selection("1-3,5-6").ranges == ((1, 3), (5, 6))


def test_long_dashes_from_word_processors_are_read_as_hyphens():
    assert parse_selection("1\u20133").numbers() == (1, 2, 3)
    assert parse_selection("1\u20143").numbers() == (1, 2, 3)


@pytest.mark.parametrize("text", ["all", "ALL", "  All  "])
def test_all(text):
    selection = parse_selection(text)
    assert selection.select_all
    assert 1 in selection and 10**9 in selection
    assert selection.count is None and selection.highest is None


# ---------------------------------------------------------------- what the result offers


def test_membership_count_and_highest():
    selection = parse_selection("1-3,7,20-22")
    assert 2 in selection and 7 in selection and 21 in selection
    assert 4 not in selection and 23 not in selection and 0 not in selection
    assert selection.count == 7
    assert selection.highest == 22


@pytest.mark.parametrize("text", ["1-3,7,20-22", "5", "1-100", "2,4,6"])
def test_str_writes_the_choice_back_in_short_form(text):
    assert str(parse_selection(text)) == text


def test_str_tidies_the_choice():
    assert str(parse_selection(" 9 , 1-2 ,2-3 ")) == "1-3,9"
    assert str(parse_selection("ALL")) == "all"


def test_numbers_of_all_is_an_error():
    with pytest.raises(ValueError):
        parse_selection("all").numbers()


def test_selection_is_frozen_and_comparable():
    assert parse_selection("1-3") == Selection(ranges=((1, 3),))


# ---------------------------------------------------------------- what is refused


@pytest.mark.parametrize(
    ("text", "fragment"),
    [
        ("", "Nothing was chosen"),
        ("   ", "Nothing was chosen"),
        ("abc", '"abc" is not a number'),
        ("1,,3", "empty item"),
        ("1,2,", "empty item"),
        (",1", "empty item"),
        ("1 2", '"1 2" is not a number'),
        ("1;2", '"1;2" is not a number'),
        ("1.5", '"1.5" is not a number'),
        ("1-", '"1-" is not a number'),
        ("-3", '"-3" is not a number'),
        ("1-x", '"1-x" is not a number'),
        ("0", "start at 1"),
        ("0-3", "start at 1"),
        ("4-1", "goes backwards"),
        ("all,3", "cannot be combined"),
        ("3,all", "cannot be combined"),
    ],
)
def test_bad_text_gives_a_clear_error(text, fragment):
    with pytest.raises(InputError) as caught:
        parse_selection(text)
    issue = caught.value.issues[0]
    assert issue.severity is Severity.ERROR
    assert fragment in issue.message


def test_syntax_errors_include_an_example_of_what_to_type():
    with pytest.raises(InputError) as caught:
        parse_selection("abc")
    assert "1,4,9" in caught.value.issues[0].message


def test_backwards_range_message_suggests_the_fix():
    with pytest.raises(InputError, match="Write it as 1-4"):
        parse_selection("4-1")


def test_numbers_above_the_maximum_are_refused():
    assert parse_selection("10", maximum=10).numbers() == (10,)
    with pytest.raises(InputError, match="highest available number is 10"):
        parse_selection("11", maximum=10)
    with pytest.raises(InputError, match="highest available number is 10"):
        parse_selection("1-12", maximum=10)


def test_choices_larger_than_the_count_limit_are_refused():
    assert parse_selection("1-100", max_count=100).count == 100
    with pytest.raises(InputError, match="chooses 101 items but the most allowed at once is 100"):
        parse_selection("1-101", max_count=100)


def test_counting_uses_the_joined_ranges_not_the_text():
    # 1-60 and 40-100 overlap, so this is 100 numbers, not 121
    assert parse_selection("1-60,40-100", max_count=100).count == 100


def test_a_huge_range_is_refused_instantly_without_building_a_list():
    with pytest.raises(InputError):
        parse_selection("1-1000000000000", max_count=100)


def test_all_is_not_checked_against_the_count_limit():
    assert parse_selection("all", max_count=100).select_all
