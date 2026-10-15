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

- CSV, with a header row, UTF-8 (a byte-order mark from Excel is accepted). If the file is not UTF-8 the tool says so and suggests "CSV UTF-8" in Excel's Save As.
- The separator can be a comma, semicolon or tab; it is detected from the header row.
- Exactly the two columns above are used. Empty trailing columns (which Excel sometimes adds) are ignored.
- If the file has exactly two columns, the first is the id and the second is the performance, whatever they are called.
- Otherwise both column names must be given (case and extra spaces do not matter). Any other columns are ignored, with a warning.
- The same id must be used every time for the same person.
- A performance cannot be named `BREAK` (any capitalisation); that word is reserved.

### Cleaning applied

| Step | Detail |
|---|---|
| Standard form | Text is converted to a standard Unicode form, so look-alikes (a non-breaking space copied from a web page, an accented letter typed two ways) match. |
| Whitespace | Leading/trailing spaces removed; runs of internal spaces collapsed to one. |
| Case | Matching ignores case (`Hip Hop` = `hip hop`). The first spelling seen is kept for display. |
| Blank rows | Completely blank rows (often at the end of a file) are skipped quietly. Rows with an empty id or performance are dropped with a warning. |
| Duplicates | Repeated (id, performance) pairs after cleaning are merged, with a warning. |

### Errors (processing stops)

- Missing or unreadable file, empty file, no usable rows
- Missing, repeated or ambiguous columns
- A performance named `BREAK`

All errors found are reported together so they can be fixed in one go.

### Warnings (processing continues)

- Duplicate rows removed (row number given)
- Rows dropped for a missing id or performance (row number given)
- Extra columns ignored
- **Near-duplicate ids** (e.g. `Jon Smith` and `John Smith`): a typo would silently remove constraints, so these are flagged for the organiser to confirm. Names that differ only in digits (`Person 0001` and `Person 0002`) are not flagged, because numbered ids are normally different people.
- **Near-duplicate performance names** (e.g. `Tap (Foundations)` and `Tap (Foundation)`). Genuinely different performances such as `Kpop Boys (Intermediate)` and `Kpop Girls (Intermediate)` are not flagged.

Similarity is scored from 0 to 1; the thresholds (0.90 for ids, 0.92 for performance names) are constants at the top of `io.py` and can be tuned.

Performers in only one performance create no constraints. That is normal (most performers), so there is no warning for it.

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
- The `position` column (any capitalisation, any place in the header) gives each row's slot number. Rows may be in any order; they are sorted by position. Positions must be exactly 1 to N with no gaps, repeats or non-numbers; otherwise the file is rejected with a message naming the rows. If there is no `position` column, every column is a schedule and row order is the running order.
- Performance names are matched using the same cleaning as above, so `bollywood (open)` in a schedule matches `Bollywood (Open)` in the performer file.
- `BREAK` (any capitalisation) marks a break. An empty cell is treated as a break, with a warning naming the row and schedule.
- Completely blank rows and empty trailing columns are ignored. Cells beyond the header's columns are ignored with a warning.
- Schedule names (the headers) must be unique.
- **Reading the file does not judge its contents.** A performance that is missing, repeated, or not in the performer file is loaded as written; the schedule checker reports it (decision D22).
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
