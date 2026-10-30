"""Tests for the page: its skeleton and "Your show" section (task U2) and the "Check a
schedule" tab (task U3).

The page is driven with Streamlit's headless `AppTest`, using inline CSV text. `AppTest`
cannot see layout or colour, so what these tests check is what is on the page, not how
it looks (docs/ui-design.md section 6). They are skipped where Streamlit is not
installed (it is in the optional `ui` extra).
"""

import ast
import re
import tomllib
from pathlib import Path

import pytest

pytest.importorskip("streamlit")

from streamlit.testing.v1 import AppTest

from performance_scheduling import app as page
from performance_scheduling.io import load_performers, load_schedules
from performance_scheduling.report import (
    format_check,
    format_overview,
    format_totals,
    format_violations_csv,
    overview_rows,
)
from performance_scheduling.validator import check_schedules

ROOT = Path(__file__).resolve().parents[1]
APP_FILE = ROOT / "src" / "performance_scheduling" / "app.py"

TABS = ["Find schedules", "Check a schedule"]

GOOD = (
    "full name,style\n"
    "Amy,Jazz\nAmy,Tap\nBen,Jazz\nCat,Tap\nCat,Hip Hop\nDan,Hip Hop\n"
)
FOUR_COLUMNS = (
    "name,Dance,Year,Level\n"
    "Amy,Jazz,1,a\nAmy,Tap,1,a\nBen,Jazz,2,b\nCat,Tap,3,c\nCat,Hip Hop,3,c\n"
)


def start() -> AppTest:
    return AppTest.from_file(str(APP_FILE), default_timeout=20).run()


def upload(at: AppTest, text: str | bytes, name: str = "show.csv") -> AppTest:
    raw = text if isinstance(text, bytes) else text.encode("utf-8")
    at.file_uploader[0].set_value((name, raw, "text/csv"))
    return at.run()


def loaded(text: str | bytes, name: str = "show.csv") -> AppTest:
    at = upload(start(), text, name)
    assert not at.exception
    return at


def plain(shown: str) -> str:
    """What the organiser reads: the page escapes markdown characters with a backslash."""
    return re.sub(r"\\(.)", r"\1", shown)


def labels(elements) -> list[str]:
    return [element.label for element in elements]


def all_text(at: AppTest) -> str:
    parts = [plain(m.value) for m in at.markdown]
    parts += [plain(e.value) for e in at.error] + [plain(s.value) for s in at.success]
    parts += [plain(i.value) for i in at.info] + [plain(c.value) for c in at.caption]
    return "\n".join(parts)


# ---------------------------------------------------------------- the page before any upload


def test_empty_page_shows_the_frame_and_nothing_else():
    at = start()
    assert not at.exception
    assert [t.value for t in at.title] == ["Performance scheduling"]
    assert labels(at.file_uploader) == ["Drop the performer file here, or browse (CSV)"]
    assert at.session_state["show"] is None
    assert len(at.tabs) == 0
    assert len(at.success) == 0 and len(at.error) == 0
    assert labels(at.button) == []  # nothing to clear yet


def test_the_uploader_accepts_csv_only():
    assert start().file_uploader[0].allowed_type == [".csv"]


def test_example_file_can_be_downloaded():
    at = start()
    assert labels(at.download_button) == ["Example file (download)"]


# ---------------------------------------------------------------- loading a good file


def test_a_good_file_shows_its_size_and_opens_the_tabs():
    at = loaded(GOOD, "tiny.csv")
    assert [plain(s.value) for s in at.success] == ["tiny.csv: 4 performers, 3 performances"]
    assert labels(at.tabs) == TABS
    assert len(at.expander) == 0  # nothing to check, so no warnings box
    assert at.session_state["show"].rows_used == 6


def test_counts_use_the_singular_for_one():
    at = loaded("who,what\nAmy,Jazz\n")
    assert [plain(s.value) for s in at.success] == ["show.csv: 1 performer, 1 performance"]


def test_example_file_loads_cleanly_on_the_page():
    example = (ROOT / "data" / "examples" / "tiny_feasible.csv").read_bytes()
    at = loaded(example, "tiny_feasible.csv")
    assert [plain(s.value) for s in at.success] == [
        "tiny_feasible.csv: 12 performers, 6 performances"
    ]
    assert len(at.expander) == 0


def test_a_byte_order_mark_from_excel_is_accepted():
    at = loaded(b"\xef\xbb\xbf" + GOOD.encode("utf-8"))
    assert len(at.success) == 1 and len(at.error) == 0


def test_clicking_elsewhere_keeps_the_loaded_show():
    at = loaded(GOOD)
    at.run()
    assert labels(at.tabs) == TABS
    assert at.session_state["show"].rows_used == 6


