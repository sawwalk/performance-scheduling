"""The page for organisers (Streamlit): upload a show, then check or find schedules.

This is the only file that imports Streamlit. It imports only the shared layer
(models, io, selection, report, validator, solver) and never `cli` (decision D48).
It holds no scheduling logic and no sentences of its own beyond labels and headings:
everything else comes from the shared layer, so the page and the commands agree
(D26, D46). Nothing is written to disk and no usage statistics are sent (D49).

Run it from the project folder, so that `.streamlit/config.toml` is found:

    streamlit run src/performance_scheduling/app.py
"""

from __future__ import annotations

import random
import re
from pathlib import Path

import pandas as pd
import streamlit as st

from performance_scheduling.io import (
    decode_text,
    format_schedules,
    parse_performers,
    parse_schedules,
    performer_file_columns,
    read_text,
    schedule_rows,
    schedules_file_name,
)
from performance_scheduling.models import (
    BREAK,
    FinderResult,
    FinderStatus,
    InputError,
    Issue,
    PerformerData,
    PerformerLoad,
    Pins,
    ScheduleCheck,
    ScheduleLoad,
)
from performance_scheduling.report import (
    MAX_ISSUES_SHOWN,
    PairProblem,
    format_availability,
    format_check,
    format_found,
    format_issues,
    format_larger_gap_prompt,
    format_missing,
    format_totals,
    format_violations_csv,
    group_violations,
    no_schedules_heading,
    overview_rows,
)
from performance_scheduling.selection import (
    Picked,
    Selection,
    apply_selection,
    next_pick,
    parse_selection,
    schedules_to_request,
)
from performance_scheduling.solver import (
    DEFAULT_TIME_LIMIT,
    SolverNotInstalled,
    find_schedules,
    solver_version,
)
from performance_scheduling.validator import check_schedules

# The example file offered for download. It is found relative to the project folder,
# so the page works from wherever the folder is copied; if it is missing, the link
# is simply not shown.
EXAMPLE_FILE = Path(__file__).resolve().parents[2] / "data" / "examples" / "tiny_feasible.csv"

UNEXPECTED_PROBLEM = (
    "Something unexpected went wrong while reading this file, so it was not loaded. "
    "Check that it is a CSV file saved as \"CSV UTF-8\", or ask whoever set this up."
)

ID_QUESTION = "Which column holds the performer's name or id?"
PERFORMANCE_QUESTION = "Which column holds the performance?"
CHOOSE_COLUMNS = "Choose the two columns to continue."

UNEXPECTED_CHECK_PROBLEM = (
    "Something unexpected went wrong while checking this schedule, so no result is shown. "
    "Ask whoever set this up."
)

SCHEDULE_FILE_LABEL = "Schedule file (CSV): one running order, or several side by side"
GAP_LABEL = "Rest between a performer's performances (slots)"
GAP_HELP = "1 means never back to back."
DOWNLOAD_PROBLEMS_LABEL = "Download the problems (CSV)"

# With more schedules than this, valid ones appear only in the overview table. This is the
# command's rule (decision D28, `cli.FULL_DETAIL_UP_TO`) and its sentence, repeated here
# because the page may not import `cli`.
FULL_DETAIL_UP_TO = 10
VALID_LISTED_IN_TABLE = "Valid schedules are listed in the table only."

# The two column pickers' widget keys (forgotten whenever a new file arrives).
_PICKER_KEYS = ("id_column", "performance_column")

# The finder tab's widget keys (forgotten whenever a new file arrives, like the pins).
_FINDER_KEYS = (
    "find_gap",
    "find_breaks",
    "pin_slot",
    "pin_item",
    "find_pick",
    "find_seed",
    "find_limit",
    "find_time_limit",
    "search_requested",
)

# The finder's defaults. The pick, the limit and their meaning are the command's
# (`cli.DEFAULT_PICK`, `cli.DEFAULT_LIMIT`, repeated here because the page may not import `cli`).
DEFAULT_PICK = "1-5"
DEFAULT_LIMIT = 100
DEFAULT_SECONDS = int(DEFAULT_TIME_LIMIT)
LARGEST_SEED = 999_999

