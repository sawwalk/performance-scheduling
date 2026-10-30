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

import pandas as pd
import streamlit as st

from performance_scheduling.io import (
    decode_text,
    parse_performers,
    parse_schedules,
    performer_file_columns,
    read_text,
)
from performance_scheduling.models import (
    InputError,
    Issue,
    PerformerData,
    PerformerLoad,
    ScheduleCheck,
    ScheduleLoad,
)
from performance_scheduling.report import (
    MAX_ISSUES_SHOWN,
    PairProblem,
    format_check,
    format_issues,
    format_totals,
    format_violations_csv,
    group_violations,
    overview_rows,
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


# ---------------------------------------------------------------- the tabs (later steps)


def _find_tab(show: PerformerLoad) -> None:
    st.caption("The schedule finder is added in step U4.")


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
