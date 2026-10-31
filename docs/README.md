# performance-scheduling

Tools for organising the running order of a dance show so that no performer appears too soon after a previous performance.

**Status:** early development. The schedule checker and the schedule finder both work from the command line. A simple web page does the same from a browser.

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

To run only the page (no test tools): `pip install -e ".[ui]"`. In VS Code, choose the `.venv` interpreter via *Python: Select Interpreter*.

## Using the schedule checker

    schedule-checker --performers data/private/performers.csv --schedule data/private/order.csv --gap 1

Try it on the examples:

    schedule-checker --performers data/examples/tiny_feasible.csv --schedule data/examples/tiny_feasible_schedule_invalid.csv

See [docs/schedule-checker.md](docs/schedule-checker.md) for all options and the output. After editing `pyproject.toml`, run `pip install -e ".[dev]"` again so the command is registered.

## Using the schedule finder

    schedule-finder --performers data/private/performers.csv --gap 2 --breaks 2 --pick 1-5

Try it on the examples:

    schedule-finder --performers data/examples/tiny_feasible.csv --fixed data/examples/tiny_feasible_pins.csv --breaks 1 --pick 1-5

The schedules are written to `output/` (created if missing) in a file named after the pick, such as `schedules_1-5.csv`. The tool never overwrites a file. It prints the exact command for the next batch, and the file can be given straight to the schedule checker. The finder needs OR-Tools, which the `dev`, `finder` and `ui` groups include. See [docs/schedule-finder.md](docs/schedule-finder.md) for all options.

## Using the page

The page does what the two commands do, in a browser, for people who prefer not to use a command line. It runs on your own computer and keeps your data in memory only (nothing is saved, nothing is sent anywhere).

**Windows:** double-click `run_app.bat` in the project folder. A window opens and, a few seconds later, so does your browser. Keep the window open while you work; close it to stop the page. If the browser does not open, go to <http://localhost:8501>.

**Any system (or to see what is happening):** from the project folder, with the `.venv` active:

    streamlit run src/performance_scheduling/app.py

Start it from the project folder, because the page reads `.streamlit/config.toml` from there. Try it with `data/examples/tiny_feasible.csv` (the page also offers it as a download): load it, press *Find schedules*, and a table of schedules appears. The page needs the `ui` group: `pip install -e ".[ui]"`. Only this computer can open the page (`server.address = "localhost"`). Do not host it publicly with real data.

The checklist for trying it in a real browser is in [docs/ui-design.md](docs/ui-design.md), section 11.

## Data and privacy

Performer names are personal data. Real files go in `data/private/`, which git ignores. Only synthetic files in `data/examples/` are committed. The rules are in [docs/data-privacy.md](docs/data-privacy.md); the datasets are described in [docs/test-datasets.md](docs/test-datasets.md).

## Documentation

See [docs/README.md](docs/README.md) for the index.
