"""Tests for conflicts.py."""

from itertools import combinations
from pathlib import Path

from performance_scheduling.conflicts import build_conflict_map
from performance_scheduling.io import load_performers
from performance_scheduling.models import PerformerData

EXAMPLES = Path(__file__).resolve().parent.parent / "data" / "examples"


def data_from(members: dict[str, list[str]]) -> PerformerData:
    """Build PerformerData from {performer: [performances]}; names are the keys themselves."""
    performances = {p for ps in members.values() for p in ps}
    return PerformerData(
        performances_by_performer={who: frozenset(ps) for who, ps in members.items()},
        performer_names={who: who for who in members},
        performance_names={p: p for p in performances},
    )


def test_two_performances_with_a_shared_performer_conflict():
    conflicts = build_conflict_map(data_from({"sam": ["jazz", "tap"], "kim": ["ballet"]}))
    assert conflicts.conflict("jazz", "tap")
    assert conflicts.conflict("tap", "jazz")
    assert conflicts.shared_performers("jazz", "tap") == frozenset({"sam"})


def test_performances_with_no_shared_performer_do_not_conflict():
    conflicts = build_conflict_map(data_from({"sam": ["jazz", "tap"], "kim": ["ballet"]}))
    assert not conflicts.conflict("jazz", "ballet")
    assert conflicts.shared_performers("jazz", "ballet") == frozenset()


def test_every_performance_appears_even_with_no_conflicts():
    conflicts = build_conflict_map(data_from({"sam": ["jazz", "tap"], "kim": ["ballet"]}))
    assert conflicts.neighbours["ballet"] == frozenset()
    assert set(conflicts.neighbours) == {"jazz", "tap", "ballet"}


def test_all_the_performers_who_cause_a_conflict_are_listed():
    members = {"sam": ["jazz", "tap"], "alex": ["tap", "jazz"], "kim": ["jazz"]}
    conflicts = build_conflict_map(data_from(members))
    assert conflicts.shared_performers("jazz", "tap") == frozenset({"sam", "alex"})


def test_a_performer_in_three_performances_conflicts_all_three_pairs():
    conflicts = build_conflict_map(data_from({"sam": ["a", "b", "c"]}))
    assert conflicts.neighbours == {
        "a": frozenset({"b", "c"}),
        "b": frozenset({"a", "c"}),
        "c": frozenset({"a", "b"}),
    }
    assert len(conflicts.shared) == 3


def test_performers_in_one_performance_each_create_no_conflicts():
    conflicts = build_conflict_map(data_from({"sam": ["jazz"], "kim": ["tap"]}))
    assert conflicts.shared == {}
    assert conflicts.neighbours == {"jazz": frozenset(), "tap": frozenset()}


# ---------------------------------------------------------------- the example datasets


def test_tiny_feasible_has_the_eight_expected_conflicts():
    load = load_performers(EXAMPLES / "tiny_feasible.csv")
    conflicts = build_conflict_map(load.data)
    assert len(conflicts.shared) == 8
    # Person 0011 is in Bollywood (Open) and Kpop Girls (Intermediate)
    pair = conflicts.shared_performers("bollywood (open)", "kpop girls (intermediate)")
    assert pair == frozenset({"person 0011"})
    assert conflicts.neighbours["bollywood (open)"] == frozenset(
        {"jazz (open)", "tap (foundations)", "kpop girls (intermediate)"}
    )


def test_tiny_needs_breaks_has_five_conflicts():
    conflicts = build_conflict_map(load_performers(EXAMPLES / "tiny_needs_breaks.csv").data)
    assert len(conflicts.shared) == 5
    # The performer in three performances makes all three of them clash with each other
    assert conflicts.shared_performers("bollywood (open)", "jazz (open)") == frozenset({"person 0001"})


def test_tiny_no_conflicts_has_none():
    conflicts = build_conflict_map(load_performers(EXAMPLES / "tiny_no_conflicts.csv").data)
    assert conflicts.shared == {}
    assert all(not others for others in conflicts.neighbours.values())


def test_realistic_example_matches_a_slow_independent_calculation():
    # Cross-check against the most obvious method: compare every pair of performances
    # and see whether any performer is in both.
    data = load_performers(EXAMPLES / "typical_20_performances.csv").data
    conflicts = build_conflict_map(data)
    members = data.performers_by_performance
    expected = {
        frozenset(pair): members[pair[0]] & members[pair[1]]
        for pair in combinations(data.performance_keys, 2)
        if members[pair[0]] & members[pair[1]]
    }
    assert dict(conflicts.shared) == expected
