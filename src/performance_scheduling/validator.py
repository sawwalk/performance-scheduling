"""The schedule checker's logic: is this running order valid, and if not, why not?

It takes the cleaned performer data and a Schedule (see models.py) and returns a
ScheduleCheck. It never reads files and never prints; the command line and the UI turn
the result into words.

The check has two stages.

Stage 1, structure. A running order only means something if it holds each performance in
the performer file exactly once. Unknown, missing and repeated performances are reported.
If there are any, stage 2 is skipped for that schedule: spacing is meaningless without a
sound arrangement.

Stage 2, spacing. For each performer, look at where their performances sit, in order, and
compare each performance with the next one of theirs. If fewer than k slots lie between
them, that is a violation. Comparing only neighbouring performances is enough: if every
neighbouring pair is far enough apart, so is every other pair, because gaps only add up.
Breaks occupy slots, so a break between two performances counts as spacing.

The performer data is all this needs. The conflict map (conflicts.py) is for the finder.
"""

from __future__ import annotations

from collections.abc import Sequence
from difflib import get_close_matches
from itertools import pairwise

from performance_scheduling.models import (
    BREAK,
    Issue,
    PerformerData,
    Schedule,
    ScheduleCheck,
    Severity,
    Violation,
)

# How alike an unknown name must be to a real one before we suggest it ("Did you mean...").
SUGGESTION_SIMILARITY = 0.85


def _join_positions(positions: Sequence[int]) -> str:
    """Write [2] as "2", [2, 3] as "2 and 3", [2, 5, 9] as "2, 5 and 9"."""
    texts = [str(position) for position in positions]
    if len(texts) <= 2:
        return " and ".join(texts)
    return ", ".join(texts[:-1]) + " and " + texts[-1]


def _structure_problems(data: PerformerData, schedule: Schedule) -> list[Issue]:
    """Stage 1: unknown, repeated and missing performances."""
    where: dict[str, list[int]] = {}
    for position, slot in enumerate(schedule.slots, start=1):
        if slot != BREAK:
            where.setdefault(slot, []).append(position)

    def shown(key: str) -> str:
        """The name as the organiser wrote it, or as in the performer file."""
        return schedule.display_names.get(key) or data.performance_names.get(key, key)

    problems: list[Issue] = []

    unknown = sorted((key for key in where if key not in data.performance_names), key=lambda k: where[k][0])
    for key in unknown:
        message = (
            f'"{shown(key)}" is in the schedule (position {_join_positions(where[key])}) '
            "but not in the performer file."
        )
        close = get_close_matches(key, data.performance_names, n=1, cutoff=SUGGESTION_SIMILARITY)
        if close:
            message += f' Did you mean "{data.performance_names[close[0]]}"?'
        problems.append(Issue(Severity.ERROR, message))

    repeated = sorted(
        (key for key, found in where.items() if len(found) > 1 and key in data.performance_names),
        key=lambda k: where[k][0],
    )
    for key in repeated:
        problems.append(
            Issue(
                Severity.ERROR,
                f'"{shown(key)}" appears {len(where[key])} times in the schedule '
                f"(positions {_join_positions(where[key])}). Each performance should appear once.",
            )
        )

    for key in sorted(data.performance_names):
        if key not in where:
            problems.append(
                Issue(
                    Severity.ERROR,
                    f'"{data.performance_names[key]}" is in the performer file '
                    "but missing from the schedule.",
                )
            )
    return problems


def check_schedule(data: PerformerData, schedule: Schedule, gap: int = 1) -> ScheduleCheck:
    """Check one schedule. `gap` is k: the fewest slots allowed between a performer's performances.

    k = 1 means a performer must never appear in two consecutive slots (the basic rule).
    k = 0 allows anything, so only the structure is checked.
    """
    if gap < 0:
        raise ValueError("gap cannot be negative")

    problems = _structure_problems(data, schedule)
    if problems:
        return ScheduleCheck(
            schedule_name=schedule.name,
            gap_required=gap,
            num_slots=schedule.num_slots,
            num_breaks=schedule.num_breaks,
            problems=tuple(problems),
            violations=(),
            smallest_gap=None,
        )

    positions = schedule.positions()
    violations: list[Violation] = []
    smallest_gap: int | None = None
    for performer, performances in data.performances_by_performer.items():
        if len(performances) < 2:
            continue  # a performer in one performance has no spacing to check
        ordered = sorted((positions[performance], performance) for performance in performances)
        for (position_a, performance_a), (position_b, performance_b) in pairwise(ordered):
            between = position_b - position_a - 1
            if smallest_gap is None or between < smallest_gap:
                smallest_gap = between
            if between < gap:
                violations.append(
                    Violation(
                        performer=performer,
                        performance_a=performance_a,
                        position_a=position_a,
                        performance_b=performance_b,
                        position_b=position_b,
                        slots_between=between,
                        required=gap,
                    )
                )

    violations.sort(key=lambda v: (v.position_a, v.position_b, v.performer))
    return ScheduleCheck(
        schedule_name=schedule.name,
        gap_required=gap,
        num_slots=schedule.num_slots,
        num_breaks=schedule.num_breaks,
        problems=(),
        violations=tuple(violations),
        smallest_gap=smallest_gap,
    )


def check_schedules(
    data: PerformerData, schedules: Sequence[Schedule], gap: int = 1
) -> tuple[ScheduleCheck, ...]:
    """Check several schedules (such as the columns of a side-by-side file), in order."""
    return tuple(check_schedule(data, schedule, gap) for schedule in schedules)
