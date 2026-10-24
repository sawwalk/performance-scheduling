"""Tests for cli.py: the schedule-checker command, run the way a user would run it."""

import csv
import importlib.util
import tomllib
from pathlib import Path

import pytest

from performance_scheduling import cli
from performance_scheduling.cli import (
    EXIT_INPUT_PROBLEM,
    EXIT_INVALID,
    EXIT_NOTHING_WRITTEN,
    EXIT_VALID,
    EXIT_WRITTEN,
    _finder_parser,
    _next_batch_command,
    checker_main,
    finder_main,
)
from performance_scheduling.io import load_schedules
from performance_scheduling.solver import SolverNotInstalled

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


# ================================================================ schedule-finder

needs_ortools = pytest.mark.skipif(
    importlib.util.find_spec("ortools") is None, reason="OR-Tools is not installed"
)
PINS = str(EXAMPLES / "tiny_feasible_pins.csv")
ROOT = Path(__file__).resolve().parent.parent


def run_finder(capsys, *args: str):
    code = finder_main(list(args))
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def finder(capsys, tmp_path, *args: str, performers: str = PERFORMERS, out: str = "out"):
    return run_finder(capsys, "--performers", performers, "--out", str(tmp_path / out), *args)


def columns(path: Path) -> dict[str, tuple[str, ...]]:
    return {s.name: s.slots for s in load_schedules(path).schedules}


@needs_ortools
def test_the_default_run_writes_five_schedules_and_the_checker_accepts_them(capsys, tmp_path):
    code, out, err = finder(capsys, tmp_path)
    assert code == EXIT_WRITTEN == 0 and err == ""
    path = tmp_path / "out" / "schedules_1-5.csv"  # the folder did not exist: it is created
    assert f"Wrote 5 schedules (numbers 1-5) to {path}." in out
    assert "More schedules exist after number 5." in out
    assert "Schedules found with a gap of 1. To see whether everyone could have a longer rest" in out
    assert "run again with a gap of 2." in out
    # the finder's output can be handed straight to the checker
    code, checked, _ = run(capsys, "--performers", PERFORMERS, "--schedule", str(path))
    assert code == EXIT_VALID and "All 5 schedules are valid." in checked


@needs_ortools
def test_the_header_describes_the_run(capsys, tmp_path):
    _, out, _ = finder(capsys, tmp_path, "--breaks", "1")
    assert "Performer file:  tiny_feasible.csv (12 performers, 6 performances)" in out
    assert "Settings:        gap 1, 1 break (7 slots), the default order" in out
    assert "Search engine:   OR-Tools " in out


@needs_ortools
def test_the_next_batch_command_is_printed_and_fits_the_first_batch(capsys, tmp_path):
    _, out, _ = finder(capsys, tmp_path, "--breaks", "1")
    expected = (
        f"schedule-finder --performers {PERFORMERS} --gap 1 --breaks 1 --pick 6-10 "
        f"--out {tmp_path / 'out'}"
    )
    assert "To write the next 5 schedules, run:" in out
    assert f"  {expected}" in out


@needs_ortools
def test_batches_are_slices_of_one_numbered_list(capsys, tmp_path):
    finder(capsys, tmp_path, "--breaks", "1", "--pick", "1-8", out="whole")
    finder(capsys, tmp_path, "--breaks", "1", "--pick", "1-5", out="parts")
    finder(capsys, tmp_path, "--breaks", "1", "--pick", "6-8", out="parts")
    whole = columns(tmp_path / "whole" / "schedules_1-8.csv")
    parts = {
        **columns(tmp_path / "parts" / "schedules_1-5.csv"),
        **columns(tmp_path / "parts" / "schedules_6-8.csv"),
    }
    assert list(whole) == [f"schedule_{n}" for n in range(1, 9)]
    assert parts == whole


