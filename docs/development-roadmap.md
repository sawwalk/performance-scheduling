# Development roadmap

**Status:** DRAFT. Tick items off as they are completed.

Each step ends with tests passing and a commit.

## Phase 0: Setup
- [x] `.gitignore`
- [x] `README.md` stub
- [x] `pyproject.toml`
- [x] Synthetic example data in `data/examples/` (see `test-datasets.md`)
- [ ] Commit these files, and add `.gitkeep` in empty folders
- [ ] Create the virtual environment and install with `pip install -e ".[dev]"`
- [ ] Copy the real anonymised file into `data/private/`

## Phase 1: Shared core
- [x] `models.py`: data structures, with `test_models.py` and `data-model.md`
- [x] `io.py`: load and clean the performer CSV; `test_io.py`
- [x] `conflicts.py`: conflict map; `test_conflicts.py`
- [x] `io.py`: read schedule CSV (one or several schedule columns)
- [x] `selection.py`: parse pick syntax (`1-3,7`, `all`); `test_selection.py`

## Phase 2: Schedule checker
- [x] `validator.py`: structural checks, then spacing checks; `test_validator.py`
- [x] `cli.py` and `report.py`: checker command; `test_cli.py`, `test_report.py`
- [ ] Try it on the example data in a notebook

## Phase 3: Schedule finder (basic)
- [x] Notebook experiment settled decision Q2: OR-Tools CP-SAT (D29, 2026-10-17)
- [ ] Record the installed OR-Tools version in `environment.md` (D32)
- [ ] Refresh the "Rough" results in `test-datasets.md` with the CP-SAT results from the experiment
- [ ] Brute-force reference counter for small examples (used to test any engine)
- [ ] `solver.py` (CP-SAT): first valid schedule, any `k`, any number of breaks, with a time limit
- [ ] Every result passed through the checker in tests
- [ ] `cli.py`: finder command, writing all requested schedules side by side in one CSV

## Phase 4: Finder controls
- [ ] Fixed positions (`io.py` reader plus solver support)
- [ ] Enumeration: more schedules on demand by re-running and skipping (D33), no repeats, exhaustion
- [ ] Optional shuffle seed (repeatable; method decided by a test, Q14), `--pick`, `--limit`, and printing the command for the next batch
- [ ] Pre-checks and infeasibility explanations (including the blocking pins reported by the solver, D34)
- [ ] Short prompt after a successful run inviting the user to try a larger `k`

## Phase 5: Interface and polish
- [ ] `ui-design.md`, then the simple UI
- [ ] README with worked examples, `user-guide.md`
