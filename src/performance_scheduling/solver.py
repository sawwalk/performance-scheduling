"""The schedule finder's logic: find valid running orders, or explain why there are none.

It takes the cleaned performer data (see models.py) plus the organiser's settings (gap,
breaks, pins, seed) and returns a FinderResult. It never reads files and never prints;
the command line and the UI turn the result into words.

A run has three stages.

1. Pre-checks. Cheap tests that spot an impossible request at once and say why in plain
   language: a pin that does not fit the show, a performer or a group of clashing
   performances that needs more slots than the show has, two pinned performances that
   clash but sit too close together. All the checks that fail are reported together.
   If any fails, no search is run and the status is EXHAUSTED: nothing can satisfy the
   request.

2. Search. OR-Tools CP-SAT lists valid schedules one after another (decision D29). The
   list is complete and repeatable but not in dictionary order (D30). Schedules are
   numbered by their place in the list. A shuffle seed changes the order in which the
   model is built, which changes where the list starts (D38).

3. Cross-check. Every schedule found is passed through the schedule checker (validator.py)
   and compared with the pins. A schedule that fails is a bug in this file, so it raises
   an error instead of being returned.

If the search finds nothing and pins were given, a second small search names pins that
cannot all be kept at once (D34).

OR-Tools is loaded only when a search is needed, so this file can always be imported (and
the pre-checks used) even where the finder's extra is not installed.
"""

from __future__ import annotations

import hashlib
import importlib
from collections.abc import Mapping, Sequence
from difflib import get_close_matches
from itertools import combinations
from types import ModuleType

from performance_scheduling.conflicts import build_conflict_map
from performance_scheduling.models import (
    BREAK,
    FinderResult,
    FinderStatus,
    Issue,
    PerformerData,
    Pins,
    Schedule,
    Severity,
)
from performance_scheduling.validator import SUGGESTION_SIMILARITY, check_schedule

# Proposed default (open question Q13): how long one search may run before it stops.
DEFAULT_TIME_LIMIT = 30.0

# The solver's own random seed is fixed. The organiser's seed works differently (see
# _build_order), because the solver's seed was found not to change where the list starts.
_SOLVER_SEED = 1

# The search for the largest group of clashing performances stops after this many steps and
# uses the best group found so far. Any group it reports is genuine; it may just not be the
# largest.
_GROUP_SEARCH_STEP_LIMIT = 200_000


class SolverNotInstalled(RuntimeError):
    """OR-Tools is missing. The pre-checks still work without it; the search does not."""


# ---------------------------------------------------------------- small helpers


def _plural(count: int, word: str) -> str:
    return f"{count} {word}" + ("" if count == 1 else "s")


def _name_list(names: Sequence[str], limit: int = 3) -> str:
    """Write ["Sam"] as "Sam", two as "Sam and Kim", many as "Sam, Kim, Lee and 4 more"."""
    shown = list(names[:limit])
    hidden = len(names) - len(shown)
    if hidden > 0:
        return ", ".join(shown) + f" and {hidden} more"
    if len(shown) <= 1:
        return "".join(shown)
    return ", ".join(shown[:-1]) + " and " + shown[-1]


def slots_needed(performances: int, gap: int) -> int:
    """The fewest slots that `performances` mutually clashing performances can fit in."""
    return (performances - 1) * (gap + 1) + 1


def _error(message: str) -> Issue:
    return Issue(Severity.ERROR, message)


def _shown(data: PerformerData, pins: Pins, item: str) -> str:
    """A pinned item as the organiser should see it."""
    if item == BREAK:
        return "a break"
    return data.performance_names.get(item) or pins.display_names.get(item) or item


# ---------------------------------------------------------------- pre-checks


