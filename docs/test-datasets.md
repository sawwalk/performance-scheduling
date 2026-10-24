# Test datasets

**Status:** DRAFT

All files live in `data/examples/`, are synthetic (names are `Person 0001` and so on), and are safe to commit.
Real or anonymised show data goes in `data/private/` (gitignored) and is never used by tests.

Column headers vary on purpose: most files use `full name,style` (like the real show file), one uses `id,performance`.

## Performer files

"Truth" below means the answer is known exactly (brute force over every ordering, only possible for 6 or fewer performances).
"Rough" means a quick, unoptimised search was run once; it is **not** a proof, and will be replaced by real results once the finder exists.

| File | Size | Purpose | What is known |
|---|---|---|---|
| `tiny_feasible.csv` | 6 performances, 12 performers | First end-to-end test; enumeration against brute force | Truth: valid schedules at k=1: 8 (0 breaks), 152 (1 break), 1,104 (2 breaks). At k=2: 0 (0 breaks), 8 (1 break), 128 (2 breaks). |
| `tiny_needs_breaks.csv` | 4 performances, 5 performers | Infeasible without breaks; checks break handling and the infeasibility message | Truth: k=1 has 0 schedules with 0 or 1 break, and 12 with 2 breaks. Note: the span rule alone suggests 1 break might work (one performer is in 3 of 4 performances), so this also shows the span rule is necessary but not sufficient. |
| `tiny_no_conflicts.csv` | 6 performances, 12 performers, nobody in two performances | Every ordering valid; check counting and the limit | Truth: 720 schedules with 0 breaks, 5,040 with 1, 20,160 with 2, for any k. |
| `messy_input.csv` | 13 rows, columns `id,performance`, UTF-8 with byte-order mark | Tests every cleaning rule and warning | See below |
| `typical_20_performances.csv` | 20 performances, 120 performers, 253 rows (1 to 4 performances each) | Realistic size, like the real show | Rough: k=1 easy with 0 breaks; k=2 impossible with 0 breaks; k=2 found with 4 breaks; k=3 impossible with 0 or 2 breaks. |
| `one_busy_performer.csv` | The typical set plus one performer in 9 performances | Span-rule pre-check and break handling | Rough: k=1 with 0 breaks not decided by the quick search; k=1 found with 2 breaks; k=2 impossible with 0 breaks (a performer in 9 performances needs 25 slots at k=2, the show has 20). |
| `dense_overlap.csv` | 20 performances, 40 performers in 3 to 5 each | Many conflicts: feasible at k=1, tight beyond | Rough: k=1 found with 0 breaks; k=2 impossible with 0 breaks; k=2 found with 4 breaks. |
| `impossible_dense.csv` | 20 performances, 70 performers in 4 to 6 each | Infeasible in practice; tests diagnostics and the stopped/exhausted distinction | Rough: k=1 impossible with 0 or 2 breaks; with 4 breaks the quick search found none after a long search; k=2 impossible with 0, 2 or 4 breaks. |

The loader is tested against every performer file here (`tests/test_io.py`): the counts of performers, performances and rows below are checked, and all files except `messy_input.csv` must load with no warnings.

### What `messy_input.csv` should produce after cleaning

- 13 rows read; 2 dropped as blank (one empty id, one empty performance); 1 duplicate merged (`Person 0001` twice, one with a trailing space) leaves **10 distinct rows**
- **7 performers** and **5 performances**
- Case and spacing are ignored when matching: `  person 0002` with `bollywood (open)` is the same performer and performance as `Person 0002` and `Bollywood (Open)`; `Jazz  (Open)` (double space) equals `Jazz (Open)`
- 5 warnings: the duplicate row (row 3), the two rows with a missing value (rows 10 and 11), near-duplicate ids (`Jon Smith` and `John Smith`), and near-duplicate performance names (`Tap (Foundations)` and `Tap (Foundation)`). `Person 0001` to `Person 0006` are not flagged against each other.

## Schedule files (for the checker), all for `tiny_feasible.csv`

| File | Purpose | Expected checker result at k=1 |
|---|---|---|
| `tiny_feasible_schedule_valid.csv` | One valid schedule | VALID |
| `tiny_feasible_schedule_invalid.csv` | The valid one with two slots swapped | INVALID: Person 0006 is in Bollywood (Open) at slot 3 and Tap (Foundations) at slot 4, 0 slots between, 1 required |
| `tiny_feasible_schedule_broken.csv` | Structural errors: a performance missing, one repeated, and an unknown name (`Salsa (Open)`) | Structural errors reported; spacing not checked |
| `tiny_feasible_schedules_all8.csv` | All 8 valid schedules side by side (the order of the columns is not significant) | 8 results, all VALID; also an example of the side-by-side format |

## Fixed-positions files (for the finder), for `tiny_feasible.csv`

| File | Purpose | What is known |
|---|---|---|
| `tiny_feasible_pins.csv` | Pins `Bollywood (Open)` to slot 1. Used by the README example and the finder tests | Truth (brute force, checked in `tests/test_solver.py`): at k=1 there are 2 schedules with 0 breaks and 28 with 1 break |

## Ideas for later datasets

- A show with breaks pre-pinned at the start and end, with a matching fixed-positions file
- A file where a performer has the same id in different spellings (id near-duplicates inside a larger show)
- A very large show (40 performances) to see where the search slows down
- The real anonymised file (`performers_sample_data1.csv`) kept in `data/private/`, used only for manual trials
