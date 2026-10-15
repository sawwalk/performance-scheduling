"""Tests for the performer loader in io.py."""

from pathlib import Path

import pytest

from performance_scheduling.io import (
    clean_text,
    load_performers,
    load_schedules,
    make_key,
    parse_performers,
    parse_schedules,
    write_text,
)
from performance_scheduling.models import BREAK, InputError, Severity

EXAMPLES = Path(__file__).resolve().parent.parent / "data" / "examples"


def warning_texts(load):
    return [str(issue) for issue in load.warnings]


def error_texts(error: InputError):
    return [str(issue) for issue in error.issues]


# ---------------------------------------------------------------- text cleaning


def test_make_key_ignores_case_and_extra_spaces():
    assert make_key("  Bollywood   (Open) ") == "bollywood (open)"
    assert make_key("bollywood (open)") == make_key("BOLLYWOOD (OPEN)")


def test_clean_text_keeps_case_but_fixes_spaces():
    assert clean_text("  Hip  Hop (Foundations) ") == "Hip Hop (Foundations)"


def test_non_breaking_space_counts_as_a_space():
    assert make_key("Hip\u00a0Hop") == "hip hop"


def test_accented_letters_typed_two_ways_match():
    assert make_key("Jos\u00e9") == make_key("Jose\u0301")


# ---------------------------------------------------------------- basic parsing


def test_basic_file_is_cleaned_and_organised():
    text = "full name,performance\nname1,Bollywood\nname2,Jazz\nname2,Hip Hop\nname3,Bollywood\n"
    load = parse_performers(text)
    data = load.data
    assert load.rows_read == 4 and load.rows_used == 4
    assert load.warnings == ()
    assert data.performances_by_performer["name2"] == frozenset({"jazz", "hip hop"})
    assert data.performance_keys == ("bollywood", "hip hop", "jazz")


def test_first_spelling_is_kept_for_display():
    load = parse_performers("id,perf\n Sam ,Bollywood (Open)\nsam,bollywood (open) \n")
    assert load.data.performer_names == {"sam": "Sam"}
    assert load.data.performance_names == {"bollywood (open)": "Bollywood (Open)"}


def test_duplicate_rows_are_merged_with_a_warning():
    load = parse_performers("id,perf\nSam,Jazz\nSam ,jazz\n")
    assert load.rows_read == 2 and load.rows_used == 1
    assert len(load.warnings) == 1
    assert "row 3" in str(load.warnings[0]) and "duplicate" in str(load.warnings[0])


def test_rows_with_a_missing_value_are_dropped_with_a_warning():
    load = parse_performers("id,perf\nSam,Jazz\n,Tap\nKim,\n")
    assert load.rows_used == 1
    assert warning_texts(load) == [
        "WARNING: row 3: missing performer; row dropped",
        "WARNING: row 4: missing performance; row dropped",
    ]


def test_completely_blank_rows_are_skipped_quietly():
    load = parse_performers("id,perf\nSam,Jazz\n\n,\nKim,Tap\n\n")
    assert load.rows_read == 2
    assert load.warnings == ()


def test_a_performance_called_break_is_an_error():
    with pytest.raises(InputError) as caught:
        parse_performers("id,perf\nSam,Jazz\nKim,  break \n")
    assert "row 3" in error_texts(caught.value)[0]
    assert "reserved" in error_texts(caught.value)[0]


def test_every_error_is_reported_together():
    with pytest.raises(InputError) as caught:
        parse_performers("id,perf\nSam,BREAK\nKim,Break\n")
    assert len(caught.value.issues) == 2


def test_file_with_no_usable_rows_is_an_error():
    with pytest.raises(InputError, match="No usable rows"):
        parse_performers("id,perf\n,\n,Tap\n")


def test_empty_file_is_an_error():
    with pytest.raises(InputError, match="empty"):
        parse_performers("\n\n")


# ---------------------------------------------------------------- columns and separators


def test_two_columns_are_used_whatever_they_are_called():
    load = parse_performers("anything,whatever\nSam,Jazz\n")
    assert load.rows_used == 1


def test_trailing_empty_columns_from_excel_are_ignored():
    load = parse_performers("id,perf,,\nSam,Jazz,,\n")
    assert load.rows_used == 1


