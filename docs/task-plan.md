# Task plan and handover

**Status:** UPDATED 2026-10-31 for a handover to a new chat. Token figures are estimates (characters divided by 4) for the files as they stand on that date. Everything in the plan up to the user guide is finished; section 3 lists what is left.

## 0. Read this first (handover)

**The project.** Two tools that help a dance-show organiser order the performances so that nobody performs again too soon: a **schedule checker** (tests a running order) and a **schedule finder** (finds running orders, with pins and breaks). Both are used from the command line or from a Streamlit page started by `run_app.bat`. The code is in `src/performance_scheduling/`, the developer tools in `scripts/`, the tests in `tests/`, and the documents in `docs/`. The entry point for any task is `docs/project-brief.md`.

**Where it stands (2026-10-31).**
- All code is finished: checker, finder (OR-Tools CP-SAT), the page (`app.py`), the launcher and packaging.
- 613 tests pass and `ruff check src tests scripts` is clean (tested on Linux, Python 3.12, Streamlit 1.66.1, OR-Tools 9.15.6755). The owner runs Windows (cmd and the VS Code terminal with a `.venv`); the first 604 tests passed there too.
- The manual checklist in `docs/ui-design.md` section 11 was run by the owner in a real browser, and everything worked.
- Documents finished: the data-privacy rules (D59), the message catalogue and its check (D60), the user guide with four screenshots (D62).
- Decisions D1 to D63 are in `docs/design-decisions.md`; no questions are open. **The next decision number is D64.**

**What is left.** Three small things, section 3: **F1** fixes from the owner's fresh-clone test (in progress), **D1** `testing-strategy.md`, **M1** refresh the "Rough" results in `test-datasets.md`. The owner dropped M2 and M3 (D63).

**Tasks already done.**

| ID | Task | Decisions |
|---|---|---|
| U1 | Core additions the UI needs (seven helpers) | D50 to D52 |
| U2 | App skeleton and the "Your show" section | D48, D49, D53, D54 |
| U3 | "Check a schedule" tab | D55 |
| U4 | "Find schedules" tab | D56 |
| U5 | Launcher (`run_app.bat`), packaging, manual checklist | D57 |
| D2 | `error-messages.md`, `scripts/list_messages.py` and its test | D60, D61 |
| D3 | `data-privacy.md` | D58, D59 |
| D4 | `user-guide.md` and screenshots | D62 |

**Rules that keep the project true. Follow them in every task.**
1. **A new message needs a catalogue row.** Any new user-facing message (an `Issue`, a `raise`, an `st.error` and so on) must get a row in `docs/error-messages.md`. `python scripts/list_messages.py --check` and `tests/test_error_messages.py` fail otherwise. The rules for what counts as a message are at the top of `scripts/list_messages.py`.
2. **Regenerate the API summary** after changing a public name: `python scripts/make_api_summary.py > docs/api-summary.md`.
3. **Wording lives in the shared layer** (`report.py`, `io.py`, `selection.py`), so the commands and the page cannot disagree (D26, D46). The tests that check wording are exact on purpose.
4. **`app.py` is the only file that imports Streamlit** and never imports `cli` (D48). The layer order is in `docs/repo-structure.md`.
5. **Privacy (D59).** Never ask for, open or paste real performer data. It lives in `data/private/`. Use the synthetic files in `data/examples/`. The page keeps data in memory only and runs on one computer.
6. **Record every decision** as the next D-number in `docs/design-decisions.md`, and tick the roadmap (`docs/development-roadmap.md`).

**Working with the owner** (the full list is "How to work with me" in `project-brief.md`). In short: explain things plainly; plan first, then code, in small steps; say why before adding a new file; ask at most one question at a time, with a recommendation; say what you did not verify; end every step with the exact list of files to copy and where they go. Use British spelling ("organiser", "colour"). Run `pytest` and `ruff` yourself.

**Known loose ends** (none block anything).
- `ruff format` is not used: most files would be reformatted. Only `ruff check` is enforced.
- One session key, `form`, listed in `ui-design.md` section 4.5 is unused (D56).
- Not verified: that the page makes no outgoing network connection other than usage statistics, which are off (`data-privacy.md` section 4); the launcher's behaviour on a Windows machine without the project set up.

