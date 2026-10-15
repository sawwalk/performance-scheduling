"""Tests for report.py (the wording of results)."""

import csv

from performance_scheduling.models import (
    BREAK,
    Issue,
    PerformerData,
    Schedule,
    Severity,
    Violation,
)
from performance_scheduling.report import (
    describe_pair,
    format_check,
    format_issues,
    format_overview,
    format_totals,
    format_violations_csv,
    group_violations,
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

# Two performers (amy and bo) are both in jazz and tap; cy is in tap and ballet.
CROWD = PerformerData(
    performances_by_performer={
        "amy": frozenset({"jazz", "tap"}),
        "bo": frozenset({"jazz", "tap"}),
        "cy": frozenset({"tap", "ballet"}),
    },
    performer_names={"amy": "Amy", "bo": "Bo", "cy": "Cy"},
    performance_names={"jazz": "Jazz", "tap": "Tap", "ballet": "Ballet"},
)


def check(*slots: str, name: str = "s", gap: int = 1, data: PerformerData = DATA):
    return check_schedule(data, Schedule(name=name, slots=tuple(slots)), gap)


# ---------------------------------------------------------------- grouping


def test_violations_for_the_same_pair_are_gathered_into_one_entry():
    result = check("jazz", "tap", "ballet", data=CROWD)  # jazz-tap: amy and bo; tap-ballet: cy
    pairs = group_violations(result.violations)
    assert len(result.violations) == 3
    assert len(pairs) == 2
    assert (pairs[0].performance_a, pairs[0].performance_b) == ("jazz", "tap")
    assert pairs[0].performers == ("amy", "bo")
    assert (pairs[1].performance_a, pairs[1].performance_b) == ("tap", "ballet")
    assert pairs[1].performers == ("cy",)


def test_pairs_are_listed_in_running_order_whatever_order_the_violations_arrive_in():
    late = Violation("cy", "tap", 5, "ballet", 6, 0, 1)
    early = Violation("amy", "jazz", 1, "tap", 2, 0, 1)
    pairs = group_violations([late, early])
    assert [(p.position_a, p.position_b) for p in pairs] == [(1, 2), (5, 6)]


def test_no_violations_means_no_pairs():
    assert group_violations([]) == ()


def test_pair_sentence_uses_display_names_slots_and_the_number_affected():
    (pair,) = group_violations(check("jazz", "tap", "ballet").violations)
    assert describe_pair(pair, DATA) == (
        "Jazz (Open) (slot 1) and Tap (Foundations) (slot 2): "
        "0 slots between, at least 1 needed (1 performer affected)."
    )


def test_pair_sentence_says_slot_in_the_singular_and_performers_in_the_plural():
    (pair, *_) = group_violations(check("jazz", BREAK, "tap", "ballet", gap=2, data=CROWD).violations)
    text = describe_pair(pair, CROWD)
    assert "1 slot between, at least 2 needed" in text
    assert "(2 performers affected)" in text


# ---------------------------------------------------------------- one schedule's write-up


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


def test_invalid_schedule_lists_the_pairs_first_then_who_is_affected():
    text = format_check(check("jazz", "tap", "ballet", data=CROWD), CROWD)
    assert text.splitlines() == [
        "s: INVALID",
        "  3 slots (no breaks).",
        "",
        "  ===== CONFLICTING PERFORMANCE PAIRS (2) =====",
        "   1. Jazz (slot 1) and Tap (slot 2): 0 slots between, at least 1 needed (2 performers affected).",
        "   2. Tap (slot 2) and Ballet (slot 3): 0 slots between, at least 1 needed (1 performer affected).",
        "",
        "  ===== WHO IS AFFECTED (3 performers) =====",
        "   1. Jazz and Tap",
        "        - Amy",
        "        - Bo",
        "   2. Tap and Ballet",
        "        - Cy",
        "  ===== END OF SPACING PROBLEMS =====",
        "",
        "  Tightest spacing: 0 slots between a performer's performances.",
    ]


def test_a_performer_in_two_conflicting_pairs_is_counted_once_in_the_total():
    data = PerformerData(
        performances_by_performer={"amy": frozenset({"a", "b", "c"})},
        performer_names={"amy": "Amy"},
        performance_names={"a": "A", "b": "B", "c": "C"},
    )
    text = format_check(check("a", "b", "c", data=data), data)
    assert "CONFLICTING PERFORMANCE PAIRS (2)" in text
    assert "WHO IS AFFECTED (1 performer)" in text


def test_structural_problems_get_their_own_section_and_spacing_is_said_to_be_skipped():
    text = format_check(check("jazz", "tap"), DATA)
    assert text.splitlines() == [
        "s: INVALID",
        "  2 slots (no breaks).",
        "",
        "  ===== PROBLEMS WITH THE SCHEDULE ITSELF (1) =====",
        "  Spacing was not checked.",
        '    - "Ballet" is in the performer file but missing from the schedule.',
        "  ===== END OF SCHEDULE PROBLEMS =====",
    ]


def test_text_for_a_show_where_spacing_cannot_matter():
    solo = PerformerData(
        performances_by_performer={"a": frozenset({"x"}), "b": frozenset({"y"})},
        performer_names={"a": "A", "b": "B"},
        performance_names={"x": "X", "y": "Y"},
    )
    result = check_schedule(solo, Schedule(name="s", slots=("x", "y")), 1)
    assert "spacing does not apply" in format_check(result, solo)


# ---------------------------------------------------------------- several schedules


def test_overview_table_is_aligned_and_has_one_row_per_schedule():
    checks = [
        check("jazz", "ballet", "tap", name="schedule_1"),
        check("jazz", "tap", "ballet", name="s2"),
    ]
    lines = format_overview(checks).splitlines()
    assert len(lines) == 3
    assert lines[0].split() == ["Schedule", "Result", "Slots", "Breaks", "Problems", "Tightest", "gap"]
    assert lines[1].split() == ["schedule_1", "VALID", "3", "0", "0", "1"]
    assert lines[2].split() == ["s2", "INVALID", "3", "0", "1", "0"]
    starts = {line.split()[1] for line in lines[1:]}
    assert starts == {"VALID", "INVALID"}
    # "Result" values start in the same column on every row
    assert len({line.index(line.split()[1]) for line in lines[1:]}) == 1


def test_overview_counts_conflicting_pairs_not_individual_violations():
    row = format_overview([check("jazz", "tap", "ballet", data=CROWD)]).splitlines()[1]
    assert row.split()[4] == "2"  # two pairs, although three performers are affected


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


# ---------------------------------------------------------------- the CSV report


def test_violations_csv_has_a_header_and_one_row_per_violation():
    results = [
        check("jazz", "tap", "ballet", name="first"),
        check("jazz", "ballet", "tap", name="second"),
    ]
    rows = list(csv.reader(format_violations_csv(results, DATA).splitlines()))
    assert rows[0] == [
        "schedule", "performer", "performance_a", "position_a",
        "performance_b", "position_b", "slots_between", "required",
    ]
    assert rows[1:] == [["first", "Sam Lee", "Jazz (Open)", "1", "Tap (Foundations)", "2", "0", "1"]]


def test_violations_csv_stays_one_row_per_performer_even_when_the_text_groups_them():
    rows = list(csv.reader(format_violations_csv([check("jazz", "tap", "ballet", data=CROWD)], CROWD).splitlines()))
    assert len(rows) == 1 + 3
    assert {row[1] for row in rows[1:]} == {"Amy", "Bo", "Cy"}


def test_violations_csv_for_a_valid_schedule_is_just_the_header():
    text = format_violations_csv([check("jazz", "ballet", "tap")], DATA)
    assert len(text.splitlines()) == 1
