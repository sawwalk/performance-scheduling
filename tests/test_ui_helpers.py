"""Tests for the small shared helpers the page needs (task U1, docs/ui-design.md section 5).

* io.decode_text, io.performer_file_columns, io.schedule_rows
* selection.next_pick
* report.format_found, report.no_schedules_heading, report.overview_rows

The helpers were pulled out of code the command line already used, so several tests check
that the old function and the new helper cannot disagree (format_schedules and
schedule_rows, format_overview and overview_rows, and so on). The wording tests are exact
on purpose: the command line and the page depend on it.
"""

import csv
import re
from io import StringIO
from pathlib import Path

import pytest

from performance_scheduling.io import (
    decode_text,
    format_schedules,
    load_performers,
    parse_performers,
    parse_schedules,
    performer_file_columns,
    read_text,
    schedule_rows,
)
from performance_scheduling.models import (
    BREAK,
    FinderResult,
    FinderStatus,
    InputError,
    Issue,
    Schedule,
    ScheduleCheck,
    Severity,
    Violation,
)
from performance_scheduling.report import (
    format_found,
    format_no_schedules,
    format_overview,
    no_schedules_heading,
    overview_rows,
)
from performance_scheduling.selection import (
    Selection,
    apply_selection,
    next_pick,
    parse_selection,
    schedules_to_request,
    selection_from_numbers,
)

EXAMPLES = Path(__file__).resolve().parent.parent / "data" / "examples"


# ---------------------------------------------------------------- io.decode_text


def test_decode_text_returns_plain_utf_8_text_unchanged():
    assert decode_text(b"name,style\nAna,Jazz\n", "show.csv") == "name,style\nAna,Jazz\n"


def test_decode_text_keeps_accents_and_non_latin_letters():
    text = "Zoë,Café Dance\n田中,Taiko\n"
    assert decode_text(text.encode("utf-8"), "show.csv") == text


def test_decode_text_drops_the_byte_order_mark_excel_adds():
    assert decode_text(b"\xef\xbb\xbfname,style\n", "show.csv") == "name,style\n"


def test_decode_text_only_drops_a_mark_at_the_very_start():
    # A mark in the middle of a file is real content, not Excel's marker.
    assert decode_text("a\ufeffb".encode("utf-8"), "show.csv") == "a\ufeffb"


def test_decode_text_leaves_line_endings_exactly_as_they_are():
    raw = b"a,b\r\nc,d\ne,f\r"
    assert decode_text(raw, "show.csv") == "a,b\r\nc,d\ne,f\r"


def test_decode_text_of_no_bytes_is_empty_text():
    assert decode_text(b"", "empty.csv") == ""


def test_decode_text_refuses_bytes_that_are_not_utf_8_and_names_the_file():
    raw = "Zoë,Jazz\n".encode("cp1252")  # what an old Excel "CSV" gives for an accent
    with pytest.raises(InputError) as problem:
        decode_text(raw, "dancers.csv")
    (issue,) = problem.value.issues
    assert issue.severity is Severity.ERROR
    assert issue.message == (
        'dancers.csv could not be read as UTF-8 text. In Excel, use "Save As" and choose "CSV UTF-8".'
    )


def test_read_text_and_decode_text_give_the_same_text_and_the_same_message(tmp_path):
    good = tmp_path / "good.csv"
    good.write_bytes(b"\xef\xbb\xbfa,b\r\nc,d\n")
    assert read_text(good) == decode_text(good.read_bytes(), "good.csv") == "a,b\r\nc,d\n"

    bad = tmp_path / "bad.csv"
    bad.write_bytes("Zoë\n".encode("cp1252"))
    with pytest.raises(InputError) as from_file:
        read_text(bad)
    with pytest.raises(InputError) as from_bytes:
        decode_text(bad.read_bytes(), "bad.csv")
    assert from_file.value.issues == from_bytes.value.issues