def _pin_problems(
    data: PerformerData, pins: Pins, total: int, breaks: int
) -> tuple[list[Issue], dict[int, str]]:
    """Pins that do not fit the show. Also returns the pins that are fine, by position."""
    issues: list[Issue] = []
    usable: dict[int, str] = {}
    for position, item in sorted(pins.slots.items()):
        if not 1 <= position <= total:
            issues.append(
                _error(
                    f"The pin at slot {position} ({_shown(data, pins, item)}) is outside the show: "
                    f"there are {total} slots ({_plural(len(data.performance_names), 'performance')} "
                    f"and {_plural(breaks, 'break')})."
                )
            )
        elif item != BREAK and item not in data.performance_names:
            message = (
                f'The pin at slot {position} names "{_shown(data, pins, item)}", '
                "which is not in the performer file."
            )
            close = get_close_matches(item, data.performance_names, n=1, cutoff=SUGGESTION_SIMILARITY)
            if close:
                message += f' Did you mean "{data.performance_names[close[0]]}"?'
            issues.append(_error(message))
        else:
            usable[position] = item

    where: dict[str, list[int]] = {}
    for position, item in sorted(usable.items()):
        if item != BREAK:
            where.setdefault(item, []).append(position)
    for item, positions in where.items():
        if len(positions) > 1:
            listed = ", ".join(str(p) for p in positions)
            issues.append(
                _error(f'"{_shown(data, pins, item)}" is pinned to more than one slot ({listed}).')
            )
            for position in positions:
                usable.pop(position)

    pinned_breaks = sum(1 for item in pins.slots.values() if item == BREAK)
    if pinned_breaks > breaks:
        issues.append(
            _error(
                f"{_plural(pinned_breaks, 'slot')} {'is' if pinned_breaks == 1 else 'are'} "
                f"pinned as breaks, but the show has only {_plural(breaks, 'break')}. "
                "Raise the number of breaks or remove a pinned break."
            )
        )
    return issues, usable


def _capacity_problems(data: PerformerData, gap: int, total: int) -> list[Issue]:
    """A performer in m performances needs (m - 1)(gap + 1) + 1 slots."""
    by_count: dict[int, list[str]] = {}
    for key, performances in data.performances_by_performer.items():
        if len(performances) >= 2 and slots_needed(len(performances), gap) > total:
            by_count.setdefault(len(performances), []).append(data.performer_names.get(key, key))
    issues = []
    for count in sorted(by_count, reverse=True):
        who = sorted(by_count[count])
        verb = "is" if len(who) == 1 else "are"
        issues.append(
            _error(
                f"{_name_list(who)} {verb} in {count} performances; with a gap of {gap} that needs "
                f"at least {slots_needed(count, gap)} slots, but the show has {total}."
            )
        )
    return issues


def _largest_clash_group(neighbours: Mapping[str, frozenset[str]]) -> list[str]:
    """The biggest set of performances that all clash with each other (a "clique").

    Uses the Bron-Kerbosch method with a pivot, walking candidates in alphabetical order so
    the answer is the same on every run. Stops after _GROUP_SEARCH_STEP_LIMIT steps.
    """
    best: list[str] = []
    steps = 0

    def expand(chosen: list[str], candidates: set[str], excluded: set[str]) -> None:
        nonlocal best, steps
        steps += 1
        if steps > _GROUP_SEARCH_STEP_LIMIT:
            return
        if not candidates and not excluded:
            if len(chosen) > len(best):
                best = list(chosen)
            return
        if len(chosen) + len(candidates) <= len(best):
            return
        pivot = max(sorted(candidates | excluded), key=lambda v: len(candidates & neighbours[v]))
        for v in sorted(candidates - neighbours[pivot]):
            expand(chosen + [v], candidates & neighbours[v], excluded & neighbours[v])
            candidates = candidates - {v}
            excluded = excluded | {v}

    expand([], set(neighbours), set())
    return sorted(best)


def _group_problems(
    data: PerformerData, neighbours: Mapping[str, frozenset[str]], gap: int, total: int
) -> list[Issue]:
    """A group of m performances that all clash needs the same number of slots as one performer in m.

    Only reported when the group is bigger than any single performer's list, because
    otherwise the performer check has already said it.
    """
    if gap == 0:
        return []
    group = _largest_clash_group(neighbours)
    busiest = max((len(p) for p in data.performances_by_performer.values()), default=0)
    if len(group) <= busiest or slots_needed(len(group), gap) <= total:
        return []
    names = [data.performance_names.get(key, key) for key in group]
    return [
        _error(
            f"{len(group)} performances all clash with each other ({_name_list(names, 6)}). "
            f"With a gap of {gap} they need at least {slots_needed(len(group), gap)} slots, "
            f"but the show has {total}."
        )
    ]


