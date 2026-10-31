# Task plan and context guide

**Status:** DRAFT (2026-10-19). Token figures are estimates (characters divided by 4) for the files as they stand today.

## 1. Keeping chats cheap

1. **Do not attach files to your messages.** An attached file becomes part of the conversation text, and every later turn carries it. This chat's first message held the whole project (docs, source, tests and the notebook), roughly 80,000 tokens. Files kept in the Project appear to me only as a list of paths, and I read the ones a task needs.
2. **Only what I read counts.** I can copy the Project's files into my sandbox, rebuild the folders, and run the whole test suite there, and none of that enters the conversation. So each task card has a **Read** list (its cost) and a **Run** line (free).
3. **One task per chat.** Start from the template in section 2 and end with the list of files to copy. Start the next task in a new chat.
4. **Keep the Project current.** After each step, replace the old versions of the changed files in the Project with the new ones. I rebuild the folder layout from the flat copies.
5. **Regenerate `docs/api-summary.md`** after any step that changes a public name: `python scripts/make_api_summary.py > docs/api-summary.md`. It is built from the code, so it cannot drift.

## 2. Starting message for a task

    Task U1 from docs/task-plan.md.
    Read docs/project-brief.md and the "Read" list in the task card, and nothing else
    unless you tell me why first. Run the whole test suite in your sandbox before and
    after your changes.
    <any answers to open questions, for example: Q16 (a) only me; Q17 guided form>

The card itself is about 400 tokens, so I read just that section of this file, not the whole of it.

## 3. Context menu

| File | Approx. tokens |
|---|---|
| `docs/project-brief.md` | 1,544 |
| `docs/api-summary.md` | 2,335 |
| `docs/ui-design.md` | 3,737 |
| `docs/design-decisions.md` | 4,306 |
| `docs/schedule-finder.md` | 3,933 |
| `docs/schedule-checker.md` | 1,695 |
| `docs/search-approaches.md` | 2,546 |
| `docs/input-data.md` | 1,795 |
| `docs/data-model.md` | 1,496 |
| `docs/repo-structure.md` | 1,134 |
| `docs/test-datasets.md` | 1,326 |
| `docs/problem-statement.md` | 828 |
| `docs/development-roadmap.md` | 803 |
| `docs/environment.md` | 594 |
| `src/io.py` | 7,264 |
| `src/solver.py` | 5,476 |
| `src/cli.py` | 4,247 |
| `src/models.py` | 2,864 |
| `src/report.py` | 2,670 |
| `src/selection.py` | 2,140 |
| `src/validator.py` | 1,572 |
| `src/conflicts.py` | 504 |

For comparison: all docs about 28,072, all source about 26,737, all tests about 27,441. The test files are never needed in the conversation, because I run them rather than read them (the exception is a task that edits a test file, which says so).

## 4. The tasks

Suggested order: answer Q16 and Q17, then U1 to U5 in order. D1 to D3 and M1 can be done at any time, each in its own chat. D4 comes last.

| ID | Task | Read cost | Needs first |
|---|---|---|---|
| U1 | Core additions the UI needs | about 9,454 tokens | Q17 answered (it does not change U1, but U1 comes first) |
| U2 | App skeleton and the "Your show" section | about 7,616 tokens | U1 |
| U3 | "Check a schedule" tab | about 7,812 tokens | U2 |
| U4 | "Find schedules" tab | about 11,768 tokens | U3, Q17 answered |
| U5 | Launcher, packaging and the manual checklist | about 3,477 tokens | U4, Q16 answered |
| D1 | `testing-strategy.md` | about 3,597 tokens | - (best after U4, so the page tests are included) |
| D2 | `error-messages.md` | about 8,879 tokens | - |
| D3 | `data-privacy.md` | about 1,977 tokens | Q16 answered |
| D4 | `user-guide.md` | about 7,236 tokens | U4 (and D2 for the message wording) |
| M1 | Refresh the "Rough" results in `test-datasets.md` | about 5,205 tokens | - |
| M2 | Optional: a capped count ("at least 10,000") | about 9,655 tokens | U4 (decide once you have seen the page) |
| M3 | Optional: a 40-performance scale test | about 3,982 tokens | - |

### U1: Core additions the UI needs

**Goal.** Add the seven small helpers in `ui-design.md` section 5, with tests in a new `tests/test_ui_helpers.py`. Rewrite `format_schedules`, `format_no_schedules`, `format_overview` and the next-batch rule in `cli.py` to use them, without changing any output.