# ---------------------------------------------------------------- io.performer_file_columns


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("name,style\nAna,Jazz\n", ["name", "style"]),
        ("name;style\nAna;Jazz\n", ["name", "style"]),
        ("name\tstyle\nAna\tJazz\n", ["name", "style"]),
        ("name,style\r\nAna,Jazz\r\n", ["name", "style"]),
        ("name,style,notes\nAna,Jazz,x\n", ["name", "style", "notes"]),
        ("name,style\n", ["name", "style"]),  # a header and nothing else
        ("name,style", ["name", "style"]),  # no final newline
    ],
)
def test_performer_file_columns_lists_the_header_names_in_order(text, expected):
    assert performer_file_columns(text) == expected


def test_performer_file_columns_tidies_names_the_way_the_loader_does():
    assert performer_file_columns("  Full   name ,  Dance  style\nAna,Jazz\n") == [
        "Full name",
        "Dance style",
    ]


def test_performer_file_columns_drops_the_empty_columns_excel_adds_at_the_end():
    assert performer_file_columns("name,style,,\nAna,Jazz,,\n") == ["name", "style"]


def test_performer_file_columns_keeps_an_empty_column_in_the_middle():
    # Same view of the header as the loader: only trailing empty columns are dropped.
    assert performer_file_columns("name,,style\nAna,x,Jazz\n") == ["name", "", "style"]


def test_performer_file_columns_skips_blank_lines_before_the_header():
    assert performer_file_columns("\n   \n\nname,style\nAna,Jazz\n") == ["name", "style"]


def test_performer_file_columns_understands_a_quoted_name_holding_the_separator():
    assert performer_file_columns('"Last, First",style\nAna,Jazz\n') == ["Last, First", "style"]


@pytest.mark.parametrize("text", ["", "\n", "   \n  \n", ",,,\n"])
def test_performer_file_columns_gives_an_empty_list_when_there_is_no_header(text):
    assert performer_file_columns(text) == []


def test_performer_file_columns_does_not_raise_on_text_the_csv_reader_rejects():
    huge_field = "x" * 200_000  # longer than the csv module's default field limit
    assert performer_file_columns(f"{huge_field},b\n") == []


@pytest.mark.parametrize(
    "text",
    [
        "name,style\nAna,Jazz\nBen,Tap\n",
        "name;style\nAna;Jazz\nBen;Tap\n",
        "name\tstyle\nAna\tJazz\nBen\tTap\n",
        "\n\nname,style,,\nAna,Jazz,,\nBen,Tap,,\n",
        "  Full   name ,  Dance  style\nAna,Jazz\nBen,Tap\n",
        '"Last, First",style\nAna,Jazz\nBen,Tap\n',
    ],
)
def test_every_name_offered_is_accepted_by_the_loader(text):
    first, second = performer_file_columns(text)[:2]
    load = parse_performers(text, first, second)  # raises InputError if a name is not found
    assert load.rows_used == 2


def test_the_columns_offered_for_each_example_file_load_the_same_as_the_default(tmp_path):
    performer_files = [
        path
        for path in sorted(EXAMPLES.glob("*.csv"))
        if "schedule" not in path.name and "pins" not in path.name
    ]
    assert len(performer_files) >= 7  # the guard: the loop below must really run
    for path in performer_files:
        names = performer_file_columns(read_text(path))
        assert len(names) == 2, path.name
        assert parse_performers(read_text(path), *names) == parse_performers(read_text(path)), path.name
        assert load_performers(path, *names) == load_performers(path), path.name


def test_the_example_file_that_starts_with_a_byte_order_mark_gives_clean_names():
    assert performer_file_columns(read_text(EXAMPLES / "messy_input.csv")) == ["id", "performance"]


def test_an_uploaded_file_goes_from_bytes_to_column_names():
    raw = b"\xef\xbb\xbfperformer;dance\r\nAna;Jazz\r\n"
    assert performer_file_columns(decode_text(raw, "upload.csv")) == ["performer", "dance"]


# ---------------------------------------------------------------- io.schedule_rows


def make_schedule(name, *slots, display=None):
    return Schedule(name=name, slots=tuple(slots), display_names=display or {})