def _pinned_clash_problems(
    data: PerformerData, pins: Pins, usable: Mapping[int, str], conflicts, gap: int
) -> list[Issue]:
    """Two pinned performances that share a performer but sit too close together."""
    pinned = sorted(
        ((position, item) for position, item in usable.items() if item != BREAK)
    )
    issues = []
    for (first_slot, first), (second_slot, second) in combinations(pinned, 2):
        shared = conflicts.shared_performers(first, second)
        between = second_slot - first_slot - 1
        if shared and between < gap:
            who = sorted(data.performer_names.get(key, key) for key in shared)
            issues.append(
                _error(
                    f"The pins at slots {first_slot} and {second_slot} "
                    f"({_shown(data, pins, first)} and {_shown(data, pins, second)}) clash: they "
                    f"share {_name_list(who)}, so they need at least {_plural(gap, 'slot')} "
                    f"between them but have {between}."
                )
            )
    return issues


# ---------------------------------------------------------------- building the search


def _rank(seed: int, *parts: str) -> str:
    """A fixed shuffle key. SHA-256 gives the same answer on every machine and Python version."""
    return hashlib.sha256("|".join((str(seed), *parts)).encode("utf-8")).hexdigest()


def _build_order(keys: Sequence[str], seed: int | None) -> list[str]:
    """The order performances are given to the solver.

    No seed: alphabetical (the default list). With a seed: shuffled by hash, so the solver
    starts its list somewhere else. The solver's own random seed was tested first and did
    not change where the list starts (decision D38).
    """
    if seed is None:
        return sorted(keys)
    return sorted(keys, key=lambda key: (_rank(seed, key), key))


def _pair_order(pairs: Sequence[tuple[str, str]], seed: int | None) -> list[tuple[str, str]]:
    if seed is None:
        return sorted(pairs)
    return sorted(pairs, key=lambda pair: (_rank(seed, *pair), pair))


def _load_cp_model() -> ModuleType:
    try:
        return importlib.import_module("ortools.sat.python.cp_model")
    except ImportError:
        raise SolverNotInstalled(
            "The schedule finder needs OR-Tools, which is not installed. "
            'Install it with: pip install -e ".[finder]"'
        ) from None


def solver_version() -> str:
    """The OR-Tools version in use. Schedule numbering can depend on it (decision D32)."""
    _load_cp_model()
    return importlib.import_module("ortools").__version__


def _build_model(
    cp_model: ModuleType,
    order: Sequence[str],
    pairs: Sequence[tuple[str, str]],
    gap: int,
    total: int,
    usable_pins: Mapping[int, str],
    pins_as_assumptions: bool,
):
    """Describe the problem to the solver.

    One variable per performance holds its slot (1 to total); no two share a slot. For
    each pair that clashes, either the first is at least gap + 1 slots before the second or
    the other way round; the yes/no helper is settled by the positions, so no schedule is
    listed twice. Breaks are the slots no performance uses. A pinned performance is fixed
    to its slot; a pinned break keeps every performance out of that slot.

    With `pins_as_assumptions` each pin can be switched off by the solver, which is how it
    reports pins that cannot all be kept. Otherwise pins are fixed outright.
    """
    model = cp_model.CpModel()
    position = {key: model.new_int_var(1, total, key) for key in order}
    model.add_all_different(list(position.values()))
    if gap > 0:
        for first, second in pairs:
            first_earlier = model.new_bool_var(f"{first}<{second}")
            model.add(position[first] + gap + 1 <= position[second]).only_enforce_if(first_earlier)
            model.add(position[second] + gap + 1 <= position[first]).only_enforce_if(
                first_earlier.negated()
            )

    pin_of_literal: dict[int, int] = {}
    for slot, item in sorted(usable_pins.items()):
        constraints = (
            [model.add(position[key] != slot) for key in order]
            if item == BREAK
            else [model.add(position[item] == slot)]
        )
        if pins_as_assumptions:
            literal = model.new_bool_var(f"pin_{slot}")
            for constraint in constraints:
                constraint.only_enforce_if(literal)
            model.add_assumption(literal)
            pin_of_literal[literal.index] = slot
    return model, position, pin_of_literal


