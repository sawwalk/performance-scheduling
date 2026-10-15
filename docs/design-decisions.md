# Design decisions

**Status:** DRAFT. Add a row whenever a decision is made or changed.

## Decisions

| # | Date | Decision | Reason |
|---|---|---|---|
| D1 | 2026-10-10 | Breaks count as slots for spacing. | One break between two performances satisfies "at least one break". |
| D2 | 2026-10-10 | No separate "guest performance" concept; guests are breaks. | Simpler model; guests have no conflicts. |
| D3 | 2026-10-10 | Plan for a simple UI for non-technical organisers. | Core logic stays separate from any UI so it can be added later. |
| D4 | 2026-10-10 | Finder enumerates schedules systematically (not randomly). | Shows every option when options are sparse; when plentiful, organiser pins more items. |
| D5 | 2026-10-10 | Output format is CSV. | Simple; other formats may come later. |
| D6 | 2026-10-10 | Organiser can fix positions of performances and breaks. | Supports chosen opening/closing acts; user can remove constraints if none are feasible. |
| D7 | 2026-10-10 | Tools named "schedule checker" and "schedule finder". | Clearer than Tool 1 / Tool 2. |
| D8 | 2026-10-10 | Shared core modules, thin tools on top. | Checker and finder must agree on what "valid" means. |
| D9 | 2026-10-12 | Number of breaks is a parameter; pinned breaks count towards it. (Q1) | Simple and predictable. |
| D10 | 2026-10-12 | Fixed positions are numbered from 1. (Q4) | Organisers count from 1. |
| D11 | 2026-10-12 | Breaks are interchangeable when enumerating. (Q5) | Schedules differing only by which break is which are the same schedule. |
| D12 | 2026-10-12 | Multiple schedules are written to **one CSV file, side by side**: a `position` column and one column per schedule. (Q3) | Easier for the organiser to compare options. Supersedes the earlier "one file each" proposal. |
| D13 | 2026-10-12 | The checker reads the same side-by-side format, so a file with one schedule column is the single-schedule case. | Finder output can be fed directly to the checker. |
| D14 | 2026-10-12 | No automatic "find the largest k". After a successful run the tool shows a short prompt inviting the user to try a larger k in a later run. (Q6) | Keeps the finder simple; the organiser stays in control. Supersedes the earlier proposal. |
| D15 | 2026-10-12 | The finder has an optional shuffle: a **seed** number that reorders the order in which items are tried. Same seed gives the same list; with no seed the fixed default order is used. (Q8) | Early schedules in a fixed order look alike; shuffling starts the list somewhere different while staying complete and repeatable. |
| D16 | 2026-10-12 | The "try a larger gap" prompt after a successful run is a plain invitation with no feasibility check. (Q7) | Keeps the finder simple. |
| D17 | 2026-10-12 | The finder lets the user choose which schedules to output from its numbered list using one option, `--pick`: a single number, a range (`6-10`), a comma-separated list mixing both (`1,4,9` or `1-3,7,20-22`), or `all`. After each run the tool prints the exact command for the next batch. (Q9) | Covers connected batches and unconnected choices with one rule; organisers who are not comfortable with the command line do not have to work it out. Replaces the earlier `--start`/`--count` idea. |
| D18 | 2026-10-12 | When a seed is used, it is printed on screen and added to the output file name (e.g. `schedules_seed42.csv`). (Q10) | The result can be reproduced. |
| D19 | 2026-10-12 | A limit caps how many schedules one run writes (default 100, confirmed 2026-10-12; changeable with `--limit`). With `all`, the first `limit` schedules are written and the tool says whether more exist. An explicit pick longer than the limit is refused with a message, not silently shortened. | Avoids enormous tables; never hides that results were cut off. |
| D20 | 2026-10-12 | Schedules are numbered by their place in the finder's list (with the same seed, the same input always gives the same numbering). Output columns keep those numbers (`schedule_1`, `schedule_4`, `schedule_9`). | A picked schedule can be found again later. |
| D21 | 2026-10-13 | Suspected typos in names are reported as warnings only. The tool never changes names because they look alike; the organiser corrects the source file. | Keeps one source of truth: the data file itself. |
| D22 | 2026-10-15 | The schedule reader checks the file (columns, position numbers) but not the contents. Unknown, missing or repeated performances are loaded as written and reported by the schedule checker. | The checker's job is to say exactly what is wrong with a proposed order; a reader that refused such files would stop it. |
| D23 | 2026-10-15 | The checker records one violation per pair of neighbouring performances of a performer (not one per performer, and not every pair). | Easy to scan, and checking neighbours is enough. |
| D24 | 2026-10-15 | If a schedule has structural problems (missing, unknown or repeated performances), the spacing check is skipped for it. | Spacing is meaningless without a sound arrangement. |
| D25 | 2026-10-15 | An unknown performance name in a schedule gets a "Did you mean..." hint when a real name is very close (similarity 0.85). Nothing is changed automatically. | Helps organisers fix the file themselves, consistent with D21. |
| D26 | 2026-10-15 | Result wording lives in `report.py` (shared layer), not in `cli.py`. | The command line and the UI must show identical wording and cannot import from each other. |
| D27 | 2026-10-15 | The command is `schedule-checker`. Exit codes: 0 all valid, 1 any invalid, 2 input or command problem. | A script can tell "invalid" from "could not check". |
| D28 | 2026-10-15 | With more than 10 schedules, valid ones appear only in the overview table. | Keeps long runs readable. |

## Open questions

| # | Question | Notes |
|---|---|---|
| Q2 | Enumeration engine: OR-Tools CP-SAT or custom backtracking? | See `search-approaches.md`. Settled by a notebook experiment. Tentative leaning: backtracking first, CP-SAT as benchmark and fallback. |
| Q12 | Where does the real anonymised show file (`performers_sample_data1.csv`) live? | Default: `data/private/` (gitignored). It can go in `data/examples/` if you are comfortable publishing it. Tests only use the synthetic files. |
