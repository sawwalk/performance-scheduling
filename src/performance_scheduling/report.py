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
from dataclasses import dataclass

from performance_scheduling.models import (
    FinderStatus,
    Issue,
    PerformerData,
    ScheduleCheck,
    Violation,
)

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


@dataclass(frozen=True)
class PairProblem:
    """One pair of performances that are too close together, and who is affected.

    All performers who are in both performances share the same slots, so one pair
    gathers every violation caused by that pair (see group_violations).
    """

    performance_a: str   # keys; a is the earlier of the two
    position_a: int
    performance_b: str
    position_b: int
    slots_between: int
    required: int
    performers: tuple[str, ...]   # keys, in alphabetical order


def group_violations(violations: Sequence[Violation]) -> tuple[PairProblem, ...]:
    """Gather violations by pair of performances, in running order.

    Violations come one per performer, so a pair that three performers share appears
    three times in the raw list. Grouped, the organiser first sees which performances
    clash and then who is affected. The UI uses the same grouping.
    """
    grouped: dict[tuple[str, str], list[Violation]] = {}
    for violation in violations:
        grouped.setdefault((violation.performance_a, violation.performance_b), []).append(violation)
    pairs = [
        PairProblem(
            performance_a=members[0].performance_a,
            position_a=members[0].position_a,
            performance_b=members[0].performance_b,
            position_b=members[0].position_b,
            slots_between=members[0].slots_between,
            required=members[0].required,
            performers=tuple(sorted(v.performer for v in members)),
        )
        for members in grouped.values()
    ]
    return tuple(sorted(pairs, key=lambda pair: (pair.position_a, pair.position_b)))


def describe_pair(pair: PairProblem, data: PerformerData) -> str:
    """One sentence about one pair of performances that are too close together."""
    first = data.performance_names.get(pair.performance_a, pair.performance_a)
    second = data.performance_names.get(pair.performance_b, pair.performance_b)
    return (
        f"{first} (slot {pair.position_a}) and {second} (slot {pair.position_b}): "
        f"{_plural(pair.slots_between, 'slot')} between, at least {pair.required} needed "
        f"({_plural(len(pair.performers), 'performer')} affected)."
    )


def _section(title: str) -> str:
    """A visible break that marks the start or end of a list in the text output."""
    return f"  ===== {title} ====="


def format_issues(heading: str, issues: Sequence[Issue], limit: int = MAX_ISSUES_SHOWN) -> str:
    """A heading followed by one indented line per issue (shortened if there are many)."""
    lines = [heading]
    lines.extend(f"  {issue}" for issue in issues[:limit])
    if len(issues) > limit:
        lines.append(f"  ... and {len(issues) - limit} more")
    return "\n".join(lines)


def format_check(check: ScheduleCheck, data: PerformerData) -> str:
    """The full write-up for one schedule.

    Spacing problems come in two lists. First the pairs of performances that clash,
    then, for each pair, exactly which performers are affected.
    """
    result = "VALID" if check.valid else "INVALID"
    breaks = "no breaks" if check.num_breaks == 0 else _plural(check.num_breaks, "break")
    lines = [f"{check.schedule_name}: {result}", f"  {_plural(check.num_slots, 'slot')} ({breaks})."]

    if check.problems:
        lines += ["", _section(f"PROBLEMS WITH THE SCHEDULE ITSELF ({len(check.problems)})")]
        lines.append("  Spacing was not checked.")
        lines.extend(f"    - {problem.message}" for problem in check.problems)
        lines.append(_section("END OF SCHEDULE PROBLEMS"))
        return "\n".join(lines)

    pairs = group_violations(check.violations)
    if pairs:
        lines += ["", _section(f"CONFLICTING PERFORMANCE PAIRS ({len(pairs)})")]
        lines.extend(f"  {number:>2}. {describe_pair(pair, data)}" for number, pair in enumerate(pairs, 1))

        affected = len({violation.performer for violation in check.violations})
        lines += ["", _section(f"WHO IS AFFECTED ({_plural(affected, 'performer')})")]
        for number, pair in enumerate(pairs, 1):
            first = data.performance_names.get(pair.performance_a, pair.performance_a)
            second = data.performance_names.get(pair.performance_b, pair.performance_b)
            lines.append(f"  {number:>2}. {first} and {second}")
            lines.extend(f"        - {data.performer_names.get(who, who)}" for who in pair.performers)
        lines.append(_section("END OF SPACING PROBLEMS"))
        lines.append("")

    if check.smallest_gap is None:
        lines.append("  No performer is in more than one performance, so spacing does not apply.")
    else:
        lines.append(
            f"  Tightest spacing: {_plural(check.smallest_gap, 'slot')} between a performer's "
            "performances."
        )
    return "\n".join(lines)