BREAKS_LABEL = "Breaks"
BREAKS_HELP = "Pinned breaks count towards this."
PINS_HEADING = "**Pins (optional):** fix a performance or a break to a slot"
PIN_SLOT_LABEL = "Slot"
PIN_ITEM_LABEL = "Item"
PIN_ITEM_PLACEHOLDER = "Choose a performance or a break"
ADD_PIN_LABEL = "Add pin"
REMOVE_PIN_LABEL = "Remove"
BLOCKING_PIN = "These cannot all be kept"
PICK_LABEL = "Which schedules"
PICK_HELP = "1-5, 6-10, 1,4,9, 1-3,7,20-22 or all"
SELECT_ALL_LABEL = "Select all"
MORE_OPTIONS_LABEL = "More options"
SEED_LABEL = "Shuffle seed"
SEED_HELP = "Leave empty for the default list. The same number always gives the same list."
SHUFFLE_LABEL = "Shuffle"
LIMIT_LABEL = "Most schedules per run"
TIME_LIMIT_LABEL = "Longest search, seconds"
FIND_LABEL = "Find schedules"
DOWNLOAD_SCHEDULES_LABEL = "Download these schedules (CSV)"
SEARCH_LONGER_LABEL = "Search for longer"
STALE_SENTENCE = "Settings changed. Press Find schedules to update."
STALE_FADE = "<style>.st-key-finder_results { opacity: 0.45; }</style>"

NOT_INSTALLED = (
    "The schedule finder is not installed on this computer. Ask whoever set it up to install it."
)
INSTALL_DETAILS_LABEL = "What to give them"
INTERNAL_PROBLEM = "Something went wrong inside the finder, and no schedule was shown."
INTERNAL_DETAILS_LABEL = "Details (to copy into a bug report)"
UNEXPECTED_FIND_PROBLEM = (
    "Something unexpected went wrong while searching, so no schedule is shown. "
    "Ask whoever set this up."
)


# ---------------------------------------------------------------- what the page remembers


def _fresh_state() -> dict[str, object]:
    """The page's memory with nothing in it (docs/ui-design.md section 4.5)."""
    return {
        "performer_file": None,  # (file name, bytes) of the uploaded performer file
        "columns": None,  # (id column, performance column) if the file needed them
        "show": None,  # the PerformerLoad, when the file loaded without errors
        "pins": {},  # pinned slots so far: position -> item (used by the finder tab)
        "form": {},  # the finder's settings (used by the finder tab)
        "run": None,  # the last search: its settings, FinderResult and Picked
    }


def _init_state() -> None:
    for key, value in _fresh_state().items():
        st.session_state.setdefault(key, value)
    st.session_state.setdefault("upload_round", 0)


def _forget_show() -> None:
    """Drop everything that depends on the performer file: results, pins, columns."""
    for key, value in _fresh_state().items():
        if key != "performer_file":
            st.session_state[key] = value
    for key in _PICKER_KEYS + _FINDER_KEYS:
        st.session_state.pop(key, None)


def _clear_all_data() -> None:
    """Empty the session, including the upload box (which gets a new key)."""
    next_round = st.session_state.get("upload_round", 0) + 1
    st.session_state.clear()
    _init_state()
    st.session_state["upload_round"] = next_round


# ---------------------------------------------------------------- small display helpers


def _plain(text: str) -> str:
    """Make text show as written where Streamlit expects markdown.

    Performer and performance names are typed by people. Without this, a `*`, `_`, `$`
    or `[` in a name could turn into bold, italics, maths or a link.
    """
    return re.sub(r"([\\`*_\[\]<>$~|&])", r"\\\1", text)


def _count(number: int, noun: str) -> str:
    return f"{number} {noun}" if number == 1 else f"{number} {noun}s"