def test_schedule_rows_starts_with_the_heading_row_then_one_row_per_slot():
    rows = schedule_rows([make_schedule("A", "jazz", BREAK, "tap")], {})
    assert rows == [
        ["position", "A"],
        ["1", "jazz"],
        ["2", BREAK],
        ["3", "tap"],
    ]


def test_schedule_rows_puts_several_schedules_side_by_side():
    rows = schedule_rows(
        [make_schedule("A", "jazz", "tap"), make_schedule("B", "tap", "jazz")], {}
    )
    assert rows == [["position", "A", "B"], ["1", "jazz", "tap"], ["2", "tap", "jazz"]]


def test_schedule_rows_are_all_text_so_a_table_can_show_them_as_they_are():
    rows = schedule_rows([make_schedule("A", "jazz", BREAK)], {})
    assert all(isinstance(cell, str) for row in rows for cell in row)


def test_schedule_rows_prefer_the_performer_file_spelling():
    schedule = make_schedule("A", "jazz (open)", display={"jazz (open)": "jazz (OPEN)"})
    rows = schedule_rows([schedule], {"jazz (open)": "Jazz (Open)"})
    assert rows[1] == ["1", "Jazz (Open)"]


def test_schedule_rows_fall_back_to_the_spelling_the_schedule_came_from_then_the_key():
    schedule = make_schedule("A", "jazz (open)", "tap", display={"jazz (open)": "JAZZ (open)"})
    rows = schedule_rows([schedule], {})
    assert [row[1] for row in rows[1:]] == ["JAZZ (open)", "tap"]


def test_schedule_rows_always_write_a_break_as_break():
    rows = schedule_rows([make_schedule("A", BREAK)], {BREAK: "Interval"})
    assert rows[1] == ["1", BREAK]


def test_schedule_rows_keep_a_name_holding_a_comma_in_one_cell():
    rows = schedule_rows([make_schedule("A", "hip, hop")], {"hip, hop": "Hip, Hop"})
    assert rows[1] == ["1", "Hip, Hop"]


def test_schedule_rows_refuse_no_schedules():
    with pytest.raises(ValueError, match="no schedules"):
        schedule_rows([], {})


def test_schedule_rows_refuse_schedules_of_different_lengths():
    with pytest.raises(ValueError, match="same number of slots"):
        schedule_rows([make_schedule("A", "x", "y"), make_schedule("B", "x")], {})


@pytest.mark.parametrize("bad_name", ["", "   ", "position", " Position "])
def test_schedule_rows_refuse_a_name_that_cannot_head_a_column(bad_name):
    with pytest.raises(ValueError, match="cannot be used as a column heading"):
        schedule_rows([make_schedule(bad_name, "x")], {})


def test_schedule_rows_refuse_the_same_name_twice_ignoring_case_and_spaces():
    with pytest.raises(ValueError, match="cannot be used as a column heading"):
        schedule_rows([make_schedule("Plan A", "x"), make_schedule("plan  a", "x")], {})


def test_format_schedules_is_exactly_the_rows_written_as_csv():
    schedules = [make_schedule("A", "hip, hop", BREAK, 'say "hi"'), make_schedule("B", BREAK, 'say "hi"', "hip, hop")]
    names = {"hip, hop": "Hip, Hop", 'say "hi"': 'Say "Hi"'}
    text = format_schedules(schedules, names)
    assert list(csv.reader(StringIO(text))) == schedule_rows(schedules, names)


def test_format_schedules_output_is_unchanged_for_a_known_case():
    schedules = [make_schedule("A", "hip, hop", BREAK), make_schedule("B", BREAK, "hip, hop")]
    assert format_schedules(schedules, {"hip, hop": "Hip, Hop"}) == (
        'position,A,B\n1,"Hip, Hop",BREAK\n2,BREAK,"Hip, Hop"\n'
    )