**Read:**
- docs/project-brief.md (about 1,544)
- docs/ui-design.md, section 5 only (about 335)
- docs/api-summary.md (about 2,335)
- src: io.py, only `read_text`, `format_schedules`, `_detect_delimiter`, `_resolve_columns` (about 1,352)
- src: selection.py (whole) (about 2,140)
- src: report.py, only `format_overview`, `format_no_schedules` (about 317)
- src: cli.py, only `finder_main` and `_next_batch_command` (about 1,431)

**Run (free).** The whole existing suite, before and after (the refactors must not change any output).

**Files I deliver.** io.py, selection.py, report.py, cli.py, tests/test_ui_helpers.py, regenerated api-summary.md, design-decisions.md, development-roadmap.md

**Done when.** All existing tests still pass unchanged, the new tests pass, ruff is clean.

### U2: App skeleton and the "Your show" section

**Goal.** Create `app.py` with the page frame, the performer upload, the column pickers, the warnings and "Clear all data"; `.streamlit/config.toml`; and `tests/test_app.py` using Streamlit's `AppTest` with inline CSV text.

**Read:**
- docs/project-brief.md (about 1,544)
- docs/ui-design.md, whole (about 3,737)
- docs/api-summary.md (about 2,335)

**Run (free).** The whole suite, plus the new app tests (needs `streamlit`, which I install in my sandbox).

**Files I deliver.** src/performance_scheduling/app.py, .streamlit/config.toml, tests/test_app.py, design-decisions.md, development-roadmap.md

**Done when.** Upload, warnings, the column pickers and clearing work in `AppTest`.

### U3: "Check a schedule" tab

**Goal.** Add the checker tab to `app.py`: upload, gap, overview table, pairs table with performers affected, structural problems, downloads.

**Read:**
- docs/project-brief.md (about 1,544)
- docs/ui-design.md, sections 2 and 4.4 to 4.6 (about 933)
- docs/api-summary.md (about 2,335)
- src: app.py as it stands (estimate) (about 3,000)

**Run (free).** The whole suite plus the app tests.

**Files I deliver.** app.py, tests/test_app.py, development-roadmap.md

**Done when.** Every checker case in `ui-design.md` section 6 passes in `AppTest`.

### U4: "Find schedules" tab

**Goal.** Add the finder tab: settings, the pins form, pick, seed and shuffle, search, results table, downloads, "Show the next 5", "Try a gap of N", the no-schedule and stopped boxes, stale results.

**Read:**
- docs/project-brief.md (about 1,544)
- docs/ui-design.md, sections 2 and 4.3 to 4.6 (about 1,490)
- docs/api-summary.md (about 2,335)
- src: app.py as it stands (estimate) (about 6,000)
- docs/schedule-finder.md, "Choosing schedules" (about 399)

**Run (free).** The whole suite plus the app tests.

**Files I deliver.** app.py, tests/test_app.py, design-decisions.md, development-roadmap.md

**Done when.** Every finder case in `ui-design.md` section 6 passes in `AppTest`.

### U5: Launcher, packaging and the manual checklist

**Goal.** Add `run_app.bat` (or a `schedule-app` command), a version range for `streamlit` in the `ui` extra, README text, and a short manual checklist for a real browser.

**Read:**
- docs/project-brief.md (about 1,544)
- docs/ui-design.md, sections 7 to 9 (about 433)
- pyproject.toml (about 258)
- README.md (about 648)
- docs/environment.md (about 594)

**Run (free).** The whole suite; I check that the launcher command starts the page headless.

**Files I deliver.** run_app.bat or launcher, pyproject.toml, README.md, environment.md

**Done when.** You can double-click it, load the example file and find a schedule.

### D1: `testing-strategy.md`

**Goal.** Write down how the project is tested: the brute-force checks, the example datasets with known answers, the fault-injection habit, the wording tests and the `AppTest` page tests.

**Read:**
- docs/project-brief.md (about 1,544)
- docs/test-datasets.md (about 1,326)
- docs/search-approaches.md, sections 5 to 7 (about 727)

**Run (free).** `pytest --collect-only -q` (I generate the test inventory myself, so you do not have to paste it).

**Files I deliver.** docs/testing-strategy.md, development-roadmap.md

**Done when.** A new contributor could tell what each test file is for and how to add a test.

### D2: `error-messages.md`

**Goal.** A catalogue of every message the tools can show, grouped by situation, with what the organiser should do. I extract the messages from the code with a small script (`ast`), so I do not read the source files.

**Read:**
- docs/project-brief.md (about 1,544)
- docs/api-summary.md (about 2,335)
- the message list my script prints (estimate) (about 5,000)

**Run (free).** A new script that lists every message string in the code (I write and run it; it goes in `scripts/`).

**Files I deliver.** docs/error-messages.md, scripts/list_messages.py, development-roadmap.md

**Done when.** Every message in the code appears once in the catalogue, and a test or the script fails if one is added without an entry.

### D3: `data-privacy.md`

