# Dependencies and environment

**Status:** DRAFT

## Python

Python 3.11 or newer, in a virtual environment named `.venv` at the repo root
(gitignored). In VS Code, choose it via *Python: Select Interpreter*.

Creating the environment (one time):

    python -m venv .venv

Then activate it (Windows: `.venv\Scripts\activate`; macOS/Linux: `source .venv/bin/activate`).

## Dependencies

Declared in `pyproject.toml` in optional groups: `dev`, `finder` and `ui`. The core has no dependencies beyond the standard library.

Install for development: `pip install -e ".[dev]"`. This includes OR-Tools, so the finder tests and the notebook work. To install only what the finder needs: `pip install -e ".[finder]"`. (The old `solver-experiments` group no longer exists.)

| Package | Purpose | Needed by |
|---|---|---|
| `ortools` | Constraint solver (CP-SAT) that finds the schedules; chosen in decision D29 | finder (`finder` group; also in `dev`) |
| `pytest` | Tests | development |
| `ruff` | Linting and formatting | development |
| `ipykernel`, `jupyter` | Notebooks in VS Code | development |
| `pandas` | Convenient tables in notebooks and the UI | notebooks, UI |
| `streamlit` | Simple web UI | UI (later) |
| `nbstripout` (optional) | Strip notebook outputs before committing | development |

Design choice: the **core** (`models`, `io`, `conflicts`, `validator`, `solver`) uses
only the standard library `csv` module plus the solver, so the logic stays small and
easy to test. `pandas` is reserved for notebooks and the UI. Dependencies are split
into "core", "finder", "dev" and "ui" groups so the checker can be installed without the rest. The UI will run the finder, so it will need the `finder` group too.

## VS Code

Extensions: Python, Pylance, Jupyter. Configure pytest as the test framework so tests
appear in the Testing panel.

## Reproducibility

- Pin minimum versions in `pyproject.toml`; record exact versions used when the project stabilises.
- **OR-Tools version matters.** The order of the finder's list, and so its schedule numbers, can change between versions (D32). Record the exact version in use here: **to be filled in** (run `pip show ortools`).
- CI is not planned yet. Revisit if more contributors join.
