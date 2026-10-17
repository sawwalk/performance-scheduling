# Schedule finder

**Status:** DRAFT. The search engine was settled on 2026-10-17 (D29): OR-Tools CP-SAT.

## Purpose

Produce running orders that satisfy the spacing rule, respect any positions the organiser
has pinned, and hand out further schedules on demand, so the organiser can compare options.

## Inputs

- Performer CSV (see `input-data.md`)
- `k`, the required gap (default 1)
- Number of breaks (default 0; pinned breaks count towards this)
- Optional fixed-positions CSV (see `input-data.md`)
- Which schedules to output, by their number in the finder's list (default `1-5`); see "Choosing schedules"
- Maximum number of schedules per run (default 100)
- Optional shuffle seed (a whole number). Without one, a fixed default seed is used
- Time limit for one run (proposed default 30 seconds; see Q13)

Total slots `N = number of performances + number of breaks`.

## Design

**Engine.** The search is done by OR-Tools CP-SAT, a constraint solver: we describe the
rules and it does the searching. It sits behind one function in `solver.py`, so the rest of
the project never needs to know it is there. Why it was chosen, and what the experiment
showed, is in `search-approaches.md`.

**Model.** Each performance gets a variable holding its slot number, 1 to N. Rules given to the solver:

- No two performances share a slot.
- For every conflicting pair of performances at positions `p`, `q`: `|p - q| >= k + 1`. The solver is told "either A is at least k + 1 slots before B, or B is at least k + 1 slots before A", using one yes/no helper per pair. Positions decide the helper, so no schedule is listed twice (to be confirmed against brute-force counts in the tests). With `k = 0` no spacing rules are added.
- A pinned performance is fixed to its slot. A pinned break stops every performance from using that slot.

Breaks are simply the slots no performance uses, so they are interchangeable automatically (D11).

**Listing schedules.** The solver lists valid schedules one after another. The list is:

- **Complete:** every valid schedule is eventually listed, none twice.
- **Repeatable:** the same input, gap, breaks, pins, seed and OR-Tools version always give the same list (the solver is run on one thread, which is what makes this possible).
- **Not in dictionary order.** The order is the solver's own. (D30)

Schedules are numbered 1, 2, 3, ... by their place in this list. If OR-Tools is upgraded the list may come out in a different order, so "schedule 7" could become a different schedule. The tool therefore prints the OR-Tools version, and a number saved in an output file never changes (D32). Repeatability was tested only on one machine, running the same code twice.

**Showing more.** There is no bookmark. Each run starts the solver again and stops once it has reached the highest number chosen; the schedules before the first one chosen are generated and discarded (D33). This is cheap at the usual limits: in the experiment 100 schedules from the real show took 0.12 s, and 1,000 from a synthetic 20-performance show took 0.89 s.

**Result status.** A run ends in one of three ways, and the tool always says which:

- *found:* the schedules asked for were produced. A run asks the solver for one more than the highest number chosen, so it can say whether more exist.
- *exhausted:* the solver finished the whole search, so no more schedules exist. This is a proof. If fewer schedules exist than were asked for, those that exist are written and the tool says so.
- *stopped:* the time limit was reached. This proves nothing either way, and the tool never presents it as "none exist". Any schedules found before the stop are still written.

**Checks before searching.** Cheap tests catch impossible requests at once and give a specific reason in plain language:

- Contradicting pins (two items in one slot, a pin outside 1..N, more pinned breaks than breaks)
- A performer who needs more slots than exist: `(m - 1)(k + 1) + 1 > N`
- A group of `m` performances that all clash with each other needs the same number of slots, `(m - 1)(k + 1) + 1`. (Example from the real show: its largest such group has 6 performances, so k = 3 needs 21 slots against 19 performances.)
- Two pinned performances that conflict but are too close together

The solver proves "no schedule exists" in a fraction of a second in the experiment (0.01 to 1.7 s), so these checks are for giving a clear explanation, not for speed. They are necessary but not sufficient: passing them does not mean a schedule exists (`test-datasets.md`, `tiny_needs_breaks.csv`).

**Cross-check.** Every schedule produced is passed through the schedule checker before
being written. This guarantees the two tools agree.

**Scale note.** 20 performances can be ordered in an astronomically large number of ways.
With few conflicts the number of valid schedules is enormous, so "all schedules" is only
realistic once enough items are pinned. The tool can show a count capped at a limit
("at least 10,000") rather than attempting to count everything.

**What to expect from the order.** Neighbouring schedules in the list still look alike: in the
experiment, neighbouring schedules differed in about 3 slots out of 20. To see more varied options, pin
more items, or give a **shuffle seed**. A seed changes where the list starts. It is still complete
and repeatable: the same input and the same seed give the same list. How the seed does this is
decided by a small test when `solver.py` is built (Q14, D31). If the organiser asks for a shuffle
without choosing a number, the tool chooses one and displays it, so the result can be reproduced.

## Features

