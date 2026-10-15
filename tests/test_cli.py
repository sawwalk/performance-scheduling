"""Tests for cli.py: the schedule-checker command, run the way a user would run it."""

import csv
from pathlib import Path

import pytest

from performance_scheduling.cli import (
    EXIT_INPUT_PROBLEM,
    EXIT_INVALID,
    EXIT_VALID,
    checker_main,
)

EXAMPLES = Path(__file__).resolve().parent.parent / "data" / "examples"
PERFORMERS = str(EXAMPLES / "tiny_feasible.csv")


def run(capsys, *args: str):
    code = checker_main(list(args))
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def schedule_file(name: str) -> str:
    return str(EXAMPLES / name)


def test_valid_schedule_exits_zero(capsys):
    code, out, err = run(capsys, "--performers", PERFORMERS, "--schedule", schedule_file("tiny_feasible_schedule_valid.csv"))
    assert code == EXIT_VALID == 0
    assert "schedule_1: VALID" in out
    assert err == ""


def test_header_lines_describe_the_run(capsys):
    _, out, _ = run(capsys, "--performers", PERFORMERS, "--schedule", schedule_file("tiny_feasible_schedule_valid.csv"))
    assert "Performer file: tiny_feasible.csv (12 performers, 6 performances)" in out
    assert "Schedule file:  tiny_feasible_schedule_valid.csv (1 schedule)" in out
    assert "Gap checked:    1 (at least 1 slot between a performer's performances)" in out


def test_invalid_schedule_exits_one_and_explains_why(capsys):
    code, out, _ = run(capsys, "--performers", PERFORMERS, "--schedule", schedule_file("tiny_feasible_schedule_invalid.csv"))
    assert code == EXIT_INVALID == 1
    assert "schedule_1: INVALID" in out
    assert "Bollywood (Open) (slot 3) and Tap (Foundations) (slot 4): 0 slots between, at least 1 needed" in out
    assert "===== CONFLICTING PERFORMANCE PAIRS (1) =====" in out
    assert "===== WHO IS AFFECTED (1 performer) =====" in out
    assert "        - Person 0006" in out
    assert out.index("CONFLICTING PERFORMANCE PAIRS") < out.index("WHO IS AFFECTED")


def test_gap_option_changes_the_result(capsys):
    valid = schedule_file("tiny_feasible_schedule_valid.csv")
    assert run(capsys, "--performers", PERFORMERS, "--schedule", valid, "--gap", "1")[0] == EXIT_VALID
    code, out, _ = run(capsys, "--performers", PERFORMERS, "--schedule", valid, "--gap", "2")
    assert code == EXIT_INVALID
    assert "Gap checked:    2 (at least 2 slots" in out


def test_gap_zero_checks_only_the_structure(capsys):
    code, out, _ = run(capsys, "--performers", PERFORMERS, "--schedule", schedule_file("tiny_feasible_schedule_invalid.csv"), "--gap", "0")
    assert code == EXIT_VALID
    assert "no spacing required" in out


def test_broken_schedule_reports_the_structural_problems(capsys):
    code, out, _ = run(capsys, "--performers", PERFORMERS, "--schedule", schedule_file("tiny_feasible_schedule_broken.csv"))
    assert code == EXIT_INVALID
    assert "===== PROBLEMS WITH THE SCHEDULE ITSELF (4) =====" in out
    assert "Spacing was not checked." in out
    assert '"Salsa (Open)" is in the schedule (position 1)' in out


def test_several_schedules_get_an_overview_and_a_total(capsys):
    code, out, _ = run(capsys, "--performers", PERFORMERS, "--schedule", schedule_file("tiny_feasible_schedules_all8.csv"))
    assert code == EXIT_VALID
    assert "Tightest gap" in out
    assert "All 8 schedules are valid." in out


def test_schedule_column_option_checks_just_that_column(capsys):
    code, out, _ = run(
        capsys, "--performers", PERFORMERS,
        "--schedule", schedule_file("tiny_feasible_schedules_all8.csv"),
        "--schedule-column", " SCHEDULE_3 ",
    )
    assert code == EXIT_VALID
    assert "schedule_3: VALID" in out and "schedule_4" not in out
    assert "(1 schedule)" in out


def test_unknown_schedule_column_lists_the_columns_and_exits_two(capsys):
    code, out, err = run(
        capsys, "--performers", PERFORMERS,
        "--schedule", schedule_file("tiny_feasible_schedules_all8.csv"),
        "--schedule-column", "nope",
    )
    assert code == EXIT_INPUT_PROBLEM == 2
    assert 'No schedule column called "nope"' in err and '"schedule_1"' in err
    assert out == ""


