# Repo structure

**Status:** DRAFT

```
performance-scheduling/
├── README.md
├── run_app.bat            # double-click to start the page (Windows)
├── .gitignore
├── .streamlit/config.toml # the page's settings (localhost only, no statistics)
├── pyproject.toml
├── data/
│   ├── examples/          # synthetic CSVs, committed
│   └── private/           # real performer data, never committed
├── src/performance_scheduling/   # the app: what pip installs
│   ├── __init__.py
│   ├── models.py
│   ├── io.py
│   ├── conflicts.py
│   ├── validator.py
│   ├── solver.py
│   ├── selection.py        # reads "1-3,7,all" style choices
│   ├── report.py           # wording of results, shared by the CLI and the UI
│   ├── cli.py
│   └── app.py              # the Streamlit page
├── scripts/                # developer tools, run from a checkout (D61)
│   ├── make_api_summary.py # writes docs/api-summary.md
│   └── list_messages.py    # checks docs/error-messages.md against the code
├── tests/                  # one test file per module, plus test_app.py and test_error_messages.py
├── notebooks/
│   └── exploration.ipynb
└── docs/
```

`scripts/` is outside the package on purpose (D61): the tools read `docs/` and the package's source files, so they only work from a checkout of the project and must not be installed with the app. Tests that need one (`tests/test_error_messages.py`) import it because `pyproject.toml` puts `scripts/` on pytest's path. Git does not track empty folders, so add a `.gitkeep` file to any folder you want to exist before it has content.
Git does not track empty folders, so add a `.gitkeep` file to any folder you want
to exist before it has content.

## What each file is responsible for

| File | Responsibility | Does it read/write files? |
|---|---|---|
| `models.py` | The vocabulary: simple data structures for a performer table, a schedule, a violation, a set of constraints. No logic beyond the structures themselves. | No |
| `io.py` | Reading and cleaning the performer CSV, reading schedule and fixed-position files, writing schedule CSVs. The only place where files are touched. Also chooses the name of the schedules file and never overwrites an existing file (D43). | Yes |
| `conflicts.py` | From cleaned performer data, works out which performances conflict and which performers cause each conflict. | No |
| `validator.py` | Schedule checker logic: given conflicts, a schedule and k, returns a list of problems. | No |
| `solver.py` | Schedule finder logic: given the performer data, k, number of breaks, pins and a seed, runs the pre-checks, lists schedules with OR-Tools CP-SAT, cross-checks each one with `validator.py` and explains why when there are none. OR-Tools is loaded only when a search runs. | No |
| `selection.py` | Turns a typed choice such as `1-3,7,20-22` or `all` into a list of schedule numbers, with a clear error for bad text. Pure function, no files. It sits in the shared layer because both the command line and the UI need it, and they must not import from each other. (Approved 2026-10-12.) Also picks the chosen schedules out of the finder's numbered list (`apply_selection`, `schedules_to_request`), so the command line and the UI choose by the same rules (D46). | No |
| `report.py` | Turns check results into plain-language text and CSV text: the sentence for each violation, the table for several schedules, the report file contents. Also groups violations by pair of performances (`group_violations`) so both interfaces list the clashing pairs first and then who is affected. Returns text and data, never prints. It sits in the shared layer for the same reason as `selection.py`: the command line and the UI must show identical wording and must not import from each other. (Added 2026-10-15; can be folded into `cli.py` if you prefer.) Also holds the wording of the schedule finder's on-screen messages (what was written, whether more exist, numbers that do not exist, the larger-gap prompt, why there is no schedule). | No |
| `app.py` | The Streamlit page: the only file that imports Streamlit, and it never imports `cli`. Shows what the shared layer returns (D48, D49, D53). | Via `io` (the example file only) |
| `cli.py` | Command-line entry points: `schedule-checker` and `schedule-finder`. Reads arguments, calls `io`, then `validator` or `solver`, prints results using `report`. No scheduling logic. | Via `io` |

`solver.py` hides the search engine (OR-Tools CP-SAT, decision D29) behind one function; see `search-approaches.md`.

## Dependency rule

    models  <-  io, conflicts, selection, report  <-  validator  <-  solver  <-  cli, app

(`report` only needs the result containers in `models`, so it sits beside `validator` rather than depending on it. `solver` imports `validator` so that every schedule it finds is cross-checked: decision D39.)

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
