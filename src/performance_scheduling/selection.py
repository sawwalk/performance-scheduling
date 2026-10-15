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
from dataclasses import dataclass

from performance_scheduling.models import InputError, Issue, Severity

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
