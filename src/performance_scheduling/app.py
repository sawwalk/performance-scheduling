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

import re
from pathlib import Path

import streamlit as st

from performance_scheduling.io import (
    decode_text,
    parse_performers,
    performer_file_columns,
    read_text,
)
from performance_scheduling.models import InputError, Issue, PerformerLoad
from performance_scheduling.report import MAX_ISSUES_SHOWN, format_issues

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

# The two column pickers' widget keys (forgotten whenever a new file arrives).
_PICKER_KEYS = ("id_column", "performance_column")


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
    for key in _PICKER_KEYS:
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


def _show_problem(issues: tuple[Issue, ...]) -> None:
    """A red box listing every message, each with its row number where it has one."""
    heading, items = _issue_list("This file cannot be used", issues, max(len(issues), 1))
    st.error(f"**{heading}**\n\n{items}", icon="🚫")


def _show_warnings(warnings: tuple[Issue, ...]) -> None:
    """Warnings in full and open by default, with the count in the heading."""
    heading, items = _issue_list(
        f"{_count(len(warnings), 'thing')} to check in this file", warnings, MAX_ISSUES_SHOWN
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


# ---------------------------------------------------------------- the tabs (later steps)


def _find_tab(show: PerformerLoad) -> None:
    st.caption("The schedule finder is added in step U4.")


def _check_tab(show: PerformerLoad) -> None:
    st.caption("The schedule checker is added in step U3.")


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