# ---------------------------------------------------------------- warnings


MESSY = (
    "id,performance\n"
    "Person 0001,Bollywood (Open)\n"
    "Person 0001,Bollywood (Open)\n"
    "Person 0002,Jazz\n"
    "Person 0003,\n"
    ",Jazz\n"
    "John Smith,Tap (Foundation)\n"
    "Jon Smith,Tap (Foundations)\n"
)


def test_warnings_are_shown_in_full_and_open_with_the_count_in_the_heading():
    at = loaded(MESSY)
    assert len(at.expander) == 1
    box = at.expander[0]
    assert box.label == "⚠️ 5 things to check in this file"
    assert box.proto.expanded is True
    text = plain(box.markdown[0].value)
    assert "row 3: duplicate of an earlier row" in text
    assert "row 5: missing performance; row dropped" in text
    assert "row 6: missing performer; row dropped" in text
    assert 'Performer ids "John Smith" and "Jon Smith" look very similar' in text
    assert 'Performance names "Tap (Foundation)" and "Tap (Foundations)"' in text


def test_a_file_with_warnings_still_loads():
    at = loaded(MESSY)
    assert len(at.success) == 1
    assert labels(at.tabs) == TABS


def test_one_warning_says_one_thing():
    at = loaded("id,performance\nAmy,Jazz\nAmy,Jazz\n")
    assert at.expander[0].label == "⚠️ 1 thing to check in this file"


def test_more_than_twenty_warnings_are_shortened_like_the_command():
    rows = "id,performance\n" + "Amy,Jazz\n" * 26  # 25 duplicates
    at = loaded(rows)
    assert at.expander[0].label == "⚠️ 25 things to check in this file"
    lines = plain(at.expander[0].markdown[0].value).splitlines()
    assert len(lines) == 21
    assert lines[-1] == "- ... and 5 more"


# ---------------------------------------------------------------- files that cannot be used


@pytest.mark.parametrize(
    "content, expected",
    [
        (b"", "The file is empty."),
        (b"id,performance\n", "No usable rows were found."),
        (b"only\nAmy\n", "Expected exactly two columns"),
        (b"\xff\xfe\x00not utf-8", 'Save As" and choose "CSV UTF-8"'),
    ],
)
def test_an_unusable_file_gets_a_red_box_and_nothing_else(content, expected):
    at = loaded(content, "bad.csv")
    assert len(at.error) == 1
    assert expected in plain(at.error[0].value)
    assert len(at.success) == 0
    assert len(at.tabs) == 0
    assert at.session_state["show"] is None


def test_the_not_utf8_message_names_the_file():
    at = loaded(b"\xff\xfe\x00not utf-8", "bad.csv")
    assert "bad.csv" in plain(at.error[0].value)


def test_a_traceback_is_never_shown_for_an_unexpected_failure(monkeypatch):
    def boom(*_args, **_kwargs):
        raise RuntimeError("secret detail naming Amy")

    monkeypatch.setattr("performance_scheduling.io.parse_performers", boom)
    at = loaded(GOOD)
    assert len(at.exception) == 0
    assert len(at.error) == 1
    message = at.error[0].value
    assert message.startswith("Something unexpected went wrong while reading this file")
    assert "Amy" not in message and "secret" not in message
    assert len(at.tabs) == 0


def test_names_with_markdown_characters_are_shown_as_written():
    csv = "id,performance\nAmy_*B*,Jazz $5 [1]\nAmy_*B*,Jazz $5 [1]\n"
    at = loaded(csv, "my_show*.csv")
    assert "my_show*.csv" in plain(at.success[0].value)
    assert "Amy_*B*, Jazz $5 [1]" in plain(at.expander[0].markdown[0].value)
    assert "*" not in re.sub(r"\\\*", "", at.expander[0].markdown[0].value)  # all escaped


# ---------------------------------------------------------------- the column pickers


def test_more_than_two_columns_asks_which_to_use_and_never_guesses():
    at = loaded(FOUR_COLUMNS)
    assert labels(at.selectbox) == [
        "Which column holds the performer's name or id?",
        "Which column holds the performance?",
    ]
    assert [s.value for s in at.selectbox] == [None, None]
    assert at.selectbox[0].options == ["name", "Dance", "Year", "Level"]
    assert [plain(i.value) for i in at.info] == ["Choose the two columns to continue."]
    assert len(at.tabs) == 0 and len(at.success) == 0 and len(at.error) == 0
    assert at.session_state["show"] is None


def test_the_pickers_do_not_guess_even_when_names_look_obvious():
    at = loaded("id,performance,extra\nAmy,Jazz,x\n")
    assert [s.value for s in at.selectbox] == [None, None]


