# Search approaches for the schedule finder (decision Q2)

**Status:** SETTLED on 2026-10-17 (D29): the schedule finder uses **OR-Tools CP-SAT**. This file is the record of why. The custom backtracking option is described for history and is not being built.

The finder has to answer: "list valid running orders, one at a time, in a repeatable
order, honouring pinned positions". Two ways to build the search engine were compared.

## 1. The two options

**Option A: OR-Tools CP-SAT.** The constraint-programming solver in Google's OR-Tools library. You describe the problem as variables and constraints, and the solver searches for assignments that satisfy them. It is built on SAT-solving techniques (it learns from dead ends so it does not repeat them).

**Option B: custom backtracking.** Build the running order slot by slot from left to right, trying candidates in a fixed order and undoing a choice when it leads to a dead end. Because the order is fixed, the list of schedules is always the same and in dictionary order, and "next schedule" is natural.

| | CP-SAT | Backtracking |
|---|---|---|
| Strengths | Strong at proving "no schedule exists". Can name the pins that block a schedule. Easy to add constraints later. | Fixed dictionary order. "Next" is natural. No heavy dependency. Easy to explain. |
| Weaknesses | Order of results is the solver's. Large dependency. The search is a black box. | Worst case is exponential. We write and test the pruning ourselves. Cannot prove "none exists" quickly on hard cases. |

## 2. The experiment

`notebooks/search_experiment.ipynb`, run on 2026-10-17. Backtracking was stopped after 300,000 steps; CP-SAT was given 20 seconds, one worker and seed 1. "Found" means a schedule was produced, "exhausted" means the engine proved none exists, "stopped" means it gave up at the limit. (Notebook outputs are stripped before committing, so the results are kept here.)

**Correctness.** On the three tiny shows (9 combinations of gap and breaks), brute force, backtracking and CP-SAT gave identical lists. The counts are the ones in `test-datasets.md`.

**The real show** (19 performances, 126 performers, largest group of performances that all clash: 6):

| k | breaks | Backtracking | CP-SAT |
|---|---|---|---|
| 1 | 0 | found, 0.00 s | found, 0.10 s |
| 2 | 0 | **stopped**, 4.19 s | found, 0.10 s |
| 2 | 2 | found, 0.45 s | found, 0.09 s |
| 3 | 0 | exhausted, 0.00 s | exhausted, 0.02 s |
| 3 | 2 | **stopped**, 5.31 s | **exhausted**, 0.12 s |
| 3 | 4 | **stopped**, 4.95 s | found, 0.12 s |

So on the real show k = 2 is possible with no breaks, and k = 3 needs 4 breaks (2 is proved impossible). Only CP-SAT could say so.

**Synthetic shows (20 performances, 15 cases).** CP-SAT gave a definite answer to all 15, the slowest taking 1.73 s. Backtracking stopped on 3: `typical_20_performances` at k=3 with 4 breaks, and `one_busy_performer` at k=1 with 0 breaks and at k=2 with 5 breaks. CP-SAT proved all three impossible. (The `one_busy_performer` k=1, 0 breaks result is new: `test-datasets.md` said "not decided".)

**Many schedules** (`typical_20_performances`, k=1, 0 breaks):

| Schedules wanted | Backtracking | CP-SAT |
|---|---|---|
| 1 | 0.00 s | 0.23 s |
| 100 | 0.01 s | 0.23 s |
| 1,000 | 0.35 s | 0.89 s |

On the real show, 100 schedules took 0.12 s with CP-SAT. Run twice, both engines gave the same list. Backtracking's list was in dictionary order and CP-SAT's was not. Neighbouring schedules differed in 3.9 slots on average for backtracking and 2.8 for CP-SAT. The two lists of 100 had no schedule in common.

**Pins.** Easy pins (an opening act, a closing act and a break) and hard pins at k=1 were solved by both. Hard pins at k=2 with 4 breaks: backtracking stopped after 5.66 s, CP-SAT found a schedule in 0.54 s. Contradicting pins were reported as impossible by both instantly. CP-SAT, given each pin as an assumption, correctly named the two clashing pins out of four.

## 3. Why CP-SAT

- It gave a definite answer, found or proved impossible, to every case in the experiment, and fast. These are the answers an organiser needs: "here is a schedule", "none exists, and here is why".
- It can name the pins that cannot all hold together (D34).
- Backtracking cannot be trusted at k of 2 or more unless its fault (section 5) is fixed, and even then it gave up on hard cases.

What we give up: dictionary order and cheap "next schedule". "Show more" means re-running and skipping (D33), and schedule numbers depend on the OR-Tools version (D32). These were judged acceptable because runs are fast. The dependency is larger, so it is optional (D35): the schedule checker does not need it.

## 4. How CP-SAT is used

The behaviour the organiser sees is in `schedule-finder.md`. The engine side:

