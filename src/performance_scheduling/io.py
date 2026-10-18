"""Reading and cleaning input files. This is the only module that touches files.

The performer loader turns the organiser's CSV into a PerformerData (see models.py)
and reports anything odd it noticed along the way. The cleaning rules are described in
docs/input-data.md.

Three kinds of file are read: the performer CSV, schedule files (a proposed running
order, or several side by side) and the fixed-positions file (items pinned to slots).
Schedules can also be written. The performer loader is split in three so each part is
easy to test (the other readers follow the same pattern):

* make_key / clean_text   tidy one piece of text
* parse_performers        works on text already in memory (no files; the UI can use it
                          for an uploaded file)
* load_performers         reads the file, then calls parse_performers
"""

from __future__ import annotations

import csv
import re
import unicodedata
from collections.abc import Mapping, Sequence
from difflib import SequenceMatcher
from io import StringIO  # the standard library's io, not this file
from pathlib import Path

from performance_scheduling.models import (
    BREAK,
    InputError,
    Issue,
    PerformerData,
    PerformerLoad,
    PinLoad,
    Pins,
    Schedule,
    ScheduleLoad,
    Severity,
)

# Column separators we recognise. Excel in some regions saves "CSV" with semicolons,
# and copying a table can produce tabs, so the separator is detected from the header.
_DELIMITERS = (",", ";", "\t")

# How alike two names must be (0 to 1) before we ask the organiser to double-check.
# Chosen so that genuinely different performances such as "Kpop Boys (Intermediate)"
# and "Kpop Girls (Intermediate)" (about 0.86) are not flagged.
_WHOLE_NUMBER = re.compile(r"[0-9]+")

ID_SIMILARITY = 0.90
PERFORMANCE_SIMILARITY = 0.92


# ---------------------------------------------------------------- text cleaning


def clean_text(text: str) -> str:
    """Tidy text for display: standard Unicode form, no stray or repeated spaces.

    The Unicode step turns look-alikes (such as a non-breaking space copied from a
    web page, or an accented letter typed two different ways) into one standard form.
    """
    return " ".join(unicodedata.normalize("NFKC", text).split())


def make_key(text: str) -> str:
    """The cleaned, lower-case form used for all matching (see models.py)."""
    return clean_text(text).casefold()


# ---------------------------------------------------------------- reading files


def read_text(path: str | Path) -> str:
    """Read a text file as UTF-8 (a byte-order mark added by Excel is accepted)."""
    path = Path(path)
    try:
        with open(path, encoding="utf-8-sig", newline="") as handle:
            return handle.read()
    except FileNotFoundError:
        raise InputError([Issue(Severity.ERROR, f"File not found: {path}")]) from None
    except UnicodeDecodeError:
        raise InputError(
            [
                Issue(
                    Severity.ERROR,
                    f"{path.name} could not be read as UTF-8 text. "
                    'In Excel, use "Save As" and choose "CSV UTF-8".',
                )
            ]
        ) from None
    except OSError as problem:
        raise InputError([Issue(Severity.ERROR, f"Could not read {path}: {problem}")]) from None


def _detect_delimiter(text: str) -> str:
    """Pick the separator that appears most often in the first non-blank line."""
    first_line = next((line for line in text.splitlines() if line.strip()), "")
    counts = {delimiter: first_line.count(delimiter) for delimiter in _DELIMITERS}
    best = max(_DELIMITERS, key=lambda delimiter: counts[delimiter])  # ties favour the comma
    return best if counts[best] > 0 else ","


