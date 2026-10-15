# Schedule checker

**Status:** DRAFT

## Purpose

Tell an organiser whether a proposed running order, including breaks, satisfies the
spacing rule, and if not, exactly which performers are affected and where.

## Inputs

- Performer CSV (see `input-data.md`)
- Schedule CSV (see `input-data.md`): one schedule column, or several side by side
- `k`, the required gap (default 1)

## Design

When the file holds several schedules, each column is checked independently with the steps below, and results are reported per schedule.

The checker uses no solver. It is a sequence of simple checks, in two stages.

**Stage 1: structure.** The schedule must be a legitimate arrangement before spacing means anything.

- Every performance in the performer CSV appears in the schedule (otherwise: reported as missing)
- No unknown performance names (reported with the spelling the organiser used; if a real name is very close, `Did you mean "..."?` is added. This is only a hint: nothing is changed)
- No repeated performance within a schedule (reported with its positions)

Position numbers (1 to N, no gaps or repeats) and `BREAK` are handled earlier, when the file is read (see `input-data.md`).

If stage 1 finds errors, they are reported and spacing is not checked.

**Stage 2: spacing.**

1. Map each performance to its position.
2. For each performer, collect the positions of their performances and sort them.
3. Compare each *consecutive* pair of positions. If `later - earlier < k + 1` (that is, fewer than `k` slots between them), record a violation. One violation is recorded per neighbouring pair, so a performer in three performances can have two. (Checking consecutive pairs is enough: if every neighbouring pair is far enough apart, all pairs are.)
4. Also compute the smallest number of slots between any two performances of the same performer anywhere in the schedule.

All logic lives in `validator.py` and returns data (a `ScheduleCheck` per schedule); the CLI and UI only format it. It needs only the performer data; the conflict map is for the finder. `k = 0` allows anything, so only the structure is checked; a negative `k` is refused.

## Features

- Breaks count as slots
- Any `k`, not just 1
- Violations name the performer, both performances, both positions, and how many slots lie between them
- Reports the **achieved gap** (`smallest_gap`): the fewest slots between two performances of the same performer. The schedule satisfies every `k` up to this number, so the organiser can see "this order actually gives everyone at least 2 slots of rest". It is blank when the spacing was not checked (structural problems) or when nobody is in more than one performance.
- Warnings for near-duplicate names carried over from loading

## Usage

    schedule-checker --performers data/private/performers.csv --schedule data/private/order.csv --gap 1

| Option | Meaning |
|---|---|
| `--performers FILE` | Performer CSV (required) |
| `--schedule FILE` | Schedule CSV: a `position` column and one or more schedule columns (required) |
| `--gap N` | Fewest slots allowed between a performer's performances. Default 1; 0 checks only the structure |
| `--schedule-column NAME` | Check only this schedule column (default: all). Case and spaces do not matter |
| `--id-column NAME`, `--performance-column NAME` | Which columns of the performer file to use, when it has more than two |
| `--report-csv FILE` | Also write every violation to a CSV file |

The command is registered by `pip install -e ".[dev]"`. After pulling a change to `pyproject.toml`, run that again.

## Output

On screen, in this order:

1. Three lines naming the files and the gap checked
2. **Warnings about the performer file** (including possible typos in names), in full, before any results. These are the organiser's only prompt to fix the data, so they are never hidden. More than 20 are shortened with "... and N more"
3. Warnings about the schedule file
4. With more than one schedule, an **overview table**: schedule, result, slots, breaks, number of problems, tightest gap
5. A write-up per schedule: `VALID` or `INVALID`, slot and break counts, then either a section of structural problems (spacing not checked) or the spacing problems in **two lists with `=====` section breaks**: first the conflicting pairs of performances, then, for each pair, who is affected. The tightest spacing follows. For example:

```
schedule_2: INVALID
  20 slots (2 breaks).

  ===== CONFLICTING PERFORMANCE PAIRS (2) =====
   1. Contemporary (Open) (slot 2) and Tap (Foundations) (slot 4): 1 slot between, at least 2 needed (1 performer affected).
   2. Hip Hop (Foundations) (slot 3) and Jazz (Open) (slot 5): 1 slot between, at least 2 needed (1 performer affected).

  ===== WHO IS AFFECTED (2 performers) =====
   1. Contemporary (Open) and Tap (Foundations)
        - Person 0005
   2. Hip Hop (Foundations) and Jazz (Open)
        - Person 0002
  ===== END OF SPACING PROBLEMS =====

  Tightest spacing: 1 slot between a performer's performances.
```
6. With more than one schedule, a closing line such as `1 of 12 schedules are invalid.`

With more than 10 schedules, valid ones appear only in the overview table; full write-ups are kept for the others.

Names are the display names from the performer file. Characters a Windows console cannot show appear as `?` instead of stopping the program.

**Command line and UI.** The terminal text above is the command line's layout. The UI shows the same facts with the same sentences, but lays them out its own way (for example a table of conflicting pairs with expandable rows for the performers affected). Both use the same grouping (`group_violations` in `report.py`), so they cannot disagree.

Optional CSV report (`--report-csv`), one row per violation (one per performer, not grouped, so it can be filtered in Excel), names as in the performer file, saved with a byte-order mark so Excel shows accents correctly. A valid run writes just the header row:

    schedule,performer,performance_a,position_a,performance_b,position_b,slots_between,required

### Exit codes

| Code | Meaning |
|---|---|
| 0 | Every schedule checked is valid |
| 1 | At least one schedule is invalid |
| 2 | The command or input files could not be used: a file is missing or unusable, a column was not found, the report could not be written, or the command was written wrongly (including a bad `--gap`). Problems with both files are reported together |

## Edge cases to test

- Performer in a single performance (never a violation)
- Two performances separated only by a break
- Back-to-back performances (violation at k = 1)
- `k` larger than the schedule length
- Performance missing from, or repeated in, the schedule
- Name typos and case differences between the two files
