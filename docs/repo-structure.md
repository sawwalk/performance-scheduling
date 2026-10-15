# Repo structure

**Status:** DRAFT

```
performance-scheduling/
├── README.md
├── .gitignore
├── pyproject.toml
├── data/
│   ├── examples/          # synthetic CSVs, committed
│   └── private/           # real performer data, never committed
├── src/performance_scheduling/
│   ├── __init__.py
│   ├── models.py
│   ├── io.py
│   ├── conflicts.py
│   ├── validator.py
│   ├── solver.py
│   ├── selection.py        # reads "1-3,7,all" style choices
│   ├── report.py           # wording of results, shared by the CLI and the UI
│   └── cli.py
├── tests/
│   ├── test_io.py
│   ├── test_conflicts.py
│   ├── test_validator.py
│   └── test_solver.py
├── notebooks/
│   └── exploration.ipynb
└── docs/
```

A UI module (for example `src/performance_scheduling/app.py`) will be added later.
Git does not track empty folders, so add a `.gitkeep` file to any folder you want
to exist before it has content.

## What each file is responsible for

| File | Responsibility | Does it read/write files? |
|---|---|---|
| `models.py` | The vocabulary: simple data structures for a performer table, a schedule, a violation, a set of constraints. No logic beyond the structures themselves. | No |
| `io.py` | Reading and cleaning the performer CSV, reading schedule and fixed-position files, writing schedule CSVs. The only place where files are touched. | Yes |
| `conflicts.py` | From cleaned performer data, works out which performances conflict and which performers cause each conflict. | No |
| `validator.py` | Schedule checker logic: given conflicts, a schedule and k, returns a list of problems. | No |
| `solver.py` | Schedule finder logic: given conflicts, k, number of breaks and fixed positions, produces schedules one at a time. | No |
| `selection.py` | Turns a typed choice such as `1-3,7,20-22` or `all` into a list of schedule numbers, with a clear error for bad text. Pure function, no files. It sits in the shared layer because both the command line and the UI need it, and they must not import from each other. (Approved 2026-10-12.) | No |
| `report.py` | Turns check results into plain-language text and CSV text: the sentence for each violation, the table for several schedules, the report file contents. Also groups violations by pair of performances (`group_violations`) so both interfaces list the clashing pairs first and then who is affected. Returns text and data, never prints. It sits in the shared layer for the same reason as `selection.py`: the command line and the UI must show identical wording and must not import from each other. (Added 2026-10-15; can be folded into `cli.py` if you prefer.) | No |
| `cli.py` | Command-line entry points. Reads arguments, calls `io`, then `validator` or `solver`, prints results using `report`. No scheduling logic. | Via `io` |

`solver.py` hides the search engine behind one function. If the engine code grows, it may be split into per-engine files; see `search-approaches.md`.

## Dependency rule

    models  <-  io, conflicts, selection, report  <-  validator, solver  <-  cli (and later the UI)

(`report` only needs the result containers in `models`, so it sits beside `validator` rather than depending on it.)

A module may import from anything to its left, never from its right. In particular
`validator.py` and `solver.py` never read files and never print; they take data in and
return data out. This is what makes them easy to test and lets the CLI and the UI share them.

## Data folder policy

Performer names and emails are personal data. Everything in `data/` is gitignored except
`data/examples/`. Only synthetic data may go in `examples/`.

## Notebooks

Notebooks are for exploring and prototyping. Anything worth keeping is moved into `src/`
and tested. Consider `nbstripout` so notebook outputs (which may contain real names) are
never committed.