def _resolve_columns(
    header: Sequence[str], id_column: str | None, performance_column: str | None
) -> tuple[int, int, list[Issue]]:
    """Work out which columns hold the performer id and the performance."""
    header = list(header)
    while header and not clean_text(header[-1]):  # Excel sometimes adds empty trailing columns
        header.pop()
    names = [clean_text(cell) for cell in header]
    listing = ", ".join(f'"{name}"' for name in names)

    if (id_column is None) != (performance_column is None):
        raise InputError(
            [Issue(Severity.ERROR, "Give both the performer column and the performance column, or neither.")]
        )

    if id_column is None:
        if len(names) != 2:
            raise InputError(
                [
                    Issue(
                        Severity.ERROR,
                        f"Expected exactly two columns (performer, then performance) but found "
                        f"{len(names)}: {listing}. Say which columns to use.",
                    )
                ]
            )
        return 0, 1, []

    errors: list[Issue] = []
    indexes: list[int] = []
    for wanted in (id_column, performance_column):
        matches = [i for i, name in enumerate(names) if make_key(name) == make_key(wanted or "")]
        if not matches:
            errors.append(Issue(Severity.ERROR, f'Column "{wanted}" not found. Columns in the file: {listing}.'))
        elif len(matches) > 1:
            errors.append(Issue(Severity.ERROR, f'Column "{wanted}" appears more than once in the file.'))
        else:
            indexes.append(matches[0])
    if not errors and indexes[0] == indexes[1]:
        errors.append(Issue(Severity.ERROR, "The performer column and the performance column are the same."))
    if errors:
        raise InputError(errors)

    extras = [name for i, name in enumerate(names) if i not in indexes]
    warnings = []
    if extras:
        ignored = ", ".join(f'"{name}"' for name in extras)
        warnings.append(Issue(Severity.WARNING, f"Ignoring other column(s): {ignored}."))
    return indexes[0], indexes[1], warnings


# ---------------------------------------------------------------- performer loader


def _similar_pairs(names: Mapping[str, str], threshold: float) -> list[tuple[str, str]]:
    """Pairs of different names that look very alike (likely typos).

    Names that differ only in digits ("Person 0001" and "Person 0002") are skipped:
    numbered ids are normally different people, and flagging them would bury the
    organiser in warnings.
    """
    keys = sorted(names)
    letters_only = {key: re.sub(r"\d", "", key) for key in keys}
    pairs = []
    for position, first in enumerate(keys):
        for second in keys[position + 1 :]:
            if letters_only[first] == letters_only[second]:
                continue
            matcher = SequenceMatcher(None, first, second)
            # The two cheap upper bounds avoid the slower exact score for most pairs.
            if matcher.real_quick_ratio() < threshold or matcher.quick_ratio() < threshold:
                continue
            if matcher.ratio() >= threshold:
                pairs.append((names[first], names[second]))
    return pairs


