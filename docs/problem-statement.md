# Problem statement

**Status:** DRAFT

## Context

A dance show is made up of a number of *performances*, each identified by a style
and level, e.g. "Bollywood (Open)", "Kpop Boys (Intermediate)", "Hip Hop (Foundations)".
Performers can enter any performance, and many enter several. The organiser must choose
the *running order*. The show may also contain *breaks* (an interval, or a guest act from
another organisation, which for scheduling purposes is the same thing).

## The problem

Order the performances so that every performer has enough rest between their performances.
At minimum, no performer appears in two consecutive slots. The organiser may also want
to know whether a larger rest is achievable for everyone.

## Definitions

| Term | Meaning |
|---|---|
| **Performance** | One act in the show, identified by a unique name. Appears exactly once in a schedule. |
| **Performer** | A person identified by a unique id (full name, email or performer id). |
| **Break** | A slot containing no performances. Conflicts with nothing. Guest acts from other organisations are treated as breaks. |
| **Slot** | One position in the running order. Occupied by a performance or a break. Numbered from 1. |
| **Schedule** | An ordered list of slots covering every performance exactly once, plus any breaks. |
| **Gap (k)** | The minimum number of slots required *between* two performances that share a performer. Default k = 1. |
| **Conflict** | Two performances that share at least one performer. |

## The rule

For any two performances that share a performer, if they sit at positions `p` and `q`:

    |p - q| >= k + 1

Breaks count as slots, so a break between two conflicting performances provides spacing.

Examples with k = 1 (performance A and B share a performer):

- A at slot 3, B at slot 4: **invalid** (no slot between)
- A at slot 3, B at slot 5: **valid** (one slot between, which may be a break or another performance)
- A at slot 3, B at slot 5, k = 2: **invalid** (needs at least two slots between)

## Quick feasibility check

A performer in `m` performances needs a stretch of at least `(m - 1)(k + 1) + 1` slots.
If that exceeds the number of slots in the show, no schedule exists for that `k`.
The tools should report this early because it explains many infeasible cases.

## Typical scale

About 20 performances and about 120 performers. A show therefore has roughly 20 to 25 slots.

## Goals

1. **Schedule checker:** given performer data and a proposed running order (breaks allowed), report whether it satisfies the rule, and if not, exactly what is wrong.
2. **Schedule finder:** given performer data, produce running orders that satisfy the rule, honouring organiser constraints (fixed positions for performances and breaks, number of breaks, gap k), and produce further schedules on demand.

## Out of scope (for now)

- Named guest performances as a separate concept (use breaks)
- Costume-change or travel time beyond the slot gap
- Preferences or scoring (e.g. "nicer" schedules); only valid/invalid
- Output formats other than CSV
- Different gaps for different performers

## Assumptions

- Every performance has at least one performer in the input data.
- A performer is listed at most once per performance (duplicates are removed).
- All slots are treated as equal length.
