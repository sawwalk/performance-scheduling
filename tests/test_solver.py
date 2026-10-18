"""Tests for solver.py (the schedule finder's logic).

The pre-check tests need no OR-Tools. The search tests do, and are skipped if it is missing.
"""

import importlib.util
import os
import subprocess
import sys
import types
from itertools import combinations, permutations
from pathlib import Path

import pytest

from performance_scheduling import solver
from performance_scheduling.io import load_performers, load_schedules
from performance_scheduling.models import (
    BREAK,
    FinderStatus,
    PerformerData,
    Pins,
    Schedule,
    Severity,
)
from performance_scheduling.solver import (
    SolverNotInstalled,
    find_schedules,
    slots_needed,
    solver_version,
)
from performance_scheduling.validator import check_schedule

EXAMPLES = Path(__file__).resolve().parent.parent / "data" / "examples"

needs_ortools = pytest.mark.skipif(
    importlib.util.find_spec("ortools") is None, reason="OR-Tools is not installed"
)


def example(name: str) -> PerformerData:
    return load_performers(EXAMPLES / name).data


def performers(members: dict[str, list[str]]) -> PerformerData:
    """PerformerData from {performer: [performances]}; display names are the keys, title-cased."""
    performances = {p for ps in members.values() for p in ps}
    return PerformerData(
        performances_by_performer={who: frozenset(ps) for who, ps in members.items()},
        performer_names={who: who.title() for who in members},
        performance_names={p: p.title() for p in performances},
    )


def messages(result) -> list[str]:
    return [issue.message for issue in result.explanation]


def slot_lists(result) -> list[tuple[str, ...]]:
    return [schedule.slots for schedule in result.schedules]


# Five performances: x1 and x2 share a performer, a, b and c are alone. Found while testing the
# old backtracking engine: at gap 2 with no breaks brute force finds 36 valid schedules.
FIVE = performers({"x": ["x1", "x2"], "p": ["a"], "q": ["b"], "r": ["c"]})

# x is in three performances; a and b are alone. With one break there are 6 slots, and x must
# use one of {1,3,5}, {1,3,6}, {1,4,6}, {2,4,6} at gap 1. Pinning a to 3 and b to 4 leaves none,
# although neither pin is a problem on its own.
SIX = performers({"x": ["x1", "x2", "x3"], "p": ["a"], "q": ["b"]})


def every_arrangement(keys, breaks):
    total = len(keys) + breaks
    for performance_slots in combinations(range(total), len(keys)):
        for order in permutations(keys):
            slots = [BREAK] * total
            for slot, key in zip(performance_slots, order):
                slots[slot] = key
            yield tuple(slots)


def brute_force(data: PerformerData, gap: int, breaks: int) -> set[tuple[str, ...]]:
    return {
        slots
        for slots in every_arrangement(data.performance_keys, breaks)
        if check_schedule(data, Schedule(name="x", slots=slots), gap).valid
    }


# ---------------------------------------------------------------- against brute force


@needs_ortools
@pytest.mark.parametrize(
    ("filename", "gap", "breaks", "expected"),
    [
        # The counts are the ones recorded in docs/test-datasets.md.
        ("tiny_feasible.csv", 1, 0, 8),
        ("tiny_feasible.csv", 1, 1, 152),
        ("tiny_feasible.csv", 1, 2, 1104),
        ("tiny_feasible.csv", 2, 0, 0),
        ("tiny_feasible.csv", 2, 1, 8),
        ("tiny_feasible.csv", 2, 2, 128),
        ("tiny_needs_breaks.csv", 1, 0, 0),
        ("tiny_needs_breaks.csv", 1, 1, 0),
        ("tiny_needs_breaks.csv", 1, 2, 12),
        ("tiny_no_conflicts.csv", 1, 0, 720),
        ("tiny_no_conflicts.csv", 2, 1, 5040),
    ],
)
def test_the_list_is_exactly_the_brute_force_set(filename, gap, breaks, expected):
    data = example(filename)
    result = find_schedules(data, gap=gap, breaks=breaks, count=10**6)
    assert result.status is FinderStatus.EXHAUSTED
    assert len(result.schedules) == expected
    assert len(set(slot_lists(result))) == expected  # none listed twice
    assert set(slot_lists(result)) == brute_force(data, gap, breaks)


