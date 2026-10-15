"""Turning check results into words for the organiser.

The schedule checker (validator.py) returns data. This file writes that data up in plain
language and as a CSV report. It lives in the shared layer, between the logic and the
interfaces, so the command line and the future UI show exactly the same wording.

Nothing here reads files or prints: every function takes data in and returns text.
Names shown to the organiser come from the performer file (display names), never the
lower-case keys.
"""

from __future__ import annotations

import csv
from collections.abc import Sequence

from performance_scheduling.models import Issue, PerformerData, ScheduleCheck, Violation

# Long lists of warnings are shortened so the important lines are not buried.
MAX_ISSUES_SHOWN = 20

CSV_COLUMNS = (
    "schedule",
    "performer",
    "performance_a",
    "position_a",
    "performance_b",
    "position_b",
    "slots_between",
    "required",
)


def _plural(count: int, word: str) -> str:
    return f"{count} {word}" + ("" if count == 1 else "s")


def describe_violation(violation: Violation, data: PerformerData) -> str:
    """One sentence about one broken spacing rule."""
    performer = data.performer_names.get(violation.performer, violation.performer)
    first = data.performance_names.get(violation.performance_a, violation.performance_a)
    second = data.performance_names.get(violation.performance_b, violation.performance_b)
    return (
        f"{performer} is in {first} (slot {violation.position_a}) and {second} "
        f"(slot {violation.position_b}): {_plural(violation.slots_between, 'slot')} between, "
        f"but at least {violation.required} needed."
    )


def format_issues(heading: str, issues: Sequence[Issue], limit: int = MAX_ISSUES_SHOWN) -> str:
    """A heading followed by one indented line per issue (shortened if there are many)."""
    lines = [heading]
    lines.extend(f"  {issue}" for issue in issues[:limit])
    if len(issues) > limit:
        lines.append(f"  ... and {len(issues) - limit} more")
    return "\n".join(lines)


def format_check(check: ScheduleCheck, data: PerformerData) -> str:
    """The full write-up for one schedule."""
    result = "VALID" if check.valid else "INVALID"
    breaks = "no breaks" if check.num_breaks == 0 else _plural(check.num_breaks, "break")
    lines = [f"{check.schedule_name}: {result}", f"  {_plural(check.num_slots, 'slot')} ({breaks})."]

    if check.problems:
        lines.append(
            f"  There {'is' if len(check.problems) == 1 else 'are'} "
            f"{_plural(len(check.problems), 'problem')} with the schedule itself, "
            "so spacing was not checked:"
        )
        lines.extend(f"    - {problem.message}" for problem in check.problems)
        return "\n".join(lines)

    if check.violations:
        lines.append(f"  Not enough rest between performances ({len(check.violations)}):")
        lines.extend(f"    - {describe_violation(v, data)}" for v in check.violations)

    if check.smallest_gap is None:
        lines.append("  No performer is in more than one performance, so spacing does not apply.")
    else:
        lines.append(
            f"  Tightest spacing: {_plural(check.smallest_gap, 'slot')} between a performer's "
            "performances."
        )
    return "\n".join(lines)


def format_overview(checks: Sequence[ScheduleCheck]) -> str:
    """A table with one row per schedule, so several can be compared at a glance."""
    rows = [("Schedule", "Result", "Slots", "Breaks", "Problems", "Tightest gap")]
    for check in checks:
        rows.append(
            (
                check.schedule_name,
                "VALID" if check.valid else "INVALID",
                str(check.num_slots),
                str(check.num_breaks),
                str(len(check.problems) + len(check.violations)),
                "-" if check.smallest_gap is None else str(check.smallest_gap),
            )
        )
    widths = [max(len(row[column]) for row in rows) for column in range(len(rows[0]))]
    return "\n".join(
        "  ".join(cell.ljust(width) for cell, width in zip(row, widths)).rstrip() for row in rows
    )


def format_totals(checks: Sequence[ScheduleCheck]) -> str:
    """One closing sentence for a run that checked several schedules."""
    invalid = sum(1 for check in checks if not check.valid)
    total = len(checks)
    if invalid == 0:
        return f"All {total} schedules are valid."
    if invalid == total:
        return f"All {total} schedules are invalid."
    return f"{invalid} of {total} schedules are invalid."


class _Collector:
    """A minimal stand-in for a file, so the csv module can write into a string."""

    def __init__(self) -> None:
        self.parts: list[str] = []

    def write(self, text: str) -> int:
        self.parts.append(text)
        return len(text)


def format_violations_csv(checks: Sequence[ScheduleCheck], data: PerformerData) -> str:
    """CSV text with one row per violation, using the names from the performer file."""
    collector = _Collector()
    writer = csv.writer(collector, lineterminator="\n")
    writer.writerow(CSV_COLUMNS)
    for check in checks:
        for v in check.violations:
            writer.writerow(
                (
                    check.schedule_name,
                    data.performer_names.get(v.performer, v.performer),
                    data.performance_names.get(v.performance_a, v.performance_a),
                    v.position_a,
                    data.performance_names.get(v.performance_b, v.performance_b),
                    v.position_b,
                    v.slots_between,
                    v.required,
                )
            )
    return "".join(collector.parts)