@needs_ortools
def test_an_unconnected_pick_keeps_the_list_numbers_in_the_file_and_name(capsys, tmp_path):
    finder(capsys, tmp_path, "--breaks", "1", "--pick", "1-9", out="whole")
    code, out, _ = finder(capsys, tmp_path, "--breaks", "1", "--pick", "9,1,4,4")
    path = tmp_path / "out" / "schedules_1_4_9.csv"
    assert code == EXIT_WRITTEN and "(numbers 1,4,9)" in out
    picked = columns(path)
    whole = columns(tmp_path / "whole" / "schedules_1-9.csv")
    assert list(picked) == ["schedule_1", "schedule_4", "schedule_9"]
    assert picked == {name: whole[name] for name in picked}
    assert "--pick 10-12" in out  # the same number of schedules, after the highest one picked


@needs_ortools
def test_all_writes_up_to_the_limit_and_says_so(capsys, tmp_path):
    code, out, _ = finder(capsys, tmp_path, "--breaks", "1", "--pick", "all", "--limit", "3")
    assert code == EXIT_WRITTEN
    assert len(columns(tmp_path / "out" / "schedules_all.csv")) == 3
    assert "More schedules exist after number 3." in out
    assert "--pick 4-6" in out and "--limit 3" in out
    assert "(Each run writes at most 3; change that with --limit.)" in out


@needs_ortools
def test_all_on_a_short_list_writes_everything_and_prints_no_next_batch(capsys, tmp_path):
    code, out, _ = finder(capsys, tmp_path, "--pick", "all")
    assert code == EXIT_WRITTEN
    assert len(columns(tmp_path / "out" / "schedules_all.csv")) == 8
    assert "There are 8 schedules in all." in out
    assert "To write the next" not in out and "More schedules exist" not in out


@needs_ortools
def test_numbers_beyond_the_end_are_listed_and_the_ones_that_exist_are_written(capsys, tmp_path):
    code, out, _ = finder(capsys, tmp_path, "--pick", "6-12")
    assert code == EXIT_WRITTEN
    assert list(columns(tmp_path / "out" / "schedules_6-12.csv")) == [
        "schedule_6", "schedule_7", "schedule_8",
    ]  # fmt: skip
    assert "Schedules 9-12 do not exist: there are only 8." in out
    assert "To write the next" not in out


@needs_ortools
def test_a_pick_entirely_beyond_the_end_writes_nothing(capsys, tmp_path):
    code, out, _ = finder(capsys, tmp_path, "--pick", "20-22")
    assert code == EXIT_NOTHING_WRITTEN == 1
    assert "Nothing was written." in out
    assert "Schedules 20-22 do not exist: there are only 8." in out
    assert not (tmp_path / "out").exists()


@needs_ortools
def test_a_seed_is_used_printed_named_in_the_file_and_repeatable(capsys, tmp_path):
    code, out, _ = finder(capsys, tmp_path, "--breaks", "1", "--seed", "42", out="a")
    assert code == EXIT_WRITTEN
    assert "gap 1, 1 break (7 slots), seed 42" in out
    assert "--seed 42" in out  # the next batch uses the same list
    again, _, _ = finder(capsys, tmp_path, "--breaks", "1", "--seed", "42", out="b")
    first = tmp_path / "a" / "schedules_seed42_1-5.csv"
    second = tmp_path / "b" / "schedules_seed42_1-5.csv"
    assert again == EXIT_WRITTEN and first.read_bytes() == second.read_bytes()
    finder(capsys, tmp_path, "--breaks", "1", "--seed", "7", out="c")
    assert (tmp_path / "c" / "schedules_seed7_1-5.csv").read_bytes() != first.read_bytes()


@needs_ortools
def test_an_existing_file_is_refused_before_any_search_and_left_alone(capsys, tmp_path):
    finder(capsys, tmp_path)
    path = tmp_path / "out" / "schedules_1-5.csv"
    before = path.read_bytes()
    code, out, err = finder(capsys, tmp_path)
    assert code == EXIT_INPUT_PROBLEM
    assert "already exists" in err and "never written over an existing file" in err
    assert out == "" and path.read_bytes() == before


