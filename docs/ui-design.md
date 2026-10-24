# UI design

**Status:** DRAFT (2026-10-19). Items marked *(proposed)* are my recommendations and are not yet confirmed. Two open questions, Q16 and Q17, are in `design-decisions.md`.

## 1. Purpose and audience

A simple web page for **non-technical organisers** (decision D3) that does what the two commands do, with the same results and the same sentences:

- **Find schedules:** the schedule finder, with settings as form fields and a "Show more schedules" button.
- **Check a schedule:** the schedule checker, for one running order or several side by side.

The core logic stays separate from the UI (D8). The UI only collects input, calls the shared code and lays out what comes back.

## 2. Principles

1. **Thin.** No scheduling logic and no sentences of its own. If the page needs a sentence that does not exist yet, it is added to `report.py` so the command line and the page cannot disagree (D26, D46).
2. **One file imports Streamlit:** `src/performance_scheduling/app.py`. It imports only the shared layer (`models`, `io`, `selection`, `report`, `validator`, `solver`) and never `cli` (D48).
3. **Never changes the organiser's data (D21).** Suspected typos in names are shown as warnings, in full and prominently, because they are the organiser's only prompt to fix the file.
4. **Plain words.** The organiser never sees a traceback, a `Severity` label or a number-with-no-meaning.
5. **Nothing is kept.** Files live in memory for the session only (D49, section 8).
6. **Same list as the command.** The same file, settings and seed give the same numbered list (D20, D32).
7. **Not colour alone.** Every status has an icon and words as well as a colour.

## 3. Technology

Streamlit, as already planned (the `ui` extra in `pyproject.toml`). It is Python-only, which keeps the core and the page in one language.

What I checked, in my sandbox with Streamlit 1.66.1 (other versions not checked):

- It has the pieces needed: file upload, download buttons, forms, tabs, expanders, spinners and `st.session_state`.
- Its headless test tool, `AppTest`, can simulate **file uploads, buttons, number and text inputs, selects and tabs**. It **cannot drive `st.data_editor`**. This is why pins are entered with a form, not an editable table (section 4.3, Q17).
- **Usage statistics are on by default** (`browser.gatherUsageStats = True`). They are switched off in `.streamlit/config.toml` (D49).
- Tracebacks are shown by default (`client.showErrorDetails = 'full'`). They are switched off for organisers *(proposed)*.

Things to design around:

- Streamlit **re-runs the whole script on every click**, so everything the page remembers goes in `st.session_state`.
- A search **blocks the page while it runs**, for up to the time limit (default 30 s). A spinner says so.
- One browser tab is one session. Two organisers on one running copy do not see each other's data.

## 4. Screens

### 4.1 Page frame

A title, one sentence ("Check a running order, or find one, so that nobody performs twice in a row"), the "Your show" section, then two tabs: **Find schedules** and **Check a schedule** *(proposed order: find first, check second)*. The tabs stay hidden until a performer file has loaded without errors.

### 4.2 Your show (shared by both tabs)

    1. Your show
    [ Drop the performer file here, or browse (CSV) ]      Example file (download)
    OK  tiny_feasible.csv: 12 performers, 6 performances
    !   5 things to check in this file
          row 3: duplicate of an earlier row (Person 0001, Bollywood (Open)); ignored
          Performer ids "John Smith" and "Jon Smith" look very similar. If they are the same person, ...
          ...

- **On upload:** `decode_text` then `parse_performers`. An `InputError` is shown as a red box listing every message, with its row number, and nothing else appears.
- **More than two columns:** the page reads the column names (`performer_file_columns`) and asks two questions, "Which column holds the performer's name or id?" and "Which column holds the performance?". It never guesses. This is the `--id-column` and `--performance-column` options.
- **Warnings** are shown in full and open by default, with the count in the heading. More than 20 are shortened with "... and N more", as in the command (`format_issues`).
- **A new file** clears every result and every pin (the old pins may name performances that no longer exist).
- A **"Clear all data"** button empties the session.

### 4.3 Find schedules tab

    Rest between a performer's performances (slots)  [ 1 ]  (help: 1 means never back to back)
    Breaks  [ 0 ]                                           (help: pinned breaks count towards this)

    Pins (optional): fix a performance or a break to a slot
      Slot [ 1 ]   Item [ Bollywood (Open) v ]   [ Add pin ]
      - Slot 1: Bollywood (Open)   [ Remove ]
      - Slot 12: a break           [ Remove ]

    Which schedules   [ 1-5 ]  [ Select all ]     (help: 1-5, 6-10, 1,4,9, 1-3,7,20-22 or all)
    > More options:  Shuffle seed [      ] [ Shuffle ]    Most schedules per run [ 100 ]    Longest search, seconds [ 30 ]

    [ Find schedules ]