def overview_rows(checks: Sequence[ScheduleCheck]) -> list[tuple[str, ...]]:
    """The overview table as rows of text: a heading row, then one row per schedule.

    "Problems" counts the structural problems if there are any; otherwise it counts the
    pairs of performances that are too close together (not the individual violations).
    format_overview lines these rows up as text and the page shows the same rows, so the two
    cannot disagree.
    """
    rows = [("Schedule", "Result", "Slots", "Breaks", "Problems", "Tightest gap")]
    for check in checks:
        rows.append(
            (
                check.schedule_name,
                "VALID" if check.valid else "INVALID",
                str(check.num_slots),
                str(check.num_breaks),
                str(len(check.problems) or len(group_violations(check.violations))),
                "-" if check.smallest_gap is None else str(check.smallest_gap),
            )
        )
    return rows


def format_overview(checks: Sequence[ScheduleCheck]) -> str:
    """A table with one row per schedule, so several can be compared at a glance."""
    rows = overview_rows(checks)
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


# ---------------------------------------------------------------- the schedule finder
#
# These take plain values (not the selection.py containers) because report.py and
# selection.py sit side by side in the layers and may not import each other.


def format_found(count: int, numbers: str) -> str:
    """One sentence saying how many schedules were found, for the page (no file is written).

    `numbers` is e.g. "1-5" or "1,4,9". Raises ValueError if `count` is below 1, because
    "Found 0 schedules" would be a mistake: the no-schedule box is shown instead.
    """
    if count < 1:
        raise ValueError("there are no schedules to report")
    label = "number" if count == 1 else "numbers"
    return f"Found {_plural(count, 'schedule')} ({label} {numbers})."


def format_written(count: int, numbers: str, path: str) -> str:
    """One sentence saying what was written and where. `numbers` is e.g. "1-5" or "1,4,9"."""
    label = "number" if count == 1 else "numbers"
    return f"Wrote {_plural(count, 'schedule')} ({label} {numbers}) to {path}."


def format_availability(
    more_exist: bool | None, *, total: int | None, produced: int, last_number: int
) -> str:
    """Whether the finder's list goes on: more exist, this is all of it, or the search was stopped."""
    if more_exist:
        return f"More schedules exist after number {last_number}."
    if more_exist is None:
        return (
            f"The search stopped at the time limit after {_plural(produced, 'schedule')}, "
            "so more may exist."
        )
    return f"There {'is' if total == 1 else 'are'} {_plural(total or 0, 'schedule')} in all."


def format_missing(numbers: str, count: int, *, stopped: bool, total: int | None) -> str:
    """Schedule numbers that were asked for but are not in the list."""
    subject = f"Schedule {numbers} does" if count == 1 else f"Schedules {numbers} do"
    if stopped:
        return f"{subject} not appear to have been reached before the time limit."
    return f"{subject} not exist: there {'is' if total == 1 else 'are'} only {total}."


def format_larger_gap_prompt(gap: int) -> str:
    """A plain invitation to try a longer rest next time (decisions D14, D16). Nothing is checked."""
    return (
        f"Schedules found with a gap of {gap}. To see whether everyone could have a longer "
        f"rest, run again with a gap of {gap + 1}."
    )


def no_schedules_heading(status: FinderStatus) -> str:
    """The heading of the no-schedule box: none exist (the search finished) or the time ran out.

    Only EXHAUSTED means the search finished; any other status reads as the time limit.
    """
    if status is FinderStatus.EXHAUSTED:
        return "No schedule exists."
    return "No schedule was found before the time limit."


def format_no_schedules(status: FinderStatus, explanation: Sequence[Issue]) -> str:
    """The heading and the reasons when the finder produced no schedule at all."""
    return "\n".join(
        [no_schedules_heading(status), *(f"  - {issue.message}" for issue in explanation)]
    )