## 1. Keeping chats cheap

1. **The project arrives as a zip.** Unzip it in the sandbox and read only the files in the task's **Read** list. Do not paste whole files into the conversation, because every later turn carries them.
2. **Run things instead of reading them.** The whole suite runs in the sandbox without entering the conversation. The test files are never read unless a task edits one.
3. **One task per chat.** Start from the template in section 2. End with the list of files to copy.
4. **Keep the zip current.** The owner replaces the changed files after each step and re-zips for the next chat.
5. **What the owner leaves out of the zip:** `.venv/`, `data/private/`, `output/`, `__pycache__/` and `*.egg-info/`. If `data/private/` is in the zip anyway, do not open it.

## 2. Starting message for a task

    Task D1 from docs/task-plan.md.
    Unzip the project. Read docs/task-plan.md section 0 and the D1 card, then docs/project-brief.md
    and the "Read" list in the card, and nothing else unless you tell me why first.
    Set up a .venv in your sandbox (pip install -e ".[dev]") and run the whole test suite before
    and after your changes.
    <any answers to open questions>

## 3. The tasks

Suggested order: F1 (the owner is doing the test now), then D1 and M1 in any order. Each card is about 400 tokens.

| ID | Task | Read cost | Needs first |
|---|---|---|---|
| F1 | Fixes from the fresh-clone test | about 6,500 tokens | the owner's notes |
| D1 | `testing-strategy.md` | about 4,800 tokens | - |
| M1 | Refresh the "Rough" results in `test-datasets.md` | about 5,900 tokens | - |

### F1: Fixes from the fresh-clone test

**Goal.** The owner copies the project to an empty folder and follows only `README.md` and `docs/user-guide.md`. Fix whatever goes wrong: missing steps, wrong commands, unclear wording, a launcher fault.

**Read:**
- docs/project-brief.md (about 1,978)
- the owner's notes, pasted into the message: the step, what was expected, what happened
- README.md (about 1,011)
- docs/user-guide.md (about 3,269)
- docs/environment.md (about 936)
- run_app.bat (about 285)

**Run (free).** The whole suite. Repeat the README's setup steps in a fresh `.venv` in the sandbox to check the commands, with the limits that Linux is not Windows.

**Files I deliver.** Whichever of README.md, docs/user-guide.md, docs/environment.md, run_app.bat and pyproject.toml needed a change; docs/design-decisions.md if a decision is made.

**Done when.** A person who follows only the README and the guide goes from an empty folder to a downloaded schedule without help.

### D1: `testing-strategy.md`

**Goal.** Write down how the project is tested: the brute-force checks, the example datasets with known answers, the fault-injection habit, the wording tests, the `AppTest` page tests, and the message-catalogue check (`scripts/list_messages.py` and `tests/test_error_messages.py`).

**Read:**
- docs/project-brief.md (about 1,978), including "Habits that have paid off"
- docs/test-datasets.md (about 1,325)
- docs/search-approaches.md, sections 5 to 7 (about 727)
- docs/ui-design.md, section 6 and section 11 (about 600)

**Run (free).** `pytest --collect-only -q` (the test inventory is generated, not pasted). Also `pytest -q --durations=5` for the slowest tests. The test files are `test_app`, `test_cli`, `test_conflicts`, `test_error_messages`, `test_io`, `test_models`, `test_report`, `test_selection`, `test_solver`, `test_ui_helpers` and `test_validator`; open one only if the inventory does not make its purpose clear.

**Files I deliver.** docs/testing-strategy.md, docs/development-roadmap.md, docs/project-brief.md (one line in "Where to find things"), docs/README.md (one line in the index).

**Done when.** A new contributor could tell what each test file is for and how to add a test.

### M1: Refresh the "Rough" results in `test-datasets.md`

**Goal.** Replace the quick-search results with answers from the finder, so each dataset states which gap and break combinations have schedules and which are proved impossible. The earlier quick search may share the backtracking fault found on 2026-10-17.

