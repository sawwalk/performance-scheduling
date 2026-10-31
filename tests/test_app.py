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


def expanders(at: AppTest) -> list:
    """The boxes with a heading of their own: the finder tab's \"More options\" is left out."""
    return [box for box in at.expander if box.label != "More options"]


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
    assert len(expanders(at)) == 0  # nothing to check, so no warnings box
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
    assert len(expanders(at)) == 0


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
    assert len(expanders(at)) == 1
    box = expanders(at)[0]
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
    assert expanders(at)[0].label == "⚠️ 1 thing to check in this file"


def test_more_than_twenty_warnings_are_shortened_like_the_command():
    rows = "id,performance\n" + "Amy,Jazz\n" * 26  # 25 duplicates
    at = loaded(rows)
    assert expanders(at)[0].label == "⚠️ 25 things to check in this file"
    lines = plain(expanders(at)[0].markdown[0].value).splitlines()
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
    assert "Amy_*B*, Jazz $5 [1]" in plain(expanders(at)[0].markdown[0].value)
    assert "*" not in re.sub(r"\\\*", "", expanders(at)[0].markdown[0].value)  # all escaped


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
    assert [box.key for box in at.selectbox] == ["pin_item"]  # the finder's, not a column picker
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
    assert labels(at.button)[0] == "Clear all data"
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
        at.number_input(key="check_gap").set_value(gap).run()
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
    assert at.tabs[0].file_uploader == []
    assert at.number_input(key="check_gap").value == 1 and at.number_input(key="check_gap").min == 0
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
    assert len(expanders(at)) == 0
    assert len(at.error) == 0 and len(at.warning) == 0
    assert labels(at.download_button) == ["Example file (download)"]  # nothing to download


def test_a_valid_schedule_with_a_break_counts_it_and_the_empty_cell_is_a_warning():
    rows = "\n".join(f"{i},{name}" for i, name in enumerate(VALID_ORDER, 1))
    at = with_schedule(f"position,schedule_1\n{rows}\n7,\n")
    assert headings(at) == ["#### ✅ schedule_1: VALID"]
    assert "7 slots (1 break)." in all_text(at)
    (box,) = expanders(at)
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
    (who,) = expanders(at)
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
    assert len(at.dataframe) == 0 and len(expanders(at)) == 0
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
    assert len(expanders(at)) == 8
    assert all(box.proto.expanded is False for box in expanders(at))


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
    at.number_input(key="check_gap").set_value(0).run()  # no rest needed: everything passes
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
    (box,) = expanders(at)
    assert plain(box.markdown[0].value) == (
        '- WARNING: row 8: empty slot in "schedule_1" treated as a break'
    )
    # the results are still there: a warning never stops the check
    assert headings(at) == ["#### ✅ schedule_1: VALID"]