def test_three_columns_without_names_is_an_error():
    with pytest.raises(InputError, match="exactly two columns"):
        parse_performers("id,perf,email\nSam,Jazz,s@example.com\n")


def test_named_columns_are_found_ignoring_case_and_spaces():
    text = "Email,  Full Name ,Style\ns@example.com,Sam,Jazz\n"
    load = parse_performers(text, id_column="full name", performance_column="STYLE")
    assert load.data.performer_names == {"sam": "Sam"}
    assert warning_texts(load) == ['WARNING: Ignoring other column(s): "Email".']


def test_missing_named_column_is_an_error_that_lists_the_columns():
    with pytest.raises(InputError) as caught:
        parse_performers("id,perf,email\nSam,Jazz,x\n", id_column="name", performance_column="perf")
    assert '"name" not found' in error_texts(caught.value)[0]
    assert '"email"' in error_texts(caught.value)[0]


def test_giving_only_one_column_name_is_an_error():
    with pytest.raises(InputError, match="both"):
        parse_performers("id,perf\nSam,Jazz\n", id_column="id")


@pytest.mark.parametrize("separator", [";", "\t"])
def test_semicolon_and_tab_separated_files_are_understood(separator):
    text = separator.join(["full name", "style"]) + "\n" + separator.join(["Sam", "Jazz"]) + "\n"
    assert parse_performers(text).data.performance_keys == ("jazz",)


# ---------------------------------------------------------------- near-duplicate warnings


def test_similar_ids_are_flagged():
    load = parse_performers("id,perf\nJon Smith,Jazz\nJohn Smith,Tap\n")
    assert len(load.warnings) == 1
    assert "John Smith" in str(load.warnings[0]) and "Jon Smith" in str(load.warnings[0])


def test_ids_that_differ_only_in_digits_are_not_flagged():
    rows = "".join(f"Person {n:04d},Jazz\n" for n in range(1, 30))
    assert parse_performers("id,perf\n" + rows).warnings == ()


def test_different_performances_with_similar_names_are_not_flagged():
    text = "id,perf\nA,Kpop Boys (Intermediate)\nB,Kpop Girls (Intermediate)\n"
    assert parse_performers(text).warnings == ()


def test_similar_performance_names_are_flagged():
    load = parse_performers("id,perf\nA,Tap (Foundations)\nB,Tap (Foundation)\n")
    assert len(load.warnings) == 1
    assert "Performance names" in str(load.warnings[0])


# ---------------------------------------------------------------- reading real files


def test_load_performers_accepts_a_byte_order_mark(tmp_path):
    path = tmp_path / "bom.csv"
    path.write_bytes(b"\xef\xbb\xbfid,perf\nSam,Jazz\n")
    assert load_performers(path).data.performer_names == {"sam": "Sam"}


def test_missing_file_is_a_clear_error(tmp_path):
    with pytest.raises(InputError, match="File not found"):
        load_performers(tmp_path / "nope.csv")


def test_file_not_saved_as_utf8_is_a_clear_error(tmp_path):
    path = tmp_path / "latin.csv"
    path.write_bytes("id,perf\nJos\u00e9,Jazz\n".encode("cp1252"))
    with pytest.raises(InputError, match="UTF-8"):
        load_performers(path)


# ---------------------------------------------------------------- the example datasets


def test_messy_input_example_matches_the_documented_result():
    load = load_performers(EXAMPLES / "messy_input.csv")
    assert load.rows_read == 13
    assert load.rows_used == 10
    assert len(load.data.performer_names) == 7
    assert len(load.data.performance_names) == 5
    assert len(load.warnings) == 5
    text = "\n".join(warning_texts(load))
    assert "duplicate" in text and "missing performer" in text and "missing performance" in text
    assert "Jon Smith" in text and "Tap (Foundation)" in text
    # "  person 0002" with "bollywood (open)" is the same person and performance as the clean rows
    assert load.data.performances_by_performer["person 0002"] == frozenset(
        {"bollywood (open)", "jazz (open)"}
    )
    assert all(issue.severity is Severity.WARNING for issue in load.warnings)


