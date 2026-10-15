"""Command-line entry points. They read arguments, call the other modules and print.

There is no scheduling logic here: loading is in io.py, judging in validator.py and the
wording in report.py. The same pieces will sit behind the future UI.

Exit codes of schedule-checker:
    0  every schedule checked is valid
    1  at least one schedule is invalid
    2  the command or input files could not be used (also what argparse uses for a
       badly written command), so a script can tell "invalid" from "could not check"
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from performance_scheduling.io import (
    load_performers,
    load_schedules,
    make_key,
    write_text,
)
from performance_scheduling.models import InputError, Issue, Schedule, Severity
from performance_scheduling.report import (
    format_check,
    format_issues,
    format_overview,
    format_totals,
    format_violations_csv,
)
from performance_scheduling.validator import check_schedules

# With more schedules than this, valid ones appear only in the overview table; the full
# write-up is kept for the ones with something to report.
FULL_DETAIL_UP_TO = 10

EXIT_VALID = 0
EXIT_INVALID = 1
EXIT_INPUT_PROBLEM = 2


def _non_negative_int(text: str) -> int:
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f'"{text}" is not a whole number') from None
    if value < 0:
        raise argparse.ArgumentTypeError("the gap cannot be negative")
    return value


def _checker_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="schedule-checker",
        description=(
            "Check whether a running order gives every performer enough rest between "
            "their performances. Breaks count as slots."
        ),
    )
    parser.add_argument("--performers", required=True, metavar="FILE", help="performer CSV file")
    parser.add_argument(
        "--schedule",
        required=True,
        metavar="FILE",
        help="schedule CSV file: a position column and one column per schedule",
    )
    parser.add_argument(
        "--gap",
        type=_non_negative_int,
        default=1,
        help="fewest slots allowed between a performer's performances (default 1)",
    )
    parser.add_argument(
        "--schedule-column",
        metavar="NAME",
        help="check only this schedule column (default: all of them)",
    )
    parser.add_argument("--id-column", metavar="NAME", help="performer column in the performer file")
    parser.add_argument(
        "--performance-column", metavar="NAME", help="performance column in the performer file"
    )
    parser.add_argument(
        "--report-csv", metavar="FILE", help="also write every violation to this CSV file"
    )
    return parser


def _only_named_column(schedules: Sequence[Schedule], wanted: str | None) -> tuple[Schedule, ...]:
    """Keep just the schedule column the organiser asked for (matching ignores case and spaces)."""
    if wanted is None:
        return tuple(schedules)
    chosen = tuple(s for s in schedules if make_key(s.name) == make_key(wanted))
    if not chosen:
        available = ", ".join(f'"{s.name}"' for s in schedules)
        raise InputError(
            [Issue(Severity.ERROR, f'No schedule column called "{wanted}". Columns found: {available}.')]
        )
    return chosen


def _show_errors(errors: Sequence[Issue]) -> None:
    print("Could not check the schedule:", file=sys.stderr)
    for issue in errors:
        print(f"  {issue}", file=sys.stderr)


def checker_main(argv: Sequence[str] | None = None) -> int:
    """Run the schedule checker. Returns the exit code (see the module notes)."""
    # Names can contain characters a Windows console cannot show; show "?" instead of crashing.
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(errors="replace")

    args = _checker_parser().parse_args(argv)

    # Read both files before giving up, so every problem is reported in one go.
    errors: list[Issue] = []
    performer_load = schedule_load = None
    try:
        performer_load = load_performers(args.performers, args.id_column, args.performance_column)
    except InputError as problem:
        errors.extend(problem.issues)
    try:
        schedule_load = load_schedules(args.schedule)
        schedules = _only_named_column(schedule_load.schedules, args.schedule_column)
    except InputError as problem:
        errors.extend(problem.issues)
    if errors or performer_load is None or schedule_load is None:
        _show_errors(errors)
        return EXIT_INPUT_PROBLEM

    data = performer_load.data
    checks = check_schedules(data, schedules, args.gap)

    gap_meaning = (
        "no spacing required"
        if args.gap == 0
        else f"at least {args.gap} slot{'' if args.gap == 1 else 's'} between a performer's performances"
    )
    print(
        f"Performer file: {Path(args.performers).name} "
        f"({len(data.performer_names)} performers, {len(data.performance_names)} performances)"
    )
    print(f"Schedule file:  {Path(args.schedule).name} ({len(schedules)} schedule{'' if len(schedules) == 1 else 's'})")
    print(f"Gap checked:    {args.gap} ({gap_meaning})")

    # The performer-file warnings are the organiser's only prompt to fix typos in the data,
    # so they are shown in full, before the results.
    if performer_load.warnings:
        print()
        print(
            format_issues(
                f"Please review these {len(performer_load.warnings)} warning(s) about the performer file:",
                performer_load.warnings,
            )
        )
    if schedule_load.warnings:
        print()
        print(
            format_issues(
                f"Please review these {len(schedule_load.warnings)} warning(s) about the schedule file:",
                schedule_load.warnings,
            )
        )

    print()
    if len(checks) > 1:
        print(format_overview(checks))
        print()
    many = len(checks) > FULL_DETAIL_UP_TO
    for check in checks:
        if many and check.valid:
            continue
        print(format_check(check, data))
        print()
    if many:
        print("Valid schedules are listed in the table only.")
    if len(checks) > 1:
        print(format_totals(checks))

    if args.report_csv:
        try:
            write_text(args.report_csv, format_violations_csv(checks, data))
        except InputError as problem:
            _show_errors(problem.issues)
            return EXIT_INPUT_PROBLEM
        rows = sum(len(check.violations) for check in checks)
        print(f"Violations written to {args.report_csv} ({rows} row{'' if rows == 1 else 's'}).")

    return EXIT_VALID if all(check.valid for check in checks) else EXIT_INVALID