def test_what_the_page_shows_can_be_read_back_by_the_schedule_reader():
    schedules = [make_schedule("A", "jazz", BREAK, "tap"), make_schedule("B", "tap", BREAK, "jazz")]
    load = parse_schedules(format_schedules(schedules, {}))
    assert [schedule.slots for schedule in load.schedules] == [s.slots for s in schedules]


# ---------------------------------------------------------------- selection.next_pick


@pytest.mark.parametrize(
    ("typed", "limit", "last", "expected"),
    [
        ("1-5", 100, 5, "6-10"),  # the usual case: the same number again
        ("6-10", 100, 10, "11-15"),
        ("1", 100, 1, "2"),  # one schedule: a single number, not "2-2"
        ("7", 100, 7, "8"),
        ("1,4,9", 100, 9, "10-12"),  # three chosen, so three more
        ("1-3,7", 100, 7, "8-11"),  # four chosen, so four more
        ("2-3", 100, 3, "4-5"),
        ("all", 100, 100, "101-200"),  # "all" means a whole limit
        ("all", 3, 3, "4-6"),
        ("all", 1, 1, "2"),
    ],
)
def test_next_pick_asks_for_a_batch_as_big_as_the_last_one(typed, limit, last, expected):
    assert next_pick(parse_selection(typed), limit, last) == expected


def test_next_pick_treats_an_empty_choice_as_one_schedule():
    # The rule the command line always had: `count or 1`.
    assert next_pick(Selection(), 100, 4) == "5"


@pytest.mark.parametrize("typed", ["1", "1-5", "1,4,9", "1-3,7,20-22", "3-4"])
def test_next_pick_can_be_read_back_and_starts_right_after_the_last_number(typed):
    selection = parse_selection(typed)
    last = selection.highest
    following = parse_selection(next_pick(selection, 100, last))
    assert following.count == selection.count
    assert following.numbers()[0] == last + 1


def test_next_pick_follows_on_from_a_real_finder_result():
    # 10 schedules exist; the first batch of 5 is picked, then the next 5, then nothing more.
    schedules = tuple(make_schedule(f"S{n}", "x") for n in range(1, 12))
    first = parse_selection("1-5")
    result = FinderResult(FinderStatus.FOUND, schedules[: schedules_to_request(first, 100)], ())
    picked = apply_selection(result, first, 100)
    assert picked.more_exist is True
    second = parse_selection(next_pick(first, 100, picked.numbers.highest))
    assert str(second) == "6-10"
    assert second.numbers() == selection_from_numbers(range(6, 11)).numbers()


# ---------------------------------------------------------------- report.format_found


@pytest.mark.parametrize(
    ("count", "numbers", "expected"),
    [
        (5, "1-5", "Found 5 schedules (numbers 1-5)."),
        (1, "1", "Found 1 schedule (number 1)."),
        (3, "1,4,9", "Found 3 schedules (numbers 1,4,9)."),
        (2, "1-2", "Found 2 schedules (numbers 1-2)."),
        (100, "1-100", "Found 100 schedules (numbers 1-100)."),
    ],
)
def test_format_found_says_how_many_and_which_numbers(count, numbers, expected):
    assert format_found(count, numbers) == expected


@pytest.mark.parametrize("count", [0, -1])
def test_format_found_refuses_a_count_below_one(count):
    with pytest.raises(ValueError, match="no schedules"):
        format_found(count, "")


# ---------------------------------------------------------------- report.no_schedules_heading


def test_the_heading_says_none_exist_when_the_search_finished():
    assert no_schedules_heading(FinderStatus.EXHAUSTED) == "No schedule exists."


def test_the_heading_says_the_time_ran_out_when_the_search_was_stopped():
    assert no_schedules_heading(FinderStatus.STOPPED) == (
        "No schedule was found before the time limit."
    )


@pytest.mark.parametrize("status", [FinderStatus.EXHAUSTED, FinderStatus.STOPPED])
def test_format_no_schedules_is_the_heading_then_one_indented_line_per_reason(status):
    reasons = (Issue(Severity.ERROR, "First reason."), Issue(Severity.ERROR, "Second reason."))
    assert format_no_schedules(status, reasons).split("\n") == [
        no_schedules_heading(status),
        "  - First reason.",
        "  - Second reason.",
    ]


