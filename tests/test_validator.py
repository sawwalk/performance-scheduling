"""Tests for validator.py (the schedule checker's logic)."""

from itertools import combinations, permutations
from pathlib import Path

import pytest

from performance_scheduling.io import load_performers, load_schedules
from performance_scheduling.models import BREAK, PerformerData, Schedule
from performance_scheduling.validator import check_schedule, check_schedules

EXAMPLES = Path(__file__).resolve().parent.parent / "data" / "examples"


def performers(members: dict[str, list[str]]) -> PerformerData:
    """PerformerData from {performer: [performances]}; names are the keys themselves."""
    performances = {p for ps in members.values() for p in ps}
    return PerformerData(
        performances_by_performer={who: frozenset(ps) for who, ps in members.items()},
        performer_names={who: who.title() for who in members},
        performance_names={p: p.title() for p in performances},
    )


def schedule(*slots: str, name: str = "s") -> Schedule:
    return Schedule(name=name, slots=tuple(slots))


# Sam is in jazz and tap; Kim is in ballet only.
SHOW = performers({"sam": ["jazz", "tap"], "kim": ["ballet"]})


# ---------------------------------------------------------------- spacing


def test_back_to_back_performances_break_the_basic_rule():
    result = check_schedule(SHOW, schedule("jazz", "tap", "ballet"), gap=1)
    assert not result.valid
    (violation,) = result.violations
    assert violation.performer == "sam"
    assert (violation.performance_a, violation.position_a) == ("jazz", 1)
    assert (violation.performance_b, violation.position_b) == ("tap", 2)
    assert violation.slots_between == 0 and violation.required == 1


def test_one_performance_between_is_enough_at_gap_one():
    result = check_schedule(SHOW, schedule("jazz", "ballet", "tap"), gap=1)
    assert result.valid and result.violations == ()
    assert result.smallest_gap == 1


def test_a_break_between_provides_spacing():
    assert check_schedule(SHOW, schedule("jazz", BREAK, "tap", "ballet"), gap=1).valid
    assert not check_schedule(SHOW, schedule("jazz", "tap", BREAK, "ballet"), gap=1).valid


def test_larger_gaps_need_more_slots():
    one_between = schedule("jazz", BREAK, "tap", "ballet")
    two_between = schedule("jazz", BREAK, BREAK, "tap", "ballet")
    assert not check_schedule(SHOW, one_between, gap=2).valid
    assert check_schedule(SHOW, two_between, gap=2).valid
    assert check_schedule(SHOW, one_between, gap=1).valid


def test_gap_zero_allows_anything():
    assert check_schedule(SHOW, schedule("jazz", "tap", "ballet"), gap=0).valid


def test_negative_gap_is_refused():
    with pytest.raises(ValueError):
        check_schedule(SHOW, schedule("jazz", "tap", "ballet"), gap=-1)


def test_performer_in_three_performances_gets_one_violation_per_neighbouring_pair():
    data = performers({"sam": ["a", "b", "c"]})
    result = check_schedule(data, schedule("a", BREAK, "b", BREAK, "c"), gap=2)
    # a-b and b-c have one slot between; a-c (three between) is fine and not reported
    assert [(v.position_a, v.position_b) for v in result.violations] == [(1, 3), (3, 5)]


def test_a_performer_in_one_performance_never_causes_a_violation():
    data = performers({"sam": ["a"], "kim": ["b"]})
    result = check_schedule(data, schedule("a", "b"), gap=5)
    assert result.valid
    assert result.smallest_gap is None  # nobody has two performances, so any gap is satisfied


def test_smallest_gap_is_the_tightest_spacing_anywhere():
    data = performers({"sam": ["a", "b"], "kim": ["c", "d"]})
    result = check_schedule(data, schedule("a", BREAK, "b", "c", BREAK, BREAK, "d"), gap=1)
    assert result.smallest_gap == 1  # sam has 1 between; kim has 2
    assert result.valid


def test_violations_are_listed_in_running_order():
    data = performers({"zed": ["c", "d"], "amy": ["a", "b"]})
    result = check_schedule(data, schedule("a", "b", "c", "d"), gap=1)
    assert [v.performer for v in result.violations] == ["amy", "zed"]


def test_counts_of_slots_and_breaks_are_reported():
    result = check_schedule(SHOW, schedule("jazz", BREAK, "tap", "ballet"), gap=1)
    assert (result.num_slots, result.num_breaks, result.gap_required) == (4, 1, 1)
    assert result.schedule_name == "s"


# ---------------------------------------------------------------- structure


def test_missing_performance_is_reported():
    result = check_schedule(SHOW, schedule("jazz", "ballet"), gap=1)
    assert not result.valid
    assert [p.message for p in result.problems] == [
        '"Tap" is in the performer file but missing from the schedule.'
    ]


def test_repeated_performance_is_reported_with_its_positions():
    result = check_schedule(SHOW, schedule("jazz", "tap", "jazz", "ballet"), gap=1)
    assert any("appears 2 times" in p.message and "positions 1 and 3" in p.message for p in result.problems)


def test_unknown_performance_is_reported_as_the_organiser_wrote_it():
    typed = Schedule(
        name="s",
        slots=("jazz", "salsa", "tap", "ballet"),
        display_names={"salsa": "Salsa (Open)"},
    )
    result = check_schedule(SHOW, typed, gap=1)
    assert [p.message for p in result.problems] == [
        '"Salsa (Open)" is in the schedule (position 2) but not in the performer file.'
    ]


