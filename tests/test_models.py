"""Tests for models.py. The containers hold little logic, so these tests are short."""

from dataclasses import FrozenInstanceError

import pytest

from performance_scheduling.models import (
    BREAK,
    ConflictMap,
    InputError,
    Issue,
    PerformerData,
    PerformerLoad,
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