def test_warnings_about_the_two_files_are_told_apart():
    rows = "\n".join(f"{i},{name}" for i, name in enumerate(VALID_ORDER, 1))
    at = with_schedule(f"position,schedule_1\n{rows}\n7,\n", show=MESSY)
    assert [box.label for box in expanders(at)] == [
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
    (who,) = expanders(at)
    raw = who.markdown[0].value
    assert plain(raw) == "**1. Jazz $5 [1] and Tap_*x***\n\n- Amy_*B*"
    assert "\\$5 \\[1\\]" in raw and "Tap\\_\\*x\\*" in raw  # escaped, so no maths, link or italics
    assert "- Amy\\_\\*B\\*" in raw  # and so are the performers' names


# ---------------------------------------------------------------- changing and removing files


def test_removing_the_schedule_file_removes_the_results():
    at = with_schedule(example(INVALID_FILE))
    at.file_uploader[1].set_value(None).run()
    assert headings(at) == []
    assert len(at.dataframe) == 0 and len(expanders(at)) == 0
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
    assert at.number_input(key="check_gap").value == 1


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


# ================================================================ the "Find schedules" tab (U4)

from performance_scheduling.io import format_schedules, schedule_rows
from performance_scheduling.models import FinderResult, FinderStatus, Issue, Severity
from performance_scheduling.report import (
    format_availability,
    format_found,
    format_larger_gap_prompt,
    format_missing,
    no_schedules_heading,
)
from performance_scheduling.solver import SolverNotInstalled, find_schedules

DENSE_FILE = "impossible_dense.csv"
BOLLYWOOD = "bollywood (open)"
HIP_HOP = "hip hop (foundations)"
TAP = "tap (foundations)"

FIND_LABEL = "Find schedules"
PICK_LABEL = "Which schedules"
STALE = "Settings changed. Press Find schedules to update."
NOT_INSTALLED_TEXT = (
    "The schedule finder is not installed on this computer. Ask whoever set it up to install it."
)


def finder(file_name: str = SHOW_FILE) -> AppTest:
    return loaded(example(file_name), file_name)


def find(at: AppTest) -> AppTest:
    at.button(key="find_schedules").click().run()
    assert not at.exception
    return at


def found(file_name: str = SHOW_FILE, **settings) -> AppTest:
    """Load a show, set widgets by key (gap=..., breaks=..., pick=..., seed=...), press Find."""
    at = finder(file_name)
    for name, value in settings.items():
        widget = at.text_input if name == "pick" else at.number_input
        widget(key=f"find_{name}").set_value(value)
    return find(at.run() if settings else at)


def pin(at: AppTest, slot: int, item: str) -> AppTest:
    at.number_input(key="pin_slot").set_value(slot)
    at.selectbox(key="pin_item").select(item).run()
    at.button(key="add_pin").click().run()
    assert not at.exception
    return at


def first_numbers(how_many: int, **settings):
    data = load_performers(EXAMPLES / SHOW_FILE).data
    return data, find_schedules(data, count=how_many, **settings)


def is_stale(at: AppTest) -> bool:
    """Is the result greyed with the "Settings changed" line? (`all_text` skips warnings.)"""
    return STALE in [plain(w.value) for w in at.warning]


def table(at: AppTest):
    (frame,) = at.dataframe
    return frame.value


# ---------------------------------------------------------------- the tab before a search


def test_the_finder_tab_holds_the_settings_the_pins_the_pick_and_the_search_button():
    at = finder()
    tab = at.tabs[0]
    assert labels(tab.number_input) == [
        GAP_LABEL,
        "Breaks",
        "Slot",
        "Shuffle seed",
        "Most schedules per run",
        "Longest search, seconds",
    ]
    assert [tab.number_input(key=k).value for k in ("find_gap", "find_breaks", "pin_slot")] == [
        1,
        0,
        1,
    ]
    assert at.number_input(key="find_seed").value is None
    assert at.number_input(key="find_limit").value == 100
    assert at.number_input(key="find_time_limit").value == 30
    assert at.text_input(key="find_pick").value == "1-5"
    assert at.selectbox(key="pin_item").value is None
    assert labels(tab.button) == ["Add pin", "Select all", "Shuffle", "Find schedules"]
    assert len(at.dataframe) == 0 and at.session_state["run"] is None
    assert at.tabs[0].expander[0].label == "More options"


def test_nothing_is_searched_until_the_button_is_pressed():
    at = finder()
    at.number_input(key="find_gap").set_value(2).run()
    assert at.session_state["run"] is None


def test_the_settings_are_a_valid_start_for_a_first_search():
    at = found()
    assert [plain(s.value) for s in at.success][-1] == "Found 5 schedules (numbers 1-5)."


# ---------------------------------------------------------------- found, more exist


def test_a_search_shows_the_commands_sentences_and_a_table_of_the_first_five():
    at = found()
    data, result = first_numbers(6)
    assert plain(at.success[-1].value) == format_found(5, "1-5")
    assert "More schedules exist after number 5." in all_text(at)
    header, *rows = schedule_rows(result.schedules[:5], data.performance_names)
    frame = table(at)
    assert list(frame.columns) == header
    assert [list(row) for row in frame.values.tolist()] == rows
    assert list(frame.columns)[1:] == [f"schedule_{n}" for n in range(1, 6)]


def test_every_schedule_shown_is_valid():
    at = found(pick="all")
    data = load_performers(EXAMPLES / SHOW_FILE).data
    shown = at.session_state["run"]["picked"].schedules
    assert len(shown) == 8  # the show has exactly eight (tiny_feasible_schedules_all8.csv)
    assert all(check.valid for check in check_schedules(data, shown, 1))


def test_the_seed_and_engine_line_names_the_default_order_and_the_version():
    at = found()
    caption = [plain(c.value) for c in at.caption][-1]
    assert caption.startswith("Seed: default order. Search engine: OR-Tools ")
    assert at.session_state["run"]["version"] in caption


def test_a_typed_pick_gives_exactly_those_numbers():
    at = found(pick="1,4,6")
    assert list(table(at).columns) == ["position", "schedule_1", "schedule_4", "schedule_6"]
    assert plain(at.success[-1].value) == format_found(3, "1,4,6")


def test_select_all_fills_in_all_and_a_search_lists_everything_up_to_the_limit():
    at = finder()
    at.button(key="select_all").click().run()
    assert at.text_input(key="find_pick").value == "all"
    find(at)
    assert plain(at.success[-1].value) == format_found(8, "1-8")
    assert "There are 8 schedules in all." in all_text(at)
    assert at.button(key="show_next") if False else not [b for b in at.button if "next" in b.label]


# ---------------------------------------------------------------- shuffle and seed


def test_shuffle_puts_a_whole_number_in_the_seed_box(monkeypatch):
    monkeypatch.setattr("random.randint", lambda low, high: 4242)
    at = finder()
    at.button(key="shuffle").click().run()
    assert at.number_input(key="find_seed").value == 4242


def test_a_seed_gives_the_same_list_as_the_command_and_names_the_file():
    at = found(seed=7)
    data, result = first_numbers(6, seed=7)
    assert [list(r) for r in table(at).values.tolist()] == schedule_rows(
        result.schedules[:5], data.performance_names
    )[1:]
    assert [plain(c.value) for c in at.caption][-1].startswith("Seed: 7. Search engine")


def test_the_same_seed_twice_gives_the_same_table():
    one = table(found(seed=3)).values.tolist()
    two = table(found(seed=3)).values.tolist()
    assert one == two


# ---------------------------------------------------------------- downloads


def offered_downloads(monkeypatch) -> list[dict]:
    """Record what the page hands to `st.download_button` (AppTest does not keep the bytes)."""
    from streamlit.delta_generator import DeltaGenerator

    offered: list[dict] = []
    real = DeltaGenerator.download_button

    def spy(self, label, data=None, file_name=None, mime=None, **kwargs):
        offered.append({"label": label, "data": data, "file_name": file_name, "mime": mime})
        return real(self, label, data=data, file_name=file_name, mime=mime, **kwargs)

    monkeypatch.setattr(DeltaGenerator, "download_button", spy)
    return offered


def schedules_offered(offered: list[dict]) -> dict:
    (one,) = [d for d in offered if d["label"] == "Download these schedules (CSV)"]
    return one


def test_the_download_is_the_commands_csv_named_by_seed_and_pick(monkeypatch):
    offered = offered_downloads(monkeypatch)
    at = found(seed=5, pick="2-3")
    data, result = first_numbers(4, seed=5)
    assert [s.name for s in at.session_state["run"]["picked"].schedules] == [
        "schedule_2",
        "schedule_3",
    ]
    download = schedules_offered(offered)
    expected = format_schedules(result.schedules[1:3], data.performance_names)
    assert expected.splitlines()[0] == "position,schedule_2,schedule_3"
    assert download["data"] == expected.encode("utf-8-sig")  # with Excel's byte-order mark
    assert download["file_name"] == "schedules_seed5_2-3.csv"
    assert download["mime"] == "text/csv"


def test_without_a_seed_the_file_is_named_by_the_pick_alone(monkeypatch):
    offered = offered_downloads(monkeypatch)
    found()
    assert schedules_offered(offered)["file_name"] == "schedules_1-5.csv"


def test_the_downloaded_file_goes_straight_to_the_schedule_checker(monkeypatch):
    offered = offered_downloads(monkeypatch)
    found()
    csv_bytes = schedules_offered(offered)["data"]
    at = with_schedule(csv_bytes, "schedules_1-5.csv")
    assert [plain(s.value) for s in at.success][-1] == format_totals(
        check_schedules(
            load_performers(EXAMPLES / SHOW_FILE).data,
            load_schedules_from_bytes(csv_bytes),
            1,
        )
    )


def load_schedules_from_bytes(raw: bytes):
    from performance_scheduling.io import decode_text, parse_schedules

    return parse_schedules(decode_text(raw, "x.csv")).schedules


# ---------------------------------------------------------------- show the next batch


def test_show_the_next_five_searches_again_and_skips_what_came_before():
    at = found()
    next_button = at.button(key="show_next")
    assert next_button.label == "Show the next 5"
    next_button.click().run()
    assert not at.exception
    assert at.text_input(key="find_pick").value == "6-10"
    assert plain(at.success[-1].value) == format_found(3, "6-8")
    assert list(table(at).columns) == ["position", "schedule_6", "schedule_7", "schedule_8"]
    assert "There are 8 schedules in all." in all_text(at)
    assert not [b for b in at.button if b.label.startswith("Show the next")]


def test_the_next_batch_is_the_same_numbers_as_the_command_would_write():
    at = found(pick="1-3")
    assert at.button(key="show_next").label == "Show the next 3"
    at.button(key="show_next").click().run()
    assert at.text_input(key="find_pick").value == "4-6"
    assert list(table(at).columns)[1:] == ["schedule_4", "schedule_5", "schedule_6"]


def test_a_single_schedule_batch_says_so():
    at = found(pick="1")
    assert at.button(key="show_next").label == "Show the next schedule"


def test_the_button_is_not_shown_when_no_more_exist():
    at = found(pick="4-8")
    assert at.button(key="show_next") if False else not [
        b for b in at.button if b.label.startswith("Show the next")
    ]
    assert "There are 8 schedules in all." in all_text(at)


def test_numbers_past_the_end_are_named_as_missing():
    at = found(pick="7-10")
    assert plain(at.success[-1].value) == format_found(2, "7-8")
    assert format_missing("9-10", 2, stopped=False, total=8) in [
        plain(w.value) for w in at.warning
    ]


def test_a_pick_entirely_past_the_end_shows_only_what_is_missing():
    at = found(pick="9-10")
    assert len(at.dataframe) == 0
    assert [plain(w.value) for w in at.warning] == [
        format_missing("9-10", 2, stopped=False, total=8)
    ]
    assert len(at.error) == 0


# ---------------------------------------------------------------- a larger gap


def test_the_larger_gap_invitation_is_the_commands_and_the_button_names_the_gap():
    at = found()
    assert format_larger_gap_prompt(1) in all_text(at)
    assert at.button(key="try_gap").label == "Try a gap of 2"


def test_try_a_larger_gap_changes_the_gap_and_searches_at_once():
    at = found()
    at.button(key="try_gap").click().run()
    assert not at.exception
    assert at.number_input(key="find_gap").value == 2
    assert at.session_state["run"]["settings"]["gap"] == 2
    assert not is_stale(at)


def test_nothing_is_checked_before_the_larger_gap_is_tried():
    # This show has 8 schedules with a gap of 1 and none with a gap of 2. The page offers
    # the larger gap anyway (D16) and the finder's own answer follows when it is pressed.
    at = found()
    assert at.button(key="try_gap").label == "Try a gap of 2"
    assert len(at.error) == 0
    at.button(key="try_gap").click().run()
    assert plain(at.error[-1].value).startswith("**" + no_schedules_heading(FinderStatus.EXHAUSTED))
    assert not [b for b in at.button if b.key == "try_gap"]  # nothing found, nothing to invite


# ---------------------------------------------------------------- none exist


def test_when_none_exist_a_red_box_gives_the_finders_reasons_unchanged():
    at = found(DENSE_FILE)
    data = load_performers(EXAMPLES / DENSE_FILE).data
    reasons = find_schedules(data, count=2).explanation
    (box,) = at.error
    text = plain(box.value)
    assert text.startswith("**No schedule exists.**")
    assert all(issue.message in text for issue in reasons)
    assert len(at.dataframe) == 0 and len(at.success) == 1  # only the file's status line
    assert not [d for d in at.download_button if d.label.startswith("Download these")]
    assert not [b for b in at.button if b.key in ("show_next", "try_gap", "search_longer")]
    assert len(at.warning) == 0


# ---------------------------------------------------------------- stopped


def stopped_result(schedules=()):
    note = Issue(Severity.WARNING, "The time limit of 30 seconds was reached.")
    return FinderResult(FinderStatus.STOPPED, tuple(schedules), explanation=(note,))


def test_a_search_stopped_with_nothing_found_gets_a_yellow_box_never_none_exist(monkeypatch):
    monkeypatch.setattr(
        "performance_scheduling.solver.find_schedules", lambda *a, **k: stopped_result()
    )
    at = found()
    (box,) = at.warning
    text = plain(box.value)
    assert text.startswith("**No schedule was found before the time limit.**")
    assert "The time limit of 30 seconds was reached." in text
    assert "No schedule exists" not in all_text(at)
    assert len(at.error) == 0


def test_search_for_longer_doubles_the_time_limit_and_searches_again(monkeypatch):
    seen = []

    def fake(*args, **kwargs):
        seen.append(kwargs["time_limit"])
        return stopped_result()

    monkeypatch.setattr("performance_scheduling.solver.find_schedules", fake)
    at = found()
    at.button(key="search_longer").click().run()
    assert seen == [30.0, 60.0]
    assert at.number_input(key="find_time_limit").value == 60


def test_a_stopped_search_that_found_some_says_more_may_exist(monkeypatch):
    real = find_schedules

    def fake(data, **kwargs):
        part = real(data, count=2)
        return stopped_result(part.schedules)

    monkeypatch.setattr("performance_scheduling.solver.find_schedules", fake)
    at = found()
    assert plain(at.success[-1].value) == format_found(2, "1-2")
    assert format_availability(None, total=None, produced=2, last_number=2) in [
        plain(w.value) for w in at.warning
    ]
    assert at.button(key="search_longer")
    assert not [b for b in at.button if b.label.startswith("Show the next")]


# ---------------------------------------------------------------- bad picks


@pytest.mark.parametrize("pick", ["", "a", "1,,3", "0", "4-1", "1-1000"])
def test_a_bad_pick_gets_a_plain_message_and_the_search_does_not_run(pick):
    at = finder()
    at.text_input(key="find_pick").set_value(pick).run()
    assert len(at.error) == 1
    assert at.error[0].value  # a sentence, with an example where the shared reader gives one
    find(at)
    assert at.session_state["run"] is None
    assert len(at.dataframe) == 0


def test_a_pick_longer_than_the_limit_is_refused_and_a_higher_limit_allows_it():
    at = finder()
    at.text_input(key="find_pick").set_value("1-150").run()
    assert "the most allowed at once is 100" in plain(at.error[0].value)
    at.number_input(key="find_limit").set_value(200).run()
    assert len(at.error) == 0


def test_the_message_goes_away_when_the_pick_is_mended():
    at = finder()
    at.text_input(key="find_pick").set_value("x").run()
    assert len(at.error) == 1
    at.text_input(key="find_pick").set_value("1-2").run()
    assert len(at.error) == 0


# ---------------------------------------------------------------- pins


def test_pinning_lists_the_pin_with_a_remove_button():
    at = pin(finder(), 3, BOLLYWOOD)
    assert at.session_state["pins"] == {3: BOLLYWOOD}
    assert "Slot 3: Bollywood (Open)" in all_text(at)
    assert at.button(key="remove_pin_3").label == "Remove"


def test_add_pin_waits_for_an_item():
    at = finder()
    assert at.button(key="add_pin").disabled


def test_a_break_can_be_pinned_and_reads_as_a_break():
    at = pin(finder(), 2, "BREAK")
    assert "Slot 2: a break" in all_text(at)


def test_the_item_list_is_the_shows_performances_plus_break():
    at = finder()
    names = at.session_state["show"].data.performance_names
    assert at.selectbox(key="pin_item").options == ["Break", *sorted(names.values(), key=str.casefold)]


def test_the_slot_runs_from_one_to_the_number_of_slots():
    at = finder()
    slot = at.number_input(key="pin_slot")
    assert (slot.min, slot.max) == (1, 6)
    at.number_input(key="find_breaks").set_value(2).run()
    assert at.number_input(key="pin_slot").max == 8


def test_pinning_onto_a_taken_slot_replaces_it_and_pinning_again_moves_it():
    at = pin(finder(), 1, BOLLYWOOD)
    pin(at, 1, TAP)
    assert at.session_state["pins"] == {1: TAP}
    pin(at, 4, TAP)
    assert at.session_state["pins"] == {4: TAP}


def test_removing_a_pin_removes_it():
    at = pin(pin(finder(), 1, BOLLYWOOD), 2, HIP_HOP)
    at.button(key="remove_pin_1").click().run()
    assert at.session_state["pins"] == {2: HIP_HOP}


def test_a_search_keeps_the_pins_the_table_marks_them_and_the_finder_honours_them():
    at = find(pin(finder(), 1, BOLLYWOOD))
    frame = table(at)
    assert frame["position"][0] == "1 (pinned)"
    assert all(frame[col][0] == "Bollywood (Open)" for col in frame.columns[1:])
    assert at.session_state["run"]["settings"]["pins"] == ((1, BOLLYWOOD),)


def test_breaks_are_shown_as_break_in_the_table():
    at = found(breaks=1)
    cells = [cell for row in table(at).values.tolist() for cell in row[1:]]
    assert cells.count("BREAK") == 5  # one break in each of five schedules


def test_pins_that_cannot_be_kept_together_get_a_red_box_and_are_marked_in_the_list():
    at = find(pin(pin(finder(), 1, BOLLYWOOD), 2, HIP_HOP))
    assert plain(at.error[-1].value).startswith("**No schedule exists.**")
    text = all_text(at)
    assert text.count("These cannot all be kept") == 2
    assert "Slot 1: Bollywood (Open) ⚠️ These cannot all be kept" in text


def test_pins_that_do_not_fit_the_show_are_explained_by_the_finder():
    at = pin(finder(), 1, "BREAK")  # but the show has no breaks
    find(at)
    assert "pinned as breaks" in plain(at.error[-1].value)
    assert "These cannot all be kept" not in all_text(at)


def test_the_marks_go_when_the_pins_change():
    at = find(pin(pin(finder(), 1, BOLLYWOOD), 2, HIP_HOP))
    at.button(key="remove_pin_2").click().run()
    assert "These cannot all be kept" not in all_text(at)


# ---------------------------------------------------------------- stale results


def changing(widget_kind: str, key: str, value):
    def change(at: AppTest) -> None:
        getattr(at, widget_kind)(key=key).set_value(value).run()

    return change


@pytest.mark.parametrize(
    "change",
    [
        changing("number_input", "find_gap", 2),
        changing("number_input", "find_breaks", 1),
        changing("text_input", "find_pick", "1-3"),
        changing("number_input", "find_seed", 9),
        changing("number_input", "find_limit", 50),
        changing("number_input", "find_time_limit", 10),
    ],
    ids=["gap", "breaks", "pick", "seed", "limit", "time limit"],
)
def test_changing_any_setting_greys_the_result_and_says_so(change):
    at = found()
    assert not is_stale(at) and not at.warning
    change(at)
    assert [plain(w.value) for w in at.warning] == [STALE]
    assert len(at.dataframe) == 1  # still shown, never silently replaced
    for key in ("show_next", "try_gap"):
        assert at.button(key=key).disabled
    assert next(d for d in at.download_button if d.label.startswith("Download these")).disabled


def test_adding_a_pin_makes_the_result_stale_too():
    at = pin(found(), 1, BOLLYWOOD)
    assert is_stale(at)


def test_changing_a_setting_back_makes_the_result_current_again():
    at = found()
    at.number_input(key="find_gap").set_value(2).run()
    at.number_input(key="find_gap").set_value(1).run()
    assert not is_stale(at)
    assert not at.button(key="try_gap").disabled


def test_pressing_find_again_brings_the_result_up_to_date():
    at = found()
    at.text_input(key="find_pick").set_value("1-3").run()
    find(at)
    assert not is_stale(at)
    assert plain(at.success[-1].value) == format_found(3, "1-3")


def test_the_result_stays_current_when_nothing_changes():
    at = found()
    at.run()
    assert not is_stale(at)


# ---------------------------------------------------------------- when something goes wrong


def test_without_ortools_the_page_says_so_with_the_command_in_a_small_box(monkeypatch):
    def missing():
        raise SolverNotInstalled('The schedule finder needs OR-Tools. Install it with: pip install -e ".[finder]"')

    monkeypatch.setattr("performance_scheduling.solver.solver_version", missing)
    at = found()
    (box,) = at.error
    assert box.value == NOT_INSTALLED_TEXT
    (details,) = [e for e in expanders(at) if e.label == "What to give them"]
    assert "pip install" in details.code[0].value
    assert len(at.dataframe) == 0


def test_an_internal_check_failure_says_nothing_was_shown_and_keeps_the_details(monkeypatch):
    def broken(*_args, **_kwargs):
        raise RuntimeError("schedule_1 failed the checker")

    monkeypatch.setattr("performance_scheduling.solver.find_schedules", broken)
    at = found()
    (box,) = at.error
    assert box.value == "Something went wrong inside the finder, and no schedule was shown."
    (details,) = [e for e in expanders(at) if e.label.startswith("Details")]
    assert details.code[0].value == "schedule_1 failed the checker"
    assert len(at.dataframe) == 0


def test_anything_else_unexpected_gives_a_short_message_without_a_traceback(monkeypatch):
    def boom(*_args, **_kwargs):
        raise ValueError("secret detail naming Amy")

    monkeypatch.setattr("performance_scheduling.solver.find_schedules", boom)
    at = found()
    (box,) = at.error
    assert box.value.startswith("Something unexpected went wrong while searching")
    assert "Amy" not in box.value and "secret" not in box.value
    assert len(at.exception) == 0


def test_a_failure_goes_when_the_search_is_run_again(monkeypatch):
    monkeypatch.setattr(
        "performance_scheduling.solver.find_schedules",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("x")),
    )
    at = found()
    monkeypatch.undo()
    find(at)
    assert len(at.error) == 0 and plain(at.success[-1].value) == format_found(5, "1-5")


