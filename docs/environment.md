# Dependencies and environment

**Status:** DRAFT (updated for task U5)

## Python

Python 3.11 or newer, in a virtual environment named `.venv` at the repo root
(gitignored). In VS Code, choose it via *Python: Select Interpreter*.

Creating the environment (one time):

    python -m venv .venv

Then activate it (Windows: `.venv\Scripts\activate`; macOS/Linux: `source .venv/bin/activate`).

## Dependencies

Declared in `pyproject.toml` in optional groups: `dev`, `finder` and `ui`. The core has no dependencies beyond the standard library.

Install for development: `pip install -e ".[dev]"`. This includes OR-Tools, so the finder tests and the notebook work. To install only what the finder needs: `pip install -e ".[finder]"`. To run the page: `pip install -e ".[ui]"`. (The old `solver-experiments` group no longer exists.)

| Package | Purpose | Needed by |
|---|---|---|
| `ortools` | Constraint solver (CP-SAT) that finds the schedules; chosen in decision D29 | finder (`finder` group; also in `dev`) |
| `pytest` | Tests | development |
| `ruff` | Linting and formatting | development |
| `ipykernel`, `jupyter` | Notebooks in VS Code | development |
| `pandas` | Convenient tables in notebooks and the UI | notebooks, UI |
| `streamlit` | The page for organisers (`>=1.66,<2`; built and tested with 1.66.1) | UI (`ui` group; also in `dev`) |
| `nbstripout` (optional) | Strip notebook outputs before committing | development |

Design choice: the **core** (`models`, `io`, `conflicts`, `validator`, `solver`) uses
only the standard library `csv` module plus the solver, so the logic stays small and
easy to test. `pandas` is reserved for notebooks and the UI. (OR-Tools itself installs `numpy` and `pandas`, so they are present wherever the finder is installed; the core code still does not import them.) Dependencies are split
into "core", "finder", "dev" and "ui" groups so the checker can be installed without the rest. The UI runs the finder, so the `ui` group includes OR-Tools too.

## Developer tools

Run from the project folder with the `.venv` active (they are not installed with the package):

    python scripts/make_api_summary.py > docs/api-summary.md   # after changing a public name
    python scripts/list_messages.py --check                    # after adding or changing a message

The test suite runs the second check as well (`tests/test_error_messages.py`).

## Starting the page

On Windows, double-click `run_app.bat` in the project folder. It uses `.venv\Scripts\python.exe`, changes to the project folder first (so `.streamlit/config.toml` is found, D53), checks that Streamlit, OR-Tools and the package import, and then runs `python -m streamlit run src\performance_scheduling\app.py`. If `.venv` is missing or a package is missing, it says so in plain words and waits for a key press. Elsewhere, run the same `streamlit run` command from the project folder with the `.venv` active.

Streamlit's first-run email prompt does not appear, because usage statistics are off in `config.toml` (checked on Linux with a fresh home folder; not yet checked on Windows).

## VS Code

Extensions: Python, Pylance, Jupyter. Configure pytest as the test framework so tests
appear in the Testing panel.

## Reproducibility

- Streamlit and OR-Tools both have version ranges in `pyproject.toml`; Streamlit 1.66.1 was the version in use when the page was built.
- Pin minimum versions in `pyproject.toml`; record exact versions used when the project stabilises.
- **OR-Tools version matters.** The order of the finder's list, and so its schedule numbers, can change between versions (D32). Record the exact version in use here: **9.15.6755** (recorded 2026-10-17).
- CI is not planned yet. Revisit if more contributors join.
