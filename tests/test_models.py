"""Tests for models.py. The containers hold little logic, so these tests are short."""

from dataclasses import FrozenInstanceError

import pytest

from performance_scheduling.models import (
    BREAK,
    ConflictMap,
    FinderResult,
    FinderStatus,
    InputError,
    Issue,
    PerformerData,
    PerformerLoad,
    PinLoad,
    Pins,
    Schedule,
    Severity,
)


def make_performer_data() -> PerformerData:
    # Sam is in Jazz and Tap; Alex is in Tap only; Kim is in Ballet only.
    return PerformerData(
        performances_by_performer={
            "sam": frozenset({"jazz", "tap"}),
            "alex": frozenset({"tap"}),
            "kim": frozenset({"ballet"}),
        },
        performer_names={"sam": "Sam", "alex": "Alex", "kim": "Kim"},
        performance_names={"jazz": "Jazz", "tap": "Tap", "ballet": "Ballet"},
    )


def test_issue_text_includes_row_when_given():
    issue = Issue(Severity.WARNING, "blank performance, row dropped", row=9)
    assert str(issue) == "WARNING: row 9: blank performance, row dropped"


def test_issue_text_without_row():
    issue = Issue(Severity.ERROR, "no usable rows")
    assert str(issue) == "ERROR: no usable rows"


def test_input_error_lists_every_issue():
    issues = [Issue(Severity.ERROR, "first problem"), Issue(Severity.ERROR, "second problem")]
    error = InputError(issues)
    assert error.issues == tuple(issues)
    assert "first problem" in str(error)
    assert "second problem" in str(error)


def test_performance_keys_are_in_alphabetical_order():
    assert make_performer_data().performance_keys == ("ballet", "jazz", "tap")


def test_performers_by_performance_flips_the_mapping():
    flipped = make_performer_data().performers_by_performance
    assert flipped == {
        "jazz": frozenset({"sam"}),
        "tap": frozenset({"sam", "alex"}),
        "ballet": frozenset({"kim"}),
    }


def test_conflict_lookup_works_in_either_order():
    conflicts = ConflictMap(
        shared={frozenset({"jazz", "tap"}): frozenset({"sam"})},
        neighbours={"jazz": frozenset({"tap"}), "tap": frozenset({"jazz"}), "ballet": frozenset()},
    )
    assert conflicts.conflict("jazz", "tap")
    assert conflicts.conflict("tap", "jazz")
    assert not conflicts.conflict("jazz", "ballet")
    assert conflicts.shared_performers("tap", "jazz") == frozenset({"sam"})
    assert conflicts.shared_performers("jazz", "ballet") == frozenset()


def test_schedule_counts_and_positions_start_at_one():
    schedule = Schedule(name="schedule_1", slots=("jazz", BREAK, "tap", "ballet"))
    assert schedule.num_slots == 4
    assert schedule.num_breaks == 1
    assert schedule.positions() == {"jazz": 1, "tap": 3, "ballet": 4}


def test_frozen_containers_cannot_be_changed():
    schedule = Schedule(name="schedule_1", slots=("jazz",))
    with pytest.raises(FrozenInstanceError):
        schedule.name = "other"  # type: ignore[misc]


def test_performer_load_carries_the_data_and_counts():
    load = PerformerLoad(data=make_performer_data(), warnings=(), rows_read=4, rows_used=4)
    assert load.data.performance_keys == ("ballet", "jazz", "tap")
    assert load.warnings == ()


def test_pins_know_which_slots_are_breaks_and_where_performances_are_pinned():
    pins = Pins(slots={1: "jazz", 12: BREAK, 5: BREAK, 20: "tap"})
    assert pins.break_positions == (5, 12)
    assert pins.performance_positions == {"jazz": 1, "tap": 20}


def test_no_pins_is_fine():
    pins = Pins(slots={})
    assert pins.break_positions == ()
    assert pins.performance_positions == {}


def test_pins_compare_by_slots_only_not_by_spelling():
    assert Pins(slots={1: "jazz"}, display_names={"jazz": "Jazz"}) == Pins(slots={1: "jazz"})


def test_pin_load_carries_the_pins_and_warnings():
    load = PinLoad(pins=Pins(slots={1: BREAK}), warnings=())
    assert load.pins.break_positions == (1,)
    assert load.warnings == ()


def test_finder_statuses_have_plain_names():
    assert [s.value for s in FinderStatus] == ["found", "exhausted", "stopped"]


def test_a_finder_result_defaults_to_no_explanation_and_no_blocking_pins():
    schedule = Schedule(name="schedule_1", slots=("jazz",))
    result = FinderResult(FinderStatus.FOUND, (schedule,))
    assert result.schedules == (schedule,)
    assert result.explanation == () and result.blocking_pins == ()


def test_a_finder_result_can_carry_an_explanation_and_blocking_pins():
    reason = Issue(Severity.ERROR, "no schedule exists")
    result = FinderResult(FinderStatus.EXHAUSTED, (), explanation=(reason,), blocking_pins=(3, 4))
    assert result.explanation == (reason,) and result.blocking_pins == (3, 4)