def parse_performers(
    text: str, id_column: str | None = None, performance_column: str | None = None
) -> PerformerLoad:
    """Clean performer CSV text into a PerformerLoad. Raises InputError if unusable.

    Row numbers in messages match what the organiser would see in a spreadsheet
    (the header is row 1). Problems that make the file unusable are collected and
    raised together, so the organiser can fix them all in one go.
    """
    rows = list(csv.reader(text.splitlines(keepends=True), delimiter=_detect_delimiter(text)))
    header_index = next((i for i, row in enumerate(rows) if any(cell.strip() for cell in row)), None)
    if header_index is None:
        raise InputError([Issue(Severity.ERROR, "The file is empty.")])

    id_index, performance_index, issues = _resolve_columns(
        rows[header_index], id_column, performance_column
    )

    performer_names: dict[str, str] = {}
    performance_names: dict[str, str] = {}
    performances_by_performer: dict[str, set[str]] = {}
    seen: set[tuple[str, str]] = set()
    rows_read = 0

    for row_number, row in enumerate(rows[header_index + 1 :], start=header_index + 2):
        if not any(cell.strip() for cell in row):
            continue  # completely blank rows (often at the end of a file) are skipped quietly
        rows_read += 1
        raw_id = row[id_index] if id_index < len(row) else ""
        raw_performance = row[performance_index] if performance_index < len(row) else ""
        performer_key, performance_key = make_key(raw_id), make_key(raw_performance)

        if not performer_key or not performance_key:
            missing = " and ".join(
                label
                for label, key in (("performer", performer_key), ("performance", performance_key))
                if not key
            )
            issues.append(Issue(Severity.WARNING, f"missing {missing}; row dropped", row_number))
            continue
        if performance_key == BREAK.casefold():
            issues.append(
                Issue(
                    Severity.ERROR,
                    f'"{clean_text(raw_performance)}" is a reserved word (it marks a break). '
                    "Rename the performance.",
                    row_number,
                )
            )
            continue
        if (performer_key, performance_key) in seen:
            issues.append(
                Issue(
                    Severity.WARNING,
                    f"duplicate of an earlier row ({clean_text(raw_id)}, "
                    f"{clean_text(raw_performance)}); ignored",
                    row_number,
                )
            )
            continue

        seen.add((performer_key, performance_key))
        performer_names.setdefault(performer_key, clean_text(raw_id))
        performance_names.setdefault(performance_key, clean_text(raw_performance))
        performances_by_performer.setdefault(performer_key, set()).add(performance_key)

    if any(issue.severity is Severity.ERROR for issue in issues):
        raise InputError(issues)
    if not seen:
        raise InputError(issues + [Issue(Severity.ERROR, "No usable rows were found.")])

    for first, second in _similar_pairs(performer_names, ID_SIMILARITY):
        issues.append(
            Issue(
                Severity.WARNING,
                f'Performer ids "{first}" and "{second}" look very similar. If they are the same '
                "person, correct the file so the spelling matches; otherwise ignore this.",
            )
        )
    for first, second in _similar_pairs(performance_names, PERFORMANCE_SIMILARITY):
        issues.append(
            Issue(
                Severity.WARNING,
                f'Performance names "{first}" and "{second}" look very similar. If they are '
                "meant to be one performance, correct the file so the spelling matches.",
            )
        )

    data = PerformerData(
        performances_by_performer={
            key: frozenset(value) for key, value in performances_by_performer.items()
        },
        performer_names=performer_names,
        performance_names=performance_names,
    )
    return PerformerLoad(data=data, warnings=tuple(issues), rows_read=rows_read, rows_used=len(seen))


def load_performers(
    path: str | Path, id_column: str | None = None, performance_column: str | None = None
) -> PerformerLoad:
    """Read a performer CSV file and clean it. Raises InputError if unusable."""
    return parse_performers(read_text(path), id_column, performance_column)


# ---------------------------------------------------------------- schedule reader


def _preview(numbers: Sequence[int], limit: int = 8) -> str:
    """Write numbers as "3, 4, 5" and shorten long lists with "..."."""
    shown = ", ".join(str(n) for n in numbers[:limit])
    return shown + (", ..." if len(numbers) > limit else "")


