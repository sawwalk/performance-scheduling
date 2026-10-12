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
- [ ] `models.py`: data structures
- [ ] `io.py`: load and clean the performer CSV; `test_io.py`
- [ ] `conflicts.py`: conflict map; `test_conflicts.py`
- [ ] `io.py`: read schedule CSV (one or several schedule columns)
- [ ] `selection.py`: parse pick syntax (`1-3,7`, `all`); `test_selection.py`

## Phase 2: Schedule checker
- [ ] `validator.py`: structural checks, then spacing checks; `test_validator.py`
- [ ] `cli.py`: checker command
- [ ] Try it on the example data in a notebook

## Phase 3: Schedule finder (basic)
- [ ] Notebook experiment to settle decision Q2 (search engine), as set out in `search-approaches.md`
- [ ] Brute-force reference counter for small examples (used to test any engine)
- [ ] `solver.py`: first valid schedule, any `k`, any number of breaks
- [ ] Every result passed through the checker in tests
- [ ] `cli.py`: finder command, writing all requested schedules side by side in one CSV

## Phase 4: Finder controls
- [ ] Fixed positions (`io.py` reader plus solver support)
- [ ] Enumeration: next schedule on demand, no repeats, exhaustion
- [ ] Optional shuffle seed (repeatable), `--pick`, `--limit`, and printing the command for the next batch
- [ ] Pre-checks and infeasibility explanations
- [ ] Short prompt after a successful run inviting the user to try a larger `k`

## Phase 5: Interface and polish
- [ ] `ui-design.md`, then the simple UI
- [ ] README with worked examples, `user-guide.md`
