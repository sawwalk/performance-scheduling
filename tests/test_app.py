"""Tests for the page's skeleton and its "Your show" section (task U2).

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