def test_many_schedules_show_full_detail_only_for_invalid_ones(capsys, tmp_path):
    valid_order = ["Bollywood (Open)", "Contemporary (Open)", "Hip Hop (Foundations)",
                   "Tap (Foundations)", "Jazz (Open)", "Kpop Girls (Intermediate)"]
    invalid_order = [valid_order[2], valid_order[1], valid_order[0], *valid_order[3:]]  # Bollywood next to Tap
    columns = [valid_order] * 11 + [invalid_order]
    lines = ["position," + ",".join(f"s{n}" for n in range(12))]
    lines += [f"{row + 1}," + ",".join(column[row] for column in columns) for row in range(6)]
    path = tmp_path / "twelve.csv"
    path.write_text("\n".join(lines) + "\n")

    code, out, _ = run(capsys, "--performers", PERFORMERS, "--schedule", str(path))

    assert code == EXIT_INVALID
    assert "11 schedules" not in out and "(12 schedules)" in out
    assert any(line.split()[:2] == ["s0", "VALID"] for line in out.splitlines())  # in the table
    assert "s0: VALID" not in out                         # but get no full write-up
    assert "s11: INVALID" in out                          # the invalid one does
    assert "Valid schedules are listed in the table only." in out
    assert "1 of 12 schedules are invalid." in out


def test_missing_files_exit_two_and_both_problems_are_shown(capsys, tmp_path):
    code, out, err = run(capsys, "--performers", str(tmp_path / "a.csv"), "--schedule", str(tmp_path / "b.csv"))
    assert code == EXIT_INPUT_PROBLEM
    assert "a.csv" in err and "b.csv" in err
    assert out == ""


def test_unusable_schedule_file_exits_two(capsys, tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("position,s\n1,Jazz\n1,Tap\n")
    code, _, err = run(capsys, "--performers", PERFORMERS, "--schedule", str(bad))
    assert code == EXIT_INPUT_PROBLEM
    assert "position 1 is repeated" in err


def test_performer_file_warnings_are_shown_before_the_results(capsys):
    code, out, _ = run(
        capsys, "--performers", str(EXAMPLES / "messy_input.csv"),
        "--schedule", schedule_file("tiny_feasible_schedule_valid.csv"),
    )
    assert code == EXIT_INVALID  # the schedule is for a different show
    assert "Please review these 5 warning(s) about the performer file:" in out
    assert '"John Smith" and "Jon Smith" look very similar' in out
    assert out.index("Please review") < out.index("INVALID")


def test_schedule_file_warnings_are_shown(capsys, tmp_path):
    path = tmp_path / "gaps.csv"
    path.write_text("position,s\n1,Bollywood (Open)\n2,\n3,Jazz (Open)\n")
    _, out, _ = run(capsys, "--performers", PERFORMERS, "--schedule", str(path))
    assert "warning(s) about the schedule file" in out
    assert 'empty slot in "s" treated as a break' in out


def test_report_csv_is_written(capsys, tmp_path):
    report = tmp_path / "report.csv"
    code, out, _ = run(
        capsys, "--performers", PERFORMERS,
        "--schedule", schedule_file("tiny_feasible_schedule_invalid.csv"),
        "--report-csv", str(report),
    )
    assert code == EXIT_INVALID
    assert "Violations written to" in out and "(1 row)" in out
    rows = list(csv.reader(report.read_text(encoding="utf-8-sig").splitlines()))
    assert rows[0][:2] == ["schedule", "performer"]
    assert rows[1] == ["schedule_1", "Person 0006", "Bollywood (Open)", "3", "Tap (Foundations)", "4", "0", "1"]


def test_report_csv_that_cannot_be_written_exits_two(capsys, tmp_path):
    code, _, err = run(
        capsys, "--performers", PERFORMERS,
        "--schedule", schedule_file("tiny_feasible_schedule_valid.csv"),
        "--report-csv", str(tmp_path / "no_such_folder" / "r.csv"),
    )
    assert code == EXIT_INPUT_PROBLEM
    assert "Could not write" in err


def test_named_columns_in_the_performer_file(capsys, tmp_path):
    performers = tmp_path / "p.csv"
    performers.write_text("email,name,style\nx@y.com,Sam,Jazz\nx@y.com,Sam,Tap\n")
    schedule = tmp_path / "s.csv"
    schedule.write_text("position,s\n1,Jazz\n2,Tap\n")
    code, out, _ = run(
        capsys, "--performers", str(performers), "--schedule", str(schedule),
        "--id-column", "name", "--performance-column", "style",
    )
    assert code == EXIT_INVALID
    assert "Jazz (slot 1) and Tap (slot 2): 0 slots between" in out
    assert "        - Sam" in out


@pytest.mark.parametrize("bad_gap", ["-1", "abc", "1.5"])
def test_a_bad_gap_is_refused_by_the_command(capsys, bad_gap):
    with pytest.raises(SystemExit) as caught:
        checker_main(["--performers", PERFORMERS, "--schedule", PERFORMERS, "--gap", bad_gap])
    assert caught.value.code == 2
    assert "gap" in capsys.readouterr().err


def test_missing_required_options_are_refused(capsys):
    with pytest.raises(SystemExit) as caught:
        checker_main([])
    assert caught.value.code == 2
