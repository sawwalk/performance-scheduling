# Development roadmap

**Status:** DRAFT. Tick items off as they are completed.

Each step ends with tests passing and a commit.

## Phase 0: Setup
- [x] `.gitignore`
- [x] `README.md` stub
- [x] `pyproject.toml`
- [x] Synthetic example data in `data/examples/` (see `test-datasets.md`)
- [x] Commit these files, and add `.gitkeep` in empty folders
- [x] Create the virtual environment and install with `pip install -e ".[dev]"`
- [x] Copy the real anonymised file into `data/private/`

## Phase 1: Shared core
- [x] `models.py`: data structures, with `test_models.py` and `data-model.md`
- [x] `io.py`: load and clean the performer CSV; `test_io.py`
- [x] `conflicts.py`: conflict map; `test_conflicts.py`
- [x] `io.py`: read schedule CSV (one or several schedule columns)
- [x] `selection.py`: parse pick syntax (`1-3,7`, `all`); `test_selection.py`

## Phase 2: Schedule checker
- [x] `validator.py`: structural checks, then spacing checks; `test_validator.py`
- [x] `cli.py` and `report.py`: checker command; `test_cli.py`, `test_report.py`
- [x] Try it on the example data in a notebook

## Phase 3: Schedule finder (basic)
- [x] Notebook experiment settled decision Q2: OR-Tools CP-SAT (D29, 2026-10-17)
- [x] Record the installed OR-Tools version in `environment.md` (D32): 9.15.6755
- [x] Refresh the "Rough" results in `test-datasets.md` with the CP-SAT results from the experiment
- [x] Brute-force reference counter for small examples (in `tests/test_solver.py`)
- [x] `solver.py` (CP-SAT): schedules for any `k`, any number of breaks, with a time limit (D38 to D41)
- [x] Every result passed through the checker, inside the finder and in tests (D39)
- [x] `io.py`: write schedules side by side (`format_schedules`, `write_schedules`; D37)
- [x] `cli.py`: finder command, writing the chosen schedules side by side in one CSV (D42 to D47)
- [x] Example fixed-positions file `tiny_feasible_pins.csv` (see `test-datasets.md`)

## Phase 4: Finder controls
- [x] Fixed positions: `io.py` reader (`parse_pins`, `load_pins`; D36)
- [x] Fixed positions: solver support
- [x] Enumeration in `solver.py`: the first `count` schedules, no repeats, found / exhausted / stopped
- [x] `cli.py`: choose schedules by number, re-running and skipping (D33)
- [x] Optional shuffle seed in `solver.py` (repeatable; D38)
- [x] `cli.py`: `--seed`, `--pick`, `--limit`, and printing the command for the next batch
- [x] Pre-checks and infeasibility explanations in `solver.py` (including the blocking pins, D34)
- [x] Short prompt after a successful run inviting the user to try a larger `k`

## Phase 5: Interface and polish
- [ ] `ui-design.md`, then the simple UI
- [x] U1, core additions the UI needs: `decode_text`, `performer_file_columns`, `schedule_rows`, `next_pick`, `format_found`, `no_schedules_heading`, `overview_rows`; `tests/test_ui_helpers.py` (D50 to D52)
- [x] U2, app skeleton and the "Your show" section: `app.py`, `.streamlit/config.toml`, `tests/test_app.py` (D48, D49, D53, D54; Q16 and Q17 answered)
- [x] U3, "Check a schedule" tab: upload, rest (gap), overview table, pairs table with who is affected, problems with the schedule itself, problems download; `app.py`, `tests/test_app.py` (D55)
- [x] U4, "Find schedules" tab: settings, pins form, pick, seed and shuffle, search, results table, downloads, "Show the next 5", "Try a gap of N", the no-schedule and stopped boxes, stale results; `app.py`, `tests/test_app.py` (D56)
- [x] U5, launcher (`run_app.bat`), `ui` extra version range, README, manual checklist in `ui-design.md` section 11 (D57). The checklist itself has not yet been run in a real browser
- [ ] README with worked examples, `user-guide.md`
