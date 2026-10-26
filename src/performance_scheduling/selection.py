"""Reading a typed choice of numbers such as "1,4,9", "1-3, 7" or "all".

The schedule finder numbers its schedules 1, 2, 3, ... and the organiser chooses which
ones to output by typing a selection (decision D17). The command line option and the
interface both use this one reader, so the rules are the same everywhere.

What is accepted
    1,4,9          single numbers
    1-5            a range (both ends included)
    1-3, 7, 20-22  any mix, with or without spaces
    all            everything (the caller applies the run's limit)

Order does not matter and repeats are ignored: "9,1,4,4" is the same as "1,4,9".
A long dash (as produced by word processors) is read as a hyphen.

This file only reads text. It does not know how many schedules exist; the caller passes
that in if it wants numbers above it refused.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

from performance_scheduling.models import (
    FinderResult,
    FinderStatus,
    InputError,
    Issue,
    Schedule,
    Severity,
)

_EXAMPLES = "Use numbers, ranges and commas, for example 1,4,9 or 1-3, 7 or the word all."
_NUMBER = re.compile(r"[0-9]+")
_RANGE = re.compile(r"([0-9]+)\s*-\s*([0-9]+)")
_LONG_DASHES = str.maketrans({"\u2013": "-", "\u2014": "-", "\u2212": "-"})


@dataclass(frozen=True)
class Selection:
    """A set of chosen numbers, or "everything".

    The numbers are stored as ranges (start, end), both included, in ascending order,
    with overlapping or touching ranges already joined. "1-1000000" is therefore tiny
    to store and quick to test.
    """

    ranges: tuple[tuple[int, int], ...] = ()
    select_all: bool = False

    def __contains__(self, number: int) -> bool:
        if self.select_all:
            return True
        return any(start <= number <= end for start, end in self.ranges)

    @property
    def count(self) -> int | None:
        """How many numbers are chosen (None for "all", which has no fixed size)."""
        if self.select_all:
            return None
        return sum(end - start + 1 for start, end in self.ranges)

    @property
    def highest(self) -> int | None:
        """The largest number chosen (None for "all" or an empty choice)."""
        if self.select_all or not self.ranges:
            return None
        return self.ranges[-1][1]

    def numbers(self) -> tuple[int, ...]:
        """Every chosen number, in ascending order."""
        if self.select_all:
            raise ValueError('"all" has no fixed list of numbers')
        return tuple(n for start, end in self.ranges for n in range(start, end + 1))

    def __str__(self) -> str:
        """The choice written in the shortest form, e.g. "1-3,7" or "all"."""
        if self.select_all:
            return "all"
        return ",".join(str(s) if s == e else f"{s}-{e}" for s, e in self.ranges)


def _error(message: str, *, with_examples: bool = False) -> InputError:
    text = f"{message} {_EXAMPLES}" if with_examples else message
    return InputError([Issue(Severity.ERROR, text)])


def _join_overlaps(intervals: list[tuple[int, int]]) -> tuple[tuple[int, int], ...]:
    """Sort ranges and join any that overlap or touch, e.g. 1-3 and 4-6 become 1-6."""
    joined: list[tuple[int, int]] = []
    for start, end in sorted(intervals):
        if joined and start <= joined[-1][1] + 1:
            joined[-1] = (joined[-1][0], max(joined[-1][1], end))
        else:
            joined.append((start, end))
    return tuple(joined)


def parse_selection(
    text: str, *, maximum: int | None = None, max_count: int | None = None
) -> Selection:
    """Read a typed choice. Raises InputError with a plain-language message if it is bad.

    maximum:   the highest number that exists; a higher number is refused
    max_count: the most numbers one choice may contain; a bigger choice is refused
               (the caller's limit, e.g. 100 schedules per run). "all" is not checked
               here because its size is not known yet.
    """
    cleaned = text.translate(_LONG_DASHES).strip()
    if not cleaned:
        raise _error("Nothing was chosen.", with_examples=True)
    if cleaned.casefold() == "all":
        return Selection(select_all=True)

    intervals: list[tuple[int, int]] = []
    for part in (piece.strip() for piece in cleaned.split(",")):
        if not part:
            raise _error(
                "There is an empty item (two commas in a row, or a comma at the start or end).",
                with_examples=True,
            )
        if part.casefold() == "all":
            raise _error('"all" cannot be combined with numbers. Use it on its own.')
        if _NUMBER.fullmatch(part):
            start = end = int(part)
        elif range_match := _RANGE.fullmatch(part):
            start, end = int(range_match[1]), int(range_match[2])
        else:
            raise _error(f'"{part}" is not a number or a range.', with_examples=True)

        if start < 1:
            raise _error(f'Numbers start at 1 (found "{part}").')
        if end < start:
            raise _error(f'The range "{part}" goes backwards. Write it as {end}-{start}.')
        if maximum is not None and end > maximum:
            raise _error(f'"{part}" is too high: the highest available number is {maximum}.')
        intervals.append((start, end))

    selection = Selection(ranges=_join_overlaps(intervals))
    if max_count is not None and selection.count > max_count:
        raise _error(
            f"That chooses {selection.count} items but the most allowed at once is {max_count}. "
            "Choose fewer, or raise the limit."
        )
    return selection


# ---------------------------------------------------------------- choosing from the finder's list


def selection_from_numbers(numbers: Iterable[int]) -> Selection:
    """A Selection of exactly these numbers, written as joined ranges (empty if none)."""
    return Selection(ranges=_join_overlaps([(n, n) for n in sorted(set(numbers))]))


def schedules_to_request(selection: Selection, limit: int) -> int:
    """How many schedules to ask the finder for: up to the highest one chosen, plus one more.

    The extra one tells the caller whether more schedules exist beyond the choice. With
    "all" the highest number is the limit.
    """
    highest = limit if selection.select_all else selection.highest
    assert highest is not None  # a parsed choice that is not "all" always has numbers
    return highest + 1


def next_pick(selection: Selection, limit: int, last_number: int) -> str:
    """The pick that asks for the next batch (decision D44), written like "6-10" or "6".

    The next batch is as big as this one: as many schedules as were chosen, or `limit` for
    "all". It starts just after `last_number`, the highest number written so far. The text
    can be given straight to parse_selection or to the command's --pick.
    """
    size = limit if selection.select_all else selection.count or 1
    return f"{last_number + 1}-{last_number + size}" if size > 1 else str(last_number + 1)


@dataclass(frozen=True)
class Picked:
    """What a choice picks out of the finder's list (see apply_selection)."""

    schedules: tuple[Schedule, ...]  # the ones to write, in ascending order of number
    numbers: Selection               # their numbers, as joined ranges
    missing: Selection               # numbers asked for that the finder's list does not reach
    more_exist: bool | None          # True: more after these; False: this is all; None: unknown
    total: int | None                # the exact number of schedules, known only if the search finished


def apply_selection(result: FinderResult, selection: Selection, limit: int) -> Picked:
    """Pick the chosen schedules out of a finder result (decisions D17, D19, D33).

    The result holds the first schedules of the finder's list, numbered from 1. With "all",
    the first `limit` are chosen. Numbers the list does not reach are reported as missing:
    if the search finished they do not exist, and if it was stopped nobody knows.
    `more_exist` is True when the finder produced the extra schedule asked for (see
    schedules_to_request), False when the search finished, and None when it was stopped.
    """
    produced = len(result.schedules)
    if selection.select_all:
        wanted: tuple[tuple[int, int], ...] = ((1, limit),)
    else:
        wanted = selection.ranges
    numbers = [n for start, end in wanted for n in range(start, min(end, produced) + 1)]
    missing = (
        []
        if selection.select_all
        else [(max(start, produced + 1), end) for start, end in wanted if end > produced]
    )
    more_exist = {
        FinderStatus.FOUND: True,
        FinderStatus.EXHAUSTED: False,
        FinderStatus.STOPPED: None,
    }[result.status]
    return Picked(
        schedules=tuple(result.schedules[n - 1] for n in numbers),
        numbers=selection_from_numbers(numbers),
        missing=Selection(ranges=tuple(missing)),
        more_exist=more_exist,
        total=produced if result.status is FinderStatus.EXHAUSTED else None,
    )