**Goal.** Write the privacy rules: what is personal data here, where real files may live, what is never committed or logged, what the UI keeps, and what hosting would need.

**Read:**
- docs/project-brief.md (about 1,544)
- docs/repo-structure.md, "Data folder policy" (about 43)
- docs/ui-design.md, section 8 (about 160)
- README.md, "Data and privacy" (about 54)
- .gitignore (about 176)

**Run (free).** Nothing to run.

**Files I deliver.** docs/data-privacy.md, design-decisions.md

**Done when.** Q16 is answered and the privacy rules cover that way of running the page.

### D4: `user-guide.md`

**Goal.** Plain-language guide for organisers: getting a CSV out of Excel, loading it, reading the warnings, finding and checking schedules, what the messages mean.

**Read:**
- docs/project-brief.md (about 1,544)
- docs/ui-design.md, section 4 (about 1,953)
- docs/schedule-checker.md, "Usage" and "Output" (about 927)
- docs/schedule-finder.md, "Usage" and "Output" (about 1,089)
- docs/input-data.md, sections 1 to 3 (about 1,723)

**Run (free).** Nothing to run. Screenshots from you would help.

**Files I deliver.** docs/user-guide.md, README.md

**Done when.** Someone who has never seen the tool can follow it from a CSV to a downloaded schedule.

### M1: Refresh the "Rough" results in `test-datasets.md`

**Goal.** Replace the quick-search results with answers from the finder, so each dataset states which gap and break combinations have schedules and which are proved impossible. The earlier quick search may share the backtracking fault found on 2026-10-17.

**Read:**
- docs/project-brief.md (about 1,544)
- docs/test-datasets.md (about 1,326)
- docs/api-summary.md (about 2,335)

**Run (free).** A throwaway script over every dataset and a grid of gaps and breaks (I write and run it; it needs the repo and OR-Tools in my sandbox).

**Files I deliver.** docs/test-datasets.md

**Done when.** Every "Rough" row says "found" or "proved impossible" with the time the finder took.

### M2: Optional: a capped count ("at least 10,000")

**Goal.** `schedule-finder.md` says the tool can show a count capped at a limit. It is not built. Decide whether the page wants it. If not, delete the sentence.

**Read:**
- docs/project-brief.md (about 1,544)
- docs/schedule-finder.md, "Scale note" paragraph (estimate) (about 300)
- docs/api-summary.md (about 2,335)
- src: solver.py (about 5,476)

**Run (free).** The whole suite.

**Files I deliver.** solver.py, tests/test_solver.py, schedule-finder.md

**Done when.** Either the sentence is gone or a capped count works and is tested.

### M3: Optional: a 40-performance scale test

**Goal.** See where the search slows down on a larger synthetic show (listed in `test-datasets.md` under "Ideas for later datasets").

**Read:**
- docs/project-brief.md (about 1,544)
- docs/test-datasets.md, "Ideas for later datasets" (about 103)
- docs/api-summary.md (about 2,335)

**Run (free).** A generator for the synthetic show and timings of the finder (I write and run them).

**Files I deliver.** docs/test-datasets.md, scripts/

**Done when.** The notes say how large a show the finder handles inside the default time limit.

## 5. Your own tasks (no chat needed)

- Copy the files from each step into the repo, then run `pip install -e ".[dev]"`, `pytest` and `ruff check src tests`. Tell me if the results differ from what I reported (I test on Linux and Python 3.12; you are on Windows).
- Commit the work so far. Add `.gitkeep` to any empty folder you want to keep (roadmap Phase 0).
- Run `nbstripout` on `notebooks/search_experiment.ipynb` before committing it. The results are kept in `search-approaches.md`.
- Run the finder on your real show and send me the output (it holds no real names): `schedule-finder --performers "data/private/2026 S2 performer data-anonymous.csv" --gap 2 --pick 1-5`, and again with `--gap 3 --breaks 2`.
- Add the new docs to the index in `docs/README.md` (I have not seen that file): `project-brief.md`, `task-plan.md`, `api-summary.md`, `ui-design.md`.
- Put `scripts/make_api_summary.py` in a `scripts/` folder, and add one line for it to `docs/repo-structure.md` if you want it listed. (Done: D61.)

## 6. Decisions waiting for you

| ID | Question | My recommendation |
|---|---|---|
| Q16 | Who runs the UI, and where? | (a) Only you, on your own computer, for now |
| Q17 | How are pins entered in the UI? | A guided "Add a pin" form |
| M2 | Build a capped count, or delete the sentence? | Decide after U4; delete it if the page does not need it |
| Dates | Change D29 to D41 from 2026-10-17 to 2026-10-19? | Only if the 17th is wrong; I do not know when you ran them |