1. Find valid schedules for a given `k` and number of breaks
2. Pin performances and breaks to slots (opening and closing acts, mid-show interval)
3. Produce further schedules on demand, never repeating one
4. Report when the schedules are exhausted ("no more schedules")
5. Explain infeasibility (below)
6. **Prompt to try a larger gap.** After a successful run, show a short message such as: "Schedules found with a gap of 1. To see whether everyone could have a longer rest, run again with a gap of 2." The tool does not run the larger gap itself. In the UI this is a button.

**Infeasibility help.** If no schedule exists, the tool says why where it can:

- Which pre-check failed (e.g. "Sam is in 6 performances; with k = 2 that needs 16 slots but the show has 14")
- Which pinned items cannot all be kept. Each pin is given to the solver as something it may switch on or off. When no schedule exists, the solver reports a set of pins that cannot all hold together, for example "Slot 1 (Bollywood (Open)) and slot 2 (Bollywood (Foundations)) cannot both be kept". The organiser relaxes at least one and runs again (D34).
- If the solver names no pins, no schedule exists even with every pin removed, and the message says so.

The reported set explains the failure but is not guaranteed to be the smallest, and there can be other sets. It was tried on one case in the experiment and named the right pins.

## Choosing schedules

Schedules are numbered 1, 2, 3, ... by their place in the finder's list. The `--pick` option accepts:

| You type | You get |
|---|---|
| `--pick 1-5` (the default) | Schedules 1 to 5 |
| `--pick 6-10` | The next five |
| `--pick 1,4,9` | Exactly schedules 1, 4 and 9 |
| `--pick 1-3,7,20-22` | A mix of ranges and single numbers |
| `--pick all` | Every schedule, up to the limit |

Rules:
- Duplicates are ignored and the schedules are written in ascending order.
- To output schedule 9 the solver must list 1 to 8 first; they are generated and discarded, not saved.
- The limit (default 100, change with `--limit`) caps the number written. With `all`, the first 100 are written and the tool says whether more exist ("showing 100 of at least 100; pin more items or pick another range"). An explicit pick longer than the limit is refused with a message rather than silently shortened.
- If fewer schedules exist than requested, those that exist are written and the missing numbers are listed.
- The same syntax is used by the UI, as a text box plus a "Select all" button.
- Spaces do not matter (`1-3, 7` is fine) and long dashes copied from a word processor are read as hyphens.
- `all` must be used on its own.
- Mistakes get a plain message that quotes the part that is wrong and shows an example: letters, empty items (`1,,3`), `0`, a backwards range (`4-1`, with the fix suggested), or a number above the highest available.
- Under the hood the choice is stored as joined ranges, so a typo like `1-1000000000000` is refused immediately and never builds a huge list.

## Usage (planned; the exact command names may change)

    schedule-finder --performers data/private/performers.csv --gap 1 --breaks 2 --fixed data/private/fixed.csv --pick 1-5 --out output/

`--pick` chooses which schedules to write (see "Choosing schedules" above). `--seed 42` changes where the list starts (any whole number works; the same number always gives the same list).

After each run the tool prints the exact command for the next batch, so nothing has to be worked out by hand.

Options: `--gap`, `--breaks`, `--fixed`, `--pick`, `--limit`, `--seed`, `--time-limit` (proposed, Q13), `--out`, `--id-column`, `--performance-column`.
The UI will present the same choices as form fields, with a "Show more schedules" button.

## Output

One CSV file in the output folder (`schedules.csv`), in the side-by-side format from
`input-data.md`: a `position` column, then one column per chosen schedule, named by its place
in the list (`schedule_1`, `schedule_4`, `schedule_9`, and so on). When a seed is used it is also added to the file name (e.g. `schedules_seed42.csv`).
Breaks appear as `BREAK`. The file can be given to the checker directly.

On screen:

- How many schedules were found, and whether more exist (found / exhausted / stopped)
- The prompt to try a larger gap (feature 6), a plain invitation with no check of whether it will work
- The seed in use, if any, the OR-Tools version, and the command for the next batch
- If none exist: the infeasibility explanation

## Edge cases to test

- No conflicts at all (every order valid)
- A performer in every performance (usually infeasible)
- Everything pinned (exactly one schedule, or zero)
- `k` too large
- Pinned break positions that cannot all be satisfied by the break count
- Fewer schedules exist than were requested
- Exhausting all schedules on a small example and comparing with a brute-force count, **including a hand-made case where a performer with two performances can start early at k = 2** (5 performances: A, B, C and X1, X2 with X in both X1 and X2; brute force gives 36 schedules). The tiny datasets alone did not catch the backtracking fault described in `search-approaches.md`, section 5
- No schedule is listed twice (the helper variables in the model must not create duplicates)
- Same input run twice gives the same list
- Same seed gives the same list; on small examples, different seeds give the same set of schedules (a different order is expected; see Q14)
- A pick that names schedules beyond the end of the list (the ones that exist are written, and the tool says which do not)
- `all` on a list longer than the limit, and an explicit pick longer than the limit
- Pick syntax: single numbers, ranges, mixed lists, duplicates, spaces, and invalid text
- Time limit reached: status is "stopped", schedules found so far are still written, and the message does not say "none exist"
- No schedule exists: the pre-check message is shown when one applies; otherwise the blocking pins are named; if no pin is named, the message says no schedule exists even without pins