def _issue_list(heading: str, issues: tuple[Issue, ...], limit: int) -> tuple[str, str]:
    """The heading and a markdown list of issues, worded by the shared `format_issues`."""
    heading_line, *lines = format_issues(heading, issues, limit).splitlines()
    return heading_line, "\n".join(f"- {_plain(line.strip())}" for line in lines)


def _show_problem(issues: tuple[Issue, ...], heading: str = "This file cannot be used") -> None:
    """A red box listing every message, each with its row number where it has one."""
    heading, items = _issue_list(heading, issues, max(len(issues), 1))
    st.error(f"**{heading}**\n\n{items}", icon="🚫")


def _show_warnings(warnings: tuple[Issue, ...], where: str = "this file") -> None:
    """Warnings in full and open by default, with the count in the heading."""
    heading, items = _issue_list(
        f"{_count(len(warnings), 'thing')} to check in {where}", warnings, MAX_ISSUES_SHOWN
    )
    with st.expander(f"⚠️ {heading}", expanded=True):
        st.markdown(items)


# ---------------------------------------------------------------- 1. Your show


def _example_download() -> None:
    try:
        text = read_text(EXAMPLE_FILE)
    except InputError:
        return  # the example file is not in this copy of the folder
    st.download_button(
        "Example file (download)", data=text, file_name=EXAMPLE_FILE.name, mime="text/csv"
    )


def _column_pickers(columns: list[str]) -> tuple[str, str] | None:
    """Ask which columns to use. Nothing is pre-selected: the page never guesses."""
    id_column = st.selectbox(
        ID_QUESTION, columns, index=None, key="id_column", placeholder="Choose a column"
    )
    performance_column = st.selectbox(
        PERFORMANCE_QUESTION,
        columns,
        index=None,
        key="performance_column",
        placeholder="Choose a column",
    )
    if id_column is None or performance_column is None:
        return None
    return id_column, performance_column


def _read_show(name: str, raw: bytes) -> PerformerLoad | None:
    """Turn the uploaded bytes into a PerformerLoad, showing whatever there is to show."""
    try:
        text = decode_text(raw, name)
        columns = performer_file_columns(text)
        chosen: tuple[str, str] | None = None
        if len(columns) > 2:
            chosen = _column_pickers(columns)
            if chosen is None:
                st.info(CHOOSE_COLUMNS, icon="👉")
                return None
        st.session_state["columns"] = chosen
        load = parse_performers(text, *(chosen or (None, None)))
    except InputError as problem:
        _show_problem(problem.issues)
        return None
    except Exception:  # noqa: BLE001 - organisers get a short message, never a traceback
        st.error(UNEXPECTED_PROBLEM, icon="🚫")
        return None

    data = load.data
    summary = (
        f"{_plain(name)}: {_count(len(data.performances_by_performer), 'performer')}, "
        f"{_count(len(data.performance_names), 'performance')}"
    )
    st.success(summary, icon="✅")
    if load.warnings:
        _show_warnings(load.warnings)
    return load


def _your_show() -> PerformerLoad | None:
    """Section 1: the performer file. Returns the loaded show, or None if not usable yet."""
    st.subheader("1. Your show")
    uploaded = st.file_uploader(
        "Drop the performer file here, or browse (CSV)",
        type=["csv"],
        key=f"performer_upload_{st.session_state['upload_round']}",
    )
    _example_download()

    show: PerformerLoad | None = None
    if uploaded is None:
        # No file, or the organiser removed it: nothing from an earlier file may stay.
        if st.session_state["performer_file"] is not None:
            _forget_show()
            st.session_state["performer_file"] = None
    else:
        current = (uploaded.name, uploaded.getvalue())
        if st.session_state["performer_file"] != current:
            # A new file clears every result and every pin (the old pins may name
            # performances that no longer exist).
            _forget_show()
            st.session_state["performer_file"] = current
        show = _read_show(*current)

    st.session_state["show"] = show
    if st.session_state["performer_file"] is not None:
        st.button("Clear all data", on_click=_clear_all_data)
    return show


# ---------------------------------------------------------------- the tabs