@needs_ortools
def test_a_performer_who_can_start_early_at_gap_two_is_not_missed():
    result = find_schedules(FIVE, gap=2, count=10**6)
    assert len(result.schedules) == 36
    assert set(slot_lists(result)) == brute_force(FIVE, 2, 0)


@needs_ortools
def test_gap_zero_allows_every_order():
    result = find_schedules(example("tiny_needs_breaks.csv"), gap=0, count=1000)
    assert result.status is FinderStatus.EXHAUSTED
    assert len(result.schedules) == 24  # 4 performances in any order


# ---------------------------------------------------------------- status and numbering


@needs_ortools
def test_asking_for_fewer_than_exist_is_found_and_schedules_are_numbered_from_one():
    result = find_schedules(example("tiny_feasible.csv"), gap=1, count=3)
    assert result.status is FinderStatus.FOUND
    assert [s.name for s in result.schedules] == ["schedule_1", "schedule_2", "schedule_3"]
    assert result.explanation == () and result.blocking_pins == ()


@needs_ortools
def test_asking_for_exactly_as_many_as_exist_is_found_and_one_extra_shows_there_are_no_more():
    data = example("tiny_feasible.csv")
    assert find_schedules(data, gap=1, count=8).status is FinderStatus.FOUND
    more = find_schedules(data, gap=1, count=9)
    assert more.status is FinderStatus.EXHAUSTED and len(more.schedules) == 8


@needs_ortools
def test_the_first_schedules_are_the_start_of_a_longer_list():
    data = example("tiny_feasible.csv")
    short = slot_lists(find_schedules(data, gap=1, breaks=1, count=5))
    long = slot_lists(find_schedules(data, gap=1, breaks=1, count=50))
    assert long[:5] == short


@needs_ortools
def test_hitting_the_time_limit_is_stopped_and_never_says_none_exist():
    # 6 performances and 8 breaks have about two million valid orders: far too many for 0.05 s
    result = find_schedules(
        example("tiny_no_conflicts.csv"), gap=1, breaks=8, count=10**7, time_limit=0.05
    )
    assert result.status is FinderStatus.STOPPED
    assert result.schedules  # what was found is still returned
    assert "time limit" in messages(result)[0] and "does not show" in messages(result)[0]
    assert result.explanation[0].severity is Severity.WARNING


@needs_ortools
def test_every_schedule_passes_the_schedule_checker_on_a_realistic_show():
    data = example("dense_overlap.csv")
    result = find_schedules(data, gap=2, breaks=4, count=3)
    assert result.status is FinderStatus.FOUND and len(result.schedules) == 3
    assert all(check_schedule(data, s, 2).valid for s in result.schedules)
    assert all(s.num_slots == 24 and s.num_breaks == 4 for s in result.schedules)


@needs_ortools
def test_the_solver_proves_none_exist_on_a_twenty_performance_show():
    # The pre-checks pass here (the busiest performer needs 17 of 20 slots); only the search knows.
    result = find_schedules(example("one_busy_performer.csv"), gap=1, breaks=0, count=1)
    assert result.status is FinderStatus.EXHAUSTED and result.schedules == ()
    assert messages(result) == [
        "No schedule exists with a gap of 1 and 0 breaks. Try more breaks or a smaller gap."
    ]


# ---------------------------------------------------------------- pins


@needs_ortools
def test_pinned_items_are_kept_and_the_count_matches_brute_force():
    data = example("tiny_feasible.csv")
    pins = Pins(slots={1: "bollywood (open)", 7: BREAK})
    result = find_schedules(data, gap=1, breaks=1, pins=pins, count=10**6)
    expected = {s for s in brute_force(data, 1, 1) if s[0] == "bollywood (open)" and s[6] == BREAK}
    assert expected  # the case is worth testing
    assert result.status is FinderStatus.EXHAUSTED
    assert set(slot_lists(result)) == expected
    assert all(s.slots[0] == "bollywood (open)" and s.slots[6] == BREAK for s in result.schedules)


