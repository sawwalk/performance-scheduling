# performance-scheduling

Tools for organising the running order of a dance show so that no performer appears too soon after a previous performance.

**Status:** early development. The schedule checker works; the schedule finder is not built yet.

## What it does

A show has many performances (e.g. "Bollywood (Open)"), and many performers take part in several of them. Two tools work from a CSV of who is in what:

- **Schedule checker:** checks a proposed running order (breaks allowed) and reports exactly which performers are not given enough rest.
- **Schedule finder:** finds valid running orders, lets the organiser pin performances and breaks to chosen slots, and gives more schedules on demand.

Full details are in [docs/](docs/README.md), starting with the [problem statement](docs/problem-statement.md).

## Setup (one time)

Requires Python 3.11 or newer.

    python -m venv .venv
    .venv\Scripts\activate            (Windows)   or   source .venv/bin/activate   (macOS/Linux)
    pip install -e ".[dev]"

In VS Code, choose the `.venv` interpreter via *Python: Select Interpreter*.

## Using the schedule checker

    schedule-checker --performers data/private/performers.csv --schedule data/private/order.csv --gap 1

Try it on the examples:

    schedule-checker --performers data/examples/tiny_feasible.csv --schedule data/examples/tiny_feasible_schedule_invalid.csv

See [docs/schedule-checker.md](docs/schedule-checker.md) for all options and the output. After editing `pyproject.toml`, run `pip install -e ".[dev]"` again so the command is registered.

## Data and privacy

Performer names are personal data. Real files go in `data/private/`, which git ignores. Only synthetic files in `data/examples/` are committed. See [docs/test-datasets.md](docs/test-datasets.md).

## Documentation

See [docs/README.md](docs/README.md) for the index.