@pytest.mark.parametrize(
    ("filename", "performers", "performances", "rows"),
    [
        ("tiny_feasible.csv", 12, 6, 20),
        ("tiny_needs_breaks.csv", 5, 4, 9),
        ("tiny_no_conflicts.csv", 12, 6, 12),
        ("typical_20_performances.csv", 120, 20, 253),
        ("one_busy_performer.csv", 121, 20, 262),
        ("dense_overlap.csv", 40, 20, 145),
        ("impossible_dense.csv", 70, 20, 339),
    ],
)
def test_example_datasets_load_cleanly(filename, performers, performances, rows):
    load = load_performers(EXAMPLES / filename)
    assert len(load.data.performer_names) == performers
    assert len(load.data.performance_names) == performances
    assert load.rows_used == rows
    assert load.warnings == ()


# ================================================================ schedule reader


def test_single_schedule_is_read_in_order():
    load = parse_schedules("position,schedule_1\n1,Jazz\n2,BREAK\n3,Tap\n")
    (schedule,) = load.schedules
    assert schedule.name == "schedule_1"
    assert schedule.slots == ("jazz", BREAK, "tap")
    assert load.warnings == ()


def test_breaks_are_recognised_in_any_capitalisation():
    load = parse_schedules("position,s\n1,break\n2,Break\n3, BREAK \n")
    assert load.schedules[0].slots == (BREAK, BREAK, BREAK)


def test_several_schedules_side_by_side():
    text = "position,schedule_1,schedule_4\n1,Jazz,Tap\n2,Tap,Jazz\n"
    first, second = parse_schedules(text).schedules
    assert (first.name, first.slots) == ("schedule_1", ("jazz", "tap"))
    assert (second.name, second.slots) == ("schedule_4", ("tap", "jazz"))


def test_names_are_cleaned_like_the_performer_file_and_the_spelling_is_remembered():
    load = parse_schedules("position,s\n1,  Hip   Hop (Open) \n2,TAP\n")
    schedule = load.schedules[0]
    assert schedule.slots == ("hip hop (open)", "tap")
    assert schedule.display_names == {"hip hop (open)": "Hip Hop (Open)", "tap": "TAP"}


def test_rows_may_be_in_any_order_and_are_sorted_by_position():
    load = parse_schedules("position,s\n3,Tap\n1,Jazz\n2,Ballet\n")
    assert load.schedules[0].slots == ("jazz", "ballet", "tap")


def test_without_a_position_column_row_order_is_the_running_order():
    load = parse_schedules("first,second\nJazz,Tap\nTap,Jazz\n")
    assert [s.name for s in load.schedules] == ["first", "second"]
    assert load.schedules[0].slots == ("jazz", "tap")


def test_position_column_can_be_anywhere_and_is_found_ignoring_case():
    load = parse_schedules("s,POSITION\nJazz,2\nTap,1\n")
    assert load.schedules[0].slots == ("tap", "jazz")


def test_empty_cell_is_a_break_with_a_warning():
    load = parse_schedules("position,schedule_1\n1,Jazz\n2,\n")
    assert load.schedules[0].slots == ("jazz", BREAK)
    assert warning_texts(load) == ['WARNING: row 3: empty slot in "schedule_1" treated as a break']


def test_missing_cells_in_a_short_row_count_as_empty():
    load = parse_schedules("position,a,b\n1,Jazz,Tap\n2,Tap\n")
    assert load.schedules[1].slots == ("tap", BREAK)
    assert len(load.warnings) == 1


def test_extra_cells_beyond_the_header_are_flagged():
    load = parse_schedules("position,s\n1,Jazz,oops\n")
    assert load.schedules[0].slots == ("jazz",)
    assert "more cells" in warning_texts(load)[0]


def test_blank_rows_and_empty_trailing_columns_are_ignored():
    load = parse_schedules("position,s,,\n1,Jazz,,\n\n,,,\n2,Tap,,\n")
    assert load.schedules[0].slots == ("jazz", "tap")
    assert load.warnings == ()


def test_semicolon_separated_schedule_files_are_understood():
    assert parse_schedules("position;s\n1;Jazz\n").schedules[0].slots == ("jazz",)