@needs_ortools
def test_a_pinned_break_counts_towards_the_number_of_breaks():
    result = find_schedules(
        example("tiny_feasible.csv"), gap=1, breaks=1, pins=Pins(slots={3: BREAK}), count=1000
    )
    assert result.schedules
    assert all(s.num_breaks == 1 and s.slots[2] == BREAK for s in result.schedules)


@needs_ortools
def test_pinning_every_slot_of_a_valid_schedule_gives_exactly_that_schedule():
    data = example("tiny_feasible.csv")
    (valid,) = load_schedules(EXAMPLES / "tiny_feasible_schedule_valid.csv").schedules
    pins = Pins(slots={position: slot for position, slot in enumerate(valid.slots, 1)})
    result = find_schedules(data, gap=1, pins=pins, count=10)
    assert result.status is FinderStatus.EXHAUSTED
    assert slot_lists(result) == [valid.slots]


def test_pinning_the_invalid_example_is_refused_with_the_clash_named():
    data = example("tiny_feasible.csv")
    (invalid,) = load_schedules(EXAMPLES / "tiny_feasible_schedule_invalid.csv").schedules
    pins = Pins(slots={position: slot for position, slot in enumerate(invalid.slots, 1)})
    result = find_schedules(data, gap=1, pins=pins)
    assert result.status is FinderStatus.EXHAUSTED and result.schedules == ()
    (text,) = messages(result)
    assert "slots 3 and 4" in text and "Person 0006" in text
    assert "at least 1 slot between them but have 0" in text


@needs_ortools
def test_pins_that_cannot_all_be_kept_are_named_without_blaming_the_innocent_one():
    pins = Pins(slots={1: "x1", 3: "a", 4: "b"})
    result = find_schedules(SIX, gap=1, breaks=1, pins=pins, count=1)
    assert result.status is FinderStatus.EXHAUSTED and result.schedules == ()
    assert {3, 4} <= set(result.blocking_pins)
    assert "slot 3 (A)" in messages(result)[0] and "slot 4 (B)" in messages(result)[0]
    assert "cannot all be kept" in messages(result)[0]


@needs_ortools
def test_without_the_blocking_pins_a_schedule_exists():
    pins = Pins(slots={1: "x1", 3: "a", 4: "b"})
    blocking = find_schedules(SIX, gap=1, breaks=1, pins=pins, count=1).blocking_pins
    kept = Pins(slots={p: item for p, item in pins.slots.items() if p != blocking[0]})
    assert find_schedules(SIX, gap=1, breaks=1, pins=kept, count=1).status is FinderStatus.FOUND


@needs_ortools
def test_when_no_schedule_exists_even_without_the_pins_the_message_says_so():
    result = find_schedules(
        example("tiny_needs_breaks.csv"), gap=1, breaks=1, pins=Pins(slots={1: "jazz (open)"})
    )
    assert result.status is FinderStatus.EXHAUSTED
    assert result.blocking_pins == ()
    assert "even without the pins" in messages(result)[0]


# ---------------------------------------------------------------- pre-checks (no search needed)


def test_a_performer_who_needs_more_slots_than_exist_is_named():
    result = find_schedules(example("tiny_needs_breaks.csv"), gap=1, breaks=0)
    assert result.status is FinderStatus.EXHAUSTED and result.schedules == ()
    assert messages(result) == [
        (
            "Person 0001 is in 3 performances; with a gap of 1 that needs at least 5 slots, "
            "but the show has 4."
        )
    ]


def test_performers_with_the_same_problem_are_listed_together():
    data = performers({"amy": ["a", "b", "c"], "bo": ["a", "b", "c"], "cy": ["d"]})
    (text,) = messages(find_schedules(data, gap=1, breaks=0))
    assert text.startswith("Amy and Bo are in 3 performances; with a gap of 1 that needs at least 5")


def test_a_group_of_performances_that_all_clash_needs_the_same_slots_as_one_busy_performer():
    # Nobody is in more than two performances, but a, b and c clash in pairs through three people
    data = performers({"p1": ["a", "b"], "p2": ["b", "c"], "p3": ["a", "c"]})
    (text,) = messages(find_schedules(data, gap=1, breaks=0))
    assert text == (
        "3 performances all clash with each other (A, B and C). "
        "With a gap of 1 they need at least 5 slots, but the show has 3."
    )


