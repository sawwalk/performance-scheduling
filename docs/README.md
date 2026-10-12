# Documentation index

| Document | What it covers |
|---|---|
| [problem-statement.md](problem-statement.md) | The problem, definitions, rules, assumptions, scope |
| [design-decisions.md](design-decisions.md) | Decisions made so far, and open questions |
| [repo-structure.md](repo-structure.md) | Folder layout and what each file is responsible for |
| [data-model.md](data-model.md) | The containers in `models.py`: what each holds and who creates and uses it |
| [input-data.md](input-data.md) | Input file formats, requirements, and cleaning applied |
| [environment.md](environment.md) | Python version, dependencies, setup |
| [schedule-checker.md](schedule-checker.md) | Purpose, design, usage and output of the schedule checker |
| [schedule-finder.md](schedule-finder.md) | Purpose, design, usage and output of the schedule finder |
| [search-approaches.md](search-approaches.md) | CP-SAT versus custom backtracking, how each works, where each fits, and the experiment to choose |
| [test-datasets.md](test-datasets.md) | The practice datasets in `data/examples/` and what each one tests |
| [development-roadmap.md](development-roadmap.md) | The order in which we build things |

## Planned (not yet written)

- `testing-strategy.md`: what we test and how
- `error-messages.md`: catalogue of every error/warning the tools can give
- `ui-design.md`: the simple interface for non-technical organisers
- `data-privacy.md`: handling of performer names and emails
- `user-guide.md`: step-by-step guide for organisers (written once the UI exists)
- `glossary.md`: if the vocabulary outgrows the problem statement

Status of every document: **DRAFT**. Documents describe the *intended* design; where
the code and a document disagree, fix whichever is wrong and note it in `design-decisions.md`.
