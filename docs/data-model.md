# Data model

**Status:** DRAFT. Describes `src/performance_scheduling/models.py`.

`models.py` is the project's vocabulary: containers for data, with almost no logic.
Every other file imports from it. Files that *fill* the containers (`io.py`, `conflicts.py`)
and files that *use* them (`validator.py`, `solver.py`) all agree on what the pieces are.

## Conventions

| Convention | Detail |
|---|---|
| **Keys and display names** | Matching uses a cleaned, lower-case **key** (`bollywood (open)`). The **display name** is the first spelling seen (`Bollywood (Open)`) and is used only in messages and output. So `Bollywood (Open) `, `bollywood (open)` and `Bollywood (Open)` are one performance. The function that makes keys will live in `io.py`. |
| **Positions** | Numbered from 1 (decision D10). |
| **Breaks** | The text `BREAK`. Performance keys are lower case so they can never equal it, and the loader rejects any performance named "break" so a file can never be ambiguous. |
| **Frozen dataclasses** | A field cannot be reassigned after creation. The dictionaries inside are not locked, so by convention they are treated as read-only. |

## The pieces

| Piece | Fields | Created by | Used by |
|---|---|---|---|
| `Severity` | `ERROR`, `WARNING` | n/a | `Issue` |
| `Issue` | `severity`, `message`, `row` (optional; spreadsheet row, header is row 1) | `io.py`, `validator.py` | CLI/UI to display |
| `InputError` | An exception holding a tuple of `Issue`s (every problem found, not just the first) | `io.py` | CLI/UI to display |
| `PerformerData` | `performances_by_performer`, `performer_names`, `performance_names`; helpers `performance_keys` (alphabetical) and `performers_by_performance` | `io.py` | `conflicts.py`, finder, checker |
| `ConflictMap` | `shared` (pair of performances -> performers they share), `neighbours` (performance -> performances it conflicts with); helpers `conflict(a, b)` and `shared_performers(a, b)` | `conflicts.py` | checker (names the performer), finder (fast legality tests) |
| `Schedule` | `name` (e.g. `schedule_4`), `slots` (a performance key or `BREAK` per slot); helpers `num_slots`, `num_breaks`, `positions()` | `io.py` (reading), finder (producing) | checker, `io.py` (writing) |

Errors stop processing; warnings do not (see `input-data.md`). That is why `Issue` has a
severity and why `InputError` carries a list: the organiser sees all the problems with
their file at once.

## Worked example

Input rows:

    Sam,Jazz        Sam,Tap        Alex,Tap        Kim,Ballet

After loading, `PerformerData` holds:

| performer key | performances |
|---|---|
| sam | jazz, tap |
| alex | tap |
| kim | ballet |

(plus the display names, e.g. `sam -> "Sam"`, `jazz -> "Jazz"`).

The `ConflictMap` built from it:

| | |
|---|---|
| `shared` | `{jazz, tap}` -> `{sam}` |
| `neighbours` | jazz -> {tap}; tap -> {jazz}; ballet -> {} |

A schedule `jazz, BREAK, tap, ballet` is held as `Schedule(name="schedule_1", slots=("jazz", "BREAK", "tap", "ballet"))`,
with `positions()` giving `{jazz: 1, tap: 3, ballet: 4}`. Jazz and tap conflict through Sam
and are 2 positions apart, so at k = 1 (they need at least 2 positions apart) this is valid.

## Left out on purpose

These are added when the phase that needs them is reached:

- Fixed positions / pins and the finder's settings (Phase 4)
- A `Violation` record for the checker (Phase 2)
- Result containers for the loaders (decided when we write `io.py`)

## Tests

`tests/test_models.py` checks the helpers (flipping the performer mapping, conflict lookup in
either order, break counts, positions from 1, issue text) and that frozen containers
reject changes. Run with `pytest` from the repo root.
