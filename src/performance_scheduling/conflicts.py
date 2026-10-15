"""Works out which performances clash, and which performers cause each clash.

Two performances conflict when at least one performer is in both. The schedule checker
uses the "who" (to name the performer in a message) and the schedule finder uses the
"which performances" (for fast tests of whether a placement is allowed). Both views are
built here, once, from the cleaned performer data.

Nothing in this file reads files or prints. It takes a PerformerData in and returns a
ConflictMap (see models.py).
"""

from __future__ import annotations

from itertools import combinations

from performance_scheduling.models import ConflictMap, PerformerData


def build_conflict_map(data: PerformerData) -> ConflictMap:
    """Build the conflict map for a show.

    The method goes performer by performer: everyone a performer is in clashes with
    everyone else that performer is in, so each pair of their performances is recorded
    along with that performer's key. A performer in a single performance adds nothing.
    This also gives the shared performers for free, which a pair-by-pair comparison of
    performances would have to work out separately.

    Every performance in `data` appears in `neighbours`, with an empty set if it
    clashes with nothing, so later code never needs to handle a missing entry.
    """
    shared: dict[frozenset[str], set[str]] = {}
    for performer, performances in data.performances_by_performer.items():
        for first, second in combinations(sorted(performances), 2):
            shared.setdefault(frozenset((first, second)), set()).add(performer)

    neighbours: dict[str, set[str]] = {key: set() for key in data.performance_keys}
    for pair in shared:
        first, second = tuple(pair)
        neighbours[first].add(second)
        neighbours[second].add(first)

    return ConflictMap(
        shared={pair: frozenset(performers) for pair, performers in shared.items()},
        neighbours={key: frozenset(others) for key, others in neighbours.items()},
    )