# ---------------------------------------------------------------- 2. Find schedules (U4)


def _item_name(show: PerformerLoad, item: str) -> str:
    """How a pinned item reads: the performance's display name, or "a break"."""
    return "a break" if item == BREAK else show.data.performance_names.get(item, item)


def _add_pin() -> None:
    """Pin the chosen item to the chosen slot (a callback, so it runs before the next draw).

    A slot holds one item and a performance has one slot, so pinning onto an occupied slot
    replaces what was there, and pinning a performance again moves it. Breaks may repeat.
    """
    state = st.session_state
    item = state.get("pin_item")
    if item is None:
        return
    slot = int(state["pin_slot"])
    pins = {
        position: pinned
        for position, pinned in state["pins"].items()
        if position != slot and (item == BREAK or pinned != item)
    }
    pins[slot] = item
    state["pins"] = pins


def _remove_pin(slot: int) -> None:
    st.session_state["pins"] = {p: i for p, i in st.session_state["pins"].items() if p != slot}


def _select_all() -> None:
    st.session_state["find_pick"] = "all"


def _shuffle() -> None:
    st.session_state["find_seed"] = random.randint(1, LARGEST_SEED)


def _request_search(**changes: object) -> None:
    """Change some settings, then search again on the next draw (the "Show the next 5" family)."""
    for key, value in changes.items():
        st.session_state[key] = value
    st.session_state["search_requested"] = True


def _blocking_slots(run: dict[str, object] | None) -> set[int]:
    """Pinned slots the last search named as impossible to keep together.

    They are only marked while the pins are the ones that search used; after any change to
    the pins the names would describe a situation that is gone.
    """
    if run is None or "result" not in run:
        return set()
    settings = run["settings"]
    result = run["result"]
    assert isinstance(settings, dict) and isinstance(result, FinderResult)
    if settings["pins"] != _pin_key(st.session_state["pins"]):
        return set()
    return set(result.blocking_pins)


def _pin_key(pins: dict[int, str]) -> tuple[tuple[int, str], ...]:
    return tuple(sorted(pins.items()))


def _pins_section(show: PerformerLoad, slots: int) -> None:
    """Section 4.3: the guided form for pins, and the list of pins so far."""
    names = show.data.performance_names
    st.markdown(PINS_HEADING)
    items = [BREAK, *sorted(names, key=lambda key: (names[key].casefold(), key))]
    slot_column, item_column, add_column = st.columns([1, 3, 1], vertical_alignment="bottom")
    slot_column.number_input(
        PIN_SLOT_LABEL, min_value=1, max_value=slots, value=1, step=1, key="pin_slot"
    )
    item_column.selectbox(
        PIN_ITEM_LABEL,
        items,
        index=None,
        key="pin_item",
        format_func=lambda key: "Break" if key == BREAK else names.get(key, key),
        placeholder=PIN_ITEM_PLACEHOLDER,
    )
    add_column.button(
        ADD_PIN_LABEL,
        key="add_pin",
        on_click=_add_pin,
        disabled=st.session_state.get("pin_item") is None,
    )

    blocking = _blocking_slots(st.session_state["run"])
    for slot, item in sorted(st.session_state["pins"].items()):
        line, remove = st.columns([4, 1], vertical_alignment="center")
        mark = f" ⚠️ {BLOCKING_PIN}" if slot in blocking else ""
        line.markdown(f"- Slot {slot}: {_plain(_item_name(show, item))}{mark}")
        remove.button(
            REMOVE_PIN_LABEL, key=f"remove_pin_{slot}", on_click=_remove_pin, args=(slot,)
        )


def _read_pick(limit: int) -> Selection | None:
    """The typed pick, or None (with the plain message shown under the box) if it is bad."""
    try:
        return parse_selection(st.session_state["find_pick"], max_count=limit)
    except InputError as problem:
        st.error("\n\n".join(_plain(issue.message) for issue in problem.issues), icon="🚫")
        return None