def _list_schedules(
    cp_model: ModuleType, model, position: Mapping[str, object], total: int, count: int,
    time_limit: float,
):
    """Run the solver until it has `count` schedules, finishes, or runs out of time."""
    solver = cp_model.CpSolver()
    solver.parameters.num_workers = 1  # one thread: the only way to get a repeatable list
    solver.parameters.random_seed = _SOLVER_SEED
    solver.parameters.enumerate_all_solutions = True
    solver.parameters.max_time_in_seconds = time_limit
    found: list[tuple[str, ...]] = []

    class Collect(cp_model.CpSolverSolutionCallback):
        def __init__(self) -> None:
            super().__init__()

        def on_solution_callback(self) -> None:
            slots = [BREAK] * total
            for key, variable in position.items():
                slots[self.value(variable) - 1] = key
            found.append(tuple(slots))
            if len(found) >= count:
                self.stop_search()

    return found, solver.solve(model, Collect())


def _blocking_pins(
    cp_model: ModuleType, order, pairs, gap, total, usable_pins, time_limit
) -> tuple[int, ...] | None:
    """Positions of pins that cannot all be kept; () if none is to blame; None if unknown."""
    model, _, pin_of_literal = _build_model(
        cp_model, order, pairs, gap, total, usable_pins, pins_as_assumptions=True
    )
    solver = cp_model.CpSolver()
    solver.parameters.num_workers = 1
    solver.parameters.random_seed = _SOLVER_SEED
    solver.parameters.max_time_in_seconds = time_limit
    if solver.solve(model) != cp_model.INFEASIBLE:
        return None
    core = solver.sufficient_assumptions_for_infeasibility()
    return tuple(sorted(pin_of_literal[index] for index in core))


def _why_none_exist(
    data: PerformerData, pins: Pins, gap: int, breaks: int, blocking: tuple[int, ...] | None,
    has_pins: bool,
) -> tuple[Issue, ...]:
    advice = "Try more breaks or a smaller gap."
    if blocking:
        listed = ", ".join(
            f"slot {slot} ({_shown(data, pins, pins.slots[slot])})" for slot in blocking
        )
        return (
            _error(
                f"No schedule exists with these pins. These pins cannot all be kept at the same "
                f"time: {listed}. Remove or move at least one of them."
            ),
        )
    if has_pins and blocking is None:
        return (
            _error(f"No schedule exists with a gap of {gap} and {_plural(breaks, 'break')}."),
            Issue(Severity.WARNING, "Which pins are the problem could not be worked out."),
        )
    where = " even without the pins" if has_pins else ""
    return (
        _error(
            f"No schedule exists with a gap of {gap} and {_plural(breaks, 'break')}{where}. {advice}"
        ),
    )


# ---------------------------------------------------------------- the finder


