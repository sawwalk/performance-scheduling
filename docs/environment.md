# Dependencies and environment

**Status:** DRAFT (updated for task U5)

## Python

Python 3.11 or newer, in a virtual environment named `.venv` at the repo root
(gitignored). In VS Code, choose it via *Python: Select Interpreter*.

Python is the only program to install. Streamlit needs 3.11 or newer. OR-Tools 9.15 publishes
ready-made packages (wheels) for Python 3.9 to 3.14 on Windows, macOS (Intel and Apple silicon)
and Linux, so no compiler is needed. The suite was run on 3.12 (Linux; the first 604 tests also
on the owner's Windows machine). Recommend **3.11 to 3.13** to users; 3.14 has not been tried.
On a Mac, the Python that ships with macOS is 3.9, which is too old: install from python.org.

Creating the environment (one time). The README gives the user-facing steps:

    py -m venv .venv          (Windows; `python -m venv .venv` also works)
    python3 -m venv .venv     (macOS/Linux)

Then activate it (Windows: `.venv\Scripts\activate`; macOS/Linux: `source .venv/bin/activate`).
Activation is optional if you call the interpreter inside `.venv` directly, as `run_app.bat`
and the README do. A `.venv` records absolute paths, so after moving or renaming the project
folder, delete it and create it again.

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

On Windows, double-click `run_app.bat` in the project folder. It uses `.venv\Scripts\python.exe`, changes to the project folder first (so `.streamlit/config.toml` is found, D53), checks that Streamlit, OR-Tools and the package import, and then runs `python -m streamlit run src\performance_scheduling\app.py`. If `.venv` is missing or a package is missing, it says so in plain words and waits for a key press. On a Mac (or Linux) there is no launcher (D64). Open Terminal in the project folder and run `.venv/bin/python -m streamlit run src/performance_scheduling/app.py` (or the same `streamlit run` command with the `.venv` active). It must be run from the project folder so that `.streamlit/config.toml` is found. The launcher's messages point to the README's Setup section, which has the one-time steps for both systems; the launcher does not install anything itself.

Streamlit's first-run email prompt does not appear, because usage statistics are off in `config.toml` (checked on Linux with a fresh home folder; not yet checked on Windows or macOS).

## VS Code

Extensions: Python, Pylance, Jupyter. Configure pytest as the test framework so tests
appear in the Testing panel.

## Reproducibility

- Streamlit and OR-Tools both have version ranges in `pyproject.toml`; Streamlit 1.66.1 was the version in use when the page was built.
- Pin minimum versions in `pyproject.toml`; record exact versions used when the project stabilises.
- **OR-Tools version matters.** The order of the finder's list, and so its schedule numbers, can change between versions (D32). Record the exact version in use here: **9.15.6755** (recorded 2026-10-17).
- CI is not planned yet. Revisit if more contributors join.