def test_format_no_schedules_with_no_reasons_is_just_the_heading():
    assert format_no_schedules(FinderStatus.STOPPED, ()) == no_schedules_heading(
        FinderStatus.STOPPED
    )


# ---------------------------------------------------------------- report.overview_rows


def make_violation(a, pos_a, b, pos_b, who="Ana"):
    return Violation(who, a, pos_a, b, pos_b, slots_between=0, required=1)


def make_check(name, *, problems=(), violations=(), smallest_gap=None, slots=5, breaks=1):
    return ScheduleCheck(
        schedule_name=name,
        gap_required=1,
        num_slots=slots,
        num_breaks=breaks,
        problems=tuple(problems),
        violations=tuple(violations),
        smallest_gap=smallest_gap,
    )


HEADINGS = ("Schedule", "Result", "Slots", "Breaks", "Problems", "Tightest gap")


def test_overview_rows_start_with_the_headings():
    assert overview_rows([])[0] == HEADINGS
    assert overview_rows([]) == [HEADINGS]


def test_overview_rows_describe_a_valid_schedule():
    rows = overview_rows([make_check("Plan A", smallest_gap=2, slots=6, breaks=2)])
    assert rows[1] == ("Plan A", "VALID", "6", "2", "0", "2")


def test_overview_rows_describe_an_invalid_schedule_and_count_pairs_not_violations():
    # Two performers clash on the same pair, and one more clash is a second pair: 3 violations
    # but 2 pairs, and the "Problems" column counts pairs.
    violations = [
        make_violation("jazz", 1, "tap", 2, who="Ana"),
        make_violation("jazz", 1, "tap", 2, who="Ben"),
        make_violation("tap", 2, "ballet", 3, who="Ana"),
    ]
    rows = overview_rows([make_check("Plan B", violations=violations, smallest_gap=0)])
    assert rows[1] == ("Plan B", "INVALID", "5", "1", "2", "0")


def test_overview_rows_count_structural_problems_instead_when_there_are_some():
    problems = [Issue(Severity.ERROR, "One."), Issue(Severity.ERROR, "Two."), Issue(Severity.ERROR, "Three.")]
    violations = [make_violation("jazz", 1, "tap", 2)]
    rows = overview_rows([make_check("Plan C", problems=problems, violations=violations)])
    assert rows[1][4] == "3"
    assert rows[1][1] == "INVALID"


def test_overview_rows_show_a_dash_when_there_is_no_tightest_gap():
    rows = overview_rows([make_check("Plan D", smallest_gap=None)])
    assert rows[1][5] == "-"


def test_overview_rows_show_a_tightest_gap_of_zero_as_zero_not_a_dash():
    rows = overview_rows([make_check("Plan E", smallest_gap=0)])
    assert rows[1][5] == "0"


def test_overview_rows_keep_the_order_of_the_schedules_and_are_all_text():
    checks = [make_check("C"), make_check("A"), make_check("B")]
    rows = overview_rows(checks)
    assert [row[0] for row in rows[1:]] == ["C", "A", "B"]
    assert all(isinstance(cell, str) for row in rows for cell in row)


def test_format_overview_is_these_rows_lined_up_as_text():
    checks = [
        make_check("Plan A", smallest_gap=2),
        make_check("Plan with a longer name", violations=[make_violation("jazz", 1, "tap", 2)], smallest_gap=0),
    ]
    rows = overview_rows(checks)
    lines = format_overview(checks).split("\n")
    assert len(lines) == len(rows)
    for line, row in zip(lines, rows, strict=True):
        assert tuple(re.split(r"\s{2,}", line)) == row
        assert line == line.rstrip()


def test_format_overview_of_no_checks_is_just_the_headings():
    assert re.split(r"\s{2,}", format_overview([])) == list(HEADINGS)
