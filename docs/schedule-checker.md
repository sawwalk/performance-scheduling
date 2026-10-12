# Schedule checker

**Status:** DRAFT

## Purpose

Tell an organiser whether a proposed running order, including breaks, satisfies the
spacing rule, and if not, exactly which performers are affected and where.

## Inputs

- Performer CSV (see `input-data.md`)
- Schedule CSV (see `input-data.md`)
- `k`, the required gap (default 1)

## Design

The checker uses no solver. It is a sequence of simple checks, in two stages.

**Stage 1: structure.** The schedule must be a legitimate arrangement before spacing means anything.

- Every performance in the performer CSV appears exactly once
- No unknown performance names
- Positions are 1..N with no gaps or repeats
- `BREAK` rows are recognised

If stage 1 finds errors, they are reported and spacing is not checked.

**Stage 2: spacing.**

1. Map each performance to its position.
2. For each performer, collect the positions of their performances and sort them.
3. Compare each *consecutive* pair of positions. If `later - earlier < k + 1`, record a violation. (Checking consecutive pairs is enough: if every neighbouring pair is far enough apart, all pairs are.)
4. Also compute the smallest gap that actually occurs for each performer.

All logic lives in `validator.py` and returns data; the CLI and UI only format it.

## Features

- Breaks count as slots
- Any `k`, not just 1
- Violations name the performer, both performances, both positions, and how many slots lie between them
- Reports the **achieved gap**: the largest `k` this schedule satisfies for everyone, so the organiser can see "this order actually gives everyone 2 slots of rest"
- Warnings for near-duplicate names carried over from loading

## Usage (planned; the exact command names may change)

    schedule-checker --performers data/private/performers.csv --schedule data/private/order.csv --gap 1

Options: `--gap` (default 1), `--id-column`, `--performance-column`, `--report-csv` (write violations to a file).

## Output

On screen:

- **Result:** `VALID` or `INVALID`
- Summary: number of slots, number of breaks, `k` checked, achieved gap
- For each violation: performer, performance A at position p, performance B at position q, slots between, slots required
- Structural errors and warnings, if any

Optional CSV report, one row per violation:

    performer,performance_a,position_a,performance_b,position_b,slots_between,required

Exit status is 0 when valid and non-zero otherwise, so the checker can be used in scripts.

## Edge cases to test

- Performer in a single performance (never a violation)
- Two performances separated only by a break
- Back-to-back performances (violation at k = 1)
- `k` larger than the schedule length
- Performance missing from, or repeated in, the schedule
- Name typos and case differences between the two files
