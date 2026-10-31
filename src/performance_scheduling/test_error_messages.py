"""Tests for the message catalogue (task D2, docs/error-messages.md).

`list_messages.py` reads every message out of the code. These tests check that the
catalogue lists each one exactly once, and that the script itself finds what it should
(and skips what it should), using a tiny fake module so the rules are tested apart from
the real code.
"""

from pathlib import Path

import pytest

from performance_scheduling import list_messages as lm

FAKE = '''
"""A module docstring that is not a message."""
from performance_scheduling.models import Issue, Severity

UNEXPECTED_PROBLEM = "Something unexpected went wrong while testing."
SEED_LABEL = "Shuffle the seed for this run"
PICK_HELP = "Leave this empty for the default list"

def check(gap, name):
    """A docstring that is not a message."""
    if gap < 0:
        raise ValueError(f"gap {gap} cannot be negative")
    message = f'"{name}" is not in the file.'
    message += " Did you mean another?"
    return Issue(Severity.ERROR, message), "PROBLEMS WITH THE SCHEDULE ITSELF (3)"

def other():
    return Issue(Severity.WARNING, "A warning with {braces} in it.", 4)
'''


@pytest.fixture
def fake_package(tmp_path, monkeypatch):
    """A package folder holding only the fake module, and a catalogue path for it."""
    (tmp_path / "fake.py").write_text(FAKE, encoding="utf-8")
    monkeypatch.setattr(lm, "PACKAGE", tmp_path)
    monkeypatch.setattr(lm, "MODULES", ("fake",))
    return tmp_path


def write_catalogue(path: Path, *messages: str) -> Path:
    rows = "\n".join(f"| `{m}` | meaning | action |" for m in messages)
    path.write_text(f"| Message | What it means | What to do |\n|---|---|---|\n{rows}\n", encoding="utf-8")
    return path


FAKE_MESSAGES = [
    "Something unexpected went wrong while testing.",
    "gap … cannot be negative",
    "\"…\" is not in the file.",
    "Did you mean another?",
    "A warning with … in it.",
]


def test_the_real_catalogue_lists_every_message_exactly_once():
    assert lm.check() == []


def test_the_script_finds_each_kind_of_message(fake_package):
    assert list(lm.code_messages()) == FAKE_MESSAGES[:1] + [
        "gap … cannot be negative",
        '"…" is not in the file.',
        "Did you mean another?",
        "A warning with … in it.",
    ]


def test_labels_help_headings_and_docstrings_are_not_messages(fake_package):
    found = " ".join(lm.code_messages())
    assert "Shuffle the seed" not in found  # a _LABEL constant
    assert "Leave this empty" not in found  # a _HELP constant
    assert "PROBLEMS WITH" not in found  # an ALL-CAPS heading
    assert "docstring" not in found


def test_a_message_without_an_entry_is_reported(fake_package, tmp_path):
    catalogue = write_catalogue(tmp_path / "c.md", *FAKE_MESSAGES[:-1])
    problems = lm.check(catalogue)
    assert len(problems) == 1
    assert "Not in the catalogue" in problems[0]
    assert "A warning with … in it." in problems[0]


def test_an_entry_for_a_message_that_is_gone_is_reported(fake_package, tmp_path):
    catalogue = write_catalogue(tmp_path / "c.md", *FAKE_MESSAGES, "A message nobody raises.")
    assert lm.check(catalogue) == ["Not in the code any more: 'A message nobody raises.'"]


def test_a_message_listed_twice_is_reported(fake_package, tmp_path):
    catalogue = write_catalogue(tmp_path / "c.md", *FAKE_MESSAGES, FAKE_MESSAGES[0])
    assert lm.check(catalogue) == [f"Listed more than once: {FAKE_MESSAGES[0]!r}"]


def test_a_complete_catalogue_passes(fake_package, tmp_path):
    assert lm.check(write_catalogue(tmp_path / "c.md", *FAKE_MESSAGES)) == []


def test_the_check_command_exits_with_the_right_code(fake_package, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(lm, "CATALOGUE", write_catalogue(tmp_path / "c.md", *FAKE_MESSAGES[:-1]))
    monkeypatch.setattr("sys.argv", ["list_messages", "--check"])
    assert lm.main() == 1
    assert "Not in the catalogue" in capsys.readouterr().out


def test_the_check_command_succeeds_when_the_catalogue_is_complete(
    fake_package, tmp_path, monkeypatch, capsys
):
    monkeypatch.setattr(lm, "CATALOGUE", write_catalogue(tmp_path / "c.md", *FAKE_MESSAGES))
    monkeypatch.setattr("sys.argv", ["list_messages", "--check"])
    assert lm.main() == 0
    assert "All 5 messages" in capsys.readouterr().out