def _current_settings() -> dict[str, object]:
    """Everything on the form that a search depends on, for comparing with the last search."""
    state = st.session_state
    seed = state["find_seed"]
    return {
        "gap": int(state["find_gap"]),
        "breaks": int(state["find_breaks"]),
        "pins": _pin_key(state["pins"]),
        "pick": str(state["find_pick"]).strip(),
        "seed": None if seed is None else int(seed),
        "limit": int(state["find_limit"]),
        "time_limit": int(state["find_time_limit"]),
    }


def _search(
    show: PerformerLoad, settings: dict[str, object], selection: Selection
) -> dict[str, object]:
    """Run the finder once and return what to remember about it (the `run` key)."""
    pins = {int(slot): item for slot, item in settings["pins"]}  # type: ignore[attr-defined]
    try:
        version = solver_version()
    except SolverNotInstalled as problem:
        return {"settings": settings, "failure": ("not_installed", str(problem))}
    limit = int(settings["limit"])  # type: ignore[call-overload]
    try:
        with st.spinner(f"Searching for up to {settings['time_limit']} seconds..."):
            result = find_schedules(
                show.data,
                gap=int(settings["gap"]),  # type: ignore[call-overload]
                breaks=int(settings["breaks"]),  # type: ignore[call-overload]
                pins=Pins(slots=pins) if pins else None,
                seed=settings["seed"],  # type: ignore[arg-type]
                count=schedules_to_request(selection, limit),
                time_limit=float(settings["time_limit"]),  # type: ignore[arg-type]
            )
            picked = apply_selection(result, selection, limit)
    except SolverNotInstalled as problem:
        return {"settings": settings, "failure": ("not_installed", str(problem))}
    except RuntimeError as problem:  # a schedule failed the cross-check: a bug (D39)
        return {"settings": settings, "failure": ("internal", str(problem))}
    except Exception:  # noqa: BLE001 - organisers get a short message, never a traceback
        return {"settings": settings, "failure": ("unexpected", "")}
    return {
        "settings": settings,
        "selection": selection,
        "result": result,
        "picked": picked,
        "version": version,
    }


def _show_failure(kind: str, detail: str) -> None:
    if kind == "not_installed":
        st.error(NOT_INSTALLED, icon="🚫")
        with st.expander(INSTALL_DETAILS_LABEL):
            st.code(detail, language=None)
    elif kind == "internal":
        st.error(INTERNAL_PROBLEM, icon="🚫")
        with st.expander(INTERNAL_DETAILS_LABEL):
            st.code(detail, language=None)
    else:
        st.error(UNEXPECTED_FIND_PROBLEM, icon="🚫")


def _no_schedule_box(result: FinderResult) -> None:
    """The finder's heading and reasons, unchanged: red if none exist, yellow if time ran out."""
    reasons = "\n".join(f"- {_plain(issue.message)}" for issue in result.explanation)
    text = f"**{no_schedules_heading(result.status)}**\n\n{reasons}".strip()
    if result.status is FinderStatus.EXHAUSTED:
        st.error(text, icon="🚫")
    else:
        st.warning(text, icon="⏱️")


def _schedule_table(
    schedules: tuple, show: PerformerLoad, pinned: dict[int, str]
) -> None:  # fmt: skip
    """Slots down, schedules across, from `schedule_rows` so it matches the CSV.

    Display only: pinned slots say so in the position column (not colour alone) and breaks
    are grey. The downloaded file is untouched.
    """
    header, *rows = schedule_rows(schedules, show.data.performance_names)
    shown = [[f"{row[0]} (pinned)" if int(row[0]) in pinned else row[0], *row[1:]] for row in rows]
    frame = pd.DataFrame(shown, columns=header)
    styled = frame.style.map(
        lambda cell: "color: grey; font-style: italic" if cell == BREAK else ""
    )
    st.dataframe(styled, hide_index=True)


