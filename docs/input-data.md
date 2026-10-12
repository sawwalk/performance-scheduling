# Input data formats

**Status:** DRAFT

Three kinds of input are used.

| Input | Used by | Required? |
|---|---|---|
| Performer CSV | checker and finder | Yes |
| Schedule CSV (a proposed running order) | checker | Yes, for the checker |
| Fixed-positions CSV | finder | Optional |

## 1. Performer CSV

One row per performer per performance.

| Column | Meaning |
|---|---|
| id column | Uniquely identifies the performer (full name, email or performer id) |
| performance column | The performance name, e.g. `Bollywood (Open)` |

Example:

```
full name,performance
name1,Bollywood
name2,Jazz
name2,Hip Hop
name3,Bollywood
name3,Jazz
name3,K-pop
```

Real files may use other headers. The anonymised show file uses `full name,style`; with exactly two columns the tool treats the first as the id and the second as the performance, so no configuration is needed. It also contains stray spaces (e.g. `Bollywood (Open) ` with a trailing space), which is why the cleaning steps below exist.

### Requirements

- CSV, with a header row, UTF-8 (a byte-order mark from Excel is accepted).
- Exactly the two columns above are used; extra columns are ignored with a warning.
- Column names are configurable. If not specified and the file has exactly two columns, the first is the id and the second is the performance.
- The same id must be used every time for the same person.
- A performance cannot be named `BREAK` (any capitalisation); that word is reserved.

### Cleaning applied

| Step | Detail |
|---|---|
| Whitespace | Leading/trailing spaces removed; runs of internal spaces collapsed to one. |
| Case | Matching ignores case (`Hip Hop` = `hip hop`). The first spelling seen is kept for display. |
| Blank rows | Rows with an empty id or performance are dropped and reported. |
| Duplicates | Repeated (id, performance) pairs after cleaning are merged, with a warning. |

### Errors (processing stops)

- Missing file, missing/ambiguous columns, or no usable rows
- A performance named `BREAK`

### Warnings (processing continues)

- Duplicate rows removed
- Blank rows dropped
- **Near-duplicate ids** (e.g. `Jon Smith` and `John Smith`): a typo would silently remove constraints, so these are flagged for the organiser to confirm
- Near-duplicate performance names (e.g. `Hip Hop (Found.)` and `Hip Hop (Foundations)`)
- Performers in only one performance (informational; they create no constraints)

### Derived data

After cleaning, the program builds:

1. **performer -> set of performances**
2. **performance -> set of performers**
3. **Conflict map:** for each pair of performances sharing a performer, the set of shared performers (kept so error messages can name the performer)

The number of performances is the number of distinct cleaned performance names.

## 2. Schedule CSV (checker input, finder output)

One row per slot, in running order. The first column is `position`; every other column is
one complete schedule, so several schedules sit **side by side** for comparison. A file with a
single schedule column is the single-schedule case.

| Column | Meaning |
|---|---|
| position | Slot number, starting at 1 |
| every other column | One schedule: a performance name, or `BREAK`, in each slot. The header is the schedule's name (e.g. `schedule_1`). |

```
position,schedule_1,schedule_2,schedule_3
1,Bollywood,Bollywood,Jazz
2,BREAK,Jazz,Bollywood
3,Jazz,BREAK,BREAK
4,Hip Hop,Hip Hop,Hip Hop
```

Rules:
- Positions must be 1..N with no gaps or repeats (if the position column is missing, row order is used).
- Every schedule column must have a value in every row.
- Performance names are matched using the same cleaning as above.
- `BREAK` (any capitalisation) marks a break; blank items are treated as breaks with a warning.
- In every schedule column, each performance in the performer CSV must appear exactly once; unknown names are errors.
- The checker checks every schedule column and reports each one separately.

## 3. Fixed-positions CSV (finder input, optional)

Pins items to slots. Same columns as the schedule CSV, but only the pinned rows are listed.

```
position,item
1,Bollywood (Open)
12,BREAK
20,Hip Hop (Foundations)
```

Rules:
- A position can be pinned once; a performance can be pinned once.
- Pinned `BREAK` rows count towards the total number of breaks.
- Positions must lie within the total number of slots (performances + breaks).
- Contradictions are reported before any search begins.