def test_the_group_is_not_reported_again_when_one_performer_explains_it():
    result = find_schedules(example("tiny_needs_breaks.csv"), gap=1, breaks=0)
    assert len(result.explanation) == 1  # the performer message only


def test_gap_zero_has_no_spacing_problems_to_pre_check():
    data = performers({"amy": ["a", "b", "c"]})
    assert slots_needed(3, 0) == 3
    assert not [
        m for m in messages(find_schedules(data, gap=0, breaks=0)) if "needs" in m or "need" in m
    ]


def test_slots_needed_formula():
    assert [slots_needed(m, 1) for m in (1, 2, 3)] == [1, 3, 5]
    assert slots_needed(6, 2) == 16  # the example in docs/schedule-finder.md


def test_a_pin_outside_the_show_is_reported():
    data = performers({"amy": ["a"], "bo": ["b"]})
    result = find_schedules(data, gap=1, breaks=1, pins=Pins(slots={9: "a", 0: BREAK}))
    assert result.status is FinderStatus.EXHAUSTED
    assert messages(result) == [
        "The pin at slot 0 (a break) is outside the show: there are 3 slots (2 performances and 1 break).",
        "The pin at slot 9 (A) is outside the show: there are 3 slots (2 performances and 1 break).",
    ]


def test_a_pinned_name_that_is_not_in_the_performer_file_is_reported_with_a_hint():
    data = performers({"amy": ["tap (foundations)"], "bo": ["jazz"]})
    pins = Pins(
        slots={1: "tap (foundation)", 2: "salsa"},
        display_names={"tap (foundation)": "Tap (Foundation)", "salsa": "Salsa"},
    )
    texts = messages(find_schedules(data, gap=1, pins=pins))
    assert texts == [
        (
            'The pin at slot 1 names "Tap (Foundation)", which is not in the performer file. '
            'Did you mean "Tap (Foundations)"?'
        ),
        'The pin at slot 2 names "Salsa", which is not in the performer file.',
    ]


def test_more_pinned_breaks_than_breaks_is_reported():
    data = performers({"amy": ["a"], "bo": ["b"]})
    pins = Pins(slots={1: BREAK, 2: BREAK})
    (text,) = messages(find_schedules(data, gap=1, breaks=1, pins=pins))
    assert text == (
        "2 slots are pinned as breaks, but the show has only 1 break. "
        "Raise the number of breaks or remove a pinned break."
    )


def test_a_performance_pinned_to_two_slots_is_reported():
    data = performers({"amy": ["a"], "bo": ["b"]})
    (text,) = messages(find_schedules(data, gap=1, pins=Pins(slots={1: "a", 2: "a"})))
    assert text == '"A" is pinned to more than one slot (1, 2).'


def test_every_failing_pre_check_is_reported_together():
    data = performers({"amy": ["a", "b", "c"], "bo": ["d"]})
    result = find_schedules(data, gap=1, breaks=0, pins=Pins(slots={9: "d", 1: "a", 2: "b"}))
    texts = messages(result)
    assert any("outside the show" in t for t in texts)
    assert any("Amy is in 3 performances" in t for t in texts)
    assert any("The pins at slots 1 and 2" in t for t in texts)
    assert all(issue.severity is Severity.ERROR for issue in result.explanation)


def test_pre_checks_work_and_no_search_is_started_when_ortools_is_missing(monkeypatch):
    def missing(name):
        raise ImportError(name)

    monkeypatch.setattr(solver, "importlib", types.SimpleNamespace(import_module=missing))
    result = find_schedules(example("tiny_needs_breaks.csv"), gap=1, breaks=0)
    assert result.status is FinderStatus.EXHAUSTED
    with pytest.raises(SolverNotInstalled, match=r'pip install -e ".\[finder\]"'):
        find_schedules(example("tiny_feasible.csv"), gap=1)
    with pytest.raises(SolverNotInstalled):
        solver_version()


# ---------------------------------------------------------------- seed and repeatability


@needs_ortools
def test_the_same_seed_gives_the_same_list_and_different_seeds_start_it_in_different_places():
    data = example("typical_20_performances.csv")
    lists = {
        seed: slot_lists(find_schedules(data, gap=1, count=5, seed=seed))
        for seed in (None, 1, 2, 3)
    }
    assert lists[1] == slot_lists(find_schedules(data, gap=1, count=5, seed=1))
    assert lists[None] == slot_lists(find_schedules(data, gap=1, count=5))
    assert len({tuple(v) for v in lists.values()}) >= 3  # the experiment gave 4 different lists