def test_unknown_name_falls_back_to_the_key_when_no_spelling_is_known():
    result = check_schedule(SHOW, schedule("jazz", "salsa", "tap", "ballet"), gap=1)
    assert '"salsa"' in result.problems[0].message


def test_a_close_unknown_name_gets_a_did_you_mean():
    data = performers({"sam": ["tap (foundations)", "jazz (open)"]})
    result = check_schedule(data, schedule("tap (foundation)", "jazz (open)"), gap=1)
    problem_texts = [p.message for p in result.problems]
    assert any('Did you mean "Tap (Foundations)"?' in text for text in problem_texts)


def test_a_distant_unknown_name_gets_no_suggestion():
    result = check_schedule(SHOW, schedule("jazz", "salsa", "tap", "ballet"), gap=1)
    assert "Did you mean" not in result.problems[0].message


def test_spacing_is_not_checked_when_the_structure_is_wrong():
    # jazz and tap are back to back, but the schedule is also missing ballet
    result = check_schedule(SHOW, schedule("jazz", "tap"), gap=1)
    assert result.violations == ()
    assert result.smallest_gap is None
    assert not result.valid


def test_a_schedule_of_only_breaks_reports_every_performance_missing():
    result = check_schedule(SHOW, schedule(BREAK, BREAK), gap=1)
    assert len(result.problems) == 3


def test_several_schedules_are_checked_in_order():
    results = check_schedules(
        SHOW,
        [schedule("jazz", "ballet", "tap", name="good"), schedule("jazz", "tap", "ballet", name="bad")],
        gap=1,
    )
    assert [(r.schedule_name, r.valid) for r in results] == [("good", True), ("bad", False)]


# ---------------------------------------------------------------- the example files


def example(name: str):
    return load_performers(EXAMPLES / name).data


def test_valid_example_schedule_is_valid_at_gap_one_but_not_two():
    data = example("tiny_feasible.csv")
    (loaded,) = load_schedules(EXAMPLES / "tiny_feasible_schedule_valid.csv").schedules
    assert check_schedule(data, loaded, gap=1).valid
    result = check_schedule(data, loaded, gap=2)
    assert not result.valid
    assert {v.performer for v in result.violations} == {"person 0005", "person 0002"}
    assert check_schedule(data, loaded, gap=1).smallest_gap == 1


def test_invalid_example_schedule_has_exactly_the_documented_violation():
    data = example("tiny_feasible.csv")
    (loaded,) = load_schedules(EXAMPLES / "tiny_feasible_schedule_invalid.csv").schedules
    (violation,) = check_schedule(data, loaded, gap=1).violations
    assert violation.performer == "person 0006"
    assert (violation.performance_a, violation.position_a) == ("bollywood (open)", 3)
    assert (violation.performance_b, violation.position_b) == ("tap (foundations)", 4)
    assert (violation.slots_between, violation.required) == (0, 1)


def test_broken_example_schedule_reports_every_structural_problem():
    data = example("tiny_feasible.csv")
    (loaded,) = load_schedules(EXAMPLES / "tiny_feasible_schedule_broken.csv").schedules
    result = check_schedule(data, loaded, gap=1)
    text = "\n".join(p.message for p in result.problems)
    assert '"Salsa (Open)" is in the schedule (position 1)' in text
    assert '"Hip Hop (Foundations)" appears 2 times' in text
    assert '"Bollywood (Open)" is in the performer file but missing' in text
    assert '"Contemporary (Open)" is in the performer file but missing' in text
    assert len(result.problems) == 4 and result.violations == ()


def test_all_eight_example_schedules_are_valid_at_gap_one_and_none_at_gap_two():
    data = example("tiny_feasible.csv")
    loaded = load_schedules(EXAMPLES / "tiny_feasible_schedules_all8.csv").schedules
    assert all(r.valid for r in check_schedules(data, loaded, gap=1))
    assert not any(r.valid for r in check_schedules(data, loaded, gap=2))


# ---------------------------------------------------------------- against brute force


def every_arrangement(keys: tuple[str, ...], breaks: int):
    """Every way to order the performances among the given number of breaks."""
    total = len(keys) + breaks
    for performance_slots in combinations(range(total), len(keys)):
        for order in permutations(keys):
            slots = [BREAK] * total
            for slot, key in zip(performance_slots, order):
                slots[slot] = key
            yield Schedule(name="x", slots=tuple(slots))


@pytest.mark.parametrize(
    ("filename", "gap", "breaks", "expected"),
    [
        # The expected counts were found earlier by an independent brute-force script
        # that compares conflicting pairs of performances (see docs/test-datasets.md).
        ("tiny_feasible.csv", 1, 0, 8),
        ("tiny_feasible.csv", 1, 1, 152),
        ("tiny_feasible.csv", 2, 0, 0),
        ("tiny_feasible.csv", 2, 1, 8),
        ("tiny_needs_breaks.csv", 1, 0, 0),
        ("tiny_needs_breaks.csv", 1, 1, 0),
        ("tiny_needs_breaks.csv", 1, 2, 12),
        ("tiny_no_conflicts.csv", 1, 0, 720),
        ("tiny_no_conflicts.csv", 2, 1, 5040),
    ],
)
def test_checker_agrees_with_brute_force_counts(filename, gap, breaks, expected):
    data = example(filename)
    valid = sum(
        check_schedule(data, arrangement, gap).valid
        for arrangement in every_arrangement(data.performance_keys, breaks)
    )
    assert valid == expected