def parse_schedules(text: str) -> ScheduleLoad:
    """Read schedule CSV text: a `position` column and one column per schedule.

    Raises InputError if the *file* is unusable: no columns to read, unnamed or repeated
    columns, or position numbers that are not exactly 1 to N. It does not judge the
    *contents*: unknown, missing or repeated performances load as they are, and the
    schedule checker reports them (decision D22).

    Details:
    * A column called "position" (any capitalisation) gives each row's slot number; rows
      may be in any order. With no such column, every column is a schedule and row order
      is the running order.
    * BREAK in any capitalisation is a break. An empty cell is also treated as a break,
      with a warning.
    * Names are cleaned the same way as in the performer file, so they match.
    """
    rows = list(csv.reader(text.splitlines(keepends=True), delimiter=_detect_delimiter(text)))
    header_index = next((i for i, row in enumerate(rows) if any(cell.strip() for cell in row)), None)
    if header_index is None:
        raise InputError([Issue(Severity.ERROR, "The file is empty.")])

    header = list(rows[header_index])
    while header and not clean_text(header[-1]):  # Excel sometimes adds empty trailing columns
        header.pop()
    names = [clean_text(cell) for cell in header]

    errors: list[Issue] = []
    unnamed = [i + 1 for i, name in enumerate(names) if not name]
    if unnamed:
        errors.append(
            Issue(Severity.ERROR, f"Column(s) {_preview(unnamed)} in the header row have no name.")
        )
    position_columns = [i for i, name in enumerate(names) if make_key(name) == "position"]
    if len(position_columns) > 1:
        errors.append(Issue(Severity.ERROR, 'More than one column is called "position".'))
    position_column = position_columns[0] if len(position_columns) == 1 else None
    schedule_columns = [i for i in range(len(names)) if i != position_column]
    if not schedule_columns and not errors:
        errors.append(
            Issue(Severity.ERROR, "The file has no schedule columns, only the position column.")
        )
    first_seen: dict[str, str] = {}
    for column in schedule_columns:
        key = make_key(names[column])
        if key and key in first_seen:
            errors.append(
                Issue(
                    Severity.ERROR,
                    f'Two schedule columns are called "{first_seen[key]}" and "{names[column]}". '
                    "Give each schedule its own name.",
                )
            )
        first_seen.setdefault(key, names[column])
    if errors:
        raise InputError(errors)

    issues: list[Issue] = []
    data_rows: list[tuple[int, list[str]]] = []
    for row_number, row in enumerate(rows[header_index + 1 :], start=header_index + 2):
        if not any(cell.strip() for cell in row):
            continue  # completely blank rows are skipped quietly
        if any(cell.strip() for cell in row[len(header) :]):
            issues.append(
                Issue(
                    Severity.WARNING,
                    "has more cells than the header has columns; the extra cells are ignored",
                    row_number,
                )
            )
        data_rows.append((row_number, row))
    if not data_rows:
        raise InputError([Issue(Severity.ERROR, "The file has no schedule rows.")])

    if position_column is not None:
        keyed: list[tuple[int, int, list[str]]] = []
        row_of_position: dict[int, int] = {}
        for row_number, row in data_rows:
            raw = (row[position_column] if position_column < len(row) else "").strip()
            if not _WHOLE_NUMBER.fullmatch(raw):
                what = f'"{raw}" is not a whole number' if raw else "is missing"
                errors.append(Issue(Severity.ERROR, f"position {what}", row_number))
                continue
            position = int(raw)
            if position in row_of_position:
                errors.append(
                    Issue(
                        Severity.ERROR,
                        f"position {position} is repeated (also used in row {row_of_position[position]})",
                        row_number,
                    )
                )
                continue
            row_of_position[position] = row_number
            keyed.append((position, row_number, row))
        if errors:
            raise InputError(errors)
        expected = set(range(1, len(data_rows) + 1))
        if set(row_of_position) != expected:
            missing = sorted(expected - set(row_of_position))
            unexpected = sorted(set(row_of_position) - expected)
            raise InputError(
                [
                    Issue(
                        Severity.ERROR,
                        f"Positions must be numbered 1 to {len(data_rows)} with no gaps "
                        f"(the file has {len(data_rows)} rows). "
                        f"Missing: {_preview(missing) or 'none'}. "
                        f"Not expected: {_preview(unexpected) or 'none'}.",
                    )
                ]
            )
        ordered = [(row_number, row) for _, row_number, row in sorted(keyed)]
    else:
        ordered = data_rows

    schedules = []
    for column in schedule_columns:
        slots: list[str] = []
        spellings: dict[str, str] = {}
        for row_number, row in ordered:
            raw = row[column] if column < len(row) else ""
            key = make_key(raw)
            if not key:
                issues.append(
                    Issue(
                        Severity.WARNING,
                        f'empty slot in "{names[column]}" treated as a break',
                        row_number,
                    )
                )
                slots.append(BREAK)
            elif key == BREAK.casefold():
                slots.append(BREAK)
            else:
                slots.append(key)
                spellings.setdefault(key, clean_text(raw))
        schedules.append(Schedule(name=names[column], slots=tuple(slots), display_names=spellings))

    return ScheduleLoad(schedules=tuple(schedules), warnings=tuple(issues))


