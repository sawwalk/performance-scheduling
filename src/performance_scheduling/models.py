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
from dataclasses import dataclass, field
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
class PerformerLoad:
    """What the performer loader returns: the cleaned data plus how loading went.

    Errors never appear here: they stop loading by raising InputError. Only
    warnings are carried, because the data is usable.
    """

    data: PerformerData
    warnings: tuple[Issue, ...]
    rows_read: int  # data rows in the file, not counting the header or completely blank rows
    rows_used: int  # distinct performer-and-performance pairs kept after cleaning


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
    # Performance key -> the spelling used in the file the schedule came from. Lets the
    # checker name a performance that is not in the performer data (a typo, say) the way
    # the organiser wrote it. Left empty for schedules the program creates. It is ignored
    # when two schedules are compared.
    display_names: Mapping[str, str] = field(default_factory=dict, compare=False)

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


@dataclass(frozen=True)
class ScheduleLoad:
    """What the schedule reader returns: every schedule in the file, plus any warnings.

    The reader checks the *file* (columns, positions) but not the *contents*: unknown,
    missing or repeated performances are loaded as they are, and the schedule checker
    reports them. Errors in the file itself stop reading by raising InputError.
    """

    schedules: tuple[Schedule, ...]
    warnings: tuple[Issue, ...]


@dataclass(frozen=True)
class Pins:
    """Items the organiser has fixed to chosen slots (the schedule finder's fixed positions).

    `slots` maps a position (numbered from 1) to a performance key or BREAK. The mapping
    is meant to be read-only. Nothing here checks the pins against a show: whether a name
    exists or a position is within the show is for the finder's pre-checks to say.
    """

    slots: Mapping[int, str]
    # Performance key -> the spelling used in the file the pins came from, so a name that
    # is not in the performer data can be shown the way the organiser wrote it. Ignored
    # when two sets of pins are compared.
    display_names: Mapping[str, str] = field(default_factory=dict, compare=False)

    @property
    def break_positions(self) -> tuple[int, ...]:
        """The positions pinned as breaks, in ascending order."""
        return tuple(sorted(position for position, item in self.slots.items() if item == BREAK))

    @property
    def performance_positions(self) -> dict[str, int]:
        """Pinned performance key -> its position. Breaks are left out."""
        return {item: position for position, item in self.slots.items() if item != BREAK}


@dataclass(frozen=True)
class PinLoad:
    """What the fixed-positions reader returns: the pins plus any warnings.

    The reader checks the *file* (columns, positions, repeats) but not the *contents*
    (decision D36). Errors in the file itself stop reading by raising InputError.
    """

    pins: Pins
    warnings: tuple[Issue, ...]


@dataclass(frozen=True)
class Violation:
    """One broken spacing rule: a performer who has too little rest between two performances.

    Performers and performances are keys; look up display names in PerformerData.
    The two performances are neighbours in that performer's own running order.
    """

    performer: str
    performance_a: str   # the earlier of the two
    position_a: int
    performance_b: str   # the later of the two
    position_b: int
    slots_between: int   # slots strictly between the two (breaks count as slots)
    required: int        # the gap k that was asked for


@dataclass(frozen=True)
class ScheduleCheck:
    """The result of checking one schedule.

    A schedule is valid when it has no structural problems and no violations. If there
    are structural problems (a missing, unknown or repeated performance) the spacing
    check is not run, so `violations` is empty and `smallest_gap` is None.
    """

    schedule_name: str
    gap_required: int                # the k that was checked
    num_slots: int
    num_breaks: int
    problems: tuple[Issue, ...]      # structural problems; any makes the schedule invalid
    violations: tuple[Violation, ...]
    # The fewest slots between two performances of the same performer anywhere in the
    # schedule. The schedule satisfies every gap up to this number. None if the spacing
    # was not checked, or if nobody is in more than one performance (any gap is satisfied).
    smallest_gap: int | None

    @property
    def valid(self) -> bool:
        return not self.problems and not self.violations


class FinderStatus(Enum):
    """How a run of the schedule finder ended. The tool always says which."""

    FOUND = "found"          # the number of schedules asked for were produced
    EXHAUSTED = "exhausted"  # the search finished (or the request is impossible): no more exist
    STOPPED = "stopped"      # the time limit was reached; this proves nothing either way


@dataclass(frozen=True)
class FinderResult:
    """What the schedule finder returns.

    `schedules` are the first schedules in the finder's list, named schedule_1,
    schedule_2, ... by their place in that list (decision D20). Whatever the status, any
    schedules found are included.

    `explanation` is plain language for the organiser. It is filled in when no schedule
    could be found: why none exist (EXHAUSTED) or that the time limit was reached (STOPPED).

    `blocking_pins` holds the positions of pins that cannot all be kept at once, when the
    solver could say which (decision D34). The set explains the failure but is not
    guaranteed to be the smallest one.
    """

    status: FinderStatus
    schedules: tuple[Schedule, ...]
    explanation: tuple[Issue, ...] = ()
    blocking_pins: tuple[int, ...] = ()