# ---------------------------------------------------------------- names, files and the session


def test_names_with_markdown_characters_show_as_written_in_the_pin_list_and_table():
    text = "who,what\nAmy,Jazz $5 [1]\nBen,Tap_*B*\nCat,Hip Hop\n"
    at = loaded(text)
    names = at.session_state["show"].data.performance_names
    key = next(k for k, v in names.items() if v.startswith("Jazz"))
    pin(at, 1, key)
    assert "Slot 1: Jazz $5 [1]" in all_text(at)
    find(at)
    assert "Jazz $5 [1]" in table(at).values.tolist()[0]


def test_a_new_performer_file_clears_the_result_the_pins_and_the_settings():
    at = find(pin(finder(), 1, BOLLYWOOD))
    at.number_input(key="find_gap").set_value(2).run()
    upload(at, GOOD, "another.csv")
    assert at.session_state["run"] is None and at.session_state["pins"] == {}
    assert at.number_input(key="find_gap").value == 1
    assert at.text_input(key="find_pick").value == "1-5"
    assert len(at.dataframe) == 0


def test_clear_all_data_clears_the_finder_too():
    at = find(finder())
    at.button[0].click().run()
    assert at.session_state["run"] is None and len(at.tabs) == 0
    upload(at, example(SHOW_FILE), SHOW_FILE)
    assert at.session_state["run"] is None and len(at.dataframe) == 0


def test_the_finder_and_the_checker_do_not_disturb_each_other():
    at = find(finder())
    at.tabs[1].number_input(key="check_gap").set_value(2).run()
    assert not is_stale(at)
    assert at.number_input(key="find_gap").value == 1


def test_the_page_writes_nothing_to_disk(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    find(finder())
    assert list(tmp_path.iterdir()) == []