def load_schedules(path: str | Path) -> ScheduleLoad:
    """Read a schedule file (one or several schedules side by side)."""
    return parse_schedules(read_text(path))


# ---------------------------------------------------------------- fixed-positions reader


def parse_pins(text: str) -> PinLoad:
    """Read fixed-positions CSV text: a `position` column and an `item` column.

    Raises InputError if the *file* is unusable: no `position` or `item` column, a position
    that is not a whole number from 1, an item that is missing, a position used twice or a
    performance pinned twice. Every such problem is reported together, with row numbers.
    It does not judge the *contents*: a name that is not in the performer file, or a
    position beyond the end of the show, loads as written and the finder's pre-checks
    report it (decision D36, in the same spirit as D22).

    Details:
    * The `position` column may have any capitalisation and sit anywhere. The other column
      is `item`; if the file has exactly two columns, the one that is not `position` is
      used whatever it is called.
    * BREAK in any capitalisation is a break. It may be pinned many times.
    * Names are cleaned the same way as in the performer file, so they match.
    * A file with no pinned rows is allowed (with a warning): nothing is pinned.
    """
    rows = list(csv.reader(text.splitlines(keepends=True), delimiter=_detect_delimiter(text)))
    header_index = next((i for i, row in enumerate(rows) if any(cell.strip() for cell in row)), None)
    if header_index is None:
        raise InputError([Issue(Severity.ERROR, "The file is empty.")])

    header = list(rows[header_index])
    while header and not clean_text(header[-1]):  # Excel sometimes adds empty trailing columns
        header.pop()
    names = [clean_text(cell) for cell in header]
    listing = ", ".join(f'"{name}"' for name in names)

    errors: list[Issue] = []
    position_columns = [i for i, name in enumerate(names) if make_key(name) == "position"]
    item_columns = [i for i, name in enumerate(names) if make_key(name) == "item"]
    position_column = item_column = 0
    if not position_columns:
        errors.append(Issue(Severity.ERROR, f'No "position" column. Columns in the file: {listing}.'))
    elif len(position_columns) > 1:
        errors.append(Issue(Severity.ERROR, 'More than one column is called "position".'))
    else:
        position_column = position_columns[0]
    if len(item_columns) > 1:
        errors.append(Issue(Severity.ERROR, 'More than one column is called "item".'))
    elif item_columns:
        item_column = item_columns[0]
    elif len(names) == 2 and len(position_columns) == 1:
        item_column = 1 - position_column
    elif position_columns:  # only say this when the position column itself was fine
        errors.append(Issue(Severity.ERROR, f'No "item" column. Columns in the file: {listing}.'))
    if errors:
        raise InputError(errors)

    issues: list[Issue] = []
    extras = [name for i, name in enumerate(names) if i not in (position_column, item_column) and name]
    if extras:
        ignored = ", ".join(f'"{name}"' for name in extras)
        issues.append(Issue(Severity.WARNING, f"Ignoring other column(s): {ignored}."))

    slots: dict[int, str] = {}
    spellings: dict[str, str] = {}
    row_of_position: dict[int, int] = {}
    row_of_performance: dict[str, int] = {}
    for row_number, row in enumerate(rows[header_index + 1 :], start=header_index + 2):
        if not any(cell.strip() for cell in row):
            continue  # completely blank rows are skipped quietly
        if any(cell.strip() for cell in row[len(header) :]):
            issues.append(
                Issue(
                    Severity.WARNING,
                    "has more cells than the header has columns; the extra cells are ignored",
                    row_number,
                )
            )
        raw_position = (row[position_column] if position_column < len(row) else "").strip()
        raw_item = row[item_column] if item_column < len(row) else ""
        key = make_key(raw_item)
        item = BREAK if key == BREAK.casefold() else key

        problems: list[str] = []
        position: int | None = None
        if not raw_position:
            problems.append("position is missing")
        elif not _WHOLE_NUMBER.fullmatch(raw_position):
            problems.append(f'position "{raw_position}" is not a whole number')
        elif int(raw_position) == 0:
            problems.append("position 0 is not allowed: positions start at 1")
        else:
            position = int(raw_position)
        if not key:
            problems.append("item is missing")
        if position is not None and position in row_of_position:
            problems.append(
                f"position {position} is repeated (also used in row {row_of_position[position]})"
            )
        if key and item != BREAK and item in row_of_performance:
            problems.append(
                f'"{clean_text(raw_item)}" is pinned more than once '
                f"(also in row {row_of_performance[item]})"
            )
        if problems:
            errors.extend(Issue(Severity.ERROR, problem, row_number) for problem in problems)
            continue

        assert position is not None  # no problems means the position was read
        slots[position] = item
        row_of_position[position] = row_number
        if item != BREAK:
            row_of_performance[item] = row_number
            spellings.setdefault(item, clean_text(raw_item))
    if errors:
        raise InputError(errors)

    if not slots:
        issues.append(Issue(Severity.WARNING, "The file has no pinned rows, so nothing is pinned."))
    pins = Pins(slots=dict(sorted(slots.items())), display_names=spellings)
    return PinLoad(pins=pins, warnings=tuple(issues))


