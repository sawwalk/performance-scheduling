# Project brief

**Attach this to every new chat.** It replaces the long opening message. Add only the files the task card in `task-plan.md` lists.

## What this is

`performance-scheduling`: tools for ordering the performances in a dance show (about 20 performances, about 120 performers) so that no performer appears again too soon. The **gap** `k` is the fewest slots allowed between two performances that share a performer (default 1, meaning never in consecutive slots). Breaks occupy slots and count as spacing. Guest acts are just breaks. Always say **"schedule checker"** and **"schedule finder"**, never Tool 1 and Tool 2.

## State (2026-10-31)

- **Schedule checker:** done (`schedule-checker` command).
- **Schedule finder:** done (`schedule-finder` command). Search engine is OR-Tools CP-SAT (9.15.6755; `pyproject.toml` asks for `>=9.15,<10`). It does pre-checks, lists schedules, cross-checks each one with the checker, explains why none exist, names pins that cannot all be kept, and honours a time limit.
- **The page:** done and tested with Streamlit's `AppTest` (Streamlit 1.66.1; `pyproject.toml` asks for `>=1.66,<2`). Tasks U1 to U5 are finished. Start it by double-clicking `run_app.bat` (Windows), or run `streamlit run src/performance_scheduling/app.py` from the project folder. It shows the "Find schedules" and "Check a schedule" tabs.
- **Tests:** 613 passing and ruff clean in my sandbox (Linux, Python 3.12). The 604 before D2 also passed on your Windows machine.
- **Still to do:** nothing in the code. The manual checklist (`ui-design.md` section 11) was run in a real browser on 2026-10-31 and everything worked. `data-privacy.md`, `error-messages.md` and `user-guide.md` are written (the guide has four screenshots in `docs/images/`). Left: `testing-strategy.md` (D1), fixes from a fresh-clone test of the setup steps (F1), and M1 (refresh the "Rough" results in `test-datasets.md`). M2 and M3 were dropped (D63). **`task-plan.md` section 0 is the handover: read it first.**

## Code layout

A file may only import from files before it in this chain:

    models  <-  io, conflicts, selection, report  <-  validator  <-  solver  <-  cli, app.py

`app.py` (the page) never imports `cli`, and it is the only file that imports Streamlit.

- Only `io.py` touches files. `validator.py` and `solver.py` never read files or print.
- `report.py` (and the messages built in `validator.py` and `solver.py`) hold the wording, so the command line and the UI show the same sentences. `selection.py` holds the "pick schedules by number" rules.
- OR-Tools is imported only inside `solver.py` when a search runs, so the checker installs and runs without it.
- `docs/api-summary.md` lists every public function and container with its signature. Use it instead of attaching source files. Regenerate it after any change to a public name with `python scripts/make_api_summary.py > docs/api-summary.md`.

## How to work with me

- This is my first project like this. I use Windows (cmd and the VS Code terminal with a `.venv`), VS Code, Python scripts and notebooks. Explain commands and concepts plainly and show me how to run things.
- Plan first, then code, in small steps. Before writing a file, explain what goes in it and why. Do not add new files without telling me why; I will approve sensible ones.
- Every step ends with: code, tests, docs updated, and the exact list of files to copy and where they go. Run `pytest` and `ruff check src tests` yourself if you can, and tell me what to run.
- Record every decision in `docs/design-decisions.md` (numbered D-entries; open questions as Q-entries).
- Ask at most one question at a time, with a recommendation.
- Be honest about what you did not verify.

## Habits that have paid off

- Test the solver against brute force on small shows, including hand-made cases. Break the code on purpose (mutation check) to see that the tests notice.
- Run ruff after adding tests: it catches a new test that reuses an old test's name, which would hide the old one.
- Keep the tests that check wording exact, because the command line and the UI depend on it.

## Key decisions, one line each (full table: `design-decisions.md`)

- **D1, D2:** breaks count as slots; guest acts are breaks. **D5:** output is CSV.
- **D6, D10:** organisers can pin items to slots, numbered from 1. **D9, D11:** the number of breaks is a parameter that includes pinned breaks; breaks are interchangeable.
- **D14:** no automatic search for the largest gap; after a run the tool only invites a larger one. **D16:** that invitation does not check anything.
- **D17, D19:** `--pick` takes `1-5`, `6-10`, `1,4,9`, `1-3,7,20-22` or `all`; `--limit` defaults to 100 and a longer explicit pick is refused.
- **D21, D22:** suspected typos only produce warnings, and the tool never changes names; the readers check the file, not its contents.
- **D26, D46:** wording lives in the shared layer so the command line and the UI cannot disagree.
- **D29, D30, D32:** the engine is CP-SAT; its list is complete and repeatable (same input, seed, OR-Tools version, one thread) but not in dictionary order, and numbering can change with the OR-Tools version.
- **D33:** "show more" re-runs the search and skips; there is no bookmark.
- **D34, D40:** when none exist the finder explains why, and names pins that cannot all be kept. Pre-check failures come back as *exhausted* with reasons.
- **D36:** the pin file reader refuses a position or performance used twice.
- **D38:** the seed shuffles the order the model is built in, by hash; the solver's own seed was tested and does not move the start of the list.
- **D39:** the finder cross-checks every schedule with the checker; a failure is a bug and raises an error.
- **D42, D43, D44, D45, D47:** finder exit codes 0/1/2; files are named by seed and pick and never overwritten; the next-batch command is printed only when more exist; the time limit is 30 s by default; everything is checked before searching.
- **D48, D49, D53:** the UI is a thin Streamlit page that imports only the shared layer; it runs on one computer (`server.address = "localhost"`), keeps data in memory, sends no usage statistics and shows no tracebacks.
- **D50 to D52:** the table helpers, upload decoding and next-batch rule live in the shared layer so the page and the commands cannot differ.
- **D54, D56:** pins are entered with a guided form, not an editable table; results go stale when a setting changes.
- **D55:** the "Check a schedule" tab works out its result again on every run and keeps nothing in `st.session_state`.
- **D57:** the launcher is `run_app.bat`, not a command; the `ui` extra includes OR-Tools because the page runs the finder.

## Open questions

None at the moment. Q12 (where the real show file lives) is settled: it lives in `data/private/`, which git ignores (D58). Q16 (who runs the page) was answered as "only the project owner, on one computer" (D53), and Q17 (how pins are entered) as a guided form (D54).

## Where to find things

| Question | File |
|---|---|
| What are the rules and terms? | `problem-statement.md` |
| What do the input and output files look like? | `input-data.md` |
| How do the two tools behave? | `schedule-checker.md`, `schedule-finder.md` |
| Why this engine? What did the experiment show? | `search-approaches.md` |
| What do the containers hold? | `data-model.md` (or `api-summary.md`) |
| What does each file do? | `repo-structure.md` |
| Which datasets have known answers? | `test-datasets.md` |
| How does the UI work? How do I try it in a browser? | `ui-design.md` (section 11 is the manual checklist) |
| What does each message mean, and what do I do about it? | `error-messages.md` (kept true by `python scripts/list_messages.py --check` and a test) |
| How does an organiser use the page, step by step? | `user-guide.md` |
| How do I start the page, and what does `.venv` need? | `README.md`, `environment.md` |
| What is left to do, and what does each task need? | `task-plan.md`, `development-roadmap.md` |