def test_one_choice_is_not_enough():
    at = loaded(FOUR_COLUMNS)
    at.selectbox[0].select("name").run()
    assert len(at.tabs) == 0
    assert len(at.info) == 1


def test_choosing_both_columns_loads_the_file():
    at = loaded(FOUR_COLUMNS)
    at.selectbox[0].select("name").run()
    at.selectbox[1].select("Dance").run()
    assert not at.exception
    assert [plain(s.value) for s in at.success] == ["show.csv: 3 performers, 3 performances"]
    assert labels(at.tabs) == TABS
    assert len(at.info) == 0
    assert at.session_state["columns"] == ("name", "Dance")
    data = at.session_state["show"].data
    assert sorted(data.performance_names.values()) == ["Hip Hop", "Jazz", "Tap"]


def test_the_same_column_twice_is_explained_in_a_red_box():
    at = loaded(FOUR_COLUMNS)
    at.selectbox[0].select("Dance").run()
    at.selectbox[1].select("Dance").run()
    assert "are the same" in plain(at.error[0].value)
    assert len(at.tabs) == 0


def test_columns_can_be_chosen_in_either_order():
    at = loaded(FOUR_COLUMNS)
    at.selectbox[1].select("Dance").run()
    at.selectbox[0].select("name").run()
    assert labels(at.tabs) == TABS


def test_two_columns_need_no_pickers_and_leave_columns_unset():
    at = loaded(GOOD)
    assert len(at.selectbox) == 0
    assert at.session_state["columns"] is None


# ---------------------------------------------------------------- a new file, removing, clearing


def test_a_new_file_clears_every_result_and_every_pin():
    at = loaded(GOOD)
    at.session_state["pins"] = {1: "jazz"}
    at.session_state["form"] = {"gap": 3}
    at.session_state["run"] = {"result": "an old result"}
    at.run()  # the same file again: nothing is lost
    assert at.session_state["pins"] == {1: "jazz"}
    assert at.session_state["run"] == {"result": "an old result"}
    upload(at, "who,what\nZed,Waltz\n", "other.csv")
    assert at.session_state["pins"] == {}
    assert at.session_state["form"] == {}
    assert at.session_state["run"] is None
    assert [plain(s.value) for s in at.success] == ["other.csv: 1 performer, 1 performance"]


def test_the_same_name_with_different_contents_counts_as_a_new_file():
    at = loaded(GOOD, "show.csv")
    at.session_state["pins"] = {1: "jazz"}
    upload(at, "who,what\nZed,Waltz\n", "show.csv")
    assert at.session_state["pins"] == {}


def test_a_new_file_forgets_the_old_column_choices():
    at = loaded(FOUR_COLUMNS)
    at.selectbox[0].select("name").run()
    at.selectbox[1].select("Dance").run()
    upload(at, "a,b,c\nx,y,z\n", "next.csv")
    assert [s.value for s in at.selectbox] == [None, None]
    assert at.session_state["columns"] is None
    assert at.session_state["show"] is None
    assert len(at.tabs) == 0


def test_a_new_file_with_the_same_headers_still_asks_again():
    at = loaded(FOUR_COLUMNS)
    at.selectbox[0].select("name").run()
    at.selectbox[1].select("Dance").run()
    upload(at, FOUR_COLUMNS.replace("Amy", "Zoe"), "updated.csv")
    assert [s.value for s in at.selectbox] == [None, None]
    assert len(at.tabs) == 0 and len(at.success) == 0


def test_a_file_replaced_by_a_bad_one_removes_the_old_show():
    at = loaded(GOOD)
    upload(at, b"", "empty.csv")
    assert at.session_state["show"] is None
    assert len(at.tabs) == 0 and len(at.success) == 0


def test_removing_the_file_clears_everything_that_depended_on_it():
    at = loaded(GOOD)
    at.session_state["pins"] = {1: "jazz"}
    at.file_uploader[0].set_value(None).run()
    assert at.session_state["performer_file"] is None
    assert at.session_state["show"] is None
    assert at.session_state["pins"] == {}
    assert len(at.tabs) == 0 and labels(at.button) == []


def test_clear_all_data_empties_the_session_and_the_upload_box():
    at = loaded(GOOD)
    at.session_state["pins"] = {1: "jazz"}
    at.session_state["run"] = {"result": "x"}
    assert labels(at.button) == ["Clear all data"]
    at.button[0].click().run()
    assert not at.exception
    assert at.session_state["performer_file"] is None
    assert at.session_state["show"] is None
    assert at.session_state["pins"] == {}
    assert at.session_state["run"] is None
    assert at.file_uploader[0].value is None
    assert len(at.tabs) == 0 and len(at.success) == 0
    assert labels(at.button) == []