**Read:**
- docs/project-brief.md (about 1,978)
- docs/test-datasets.md (about 1,325)
- docs/api-summary.md (about 2,597)

**Run (free).** A throwaway script over every dataset in `data/examples/` and a grid of gaps and breaks (the chat writes and runs it; it needs the package and OR-Tools, so a `.venv` with `pip install -e ".[dev]"`). Report each result as "found" or "proved impossible" with the time the finder took. Do not commit the script unless it is worth keeping, and if it is, put it in `scripts/` and say so first.

**Files I deliver.** docs/test-datasets.md, docs/development-roadmap.md

**Done when.** Every "Rough" row says "found" or "proved impossible" with the time the finder took, and the file says which machine the timings are from.

## 4. Context menu

Paths are inside the project folder. Approximate tokens, from 2026-10-31.

| File | Approx. tokens |
|---|---|
| `docs/project-brief.md` | 1,978 |
| `docs/README.md` (index) | 700 |
| `docs/api-summary.md` | 2,597 |
| `docs/design-decisions.md` (read one D-entry with `grep`, not the whole table) | 9,000 |
| `docs/user-guide.md` | 3,269 |
| `docs/error-messages.md` | 6,652 |
| `docs/data-privacy.md` | 1,803 |
| `docs/ui-design.md` | 4,070 |
| `docs/schedule-finder.md` | 3,900 |
| `docs/schedule-checker.md` | 1,694 |
| `docs/search-approaches.md` | 2,545 |
| `docs/input-data.md` | 1,795 |
| `docs/data-model.md` | 1,496 |
| `docs/repo-structure.md` | 1,372 |
| `docs/test-datasets.md` | 1,325 |
| `docs/problem-statement.md` | 828 |
| `docs/development-roadmap.md` | 1,000 |
| `docs/environment.md` | 936 |
| `README.md` | 1,011 |
| `src/performance_scheduling/io.py` | 7,791 |
| `src/performance_scheduling/app.py` | 8,095 |
| `src/performance_scheduling/solver.py` | 5,476 |
| `src/performance_scheduling/cli.py` | 4,249 |
| `src/performance_scheduling/models.py` | 2,863 |
| `src/performance_scheduling/report.py` | 2,995 |
| `src/performance_scheduling/selection.py` | 2,286 |
| `src/performance_scheduling/validator.py` | 1,572 |
| `src/performance_scheduling/conflicts.py` | 503 |
| `scripts/list_messages.py` | 2,676 |
| `scripts/make_api_summary.py` | 954 |

For comparison, all tests are about 30,000 tokens and are never needed in the conversation, because they are run rather than read (the exception is a task that edits a test file, which says so). Check `docs/api-summary.md` before opening a source file.

## 5. Your own tasks (no chat needed)

- After each step, copy the new files into the project and run `pip install -e ".[dev]"`, `pytest`, `ruff check src tests scripts` and `python scripts/list_messages.py --check`. Tell the chat if the results differ from what it reported.
- Replace `docs/README.md` with the index in this handover, if yours is still a copy of the root README (the one the previous chat saw was).
- Commit the work. Check `git status` shows nothing from `data/private/` (`data-privacy.md` section 8).
- Before zipping for a new chat, leave out `.venv/`, `data/private/`, `output/`, `__pycache__/` and `*.egg-info/`.
- When the guide is shown to a first organiser, write down every place they hesitate and send the notes to a chat as F1 input.
- Optional: run the finder on your real show and keep the output for yourself (it holds no real names): `schedule-finder --performers "data/private/<your file>.csv" --gap 2 --pick 1-5`, and again with `--gap 3 --breaks 2`.

## 6. Decisions waiting for you

| ID | Question | Recommendation |
|---|---|---|
| Dates | D29 to D41 in `design-decisions.md` are dated 2026-10-17. Change them to 2026-10-19? | Only if the 17th is wrong; the previous chat did not know when the owner ran them |

Everything else is answered: Q12, Q16 and Q17 (D58, D53, D54), and M2 and M3 are dropped (D63).