def _show_found(
    show: PerformerLoad, run: dict[str, object], settings: dict[str, object], *, stale: bool
) -> None:
    """The result of the last search: the table, the downloads and the buttons."""
    result = run["result"]
    picked = run["picked"]
    selection = run["selection"]
    assert isinstance(result, FinderResult) and isinstance(picked, Picked)
    assert isinstance(selection, Selection)
    limit = int(settings["limit"])  # type: ignore[call-overload]
    gap = int(settings["gap"])  # type: ignore[call-overload]
    seed = settings["seed"]
    stopped = picked.more_exist is None
    last = picked.numbers.highest or 0

    if picked.schedules:
        st.success(format_found(len(picked.schedules), str(picked.numbers)), icon="✅")
        availability = format_availability(
            picked.more_exist, total=picked.total, produced=len(result.schedules), last_number=last
        )
        if stopped:
            st.warning(availability, icon="⏱️")
        else:
            st.markdown(availability)
    elif not result.schedules:
        _no_schedule_box(result)

    if picked.missing.ranges and result.schedules:
        st.warning(
            format_missing(
                str(picked.missing),
                picked.missing.count or 0,
                stopped=stopped,
                total=picked.total,
            ),
            icon="⚠️",
        )

    if picked.schedules:
        _schedule_table(picked.schedules, show, dict(settings["pins"]))  # type: ignore[call-overload]
        columns = st.columns(2)
        columns[0].download_button(
            DOWNLOAD_SCHEDULES_LABEL,
            data=format_schedules(picked.schedules, show.data.performance_names).encode(
                "utf-8-sig"
            ),
            file_name=schedules_file_name(seed, str(selection)),  # type: ignore[arg-type]
            mime="text/csv",
            disabled=stale,
        )
        if picked.more_exist:
            following = next_pick(selection, limit, last)
            size = parse_selection(following).count or 1
            label = f"Show the next {size}" if size > 1 else "Show the next schedule"
            columns[1].button(
                label,
                key="show_next",
                on_click=_request_search,
                kwargs={"find_pick": following},
                disabled=stale,
            )

    if stopped:
        st.button(
            SEARCH_LONGER_LABEL,
            key="search_longer",
            on_click=_request_search,
            kwargs={"find_time_limit": int(settings["time_limit"]) * 2},  # type: ignore[call-overload]
            disabled=stale,
        )

    if picked.schedules:
        st.markdown(format_larger_gap_prompt(gap))
        st.button(
            f"Try a gap of {gap + 1}",
            key="try_gap",
            on_click=_request_search,
            kwargs={"find_gap": gap + 1},
            disabled=stale,
        )

    order = "default order" if seed is None else f"{seed}"
    st.caption(f"Seed: {order}. Search engine: OR-Tools {run['version']}.")


def _show_run(show: PerformerLoad, run: dict[str, object], current: dict[str, object]) -> None:
    """Section 4.3, results: what the last search found, greyed if the form has moved on."""
    settings = run["settings"]
    assert isinstance(settings, dict)
    stale = settings != current
    with st.container(key="finder_results"):
        if stale:
            st.html(STALE_FADE)
            st.warning(STALE_SENTENCE, icon="✏️")
        if "failure" in run:
            kind, detail = run["failure"]  # type: ignore[misc]
            _show_failure(kind, detail)
        else:
            _show_found(show, run, settings, stale=stale)