def test_clear_all_data_gives_the_upload_box_a_new_identity():
    at = loaded(GOOD)
    before = at.file_uploader[0].key
    at.button[0].click().run()
    assert at.file_uploader[0].key != before
    upload(at, GOOD)
    before_second = at.file_uploader[0].key
    at.button[0].click().run()
    assert at.file_uploader[0].key not in (before, before_second)


def test_clear_all_data_also_removes_an_error_box_and_the_pickers():
    at = loaded(FOUR_COLUMNS)
    at.button[0].click().run()
    assert len(at.selectbox) == 0 and len(at.info) == 0
    at = loaded(b"")
    assert len(at.error) == 1
    at.button[0].click().run()
    assert len(at.error) == 0


def test_a_file_can_be_loaded_again_after_clearing():
    at = loaded(GOOD)
    at.button[0].click().run()
    upload(at, GOOD)
    assert len(at.success) == 1
    assert labels(at.tabs) == TABS


# ---------------------------------------------------------------- the settings and the rules


def test_the_config_switches_off_statistics_and_tracebacks_and_stays_local():
    config = tomllib.loads((ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8"))
    assert config["browser"]["gatherUsageStats"] is False  # D49
    assert config["client"]["showErrorDetails"] == "none"
    assert config["server"]["address"] == "localhost"  # Q16 (a): this computer only
    assert config["server"]["maxUploadSize"] <= 10


def imported_modules(path: Path) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
    return found


def test_the_page_imports_only_the_shared_layer_never_the_command_line():
    allowed = {"models", "io", "selection", "report", "validator", "solver"}
    ours = {
        name.split(".")[1]
        for name in imported_modules(APP_FILE)
        if name.startswith("performance_scheduling.")
    }
    assert ours <= allowed
    assert "cli" not in ours


def test_only_the_page_imports_streamlit():
    for path in (ROOT / "src" / "performance_scheduling").glob("*.py"):
        uses = any(name.split(".")[0] == "streamlit" for name in imported_modules(path))
        assert uses == (path.name == "app.py"), path.name


# ================================================================ the "Check a schedule" tab (U3)

EXAMPLES = ROOT / "data" / "examples"
SHOW_FILE = "tiny_feasible.csv"
VALID_FILE = "tiny_feasible_schedule_valid.csv"
INVALID_FILE = "tiny_feasible_schedule_invalid.csv"
BROKEN_FILE = "tiny_feasible_schedule_broken.csv"
ALL_EIGHT_FILE = "tiny_feasible_schedules_all8.csv"

SCHEDULE_LABEL = "Schedule file (CSV): one running order, or several side by side"
GAP_LABEL = "Rest between a performer's performances (slots)"
DOWNLOAD_LABEL = "Download the problems (CSV)"

VALID_ORDER = [
    "Bollywood (Open)",
    "Contemporary (Open)",
    "Hip Hop (Foundations)",
    "Tap (Foundations)",
    "Jazz (Open)",
    "Kpop Girls (Intermediate)",
]
# The valid order with Hip Hop and Bollywood swapped: Person 0006 is in Bollywood (slot 3)
# and Tap (slot 4), back to back.
INVALID_ORDER = [
    "Hip Hop (Foundations)",
    "Contemporary (Open)",
    "Bollywood (Open)",
    "Tap (Foundations)",
    "Jazz (Open)",
    "Kpop Girls (Intermediate)",
]


def example(name: str) -> bytes:
    return (EXAMPLES / name).read_bytes()


def side_by_side(columns: dict[str, list[str]]) -> str:
    """Schedule CSV text: a position column and one column per schedule."""
    length = len(next(iter(columns.values())))
    lines = ["position," + ",".join(columns)]
    for row in range(length):
        lines.append(f"{row + 1}," + ",".join(order[row] for order in columns.values()))
    return "\n".join(lines) + "\n"


def with_schedule(
    schedule: str | bytes,
    name: str = "plan.csv",
    *,
    show: str | bytes | None = None,
    gap: int | None = None,
) -> AppTest:
    """The page with a performer file loaded (the example show unless `show` is given), a
    schedule file uploaded and, if asked, the rest changed."""
    at = loaded(example(SHOW_FILE) if show is None else show, SHOW_FILE)
    return add_schedule(at, schedule, name, gap=gap)


def add_schedule(
    at: AppTest, schedule: str | bytes, name: str = "plan.csv", *, gap: int | None = None
) -> AppTest:
    raw = schedule if isinstance(schedule, bytes) else schedule.encode("utf-8")
    assert at.file_uploader[1].label == SCHEDULE_LABEL
    at.file_uploader[1].set_value((name, raw, "text/csv")).run()
    if gap is not None:
        at.number_input[0].set_value(gap).run()
    assert not at.exception
    return at


def headings(at: AppTest) -> list[str]:
    """The headings of each schedule's write-up and the overview, as the organiser reads them."""
    return [plain(m.value) for m in at.markdown if m.value.startswith("####")]


def boxes(elements) -> list[str]:
    return [plain(element.value) for element in elements]


def checked(schedule_file: str, gap: int = 1):
    data = load_performers(EXAMPLES / SHOW_FILE).data
    schedules = load_schedules(EXAMPLES / schedule_file).schedules
    return data, check_schedules(data, schedules, gap)


# ---------------------------------------------------------------- the tab before any upload


def test_the_checker_tab_holds_the_uploader_and_the_rest_and_nothing_else_yet():
    at = loaded(example(SHOW_FILE), SHOW_FILE)
    check_tab = at.tabs[1]
    assert labels(check_tab.file_uploader) == [SCHEDULE_LABEL]
    assert check_tab.file_uploader[0].allowed_type == [".csv"]
    assert labels(check_tab.number_input) == [GAP_LABEL]
    assert at.tabs[0].file_uploader == [] and at.tabs[0].number_input == []
    assert at.number_input[0].value == 1 and at.number_input[0].min == 0
    assert headings(at) == []
    assert len(at.dataframe) == 0 and len(at.error) == 0 and len(at.warning) == 0
    assert labels(at.download_button) == ["Example file (download)"]


# ---------------------------------------------------------------- one valid schedule


def test_a_valid_schedule_says_valid_and_nothing_is_wrong():
    at = with_schedule(example(VALID_FILE), "valid.csv")
    assert headings(at) == ["#### ✅ schedule_1: VALID"]
    text = all_text(at)
    assert "6 slots (no breaks)." in text
    assert "Tightest spacing: 1 slot between a performer's performances." in text
    assert len(at.dataframe) == 0  # no overview for one schedule, no pairs to list
    assert len(at.expander) == 0
    assert len(at.error) == 0 and len(at.warning) == 0
    assert labels(at.download_button) == ["Example file (download)"]  # nothing to download


def test_a_valid_schedule_with_a_break_counts_it_and_the_empty_cell_is_a_warning():
    rows = "\n".join(f"{i},{name}" for i, name in enumerate(VALID_ORDER, 1))
    at = with_schedule(f"position,schedule_1\n{rows}\n7,\n")
    assert headings(at) == ["#### ✅ schedule_1: VALID"]
    assert "7 slots (1 break)." in all_text(at)
    (box,) = at.expander
    assert box.label == "⚠️ 1 thing to check in the schedule file"
    assert box.proto.expanded is True


# ---------------------------------------------------------------- one invalid schedule


def test_an_invalid_schedule_lists_the_clashing_pair_and_who_is_affected():
    at = with_schedule(example(INVALID_FILE), "invalid.csv")
    assert headings(at) == ["#### ❌ schedule_1: INVALID"]
    assert "6 slots (no breaks)." in all_text(at)
    assert "**Conflicting performance pairs (1)**" in [m.value for m in at.markdown]
    (table,) = at.dataframe
    assert table.value.to_dict("records") == [
        {
            "No.": 1,
            "First performance": "Bollywood (Open)",
            "First slot": 3,
            "Second performance": "Tap (Foundations)",
            "Second slot": 4,
            "Slots between": 0,
            "Slots needed": 1,
            "Performers affected": 1,
        }
    ]
    (who,) = at.expander
    assert who.label == "Who is affected (1 performer)"
    assert who.proto.expanded is True  # one schedule: the organiser wants the names at once
    assert plain(who.markdown[0].value) == "**1. Bollywood (Open) and Tap (Foundations)**\n\n- Person 0006"
    assert "Tightest spacing: 0 slots between a performer's performances." in all_text(at)


def test_the_page_uses_the_commands_sentences():
    data, (check,) = checked(INVALID_FILE)
    at = with_schedule(example(INVALID_FILE))
    shown = all_text(at)
    write_up = [line.strip() for line in format_check(check, data).splitlines()]
    assert write_up[0] in shown  # "schedule_1: INVALID"
    assert write_up[1] in shown  # "6 slots (no breaks)."
    assert write_up[-1] in shown  # "Tightest spacing: ..."


def test_an_invalid_schedule_offers_the_problems_as_a_download():
    at = with_schedule(example(INVALID_FILE))
    assert labels(at.download_button) == ["Example file (download)", DOWNLOAD_LABEL]
    assert len(at.dataframe) == 1  # only the pairs: one schedule has no overview table


def test_the_download_is_the_commands_report_in_utf8_with_a_byte_order_mark():
    data, checks = checked(INVALID_FILE)
    raw = page._problems_csv(checks, data)
    assert raw.startswith(b"\xef\xbb\xbf")  # as io.write_text writes it, so Excel shows accents
    text = raw.decode("utf-8-sig")
    assert text == format_violations_csv(checks, data)
    assert text.splitlines() == [
        "schedule,performer,performance_a,position_a,performance_b,position_b,slots_between,required",
        "schedule_1,Person 0006,Bollywood (Open),3,Tap (Foundations),4,0,1",
    ]


def test_the_downloaded_file_is_named_after_the_schedule_file():
    assert page._problems_file_name("my show.csv") == "my show_problems.csv"
    assert page._problems_file_name("plan") == "plan_problems.csv"


# ---------------------------------------------------------------- problems with the schedule itself


def test_structural_problems_get_their_own_box_and_spacing_is_not_checked():
    at = with_schedule(example(BROKEN_FILE), "broken.csv")
    assert headings(at) == ["#### ❌ schedule_1: INVALID"]
    (box,) = at.error
    text = plain(box.value)
    assert text.startswith("**Problems with the schedule itself (4)**")
    assert "Spacing was not checked." in text
    assert '- "Salsa (Open)" is in the schedule (position 1) but not in the performer file.' in text
    assert '- "Hip Hop (Foundations)" appears 2 times in the schedule (positions 2 and 3).' in text
    assert '- "Bollywood (Open)" is in the performer file but missing from the schedule.' in text
    assert '- "Contemporary (Open)" is in the performer file but missing from the schedule.' in text
    assert len(at.dataframe) == 0 and len(at.expander) == 0
    assert labels(at.download_button) == ["Example file (download)"]  # no violations to download
    assert "Tightest spacing" not in all_text(at)
    assert "=====" not in all_text(at)  # none of the command's divider lines leaks onto the page


def test_a_misspelt_performance_comes_with_the_did_you_mean_hint():
    typo = [name.replace("Bollywood", "Bolywood") for name in VALID_ORDER]
    at = with_schedule(side_by_side({"schedule_1": typo}))
    text = plain(at.error[0].value)
    assert "Did you mean" in text
    assert "Bollywood (Open)" in text


# ---------------------------------------------------------------- several schedules


def test_several_schedules_get_an_overview_table_that_matches_the_command():
    _, checks = checked(ALL_EIGHT_FILE, gap=2)
    at = with_schedule(example(ALL_EIGHT_FILE), "all8.csv", gap=2)
    overview = at.dataframe[0].value
    rows = overview_rows(checks)
    assert list(overview.columns) == [
        "Schedule", "Result", "Slots", "Breaks", "Problems", "Tightest gap"
    ]
    assert [tuple(row) for row in overview.itertuples(index=False)] == rows[1:]
    # and it is the table the command prints, cell for cell
    printed = [tuple(line.split()) for line in format_overview(checks).splitlines()]
    assert printed[1:] == rows[1:]  # (the header's "Tightest gap" has a space in it)
    assert headings(at)[0] == "#### Overview"
    assert len(headings(at)) == 1 + 8  # the overview and a write-up for each of the 8


def test_the_closing_sentence_is_the_commands_and_its_colour_follows_the_result():
    _, all_invalid = checked(ALL_EIGHT_FILE, gap=2)
    at = with_schedule(example(ALL_EIGHT_FILE), gap=2)
    assert boxes(at.error) == [format_totals(all_invalid)] == ["All 8 schedules are invalid."]

    at = with_schedule(example(ALL_EIGHT_FILE), gap=1)
    assert boxes(at.success)[-1] == "All 8 schedules are valid."
    assert len(at.error) == 0 and len(at.warning) == 0


def test_all_valid_schedules_have_nothing_to_download_and_no_pairs_table():
    at = with_schedule(example(ALL_EIGHT_FILE), gap=1)
    assert len(at.dataframe) == 1  # the overview only
    assert labels(at.download_button) == ["Example file (download)"]
    assert headings(at) == ["#### Overview"] + [f"#### ✅ schedule_{n}: VALID" for n in range(1, 9)]


def test_a_mixture_is_reported_with_a_warning_box_and_each_verdict():
    both = side_by_side({"good": VALID_ORDER, "bad": INVALID_ORDER})
    at = with_schedule(both)
    assert headings(at) == ["#### Overview", "#### ✅ good: VALID", "#### ❌ bad: INVALID"]
    assert boxes(at.warning) == ["1 of 2 schedules are invalid."]
    assert len(at.error) == 0
    overview = at.dataframe[0].value
    assert list(overview["Result"]) == ["VALID", "INVALID"]
    assert labels(at.download_button) == ["Example file (download)", DOWNLOAD_LABEL]


def test_the_names_of_who_is_affected_are_collapsed_when_there_are_several_schedules():
    at = with_schedule(example(ALL_EIGHT_FILE), gap=2)
    assert len(at.expander) == 8
    assert all(box.proto.expanded is False for box in at.expander)


def test_with_more_than_ten_schedules_valid_ones_appear_only_in_the_table():
    columns = {f"schedule_{n}": VALID_ORDER for n in range(1, 13)}
    columns["schedule_7"] = INVALID_ORDER
    at = with_schedule(side_by_side(columns))
    assert headings(at) == ["#### Overview", "#### ❌ schedule_7: INVALID"]
    assert len(at.dataframe[0].value) == 12
    assert "Valid schedules are listed in the table only." in [c.value for c in at.caption]
    assert boxes(at.warning) == ["1 of 12 schedules are invalid."]


def test_ten_schedules_still_get_a_full_write_up_each():
    at = with_schedule(side_by_side({f"s{n}": VALID_ORDER for n in range(1, 11)}))
    assert len(headings(at)) == 11
    assert "Valid schedules are listed in the table only." not in [c.value for c in at.caption]


# ---------------------------------------------------------------- the rest (the gap)


def test_changing_the_rest_checks_again_at_once():
    at = with_schedule(example(INVALID_FILE))
    assert headings(at) == ["#### ❌ schedule_1: INVALID"]
    at.number_input[0].set_value(0).run()  # no rest needed: everything passes
    assert headings(at) == ["#### ✅ schedule_1: VALID"]
    assert "Tightest spacing: 0 slots" in all_text(at)
    assert len(at.dataframe) == 0


def test_a_longer_rest_can_make_a_valid_schedule_invalid():
    at = with_schedule(example(VALID_FILE), gap=2)
    assert headings(at) == ["#### ❌ schedule_1: INVALID"]
    (table,) = at.dataframe
    assert set(table.value["Slots needed"]) == {2}


# ---------------------------------------------------------------- files that cannot be used

@pytest.mark.parametrize(
    "content, expected",
    [
        (b"", "The file is empty."),
        (b"position\n1\n", "The file has no schedule columns, only the position column."),
        (b"position,a,a\n1,Jazz,Tap\n", 'Two schedule columns are called "a" and "a"'),
        (b"\xff\xfe\x00not utf-8", 'Save As" and choose "CSV UTF-8"'),
    ],
)
def test_an_unusable_schedule_file_gets_a_red_box_and_the_show_stays_loaded(content, expected):
    at = with_schedule(content, "plan.csv")
    (box,) = at.error
    text = plain(box.value)
    assert text.startswith("**The schedule file plan.csv cannot be used**")
    assert expected in text
    assert headings(at) == []
    assert len(at.dataframe) == 0
    assert labels(at.tabs) == TABS  # the performer file is still fine
    assert at.session_state["show"] is not None


def test_a_schedule_file_with_markdown_characters_in_its_name_is_named_as_written():
    at = with_schedule(b"", "my_*plan*.csv")
    assert "The schedule file my_*plan*.csv cannot be used" in plain(at.error[0].value)


def test_an_unexpected_failure_while_reading_shows_no_traceback(monkeypatch):
    def boom(*_args, **_kwargs):
        raise RuntimeError("secret detail naming Amy")

    monkeypatch.setattr("performance_scheduling.io.parse_schedules", boom)
    at = with_schedule(example(VALID_FILE))
    assert len(at.exception) == 0
    (box,) = at.error
    assert box.value.startswith("Something unexpected went wrong while reading this file")
    assert "Amy" not in box.value and "secret" not in box.value


def test_an_unexpected_failure_while_checking_shows_no_traceback(monkeypatch):
    def boom(*_args, **_kwargs):
        raise RuntimeError("secret detail naming Amy")

    monkeypatch.setattr("performance_scheduling.validator.check_schedules", boom)
    at = with_schedule(example(VALID_FILE))
    assert len(at.exception) == 0
    (box,) = at.error
    assert box.value.startswith("Something unexpected went wrong while checking this schedule")
    assert "Amy" not in box.value and "secret" not in box.value
    assert headings(at) == []


# ---------------------------------------------------------------- warnings about the schedule file


def test_warnings_about_the_schedule_file_are_shown_in_full_above_the_results():
    rows = "\n".join(f"{i},{name}" for i, name in enumerate(VALID_ORDER, 1))
    at = with_schedule(f"position,schedule_1\n{rows}\n7,\n")
    (box,) = at.expander
    assert plain(box.markdown[0].value) == (
        '- WARNING: row 8: empty slot in "schedule_1" treated as a break'
    )
    # the results are still there: a warning never stops the check
    assert headings(at) == ["#### ✅ schedule_1: VALID"]


def test_warnings_about_the_two_files_are_told_apart():
    rows = "\n".join(f"{i},{name}" for i, name in enumerate(VALID_ORDER, 1))
    at = with_schedule(f"position,schedule_1\n{rows}\n7,\n", show=MESSY)
    assert [box.label for box in at.expander] == [
        "⚠️ 5 things to check in this file",
        "⚠️ 1 thing to check in the schedule file",
    ]


# ---------------------------------------------------------------- names typed by people


def test_names_with_markdown_characters_are_shown_as_written_in_the_results():
    show = "id,performance\nAmy_*B*,Jazz $5 [1]\nAmy_*B*,Tap_*x*\nCat,Other <b>\n"
    plan = side_by_side({"my_*plan*": ["Jazz $5 [1]", "Tap_*x*", "Other <b>"]})
    at = with_schedule(plan, show=show)
    assert headings(at) == ["#### ❌ my_*plan*: INVALID"]
    (table,) = at.dataframe  # a table shows text as it is
    assert table.value["First performance"][0] == "Jazz $5 [1]"
    assert table.value["Second performance"][0] == "Tap_*x*"
    (who,) = at.expander
    raw = who.markdown[0].value
    assert plain(raw) == "**1. Jazz $5 [1] and Tap_*x***\n\n- Amy_*B*"
    assert "\\$5 \\[1\\]" in raw and "Tap\\_\\*x\\*" in raw  # escaped, so no maths, link or italics
    assert "- Amy\\_\\*B\\*" in raw  # and so are the performers' names


# ---------------------------------------------------------------- changing and removing files


def test_removing_the_schedule_file_removes_the_results():
    at = with_schedule(example(INVALID_FILE))
    at.file_uploader[1].set_value(None).run()
    assert headings(at) == []
    assert len(at.dataframe) == 0 and len(at.expander) == 0
    assert labels(at.download_button) == ["Example file (download)"]


def test_a_new_schedule_file_replaces_the_old_result():
    at = with_schedule(example(INVALID_FILE), "one.csv")
    add_schedule(at, example(VALID_FILE), "two.csv")
    assert headings(at) == ["#### ✅ schedule_1: VALID"]
    assert len(at.dataframe) == 0


def test_a_new_performer_file_checks_the_same_schedule_again():
    show_a = "who,what\nAmy,Jazz\nAmy,Tap\nBen,Hip Hop\n"  # Amy: Jazz then Tap, back to back
    show_b = "who,what\nAmy,Jazz\nBen,Tap\nCat,Hip Hop\n"  # nobody is in two performances
    plan = side_by_side({"plan": ["Jazz", "Tap", "Hip Hop"]})
    at = with_schedule(plan, show=show_a)
    assert headings(at) == ["#### ❌ plan: INVALID"]
    upload(at, show_b, "other.csv")
    assert not at.exception
    assert headings(at) == ["#### ✅ plan: VALID"]
    assert "No performer is in more than one performance, so spacing does not apply." in all_text(at)


def test_a_performer_file_that_cannot_be_used_hides_the_results():
    at = with_schedule(example(INVALID_FILE))
    upload(at, b"", "empty.csv")
    assert len(at.tabs) == 0
    assert headings(at) == []
    assert len(at.dataframe) == 0


def test_clear_all_data_also_forgets_the_schedule_file():
    at = with_schedule(example(INVALID_FILE))
    at.button[0].click().run()
    assert len(at.tabs) == 0 and headings(at) == []
    upload(at, example(SHOW_FILE), SHOW_FILE)
    assert at.file_uploader[1].label == SCHEDULE_LABEL
    assert at.file_uploader[1].value is None  # a fresh upload box, not the old file
    assert headings(at) == []
    assert at.number_input[0].value == 1


def test_clear_all_data_gives_the_schedule_upload_box_a_new_identity():
    # In a browser an unchanged key would keep showing the old file, so the key is checked.
    at = with_schedule(example(INVALID_FILE))
    before = at.file_uploader[1].key
    at.button[0].click().run()
    upload(at, example(SHOW_FILE), SHOW_FILE)
    assert at.file_uploader[1].key != before


def test_the_checker_keeps_nothing_in_the_pages_memory():
    at = with_schedule(example(INVALID_FILE))
    assert at.session_state["run"] is None and at.session_state["pins"] == {}
    assert at.session_state["form"] == {}