- **Model:** one slot variable per performance, all different; for each conflicting pair, a choice of "A first" or "B first" with the spacing rule on each side; pins fix a performance or forbid a slot for every performance. Breaks are the unused slots.
- **Listing:** the solver option that enumerates all solutions, with a callback that collects schedules and stops the search after the highest number wanted. One worker and a fixed seed, so the list is repeatable.
- **Statuses:** a finished search with no schedule left is *exhausted*; reaching the wanted number is *found*; hitting the time limit is *stopped*. If fewer schedules exist than wanted, the search finishes and the answer is *exhausted*. (The notebook labelled that case "found". The finder must not.)
- **Counting:** not built. The same search with a cap and without storing schedules ("at least 10,000") was considered and dropped (D63).
- **Infeasibility:** a separate model where each pin is switched on by an assumption. If it is infeasible, the solver returns a subset of assumptions that is enough to cause that. This is not used for enumeration.
- **Seed:** the organiser's seed changes the order the model is built in (performances and clashing pairs sorted by a hash of the seed and their names); the solver's own seed stays fixed (D38). Tested on 2026-10-17 on `typical_20_performances`, gap 1, first 5 schedules: the solver's `random_seed` 0, 1, 2 and 3 all gave the same list. Build-order shuffles with no seed and seeds 1, 2 and 3 gave 4 different lists, each repeatable, and on `tiny_feasible` (gap 1, 1 break) all gave the same 152 schedules in different orders.

Sources (carried over from the earlier version of this file; the last was never opened):

- The official CP-SAT page says to find all solutions you implement a solution callback and set `enumerate_all_solutions` to true. [CP-SAT solver, OR-Tools docs](https://developers.google.com/optimization/cp/cp_solver)
- The parameter file documents `random_seed` and `num_workers` (1 means no parallelism). [sat_parameters.proto](https://github.com/google/or-tools/blob/stable/ortools/sat/sat_parameters.proto)
- A user-reported issue shows enumeration slows quickly because the number of solutions grows exponentially. [or-tools issue #4220](https://github.com/google/or-tools/issues/4220)
- Python API reference: [cp_model](https://developers.google.com/optimization/reference/python/sat/python/cp_model)
- Community guide, **not opened**: [The CP-SAT Primer](https://d-krupke.github.io/cpsat-primer/)

## 5. A fault found in the backtracking code

The notebook's backtracking engine starts every performer's "last appearance" at slot 0. Its capacity check then assumes nobody can start before slot k + 1. For k = 1 this does no harm, but for k of 2 or more it throws away valid schedules.

Example: 5 performances A, B, C, X1, X2, where X is in both X1 and X2, at k = 2 with no breaks. Brute force finds **36** valid schedules; the notebook's backtracking finds **24**. Starting the value at `-k` instead of `0` gives 36, which confirms the cause. The tiny datasets did not expose it, so the brute-force agreement in section 2 was luck at k = 2.

What this means:

- Backtracking was not carried forward, so the fault is not being fixed. If backtracking is ever revisited, fix this first.
- Every case in the experiment where both engines gave a verdict agreed, so none of the results above are contradicted. But backtracking's "exhausted" at k of 2 or more was not independent evidence. Its one-step "exhausted" for the real show at k=3 with 0 breaks very likely comes from this same check (reasoned from the code, not traced). The answer is right: CP-SAT agrees, and a group of 6 clashing performances needs 21 slots at k=3 against 19.
- The "Rough" results in `test-datasets.md` came from an earlier quick search that may share the fault. They are to be refreshed from the CP-SAT results (roadmap, Phase 3).
- The 5-performance example is now a required test for the finder (`schedule-finder.md`, edge cases).

## 6. Believed but not verified

- That the order is stable across OR-Tools versions or machines. Only "same machine, same code, twice" was tested (D32).
- That a seed changes the list *usefully*. It changes the first schedules (tested), but neighbouring schedules still look alike (D38).
- That the list is complete on shows of 20 performances. Completeness was checked against brute force only on shows of 6 or fewer performances; beyond that it rests on the solver being correct and on every schedule passing the schedule checker.
- How long it takes to reach very high schedule numbers (such as number 10,000). The default limit of 100 keeps this bounded; 1,000 took 0.89 s on one synthetic show.
- That the blocking-pins report is useful on messier cases. It was tried once.

## 7. Where the engine sits in the workflow

```
performer CSV -> io (load, clean) -> conflicts -> pre-checks -> CP-SAT (solver.py) -> validator -> output
                                                                                    (cross-check)
```

**Testing.** Every schedule is checked two ways: it goes through the schedule checker, and on small examples (up to about 7 performances, plus the 5-performance hand-made case) the number of schedules is compared with a brute-force count over all orderings. The brute-force helper is in `tests/test_validator.py`. Same input twice must give the same list.
