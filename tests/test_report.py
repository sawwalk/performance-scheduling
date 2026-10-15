"""Tests for report.py (the wording of results)."""

import csv

from performance_scheduling.models import (
    BREAK,
    Issue,
    PerformerData,
    Schedule,
    Severity,
)
from performance_scheduling.report import (
    describe_violation,
    format_check,
    format_issues,
    format_overview,
    format_totals,
    format_violations_csv,
)
from performance_scheduling.validator import check_schedule

DATA = PerformerData(
    performances_by_performer={
        "sam": frozenset({"jazz", "tap"}),
        "kim": frozenset({"ballet"}),
    },
    performer_names={"sam": "Sam Lee", "kim": "Kim Wu"},
    performance_names={"jazz": "Jazz (Open)", "tap": "Tap (Foundations)", "ballet": "Ballet"},
)


def check(*slots: str, name: str = "s", gap: int = 1):
    return check_schedule(DATA, Schedule(name=name, slots=tuple(slots)), gap)


def test_violation_sentence_uses_display_names_and_slots():
    result = check("jazz", "tap", "ballet")
    assert describe_violation(result.violations[0], DATA) == (
        "Sam Lee is in Jazz (Open) (slot 1) and Tap (Foundations) (slot 2): "
        "0 slots between, but at least 1 needed."
    )


def test_violation_sentence_says_slot_in_the_singular():
    result = check("jazz", BREAK, "tap", "ballet", gap=2)
    assert "1 slot between, but at least 2 needed" in describe_violation(result.violations[0], DATA)


def test_valid_schedule_text():
    text = format_check(check("jazz", "ballet", "tap"), DATA)
    assert text.splitlines() == [
        "s: VALID",
        "  3 slots (no breaks).",
        "  Tightest spacing: 1 slot between a performer's performances.",
    ]


def test_break_count_is_mentioned():
    assert "(1 break)" in format_check(check("jazz", BREAK, "tap", "ballet"), DATA)
    assert "(2 breaks)" in format_check(check("jazz", BREAK, BREAK, "tap", "ballet"), DATA)


def test_invalid_schedule_lists_each_violation():
    text = format_check(check("jazz", "tap", "ballet"), DATA)
    assert "s: INVALID" in text
    assert "Not enough rest between performances (1):" in text
    assert "    - Sam Lee is in Jazz (Open)" in text


def test_structural_problems_are_listed_and_spacing_is_said_to_be_skipped():
    text = format_check(check("jazz", "tap"), DATA)
    assert "There is 1 problem with the schedule itself, so spacing was not checked:" in text
    assert '"Ballet" is in the performer file but missing from the schedule.' in text
    assert "Tightest spacing" not in text


def test_text_for_a_show_where_spacing_cannot_matter():
    solo = PerformerData(
        performances_by_performer={"a": frozenset({"x"}), "b": frozenset({"y"})},
        performer_names={"a": "A", "b": "B"},
        performance_names={"x": "X", "y": "Y"},
    )
    result = check_schedule(solo, Schedule(name="s", slots=("x", "y")), 1)
    assert "spacing does not apply" in format_check(result, solo)


def test_overview_table_is_aligned_and_has_one_row_per_schedule():
    checks = [check("jazz", "ballet", "tap", name="schedule_1"), check("jazz", "tap", "ballet", name="s2")]
    lines = format_overview(checks).splitlines()
    assert len(lines) == 3
    assert lines[0].split() == ["Schedule", "Result", "Slots", "Breaks", "Problems", "Tightest", "gap"]
    assert lines[1].split() == ["schedule_1", "VALID", "3", "0", "0", "1"]
    assert lines[2].split() == ["s2", "INVALID", "3", "0", "1", "0"]
    # columns line up: "Result" starts in the same place on every row
    assert len({line.index("VALID") if "VALID" in line and "INVALID" not in line else line.index("INVALID")
                for line in lines[1:]}) == 1


def test_totals_sentences():
    good, bad = check("jazz", "ballet", "tap"), check("jazz", "tap", "ballet")
    assert format_totals([good, good]) == "All 2 schedules are valid."
    assert format_totals([bad, bad]) == "All 2 schedules are invalid."
    assert format_totals([good, bad, good]) == "1 of 3 schedules are invalid."


def test_long_issue_lists_are_shortened():
    issues = [Issue(Severity.WARNING, f"problem {n}") for n in range(25)]
    lines = format_issues("Heading", issues, limit=20).splitlines()
    assert lines[0] == "Heading"
    assert len(lines) == 22
    assert lines[-1] == "  ... and 5 more"


def test_violations_csv_has_a_header_and_one_row_per_violation():
    results = [check("jazz", "tap", "ballet", name="first"), check("jazz", "ballet", "tap", name="second")]
    rows = list(csv.reader(format_violations_csv(results, DATA).splitlines()))
    assert rows[0] == [
        "schedule", "performer", "performance_a", "position_a",
        "performance_b", "position_b", "slots_between", "required",
    ]
    assert rows[1:] == [["first", "Sam Lee", "Jazz (Open)", "1", "Tap (Foundations)", "2", "0", "1"]]


def test_violations_csv_for_a_valid_schedule_is_just_the_header():
    text = format_violations_csv([check("jazz", "ballet", "tap")], DATA)
    assert len(text.splitlines()) == 1