def test_mistakes_in_the_contents_are_loaded_for_the_checker_to_report():
    # unknown name, a repeat, and BREAK mixed in: the reader does not judge any of it
    load = parse_schedules("position,s\n1,Salsa\n2,Jazz\n3,Jazz\n")
    assert load.schedules[0].slots == ("salsa", "jazz", "jazz")
    assert load.warnings == ()


@pytest.mark.parametrize(
    ("text", "fragment"),
    [
        ("", "empty"),
        ("position,s\n", "no schedule rows"),
        ("position\n1\n2\n", "no schedule columns"),
        ("position,s,s\n1,Jazz,Tap\n", "Give each schedule its own name"),
        ("position,position,s\n1,1,Jazz\n", "More than one column"),
        ("position,,s\n1,x,Jazz\n", "have no name"),
        ("position,s\n1,Jazz\n1,Tap\n", "position 1 is repeated"),
        ("position,s\nx,Jazz\n", 'position "x" is not a whole number'),
        ("position,s\n,Jazz\n", "position is missing"),
        ("position,s\n0,Jazz\n1,Tap\n", "numbered 1 to 2 with no gaps"),
        ("position,s\n1,Jazz\n3,Tap\n", "Missing: 2"),
    ],
)
def test_unusable_files_give_clear_errors(text, fragment):
    with pytest.raises(InputError) as caught:
        parse_schedules(text)
    assert fragment in "\n".join(error_texts(caught.value))


def test_position_errors_name_the_rows():
    with pytest.raises(InputError) as caught:
        parse_schedules("position,s\n1,Jazz\nx,Tap\n1,Ballet\n")
    texts = error_texts(caught.value)
    assert any("row 3" in text and "whole number" in text for text in texts)
    assert any("row 4" in text and "repeated" in text and "row 2" in text for text in texts)


def test_missing_schedule_file_is_a_clear_error(tmp_path):
    with pytest.raises(InputError, match="File not found"):
        load_schedules(tmp_path / "nope.csv")


# ---------------------------------------------------------------- the example schedule files


def test_valid_example_schedule_uses_names_from_the_performer_file():
    performers = load_performers(EXAMPLES / "tiny_feasible.csv").data
    (schedule,) = load_schedules(EXAMPLES / "tiny_feasible_schedule_valid.csv").schedules
    assert schedule.num_slots == 6 and schedule.num_breaks == 0
    # every name in the schedule file matches a name in the performer file
    assert set(schedule.slots) == set(performers.performance_names)


def test_invalid_example_schedule_loads_fine():
    (schedule,) = load_schedules(EXAMPLES / "tiny_feasible_schedule_invalid.csv").schedules
    assert schedule.positions()["bollywood (open)"] == 3
    assert schedule.positions()["tap (foundations)"] == 4


def test_broken_example_schedule_loads_with_its_mistakes_intact():
    (schedule,) = load_schedules(EXAMPLES / "tiny_feasible_schedule_broken.csv").schedules
    assert schedule.slots[0] == "salsa (open)"
    assert schedule.display_names["salsa (open)"] == "Salsa (Open)"
    assert schedule.slots.count("hip hop (foundations)") == 2
    assert "bollywood (open)" not in schedule.slots


def test_all_eight_example_schedules_are_read_side_by_side():
    load = load_schedules(EXAMPLES / "tiny_feasible_schedules_all8.csv")
    assert [s.name for s in load.schedules] == [f"schedule_{n}" for n in range(1, 9)]
    assert all(s.num_slots == 6 for s in load.schedules)
    assert len({s.slots for s in load.schedules}) == 8  # eight different running orders


# ---------------------------------------------------------------- writing files


def test_write_text_round_trips_with_accents(tmp_path):
    path = tmp_path / "out.csv"
    write_text(path, "name\nJos\u00e9\n")
    assert path.read_bytes().startswith(b"\xef\xbb\xbf")  # byte-order mark, for Excel
    assert path.read_text(encoding="utf-8-sig") == "name\nJos\u00e9\n"


def test_write_text_to_a_missing_folder_is_a_clear_error(tmp_path):
    with pytest.raises(InputError, match="Could not write"):
        write_text(tmp_path / "missing" / "out.csv", "x")