def _find_tab(show: PerformerLoad) -> None:
    """Section 4.3: the settings, the pins, the pick, the search and its results.

    The form is the widgets themselves (each has a key). A search stores its settings with
    its result in `run`, so the page can tell when the form no longer matches the result.
    """
    state = st.session_state
    state.setdefault("find_limit", DEFAULT_LIMIT)

    st.number_input(GAP_LABEL, min_value=0, value=1, step=1, key="find_gap", help=GAP_HELP)
    breaks = int(
        st.number_input(
            BREAKS_LABEL, min_value=0, value=0, step=1, key="find_breaks", help=BREAKS_HELP
        )
    )
    _pins_section(show, len(show.data.performance_names) + breaks)

    st.text_input(PICK_LABEL, value=DEFAULT_PICK, key="find_pick", help=PICK_HELP)
    selection = _read_pick(int(state["find_limit"]))
    st.button(SELECT_ALL_LABEL, key="select_all", on_click=_select_all)

    with st.expander(MORE_OPTIONS_LABEL):
        seed_column, shuffle_column = st.columns([3, 1], vertical_alignment="bottom")
        seed_column.number_input(
            SEED_LABEL, value=None, step=1, format="%d", key="find_seed", help=SEED_HELP
        )
        shuffle_column.button(SHUFFLE_LABEL, key="shuffle", on_click=_shuffle)
        st.number_input(LIMIT_LABEL, min_value=1, step=10, key="find_limit")
        st.number_input(
            TIME_LIMIT_LABEL, min_value=1, value=DEFAULT_SECONDS, step=5, key="find_time_limit"
        )

    current = _current_settings()
    clicked = st.button(FIND_LABEL, type="primary", key="find_schedules")
    requested = state.pop("search_requested", False)
    if (clicked or requested) and selection is not None:
        state["run"] = _search(show, current, selection)
        st.rerun()  # so the pin list can mark the pins the search named

    if state["run"] is not None:
        _show_run(show, state["run"], current)


def _problems_csv(checks: tuple[ScheduleCheck, ...], data: PerformerData) -> bytes:
    """The violations report, as the command writes it (UTF-8 with a byte-order mark, so
    Excel shows accents correctly; see `io.write_text`)."""
    return format_violations_csv(checks, data).encode("utf-8-sig")


def _problems_file_name(schedule_file_name: str) -> str:
    return f"{Path(schedule_file_name).stem}_problems.csv"


def _read_schedules(name: str, raw: bytes) -> ScheduleLoad | None:
    """Turn the uploaded bytes into a ScheduleLoad, or show why not."""
    try:
        return parse_schedules(decode_text(raw, name))
    except InputError as problem:
        _show_problem(problem.issues, f"The schedule file {_plain(name)} cannot be used")
    except Exception:  # noqa: BLE001 - organisers get a short message, never a traceback
        st.error(UNEXPECTED_PROBLEM, icon="🚫")
    return None


def _overview_table(checks: tuple[ScheduleCheck, ...]) -> None:
    """One row per schedule, worded and counted by `report.overview_rows` like the command."""
    header, *rows = overview_rows(checks)
    st.markdown("#### Overview")
    st.dataframe(pd.DataFrame(rows, columns=list(header)), hide_index=True)


def _pairs_table(pairs: tuple[PairProblem, ...], data: PerformerData) -> pd.DataFrame:
    """One row per pair of performances that are too close together."""

    def name(key: str) -> str:
        return data.performance_names.get(key, key)

    return pd.DataFrame(
        {
            "No.": list(range(1, len(pairs) + 1)),
            "First performance": [name(pair.performance_a) for pair in pairs],
            "First slot": [pair.position_a for pair in pairs],
            "Second performance": [name(pair.performance_b) for pair in pairs],
            "Second slot": [pair.position_b for pair in pairs],
            "Slots between": [pair.slots_between for pair in pairs],
            "Slots needed": [pair.required for pair in pairs],
            "Performers affected": [len(pair.performers) for pair in pairs],
        }
    )


def _who_is_affected(
    check: ScheduleCheck, pairs: tuple[PairProblem, ...], data: PerformerData, *, expanded: bool
) -> None:
    """For each pair, the performers affected: the command's second list."""
    affected = len({violation.performer for violation in check.violations})
    with st.expander(f"Who is affected ({_count(affected, 'performer')})", expanded=expanded):
        for number, pair in enumerate(pairs, 1):
            first = data.performance_names.get(pair.performance_a, pair.performance_a)
            second = data.performance_names.get(pair.performance_b, pair.performance_b)
            people = "\n".join(
                f"- {_plain(data.performer_names.get(who, who))}" for who in pair.performers
            )
            st.markdown(f"**{number}. {_plain(first)} and {_plain(second)}**\n\n{people}")