@needs_ortools
def test_pins_are_kept_and_counted(capsys, tmp_path):
    code, out, _ = finder(capsys, tmp_path, "--fixed", PINS, "--breaks", "1", "--pick", "all")
    assert code == EXIT_WRITTEN
    assert "Fixed positions: tiny_feasible_pins.csv (1 pin)" in out
    schedules = columns(tmp_path / "out" / "schedules_all.csv")
    assert len(schedules) == 28 and "There are 28 schedules in all." in out
    assert all(slots[0] == "bollywood (open)" for slots in schedules.values())


@needs_ortools
def test_pins_that_cannot_all_be_kept_are_named(capsys, tmp_path):
    performers = tmp_path / "p.csv"
    performers.write_text("full name,style\nx,X1\nx,X2\nx,X3\np,A\nq,B\n")
    pins = tmp_path / "pins.csv"
    pins.write_text("position,item\n1,X1\n3,A\n4,B\n")
    code, out, _ = finder(
        capsys, tmp_path, "--breaks", "1", "--fixed", str(pins), performers=str(performers)
    )
    assert code == EXIT_NOTHING_WRITTEN
    assert "No schedule exists." in out
    assert "These pins cannot all be kept at the same time" in out
    assert "slot 3 (A)" in out and "slot 4 (B)" in out
    assert not (tmp_path / "out").exists()


@needs_ortools
def test_a_pinned_name_that_is_not_in_the_performer_file_is_explained(capsys, tmp_path):
    pins = tmp_path / "pins.csv"
    pins.write_text("position,item\n1,Salsa (Open)\n")
    code, out, _ = finder(capsys, tmp_path, "--fixed", str(pins))
    assert code == EXIT_NOTHING_WRITTEN
    assert 'The pin at slot 1 names "Salsa (Open)", which is not in the performer file.' in out


@needs_ortools
def test_when_no_schedule_exists_the_reasons_are_shown_and_nothing_is_written(capsys, tmp_path):
    needs_breaks = str(EXAMPLES / "tiny_needs_breaks.csv")
    code, out, _ = finder(capsys, tmp_path, performers=needs_breaks)
    assert code == EXIT_NOTHING_WRITTEN
    assert "No schedule exists." in out
    assert "Person 0001 is in 3 performances; with a gap of 1 that needs at least 5 slots" in out
    assert not (tmp_path / "out").exists()
    # one break passes the pre-checks, so here the solver is the one that proves it
    code, out, _ = finder(capsys, tmp_path, "--breaks", "1", performers=needs_breaks)
    assert code == EXIT_NOTHING_WRITTEN
    assert "No schedule exists with a gap of 1 and 1 break." in out


@needs_ortools
def test_a_stopped_search_never_says_none_exist(capsys, tmp_path):
    no_conflicts = str(EXAMPLES / "tiny_no_conflicts.csv")
    code, out, _ = finder(
        capsys, tmp_path, "--breaks", "8", "--pick", "5000000", "--time-limit", "0.05",
        performers=no_conflicts,
    )  # fmt: skip
    assert code == EXIT_NOTHING_WRITTEN
    assert "Schedule 5000000 does not appear to have been reached before the time limit." in out
    assert " exist" not in out.replace("More schedules exist", "")  # never "none exist" / "do not exist"


@needs_ortools
def test_the_finder_shows_performer_file_warnings_in_full_before_the_results(capsys, tmp_path):
    code, out, _ = finder(capsys, tmp_path, performers=str(EXAMPLES / "messy_input.csv"))
    assert code == EXIT_WRITTEN
    assert "Please review these 5 warning(s) about the performer file:" in out
    assert '"John Smith" and "Jon Smith" look very similar' in out
    assert out.index("Please review") < out.index("Wrote 5 schedules")


def test_the_pin_files_own_warnings_are_shown(capsys, tmp_path):
    pins = tmp_path / "pins.csv"
    pins.write_text("position,item,notes\n1,Bollywood (Open),opening act\n")
    _, out, _ = finder(capsys, tmp_path, "--fixed", str(pins))
    assert "warning(s) about the fixed-positions file" in out
    assert 'Ignoring other column(s): "notes"' in out


# ---------------------------------------------------------------- problems with the command or files