- **Pins** are a guided form, not a table *(proposed, Q17)*. The item is chosen from a list of the show's performances plus "Break", so a typo cannot happen. The slot is a number from 1 up to the number of slots (performances + breaks). The form is testable (see section 6).
- **Pick:** the same syntax as `--pick`, read by `parse_selection` with the run's limit. Mistakes get the same plain message. "Select all" fills in `all`.
- **Shuffle** picks a random whole number and shows it in the seed box, so the result can be reproduced (the behaviour described in `schedule-finder.md`). The seed can also be typed.
- **Find schedules** calls `find_schedules` with `count = schedules_to_request(selection, limit)`, then `apply_selection` (D17, D19, D33).

Results appear below the button.

    OK  Found 5 schedules (numbers 1-5).
        More schedules exist after number 5.
        [ table: one row per slot, one column per schedule ]
        [ Download these schedules (CSV) ]   [ Show the next 5 ]
    Schedules found with a gap of 1. To see whether everyone could have a longer rest, run again with a gap of 2.   [ Try a gap of 2 ]
    (caption) Seed: default order. Search engine: OR-Tools 9.15.6755.

- **Table:** slots down, schedules across, each column headed `schedule_N` (its place in the list). Breaks are shown in grey and pinned slots are marked. Names are the performer file's display names.
- **Download:** the CSV from `format_schedules`, named by `schedules_file_name` (D43). The file goes straight to the schedule checker. Nothing is written to the computer's disk by the page itself.
- **Show the next 5** sets the pick to `next_pick(...)` (D44) and searches again from the start, skipping what came before (D33). It shows only when more schedules exist. The label says the real number.
- **Try a gap of 2** sets the gap to one more and searches again. It is a button the organiser presses, so the organiser stays in control (D14, D16). *(proposed: it runs the search immediately, and does not check in advance whether it will work.)*
- **Numbers that do not exist** are named with `format_missing`, as in the command.

When **no schedule exists**, a red box shows the heading and the reasons (the explanation from the finder, unchanged). Blocking pins are marked in the pin list ("These cannot all be kept") so the organiser can remove one. When the search was **stopped**, a yellow box says so in the finder's words and offers **Search for longer**, which doubles the time limit *(proposed)*. It never says "none exist" (D45).

**Stale results.** The settings used for a run are stored with its result. If any setting changes afterwards, the result is greyed and a line says "Settings changed. Press Find schedules to update." The page never shows a result that does not match the form.

### 4.4 Check a schedule tab

    Schedule file (CSV): one running order, or several side by side   [ upload ]
    Rest between a performer's performances (slots)  [ 1 ]

    Overview (when there are two or more):
      Schedule | Result | Slots | Breaks | Problems | Tightest gap
    schedule_2: INVALID   20 slots (2 breaks)
      Conflicting performance pairs (2)
        Contemporary (Open) (slot 2) and Tap (Foundations) (slot 4)   1 slot between, 2 needed   1 performer affected [v]
      ...
    [ Download the problems (CSV) ]
    1 of 12 schedules are invalid.

- The result is shown as soon as a file is uploaded or the gap changes. It uses `check_schedules` and `group_violations`.
- **Table of pairs:** one row per clashing pair, with the performers affected in an expander (the same two lists as the command: pairs first, then who is affected).
- **Structural problems** (missing, unknown or repeated performances) get their own box, with "Spacing was not checked", and the "Did you mean ..." hints.
- **More than 10 schedules:** valid ones appear only in the overview table (D28).
- **Warnings** about the schedule file and the performer file are shown in full above the results.
- **Download:** the violations CSV from `format_violations_csv`.

### 4.5 What the page remembers (`st.session_state`)

| Key | Holds |
|---|---|
| `performer_file` | The uploaded file's name and bytes |
| `columns` | The chosen id and performance columns, if the file needed them |
| `show` | The `PerformerLoad` (data and warnings) |
| `pins` | The pinned slots so far (position to item) |
| `form` | Gap, breaks, pick, seed, limit, time limit |
| `run` | The settings of the last search, its `FinderResult` and its `Picked` |

### 4.6 What the organiser sees when something goes wrong