def find_schedules(
    data: PerformerData,
    *,
    gap: int = 1,
    breaks: int = 0,
    pins: Pins | None = None,
    seed: int | None = None,
    count: int = 1,
    time_limit: float = DEFAULT_TIME_LIMIT,
) -> FinderResult:
    """List the first `count` valid schedules, or say why there are none.

    gap         fewest slots allowed between a performer's performances (k); 0 allows anything
    breaks      number of breaks; pinned breaks count towards it (D9)
    pins        items fixed to chosen slots (numbered from 1)
    seed        None for the default list; a whole number to start the list somewhere else.
                The same input and seed give the same list (on the same OR-Tools version)
    count       how many schedules to list. To say whether more exist, ask for one extra
    time_limit  seconds one search may take. Hitting it gives STOPPED, which proves nothing

    Status: FOUND when `count` schedules were produced; EXHAUSTED when the search finished
    with fewer (so no more exist) or the request is impossible; STOPPED at the time limit.

    Raises ValueError for settings the program should never pass (a negative gap, ...),
    SolverNotInstalled if a search is needed and OR-Tools is missing, and RuntimeError if a
    schedule fails the cross-check (a bug, never a user mistake).
    """
    if gap < 0:
        raise ValueError("gap cannot be negative")
    if breaks < 0:
        raise ValueError("breaks cannot be negative")
    if count < 1:
        raise ValueError("count must be at least 1")
    if time_limit <= 0:
        raise ValueError("time_limit must be positive")
    if not data.performance_names:
        raise ValueError("the show has no performances")
    pins = pins if pins is not None else Pins(slots={})

    keys = data.performance_keys
    total = len(keys) + breaks
    conflicts = build_conflict_map(data)

    # Stage 1: pre-checks. All that fail are reported together.
    problems, usable = _pin_problems(data, pins, total, breaks)
    problems += _capacity_problems(data, gap, total)
    problems += _group_problems(data, conflicts.neighbours, gap, total)
    problems += _pinned_clash_problems(data, pins, usable, conflicts, gap)
    if problems:
        return FinderResult(FinderStatus.EXHAUSTED, (), explanation=tuple(problems))

    # Stage 2: search.
    cp_model = _load_cp_model()
    order = _build_order(keys, seed)
    pairs = _pair_order(
        [(a, b) for a, others in conflicts.neighbours.items() for b in others if a < b], seed
    )
    model, position, _ = _build_model(
        cp_model, order, pairs, gap, total, usable, pins_as_assumptions=False
    )
    found, status = _list_schedules(cp_model, model, position, total, count, time_limit)
    if status == cp_model.MODEL_INVALID:
        raise RuntimeError(f"The solver rejected the model: {model.validate()}")

    # Stage 3: cross-check, then build the result.
    schedules = tuple(
        Schedule(name=f"schedule_{number}", slots=slots) for number, slots in enumerate(found, 1)
    )
    _cross_check(data, schedules, gap, breaks, usable)

    if len(schedules) >= count:
        return FinderResult(FinderStatus.FOUND, schedules)
    if status in (cp_model.OPTIMAL, cp_model.INFEASIBLE):
        # The whole search finished. Nothing was found, or fewer than asked for.
        if schedules:
            return FinderResult(FinderStatus.EXHAUSTED, schedules)
        blocking = (
            _blocking_pins(cp_model, order, pairs, gap, total, usable, time_limit)
            if usable
            else ()
        )
        explanation = _why_none_exist(data, pins, gap, breaks, blocking, has_pins=bool(usable))
        return FinderResult(
            FinderStatus.EXHAUSTED, (), explanation=explanation, blocking_pins=blocking or ()
        )
    note = Issue(
        Severity.WARNING,
        f"The time limit of {time_limit:g} seconds was reached before the search finished. "
        "This does not show that no more schedules exist.",
    )
    return FinderResult(FinderStatus.STOPPED, schedules, explanation=(note,))


def _cross_check(
    data: PerformerData,
    schedules: Sequence[Schedule],
    gap: int,
    breaks: int,
    usable: Mapping[int, str],
) -> None:
    """Every schedule must pass the schedule checker, honour the pins and be new.

    A failure here means a bug in this file, so it stops the run rather than hand the
    organiser a schedule that does not work.
    """
    seen: set[tuple[str, ...]] = set()
    for schedule in schedules:
        check = check_schedule(data, schedule, gap)
        if not check.valid:
            raise RuntimeError(f"Internal error: {schedule.name} failed the schedule checker.")
        if schedule.num_breaks != breaks:
            raise RuntimeError(f"Internal error: {schedule.name} has the wrong number of breaks.")
        if any(schedule.slots[slot - 1] != item for slot, item in usable.items()):
            raise RuntimeError(f"Internal error: {schedule.name} does not keep the pins.")
        if schedule.slots in seen:
            raise RuntimeError(f"Internal error: {schedule.name} repeats an earlier schedule.")
        seen.add(schedule.slots)