def test_a_pick_longer_than_the_limit_is_refused_before_any_search(capsys, tmp_path):
    code, out, err = finder(capsys, tmp_path, "--pick", "1-200", "--limit", "100")
    assert code == EXIT_INPUT_PROBLEM and out == ""
    assert "Could not run the schedule finder:" in err
    assert "chooses 200 items but the most allowed at once is 100" in err


def test_a_badly_written_pick_gets_a_plain_message_and_an_example(capsys, tmp_path):
    code, _, err = finder(capsys, tmp_path, "--pick", "abc")
    assert code == EXIT_INPUT_PROBLEM
    assert '"abc" is not a number or a range.' in err and "1,4,9" in err


def test_a_huge_range_is_refused_instantly(capsys, tmp_path):
    code, _, err = finder(capsys, tmp_path, "--pick", "1-1000000000000")
    assert code == EXIT_INPUT_PROBLEM and "most allowed at once" in err


def test_every_problem_with_the_inputs_is_reported_together(capsys, tmp_path):
    bad_pins = tmp_path / "pins.csv"
    bad_pins.write_text("position,item\n1,Jazz\n1,Tap\n")
    code, out, err = finder(
        capsys, tmp_path, "--fixed", str(bad_pins), "--pick", "x",
        performers=str(tmp_path / "missing.csv"),
    )  # fmt: skip
    assert code == EXIT_INPUT_PROBLEM and out == ""
    assert "missing.csv" in err and "position 1 is repeated" in err and '"x" is not a number' in err


def test_a_missing_performer_file_exits_two(capsys, tmp_path):
    code, _, err = finder(capsys, tmp_path, performers=str(tmp_path / "nope.csv"))
    assert code == EXIT_INPUT_PROBLEM and "nope.csv" in err


@pytest.mark.parametrize(
    "bad",
    [
        ["--gap", "-1"], ["--gap", "x"], ["--breaks", "-1"], ["--limit", "0"],
        ["--time-limit", "0"], ["--time-limit", "abc"], ["--seed", "1.5"],
    ],
)  # fmt: skip
def test_bad_numbers_are_refused_by_the_command(capsys, bad):
    with pytest.raises(SystemExit) as caught:
        finder_main(["--performers", PERFORMERS, *bad])
    assert caught.value.code == 2


def test_the_performers_option_is_required(capsys):
    with pytest.raises(SystemExit) as caught:
        finder_main([])
    assert caught.value.code == 2


def test_a_missing_ortools_is_explained_and_exits_two(capsys, tmp_path, monkeypatch):
    def missing():
        raise SolverNotInstalled('OR-Tools is not installed. Install it with: pip install -e ".[finder]"')

    monkeypatch.setattr(cli, "solver_version", missing)
    code, out, err = finder(capsys, tmp_path)
    assert code == EXIT_INPUT_PROBLEM and out == ""
    assert 'pip install -e ".[finder]"' in err


# ---------------------------------------------------------------- the next-batch command


def test_the_next_batch_command_repeats_every_setting_that_matters():
    args = _finder_parser().parse_args([
        "--performers", "data/my show.csv", "--gap", "2", "--breaks", "3", "--fixed", "pins.csv",
        "--limit", "20", "--seed", "42", "--time-limit", "60", "--out", "results",
        "--id-column", "name", "--performance-column", "style",
    ])  # fmt: skip
    assert _next_batch_command(args, "6-10") == (
        'schedule-finder --performers "data/my show.csv" --gap 2 --breaks 3 --fixed pins.csv '
        "--pick 6-10 --limit 20 --seed 42 --time-limit 60 --out results "
        "--id-column name --performance-column style"
    )


def test_the_next_batch_command_leaves_out_settings_that_are_the_default():
    args = _finder_parser().parse_args(["--performers", "p.csv"])
    assert _next_batch_command(args, "6-10") == (
        "schedule-finder --performers p.csv --gap 1 --breaks 0 --pick 6-10"
    )


def test_both_commands_are_registered_in_pyproject():
    scripts = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["scripts"]
    assert scripts["schedule-checker"] == "performance_scheduling.cli:checker_main"
    assert scripts["schedule-finder"] == "performance_scheduling.cli:finder_main"