| Situation | What the page does |
|---|---|
| File is not UTF-8 | Red box with the existing message ("Save As ... CSV UTF-8") |
| Performer or schedule file unusable | Red box listing every issue with its row number |
| Pick mistyped, or longer than the limit | The field's plain message (with an example) under the pick box; the search does not run |
| Pins do not fit the show | Red box with the finder's reasons |
| No schedule exists | Red box with reasons and marked pins |
| Time limit reached | Yellow box, never "none exist" |
| OR-Tools not installed | "The schedule finder is not installed on this computer. Ask whoever set it up to install it." The command to give them is shown in a small expander |
| An internal check failed (`RuntimeError`) | "Something went wrong inside the finder, and no schedule was shown." The details are in an expander, to copy into a bug report |
| Anything else unexpected | A short generic message, not a traceback *(proposed)* |

## 5. Core additions the UI needs

Small, pure, tested helpers, built **before** `app.py` (step U1). Each puts a rule or a sentence in the shared layer so the page and the command share it.

| Addition | Why |
|---|---|
| `io.decode_text(raw: bytes, name: str) -> str` | An upload arrives as bytes, not a path. Same UTF-8 and byte-order-mark handling and the same "CSV UTF-8" message as `read_text`, which then uses it. |
| `io.performer_file_columns(text: str) -> list[str]` | Fills the two column pickers (section 4.2). |
| `io.schedule_rows(schedules, performance_names) -> list[list[str]]` | The table of schedules shown on the page. `format_schedules` is rewritten to use it, so the page and the CSV cannot differ. |
| `selection.next_pick(selection, limit, last_number) -> str` | The "next batch" rule (D44) now lives inside `cli.py`. The page needs it too, so it moves here and `cli.py` calls it. |
| `report.format_found(count, numbers) -> str` | "Found 5 schedules (numbers 1-5)." The command's "Wrote ... to path" does not fit a page. |
| `report.no_schedules_heading(status) -> str` | The heading of the no-schedule box. `format_no_schedules` is rewritten to use it. |
| `report.overview_rows(checks) -> list[tuple[str, ...]]` | The overview table, including how "Problems" is counted. `format_overview` is rewritten to use it. |

## 6. Testing

- **The seven helpers:** ordinary tests in a new file, `tests/test_ui_helpers.py`. The existing test files are not touched, which keeps the context for that step small.
- **The page:** `tests/test_app.py` with Streamlit's `AppTest`, using the example datasets. It uploads files, presses buttons and reads what is on the page. Covered: loading and warnings, the column pickers, the checker (valid, invalid, structural problems, several schedules), the finder (found, more exist, show the next batch, larger gap, none exist, stopped, stale results, bad pick, pins) and the missing-OR-Tools message. `AppTest` cannot see layout or colour.
- **By hand, once, before release:** the checklist in step U5, in a real browser, with the real show file. It covers what `AppTest` cannot: a long search showing its spinner, the downloads, and the table on a small screen.

## 7. Files

| File | Purpose |
|---|---|
| `src/performance_scheduling/app.py` | The page. The only file that imports Streamlit |
| `.streamlit/config.toml` | Usage statistics off, hidden tracebacks, a smaller upload limit (the performer file is small) |
| `tests/test_ui_helpers.py`, `tests/test_app.py` | Tests (section 6) |
| `run_app.bat` (or a `schedule-app` command) | One-click start for Windows (step U5) |

The `ui` extra in `pyproject.toml` gets a version range for `streamlit` in step U5 (it is unpinned now).

## 8. Privacy (decision D49)

Performer names are personal data (`repo-structure.md`, data folder policy).

- The page runs **on the user's own computer** by default, and the data stays in memory for the session.
- **No usage statistics** are sent (`gatherUsageStats = false`).
- **Nothing is written to disk** except a file the organiser downloads. No on-disk caching (`persist="disk"` is never used).
- **No names in logs or error messages** beyond the ones the organiser has already seen on screen.
- **Do not host it publicly with real data.** Putting it on a shared server is a separate decision (Q16) and needs `data-privacy.md` first.

## 9. Build steps

| Step | What | Done when |
|---|---|---|
| U1 | The seven core additions (section 5) with tests | `pytest` and `ruff` pass; `cli.py` behaves exactly as before |
| U2 | `app.py` skeleton, "Your show" section, `config.toml` | Upload, warnings and column pickers work in `AppTest` |
| U3 | "Check a schedule" tab | Every checker case in section 6 passes |
| U4 | "Find schedules" tab | Every finder case in section 6 passes |
| U5 | Launcher, `ui` extra version range, README, manual checklist | A non-technical person can start it and find a schedule |

## 10. Out of scope for the first version

Excel (`.xlsx`) upload (CSV only, D5); editing a running order by hand in the page; loading pins from a file; saving a project or history; accounts or a shared hosted version (Q16); printing or PDF; charts; a "my schedule" view for one performer; other languages.
