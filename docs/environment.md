# Dependencies and environment

**Status:** DRAFT

## Python

Python 3.11 or newer, in a virtual environment named `.venv` at the repo root
(gitignored). In VS Code, choose it via *Python: Select Interpreter*.

Creating the environment (one time):

    python -m venv .venv

Then activate it (Windows: `.venv\Scripts\activate`; macOS/Linux: `source .venv/bin/activate`).

## Dependencies

Declared in `pyproject.toml` in three optional groups: `dev`, `solver-experiments` and `ui`. The core has no dependencies beyond the standard library.

Install for development: `pip install -e ".[dev]"`. Add `solver-experiments` (e.g. `pip install -e ".[dev,solver-experiments]"`) when we reach the search-engine experiment.

| Package | Purpose | Needed by |
|---|---|---|
| `ortools` | Constraint solver. Installed only through the `solver-experiments` extra until decision Q2 is settled | experiment, possibly finder |
| `pytest` | Tests | development |
| `ruff` | Linting and formatting | development |
| `ipykernel`, `jupyter` | Notebooks in VS Code | development |
| `pandas` | Convenient tables in notebooks and the UI | notebooks, UI |
| `streamlit` | Simple web UI | UI (later) |
| `nbstripout` (optional) | Strip notebook outputs before committing | development |

Design choice: the **core** (`models`, `io`, `conflicts`, `validator`, `solver`) uses
only the standard library `csv` module plus the solver, so the logic stays small and
easy to test. `pandas` is reserved for notebooks and the UI. Dependencies are split
into "core", "dev" and "ui" groups so the checker can be installed without the rest.

## VS Code

Extensions: Python, Pylance, Jupyter. Configure pytest as the test framework so tests
appear in the Testing panel.

## Reproducibility

- Pin minimum versions in `pyproject.toml`; record exact versions used when the project stabilises.
- CI is not planned yet. Revisit if more contributors join.