def load_pins(path: str | Path) -> PinLoad:
    """Read a fixed-positions file. Raises InputError if unusable."""
    return parse_pins(read_text(path))


# ---------------------------------------------------------------- schedule writer


def format_schedules(schedules: Sequence[Schedule], performance_names: Mapping[str, str]) -> str:
    """CSV text for one or several schedules side by side (the format of docs/input-data.md).

    The first column is `position`; each schedule is one column, headed by its name.
    Performances are written with the spelling from `performance_names` (the performer
    file's display names), falling back to the spelling the schedule came from, then to the
    key itself. Breaks are written as BREAK. The text can be read back by parse_schedules,
    so the finder's output can be given straight to the schedule checker.

    Raises ValueError for a request the program should never make: no schedules, schedules
    of different lengths, or names that could not be told apart in a file (empty, "position",
    or the same name twice, ignoring case and spaces).
    """
    if not schedules:
        raise ValueError("there are no schedules to write")
    length = schedules[0].num_slots
    if any(schedule.num_slots != length for schedule in schedules):
        raise ValueError("all schedules must have the same number of slots")
    seen: set[str] = set()
    for schedule in schedules:
        key = make_key(schedule.name)
        if not key or key == "position" or key in seen:
            raise ValueError(
                f'schedule name "{schedule.name}" cannot be used as a column heading '
                '(it is empty, is "position", or repeats another name)'
            )
        seen.add(key)

    def shown(schedule: Schedule, slot: str) -> str:
        if slot == BREAK:
            return BREAK
        return performance_names.get(slot) or schedule.display_names.get(slot) or slot

    buffer = StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(("position", *(schedule.name for schedule in schedules)))
    for index in range(length):
        writer.writerow((index + 1, *(shown(schedule, schedule.slots[index]) for schedule in schedules)))
    return buffer.getvalue()


def write_schedules(
    path: str | Path, schedules: Sequence[Schedule], performance_names: Mapping[str, str]
) -> None:
    """Write schedules side by side to a CSV file. Raises InputError if it cannot be written."""
    write_text(path, format_schedules(schedules, performance_names))


def write_text(path: str | Path, text: str) -> None:
    """Write a text file. UTF-8 with a byte-order mark, so Excel shows accents correctly
    (the readers above accept the mark)."""
    path = Path(path)
    try:
        with open(path, "w", encoding="utf-8-sig", newline="") as handle:
            handle.write(text)
    except OSError as problem:
        raise InputError([Issue(Severity.ERROR, f"Could not write {path}: {problem}")]) from None
