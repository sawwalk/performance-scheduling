"""Command-line entry points. They read arguments, call the other modules and print.

There is no scheduling logic here: loading is in io.py, judging in validator.py, searching
in solver.py, choosing from the finder's list in selection.py and the wording in report.py.
The same pieces will sit behind the future UI.

Exit codes of schedule-checker:
    0  every schedule checked is valid
    1  at least one schedule is invalid
    2  the command or input files could not be used (also what argparse uses for a
       badly written command), so a script can tell "invalid" from "could not check"

Exit codes of schedule-finder (decision D42):
    0  at least one schedule was written
    1  no schedule was written: none exist, the time limit was reached first, or none of the
       numbers picked exist
    2  the command or input files could not be used, or the output file already exists
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from performance_scheduling.io import (
    check_output_free,
    load_performers,
    load_pins,
    load_schedules,
    make_key,
    schedules_file_name,
    write_schedules,
    write_text,
)
from performance_scheduling.models import InputError, Issue, Schedule, Severity
from performance_scheduling.report import (
    format_availability,
    format_check,
    format_issues,
    format_larger_gap_prompt,
    format_missing,
    format_no_schedules,
    format_overview,
    format_totals,
    format_violations_csv,
    format_written,
)
from performance_scheduling.selection import (
    apply_selection,
    parse_selection,
    schedules_to_request,
)
from performance_scheduling.solver import (
    DEFAULT_TIME_LIMIT,
    SolverNotInstalled,
    find_schedules,
    solver_version,
)
from performance_scheduling.validator import check_schedules

# With more schedules than this, valid ones appear only in the overview table; the full
# write-up is kept for the ones with something to report.
FULL_DETAIL_UP_TO = 10

EXIT_VALID = 0
EXIT_INVALID = 1
EXIT_INPUT_PROBLEM = 2

# schedule-finder (the input-problem code is shared)
EXIT_WRITTEN = 0
EXIT_NOTHING_WRITTEN = 1

DEFAULT_PICK = "1-5"
DEFAULT_LIMIT = 100
DEFAULT_OUT = "output"


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


def _show_errors(errors: Sequence[Issue], heading: str = "Could not check the schedule:") -> None:
    print(heading, file=sys.stderr)
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


# ---------------------------------------------------------------- schedule-finder


def _positive_int(text: str) -> int:
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f'"{text}" is not a whole number') from None
    if value < 1:
        raise argparse.ArgumentTypeError("this must be at least 1")
    return value


def _positive_number(text: str) -> float:
    try:
        value = float(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f'"{text}" is not a number') from None
    if not value > 0:
        raise argparse.ArgumentTypeError("this must be more than 0")
    return value


def _finder_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="schedule-finder",
        description=(
            "Find running orders that give every performer enough rest between their "
            "performances. Breaks count as slots. Schedules are numbered by their place in "
            "the finder's list; choose which ones to write with --pick."
        ),
    )
    parser.add_argument("--performers", required=True, metavar="FILE", help="performer CSV file")
    parser.add_argument(
        "--gap",
        type=_non_negative_int,
        default=1,
        help="fewest slots allowed between a performer's performances (default 1)",
    )
    parser.add_argument(
        "--breaks",
        type=_non_negative_int,
        default=0,
        help="number of breaks in the show; pinned breaks count towards it (default 0)",
    )
    parser.add_argument(
        "--fixed", metavar="FILE", help="fixed-positions CSV: items pinned to chosen slots"
    )
    parser.add_argument(
        "--pick",
        default=DEFAULT_PICK,
        metavar="CHOICE",
        help=(
            f"which schedules to write, by number: 1-5, 6-10, 1,4,9, 1-3,7,20-22 or all "
            f"(default {DEFAULT_PICK})"
        ),
    )
    parser.add_argument(
        "--limit",
        type=_positive_int,
        default=DEFAULT_LIMIT,
        help=f"most schedules written by one run (default {DEFAULT_LIMIT})",
    )
    parser.add_argument(
        "--seed",
        type=int,
        help="a whole number that starts the list somewhere else; the same number always "
        "gives the same list",
    )
    parser.add_argument(
        "--time-limit",
        type=_positive_number,
        default=DEFAULT_TIME_LIMIT,
        metavar="SECONDS",
        help=f"longest one search may take (default {DEFAULT_TIME_LIMIT:g})",
    )
    parser.add_argument(
        "--out",
        default=DEFAULT_OUT,
        metavar="FOLDER",
        help=f"folder for the schedules file; created if missing (default {DEFAULT_OUT})",
    )
    parser.add_argument("--id-column", metavar="NAME", help="performer column in the performer file")
    parser.add_argument(
        "--performance-column", metavar="NAME", help="performance column in the performer file"
    )
    return parser


def _plural(count: int, word: str) -> str:
    return f"{count} {word}" + ("" if count == 1 else "s")


def _quoted(argument: str) -> str:
    """Quote an argument that holds spaces, as a Windows or Unix shell expects."""
    return f'"{argument}"' if (not argument or any(c.isspace() for c in argument)) else argument


def _next_batch_command(args: argparse.Namespace, next_pick: str) -> str:
    """The exact command for the next batch (decision D44): the same settings, a new --pick."""
    parts = [
        "schedule-finder",
        "--performers", args.performers,
        "--gap", str(args.gap),
        "--breaks", str(args.breaks),
    ]  # fmt: skip
    if args.fixed:
        parts += ["--fixed", args.fixed]
    parts += ["--pick", next_pick]
    if args.limit != DEFAULT_LIMIT:
        parts += ["--limit", str(args.limit)]
    if args.seed is not None:
        parts += ["--seed", str(args.seed)]
    if args.time_limit != DEFAULT_TIME_LIMIT:
        parts += ["--time-limit", f"{args.time_limit:g}"]
    if args.out != DEFAULT_OUT:
        parts += ["--out", args.out]
    if args.id_column:
        parts += ["--id-column", args.id_column, "--performance-column", args.performance_column]
    return " ".join(_quoted(part) for part in parts)


def finder_main(argv: Sequence[str] | None = None) -> int:
    """Run the schedule finder. Returns the exit code (see the module notes)."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(errors="replace")

    args = _finder_parser().parse_args(argv)
    heading = "Could not run the schedule finder:"

    # Check everything that can be checked before the search, and report every problem in
    # one go. The pick is checked first because a typo should not cost a long search.
    errors: list[Issue] = []
    performer_load = pin_load = selection = out_path = None
    try:
        performer_load = load_performers(args.performers, args.id_column, args.performance_column)
    except InputError as problem:
        errors.extend(problem.issues)
    if args.fixed:
        try:
            pin_load = load_pins(args.fixed)
        except InputError as problem:
            errors.extend(problem.issues)
    try:
        selection = parse_selection(args.pick, max_count=args.limit)
        out_path = Path(args.out) / schedules_file_name(args.seed, str(selection))
        check_output_free(out_path)
    except InputError as problem:
        errors.extend(problem.issues)
    if errors or performer_load is None or selection is None or out_path is None:
        _show_errors(errors, heading)
        return EXIT_INPUT_PROBLEM
    try:
        version = solver_version()
    except SolverNotInstalled as problem:
        print(f"{heading}\n  {problem}", file=sys.stderr)
        return EXIT_INPUT_PROBLEM

    data = performer_load.data
    pins = pin_load.pins if pin_load is not None else None
    slots = len(data.performance_names) + args.breaks
    print(
        f"Performer file:  {Path(args.performers).name} "
        f"({len(data.performer_names)} performers, {len(data.performance_names)} performances)"
    )
    if pin_load is not None and pins is not None:
        print(f"Fixed positions: {Path(args.fixed).name} ({_plural(len(pins.slots), 'pin')})")
    order = "the default order" if args.seed is None else f"seed {args.seed}"
    print(f"Settings:        gap {args.gap}, {_plural(args.breaks, 'break')} ({slots} slots), {order}")
    print(f"Search engine:   OR-Tools {version} (schedule numbers can change if this changes)")

    for load, what in ((performer_load, "performer"), (pin_load, "fixed-positions")):
        if load is not None and load.warnings:
            print()
            print(
                format_issues(
                    f"Please review these {len(load.warnings)} warning(s) about the {what} file:",
                    load.warnings,
                )
            )
    print()

    result = find_schedules(
        data,
        gap=args.gap,
        breaks=args.breaks,
        pins=pins,
        seed=args.seed,
        count=schedules_to_request(selection, args.limit),
        time_limit=args.time_limit,
    )
    picked = apply_selection(result, selection, args.limit)
    stopped = picked.more_exist is None

    if not picked.schedules:
        if result.schedules:  # the list was found, but nothing picked is in it
            print("Nothing was written.")
        else:
            print(format_no_schedules(result.status, result.explanation))
        if picked.missing.ranges:
            print(
                format_missing(
                    str(picked.missing), picked.missing.count or 0, stopped=stopped, total=picked.total
                )
            )
        return EXIT_NOTHING_WRITTEN

    try:
        write_schedules(out_path, picked.schedules, data.performance_names)
    except InputError as problem:
        _show_errors(problem.issues, heading)
        return EXIT_INPUT_PROBLEM

    last = picked.numbers.highest or 0
    print(format_written(len(picked.schedules), str(picked.numbers), str(out_path)))
    print(
        format_availability(
            picked.more_exist, total=picked.total, produced=len(result.schedules), last_number=last
        )
    )
    if picked.missing.ranges:
        print(
            format_missing(
                str(picked.missing), picked.missing.count or 0, stopped=stopped, total=picked.total
            )
        )
    if picked.more_exist:
        size = args.limit if selection.select_all else selection.count or 1
        next_pick = f"{last + 1}-{last + size}" if size > 1 else str(last + 1)
        print()
        print(f"To write the next {_plural(size, 'schedule')}, run:")
        print(f"  {_next_batch_command(args, next_pick)}")
        if selection.select_all:
            print(f"(Each run writes at most {args.limit}; change that with --limit.)")
    print()
    print(format_larger_gap_prompt(args.gap))
    return EXIT_WRITTEN
