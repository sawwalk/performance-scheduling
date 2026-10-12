# Search approaches for the schedule finder (decision Q2)

**Status:** DRAFT. The choice is not final: it is settled by the notebook experiment described below.

The finder has to answer: "list valid running orders, one at a time, in a repeatable
order, honouring pinned positions". Two ways to build the search engine are on the table.

## 1. Option A: OR-Tools CP-SAT

### What it is

CP-SAT is the constraint-programming solver in Google's OR-Tools library. You describe the
problem as variables and constraints, and the solver searches for assignments that satisfy
them. It is built on SAT-solving techniques (it learns from dead ends so it does not repeat them).

### How our problem would be modelled

- One integer variable per **performance**, holding its slot number (1 to N, where N = performances + breaks).
- All performance variables must differ (one performance per slot). Slots no performance takes are the breaks, so breaks are automatically interchangeable (decision D11).
- For each conflicting pair of performances, their slot numbers must differ by at least k + 1.
- A pinned performance fixes its variable. A pinned break forbids every performance from that slot.

### What the sources confirm

- The official CP-SAT page says to find all solutions, you implement a solution printer (a callback) and set `enumerate_all_solutions` to true in the solver configuration. [CP-SAT solver, OR-Tools docs](https://developers.google.com/optimization/cp/cp_solver)
- The solver's parameter file documents `random_seed` (changes the solver's choices), and `num_workers` (0 means use all cores, 1 means no parallelism). It also has an experimental `interleave_search` option described as deterministic. [sat_parameters.proto](https://github.com/google/or-tools/blob/stable/ortools/sat/sat_parameters.proto)
- A user-reported OR-Tools issue shows enumeration gets slow quickly because the number of solutions grows exponentially. This is a general warning, not a verdict on our problem. [or-tools issue #4220](https://github.com/google/or-tools/issues/4220)
- Python API reference: [cp_model](https://developers.google.com/optimization/reference/python/sat/python/cp_model)
- A widely used community guide, which I have **not** opened in this research, so check it yourself: [The CP-SAT Primer](https://d-krupke.github.io/cpsat-primer/)

### What I believe but did not verify (check in the experiment)

- The order in which `enumerate_all_solutions` returns schedules is not documented as stable or lexicographic. We can make runs repeatable with a fixed seed and one worker, but we cannot choose the order.
- Enumeration mode may restrict parallelism, and may interact with presolve.
- "Give me the next schedule" is not a built-in operation. The usual approach is to solve again with an extra constraint excluding each schedule already shown. That works for tens of schedules; the cost grows as the excluded list grows.

### Strengths and weaknesses

| Strengths | Weaknesses |
|---|---|
| Strong at proving "no schedule exists", which matters for infeasible pinning | Order of results is not under our control |
| Extra constraints later (quick-change time, preferences) are easy to add | "Next schedule" needs exclusion constraints |
| Can optimise (e.g. maximise the smallest gap) if we ever want that | Large dependency to install, harder to explain to others |
| Mature, fast, well documented | The search is a black box, so bugs are harder to trace |

## 2. Option B: custom backtracking

### The idea

Build the running order slot by slot from left to right. At each slot, try the candidates
in a fixed order. If a choice leads to a dead end, undo it and try the next one.
Because the order is fixed, the sequence of schedules found is always the same,
and it is lexicographic (like a dictionary).

### State

- The partly built running order (slots 1 to p - 1 filled)
- The set of performances not yet placed
- The number of free breaks still available (total breaks minus pinned breaks minus free breaks already used)
- The pins, as a lookup from slot to item

### Fixed candidate order ("canonical order")

Performances are put in a fixed list (alphabetical by cleaned name, unless a shuffle seed is
given, in which case the list is shuffled using that seed; see D15 in `design-decisions.md`). At each slot the candidates are tried in that list
order, with BREAK tried last. This order defines which schedule is "first", "second" and so on.

### Steps at each slot p

1. If slot p is pinned, the only candidate is the pinned item. Otherwise the candidates are every unplaced performance that is not pinned elsewhere, in canonical order, plus BREAK if a free break remains.
2. **Legality check** for a performance X: it is illegal if X conflicts with any performance in slots p - k to p - 1 (only the last k slots need checking, because everything earlier is already far enough away). It is also illegal if it conflicts with a performance pinned in one of the next k slots.
3. **Pruning check** after the tentative placement. Reject the choice now if any of these fail:
   - Performer capacity: a performer with r performances still to place needs at least (r - 1)(k + 1) + 1 slots, starting no earlier than their last appearance plus k + 1. If the remaining slots cannot hold that, this branch is dead.
   - Every unplaced performance still has at least one slot it could legally occupy.
   - Every pinned item further on can still be placed legally.
4. Place the item and move to slot p + 1.
5. When slot N is filled, report the schedule, then keep going (backtrack to the deepest slot that has untried candidates) to find the next one.

### Results are one of three kinds

| Outcome | Meaning |
|---|---|
| Schedule found | Reported and passed through the schedule checker |
| Exhausted | The whole search was completed: there are no more schedules. This is a proof. |
| Stopped | A time or node limit was reached before finishing. Not a proof either way. |

The tool must never present "stopped" as "none exist".

### Next on demand

The search is a Python generator: asking for the next schedule resumes where it stopped.
For the UI, which may rerun between clicks, the last schedule shown can serve as a bookmark:
the search restarts with that schedule as its prefix and carries on from the next candidate.
This is possible only because the order is fixed.

### Picking schedules by number

The search numbers schedules 1, 2, 3, ... as it finds them. To output a chosen set (for example 1, 4 and 9) it runs until the highest number picked, keeps only the chosen schedules and discards the rest. Reaching a high number costs time, so the time and size limits apply here too.

### Counting

Same search without storing results, with a cap ("at least 10,000 schedules").

### Infeasibility explanation

Run the existence search again with each pin removed in turn, and report the pins whose removal gives a schedule.

### Strengths and weaknesses

| Strengths | Weaknesses |
|---|---|
| Fixed, lexicographic, repeatable order | Worst case is exponential; slow on near-impossible requests unless pruning is strong |
| "Next schedule" and "resume" are natural | We write and test the pruning ourselves |
| No heavy dependency; easy to explain and debug | Each new kind of constraint needs new code |
| Good fit for the "show me every option" goal (D4) | Cannot optimise, only enumerate |

### Consequence of lexicographic order

Early schedules in a lexicographic list share long beginnings (they differ near the end).
Looking at the first five may feel like seeing one schedule five times. The organiser's
remedy is to pin more slots, which is exactly the workflow you described. The optional
seed shuffles the canonical order, which changes where the list starts without losing completeness (D15).

## 3. Where each approach fits in the workflow

```
performer CSV -> io (load, clean) -> conflicts -> pre-checks -> SEARCH ENGINE -> validator -> output
                                                               (A or B)        (cross-check)
```

| Stage | Role of the search engine |
|---|---|
| Project structure | Lives in `solver.py` behind one function that returns schedules and a status (found / exhausted / stopped). Nothing else in the project knows which engine is inside. If the engines grow large, split into `search_backtracking.py` and `search_cpsat.py`, but not before. |
| Phase 3, the experiment | Both are prototyped in a notebook on the same data and compared (below). |
| Testing | Whichever engine is used is checked two ways: every schedule goes through the schedule checker, and on small examples (up to about 7 performances) the number of schedules is compared with a brute-force count over all orderings. |
| Possible hybrid | Backtracking for enumeration; CP-SAT only to prove infeasibility on hard cases. Only worth the added dependency if backtracking proves too slow there. |

## 4. The experiment that settles Q2

Run both on (a) the small synthetic example, and (b) a synthetic show with about 20
performances and 120 performers, at k = 1, 2 and 3, with and without pins.

| Question | Measure |
|---|---|
| Is the first schedule quick? | Time to the first schedule |
| Is "no schedule" proved quickly? | Time to prove infeasibility on hard cases (k large, awkward pins) |
| Is the order repeatable? | Same input twice gives the same sequence |
| Is "next" cheap? | Time for schedules 1, 10, 100 |
| Is it correct? | Counts match brute force on small cases |

**Tentative recommendation (to confirm by the experiment):** build the backtracking engine
first. It delivers the fixed order and cheap "next" that decision D4 needs, avoids a large
dependency for a tool aimed at non-technical users, and is a good way to learn the problem.
Keep CP-SAT as the benchmark and as the fallback if backtracking is too slow on infeasible cases.
