# Schedule finder

**Status:** DRAFT

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
- Optional shuffle seed (a whole number). Without one, the fixed default order is used

Total slots `N = number of performances + number of breaks`.

## Design

**Model.** Each performance is assigned a distinct position in 1..N. Breaks occupy the
remaining positions and are interchangeable. For every conflicting pair of performances
at positions `p`, `q`: `|p - q| >= k + 1`. Pinned items are fixed to their positions.

**Systematic enumeration.** Schedules are produced in a fixed, repeatable order, one at a
time, so the organiser can ask for "the next one" and eventually see all of them. The same
input always gives the same list. The search engine is an open decision (custom
backtracking or OR-Tools CP-SAT); the options, plans and the experiment to choose are in
`search-approaches.md`. The engine sits behind one function, so it can be changed later.

**Result status.** A search ends in one of three ways, and the tool always says which:
*found*, *exhausted* (the whole search finished, so no more schedules exist) or *stopped*
(a time or size limit was reached; this proves nothing either way).

**Checks before searching.** Cheap tests catch impossible requests immediately:

- Contradicting pins (two items in one slot, a pin outside 1..N)
- A performer who needs more slots than exist: `(m - 1)(k + 1) + 1 > N`
- Two pinned performances that conflict but are too close together

**Cross-check.** Every schedule produced is passed through the schedule checker before
being written. This guarantees the two tools agree.

**Scale note.** 20 performances can be ordered in an astronomically large number of ways.
With few conflicts the number of valid schedules is enormous, so "all schedules" is only
realistic once enough items are pinned. The tool can show a count capped at a limit
("at least 10,000") rather than attempting to count everything.

**What to expect from systematic order.** Schedules are listed in a fixed order, so
neighbouring ones in the list look very similar (they differ near the end). There are two ways to see more varied options:
pin more items, or give a **shuffle seed**. A seed reorders the order in which items are tried, so the list starts
somewhere different. The list is still complete (nothing is missed) and repeatable: the same input and the
same seed always give the same list. If the organiser asks for a shuffle without choosing a number, the tool
chooses one and displays it, so the result can be reproduced.

## Features

1. Find valid schedules for a given `k` and number of breaks
2. Pin performances and breaks to slots (opening and closing acts, mid-show interval)
3. Produce further schedules on demand, never repeating one
4. Report when the schedules are exhausted ("no more schedules")
5. Explain infeasibility (below)
6. **Prompt to try a larger gap.** After a successful run, show a short message such as: "Schedules found with a gap of 1. To see whether everyone could have a longer rest, run again with a gap of 2." The tool does not run the larger gap itself. In the UI this is a button.

**Infeasibility help.** If no schedule exists, the tool says why where it can:

- Which pre-check failed (e.g. "Sam is in 6 performances; with k = 2 that needs 16 slots but the show has 14")
- Which pinned items are responsible: the tool retries with each pin removed in turn and lists the pins whose removal makes a schedule possible. This lets the organiser decide which constraint to relax.

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
- To output schedule 9 the search must pass through 1 to 8 first; they are generated and discarded, not saved.
- The limit (default 100, change with `--limit`) caps the number written. With `all`, the first 100 are written and the tool says whether more exist ("showing 100 of at least 100; pin more items or pick another range"). An explicit pick longer than the limit is refused with a message rather than silently shortened.
- If fewer schedules exist than requested, those that exist are written and the missing numbers are listed.
- The same syntax is used by the UI, as a text box plus a "Select all" button.

## Usage (planned; the exact command names may change)

    schedule-finder --performers data/private/performers.csv --gap 1 --breaks 2 --fixed data/private/fixed.csv --pick 1-5 --out output/

`--pick` chooses which schedules to write (see "Choosing schedules" below). `--seed 42` shuffles the order (any whole number works; the same number always gives the same list).

After each run the tool prints the exact command for the next batch, so nothing has to be worked out by hand.

Options: `--gap`, `--breaks`, `--fixed`, `--pick`, `--limit`, `--seed`, `--out`, `--id-column`, `--performance-column`.
The UI will present the same choices as form fields, with a "Show more schedules" button.

## Output

One CSV file in the output folder (`schedules.csv`), in the side-by-side format from
`input-data.md`: a `position` column, then one column per chosen schedule, named by its place
in the list (`schedule_1`, `schedule_4`, `schedule_9`, and so on). When a seed is used it is also added to the file name (e.g. `schedules_seed42.csv`).
Breaks appear as `BREAK`. The file can be given to the checker directly.

On screen:

- How many schedules were found, and whether more exist (found / exhausted / stopped)
- The prompt to try a larger gap (feature 6), a plain invitation with no check of whether it will work
- The seed in use, if any, and the command for the next batch
- If none exist: the infeasibility explanation

## Edge cases to test

- No conflicts at all (every order valid)
- A performer in every performance (usually infeasible)
- Everything pinned (exactly one schedule, or zero)
- `k` too large
- Pinned break positions that cannot all be satisfied by the break count
- Fewer schedules exist than were requested
- Exhausting all schedules on a small example and comparing with a brute-force count
- Same input run twice gives the same list
- Same seed gives the same list; different seeds give the same set of schedules in a different order
- A pick that names schedules beyond the end of the list (the ones that exist are written, and the tool says which do not)
- `all` on a list longer than the limit, and an explicit pick longer than the limit
- Pick syntax: single numbers, ranges, mixed lists, duplicates, spaces, and invalid text
