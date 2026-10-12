"""The project's vocabulary: simple containers for the data every other file works with.

This file only describes *what things are*. It never reads files, never prints and
contains no scheduling logic. Other files fill these containers (io.py, conflicts.py)
or use them (validator.py, solver.py).

Two conventions run through the whole project:

* Keys and display names. Raw text such as "Bollywood (Open) " and "bollywood (open)"
  must count as the same performance. So the loader makes a cleaned, lower-case *key*
  for matching and remembers the first spelling it saw as the *display name* for
  messages and output. All logic uses keys. Display names appear only when talking
  to the organiser.
* Positions are numbered from 1, because organisers count from 1.

Most containers are "frozen" dataclasses. A dataclass is a short way to write a class
that is just a bundle of named fields. Frozen means a field cannot be reassigned after
creation, which prevents one part of the program silently changing data that another
part is using.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum

# The text that marks a break in a schedule. Performance keys are always lower case,
# so a performance key can never equal this. The loader also rejects any performance
# called "break" (in any capitalisation) so the two can never be confused in a file.
BREAK = "BREAK"


class Severity(Enum):
    """How serious an Issue is."""

    ERROR = "error"      # the input cannot be used; processing stops
    WARNING = "warning"  # worth telling the organiser, but processing continues


@dataclass(frozen=True)
class Issue:
    """One problem or warning found while reading or checking input."""

    severity: Severity
    message: str
    # Row number as the organiser sees it in a spreadsheet (the header row is row 1).
    # None when the issue is about the file as a whole.
    row: int | None = None

    def __str__(self) -> str:
        where = f"row {self.row}: " if self.row is not None else ""
        return f"{self.severity.value.upper()}: {where}{self.message}"


class InputError(Exception):
    """Raised when input is unusable. Carries every Issue found, not just the first."""

    def __init__(self, issues: Sequence[Issue]) -> None:
        self.issues: tuple[Issue, ...] = tuple(issues)
        super().__init__("\n".join(str(issue) for issue in self.issues))


@dataclass(frozen=True)
class PerformerData:
    """The cleaned contents of the performer CSV.

    Everything is stored by key (see the module notes). The three mappings are meant
    to be treated as read-only.
    """

    # performer key -> keys of the performances that performer is in
    performances_by_performer: Mapping[str, frozenset[str]]
    # performer key -> display name (the first spelling seen)
    performer_names: Mapping[str, str]
    # performance key -> display name (the first spelling seen)
    performance_names: Mapping[str, str]

    @property
    def performance_keys(self) -> tuple[str, ...]:
        """Every performance key in a fixed (alphabetical) order."""
        return tuple(sorted(self.performance_names))

    @property
    def performers_by_performance(self) -> dict[str, frozenset[str]]:
        """The same information the other way round: performance key -> performer keys."""
        result: dict[str, set[str]] = {key: set() for key in self.performance_names}
        for performer, performances in self.performances_by_performer.items():
            for performance in performances:
                result[performance].add(performer)
        return {key: frozenset(members) for key, members in result.items()}


@dataclass(frozen=True)
class ConflictMap:
    """Which performances clash, and which performers cause each clash.

    Two performances conflict when at least one performer is in both. The map is
    filled in by conflicts.py. It holds two views of the same facts:

    * shared:     for each conflicting pair, the performers they have in common
                  (used to name the performer in error messages)
    * neighbours: for each performance, the set of performances it conflicts with
                  (used for fast "is this placement allowed?" tests). Every
                  performance appears, with an empty set if it conflicts with nothing.
    """

    shared: Mapping[frozenset[str], frozenset[str]]
    neighbours: Mapping[str, frozenset[str]]

    def conflict(self, a: str, b: str) -> bool:
        """True if performances a and b share at least one performer."""
        return b in self.neighbours.get(a, frozenset())

    def shared_performers(self, a: str, b: str) -> frozenset[str]:
        """The performers who are in both a and b (empty if they do not conflict)."""
        return self.shared.get(frozenset((a, b)), frozenset())


@dataclass(frozen=True)
class Schedule:
    """One running order: slot 1 is the first item, and so on."""

    name: str                # e.g. "schedule_4"
    slots: tuple[str, ...]   # each item is a performance key, or BREAK

    @property
    def num_slots(self) -> int:
        return len(self.slots)

    @property
    def num_breaks(self) -> int:
        return sum(1 for slot in self.slots if slot == BREAK)

    def positions(self) -> dict[str, int]:
        """Performance key -> position (numbered from 1). Breaks are left out.

        If a performance wrongly appears twice, the later position wins here. The
        validator looks for repeats in `slots` itself before it uses this.
        """
        return {
            slot: position
            for position, slot in enumerate(self.slots, start=1)
            if slot != BREAK
        }