def _show_check(check: ScheduleCheck, data: PerformerData, *, expanded: bool) -> None:
    """The write-up for one schedule.

    The sentences come from `format_check`, so they are the command's. Its layout is
    fixed: line 0 is the verdict, line 1 the slot count, line 4 (when the schedule itself
    has problems) says that spacing was not checked, and the last line (when it has not)
    is the tightest spacing.
    """
    lines = [line.strip() for line in format_check(check, data).splitlines()]
    st.markdown(f"#### {'✅' if check.valid else '❌'} {_plain(lines[0])}")
    st.markdown(_plain(lines[1]))

    if check.problems:
        items = "\n".join(f"- {_plain(problem.message)}" for problem in check.problems)
        st.error(
            f"**Problems with the schedule itself ({len(check.problems)})**\n\n"
            f"{_plain(lines[4])}\n\n{items}",
            icon="🚫",
        )
        return

    pairs = group_violations(check.violations)
    if pairs:
        st.markdown(f"**Conflicting performance pairs ({len(pairs)})**")
        st.dataframe(_pairs_table(pairs, data), hide_index=True)
        _who_is_affected(check, pairs, data, expanded=expanded)
    st.markdown(_plain(lines[-1]))


def _show_totals(checks: tuple[ScheduleCheck, ...]) -> None:
    invalid = sum(1 for check in checks if not check.valid)
    sentence = format_totals(checks)
    if invalid == 0:
        st.success(sentence, icon="✅")
    elif invalid == len(checks):
        st.error(sentence, icon="🚫")
    else:
        st.warning(sentence, icon="⚠️")


def _show_results(checks: tuple[ScheduleCheck, ...], data: PerformerData, file_name: str) -> None:
    """The overview, the write-up of each schedule, the download and the closing sentence."""
    several = len(checks) > 1
    many = len(checks) > FULL_DETAIL_UP_TO
    if several:
        _overview_table(checks)
    for check in checks:
        if many and check.valid:
            continue
        _show_check(check, data, expanded=not several)
    if many:
        st.caption(VALID_LISTED_IN_TABLE)
    if any(check.violations for check in checks):
        st.download_button(
            DOWNLOAD_PROBLEMS_LABEL,
            data=_problems_csv(checks, data),
            file_name=_problems_file_name(file_name),
            mime="text/csv",
        )
    if several:
        _show_totals(checks)


def _check_tab(show: PerformerLoad) -> None:
    """Section 4.4: upload a schedule file, choose the rest, read the result.

    Nothing is stored: the result is worked out again on every run, so it always matches
    the performer file, the schedule file and the gap that are on the page.
    """
    uploaded = st.file_uploader(
        SCHEDULE_FILE_LABEL,
        type=["csv"],
        key=f"schedule_upload_{st.session_state['upload_round']}",
    )
    gap = int(
        st.number_input(GAP_LABEL, min_value=0, value=1, step=1, key="check_gap", help=GAP_HELP)
    )
    if uploaded is None:
        return

    load = _read_schedules(uploaded.name, uploaded.getvalue())
    if load is None:
        return
    if load.warnings:
        _show_warnings(load.warnings, "the schedule file")
    try:
        checks = check_schedules(show.data, load.schedules, gap)
    except Exception:  # noqa: BLE001 - organisers get a short message, never a traceback
        st.error(UNEXPECTED_CHECK_PROBLEM, icon="🚫")
        return
    _show_results(checks, show.data, uploaded.name)


# ---------------------------------------------------------------- the page


def main() -> None:
    st.set_page_config(page_title="Performance scheduling")
    _init_state()
    st.title("Performance scheduling")
    st.write("Check a running order, or find one, so that nobody performs twice in a row.")

    show = _your_show()
    if show is None:
        return  # the tabs stay hidden until a performer file has loaded without errors

    find_tab, check_tab = st.tabs(["Find schedules", "Check a schedule"])
    with find_tab:
        _find_tab(show)
    with check_tab:
        _check_tab(show)


if __name__ == "__main__":
    main()