@needs_ortools
def test_different_seeds_list_the_same_schedules_in_a_different_order():
    data = example("tiny_feasible.csv")
    lists = [
        slot_lists(find_schedules(data, gap=1, breaks=1, count=10**6, seed=seed))
        for seed in (None, 1, 2)
    ]
    assert all(len(v) == 152 for v in lists)
    assert len({frozenset(v) for v in lists}) == 1
    assert len({tuple(v) for v in lists}) > 1


@needs_ortools
def test_the_list_is_the_same_in_separate_runs_whatever_the_hash_randomisation():
    # Python orders strings differently in every process unless told otherwise. The list must not.
    code = (
        "from performance_scheduling.io import load_performers\n"
        "from performance_scheduling.solver import find_schedules\n"
        f"d = load_performers(r'{EXAMPLES / 'typical_20_performances.csv'}').data\n"
        "for seed in (None, 7):\n"
        "    print([s.slots for s in find_schedules(d, gap=1, count=3, seed=seed).schedules])\n"
    )
    outputs = set()
    for hash_seed in ("0", "1", "4242"):
        env = {**os.environ, "PYTHONHASHSEED": hash_seed}
        done = subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True, env=env, check=True
        )
        outputs.add(done.stdout)
    assert len(outputs) == 1


# ---------------------------------------------------------------- safety


@needs_ortools
def test_a_schedule_that_fails_the_cross_check_stops_the_run(monkeypatch):
    monkeypatch.setattr(solver, "check_schedule", lambda *a, **k: types.SimpleNamespace(valid=False))
    with pytest.raises(RuntimeError, match="failed the schedule checker"):
        find_schedules(example("tiny_feasible.csv"), gap=1, count=1)


@needs_ortools
def test_the_cross_check_catches_a_model_that_ignores_the_pins(monkeypatch):
    real = solver._build_model

    def forgetful(cp_model, order, pairs, gap, total, usable_pins, pins_as_assumptions):
        return real(cp_model, order, pairs, gap, total, {}, pins_as_assumptions)

    monkeypatch.setattr(solver, "_build_model", forgetful)
    with pytest.raises(RuntimeError, match="does not keep the pins"):
        find_schedules(
            example("tiny_feasible.csv"), gap=1, pins=Pins(slots={1: "bollywood (open)"}), count=8
        )


@needs_ortools
def test_the_cross_check_catches_a_repeated_schedule(monkeypatch):
    real = solver._list_schedules

    def repeating(*args, **kwargs):
        found, status = real(*args, **kwargs)
        return found + found, status

    monkeypatch.setattr(solver, "_list_schedules", repeating)
    with pytest.raises(RuntimeError, match="repeats an earlier schedule"):
        find_schedules(example("tiny_feasible.csv"), gap=1, count=1)


@needs_ortools
def test_the_cross_check_catches_the_wrong_number_of_breaks(monkeypatch):
    real = solver._list_schedules

    def extra_break(*args, **kwargs):
        found, status = real(*args, **kwargs)
        return [slots + (BREAK,) for slots in found], status

    monkeypatch.setattr(solver, "_list_schedules", extra_break)
    with pytest.raises(RuntimeError, match="wrong number of breaks"):
        find_schedules(example("tiny_feasible.csv"), gap=1, count=1)


@pytest.mark.parametrize(
    "bad",
    [{"gap": -1}, {"breaks": -1}, {"count": 0}, {"time_limit": 0}, {"time_limit": -5}],
)
def test_settings_the_program_should_never_pass_are_refused(bad):
    with pytest.raises(ValueError):
        find_schedules(example("tiny_feasible.csv"), **bad)


def test_a_show_with_no_performances_is_refused():
    empty = PerformerData(performances_by_performer={}, performer_names={}, performance_names={})
    with pytest.raises(ValueError, match="no performances"):
        find_schedules(empty)


@needs_ortools
def test_the_solver_version_is_reported():
    import ortools

    assert solver_version() == ortools.__version__
