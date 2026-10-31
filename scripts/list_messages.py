"""List every message the tools can show, and check the catalogue in docs/error-messages.md.

Run from the repo root. It is a developer tool for a checkout of the project, not part of the
installed package, and it reads the files in `src/performance_scheduling/`:

    python scripts/list_messages.py            # print every message
    python scripts/list_messages.py --check    # fail if the catalogue is out of date

It reads the code with `ast` (it imports nothing from the package, so it never loads
OR-Tools or Streamlit), so it cannot drift from the code. `tests/test_error_messages.py`
runs the same check, so adding a message without a catalogue entry fails the test suite.

What counts as a message (the catalogue's "what is listed" section repeats this):

1. Text given to the calls that report a problem or a result: `Issue(...)`, `InputError(...)`,
   `ValueError(...)`, `RuntimeError(...)`, `SolverNotInstalled(...)`, `argparse.ArgumentTypeError(...)`,
   `_error(...)`, `problems.append(...)`, `format_issues(...)`, `print(...)` in cli.py and
   the page's `st.error`, `st.warning`, `st.info`, `st.success`, `st.caption`, `st.spinner`,
   `_show_problem`, `_issue_list`.
2. Module-level text constants such as `UNEXPECTED_PROBLEM` (not the ones ending in `_LABEL`,
   `_HELP`, `_HEADING`, `_PLACEHOLDER`, `_FADE` or `_QUESTION`, which are widget wording).
3. Text inside the functions listed in `MESSAGE_FUNCTIONS`, which build result sentences.
4. Text assigned to a local variable called `message`, `what` or `heading`, or given as the default
   of a parameter called `heading`: these are built first and passed on later.

Docstrings, comments, `--help` text, widget labels, table headings (including the ALL-CAPS
section headings in the report) and file-name patterns are not messages. A message is compared by its words only: each `{...}` placeholder in an f-string
counts as `…`, so the catalogue shows `…` where the organiser sees a value.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src" / "performance_scheduling"
CATALOGUE = ROOT / "docs" / "error-messages.md"

# Layer order, then the page (docs/repo-structure.md). This file and make_api_summary are not listed.
MODULES = (
    "models",
    "io",
    "conflicts",
    "selection",
    "report",
    "validator",
    "solver",
    "cli",
    "app",
)

# Calls whose text arguments are messages.
MESSAGE_CALLS = frozenset(
    {
        "Issue",
        "InputError",
        "ValueError",
        "RuntimeError",
        "SolverNotInstalled",
        "argparse.ArgumentTypeError",
        "_error",
        "problems.append",
        "format_issues",
        "_issue_list",
        "_show_problem",
        "print",
        "st.error",
        "st.warning",
        "st.info",
        "st.success",
        "st.caption",
        "st.spinner",
    }
)

# Module-level constants with these endings are widget wording, not messages.
WORDING_SUFFIXES = ("_LABEL", "_HELP", "_HEADING", "_PLACEHOLDER", "_FADE", "_QUESTION")

# Functions that build result sentences without calling one of the message calls.
MESSAGE_FUNCTIONS = {
    "report": (
        "format_check",
        "format_totals",
        "format_found",
        "format_written",
        "format_availability",
        "format_missing",
        "format_larger_gap_prompt",
        "no_schedules_heading",
    ),
    "solver": ("_why_none_exist", "find_schedules"),
}

# Local variables whose text is built first and passed on later (rule 4).
MESSAGE_VARIABLES = frozenset({"message", "what"})

PLACEHOLDER = "…"


def _words(text: str) -> int:
    """How many space-separated words contain letters (a placeholder is not a word)."""
    return sum(1 for word in text.split() if re.search(r"[A-Za-z]{2,}", word))


def _is_heading(text: str) -> bool:
    """ALL-CAPS text, such as the report's section headings."""
    letters = [c for c in text if c.isalpha()]
    return bool(letters) and all(c.isupper() for c in letters)


def _render(node: ast.AST) -> str | None:
    """The text of a string literal or f-string, with each placeholder shown as `…`."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        text = re.sub(r"\{[^{}]*\}", PLACEHOLDER, node.value)
    elif isinstance(node, ast.JoinedStr):
        text = "".join(
            part.value if isinstance(part, ast.Constant) else PLACEHOLDER for part in node.values
        )
    else:
        return None
    return " ".join(text.split())


def _call_name(call: ast.Call) -> str:
    return ast.unparse(call.func)


def _strings_in(node: ast.AST) -> list[ast.AST]:
    """String literals and whole f-strings under `node`, not their pieces."""
    found: list[ast.AST] = []

    def visit(current: ast.AST) -> None:
        if isinstance(current, ast.JoinedStr) or (
            isinstance(current, ast.Constant) and isinstance(current.value, str)
        ):
            found.append(current)
            return
        for child in ast.iter_child_nodes(current):
            visit(child)

    visit(node)
    return found


def _docstrings(tree: ast.AST) -> set[int]:
    ids: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef)):
            first = node.body[0] if node.body else None
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
                ids.add(id(first.value))
    return ids


def extract(module: str) -> list[tuple[str, int]]:
    """(text, line) for every message in one module, in code order."""
    tree = ast.parse((PACKAGE / f"{module}.py").read_text(encoding="utf-8"))
    skip = _docstrings(tree)
    found: list[tuple[str, int, ast.AST]] = []

    def add(node: ast.AST, minimum: int) -> None:
        text = _render(node)
        if (
            text is not None
            and id(node) not in skip
            and _words(text) >= minimum
            and not _is_heading(text)
        ):
            found.append((text, node.lineno, node))  # type: ignore[attr-defined]

    for node in ast.walk(tree):
        # 1. text given to the message calls
        if isinstance(node, ast.Call) and _call_name(node) in MESSAGE_CALLS:
            if module != "cli" and _call_name(node) == "print":
                continue
            for argument in [*node.args, *(k.value for k in node.keywords)]:
                for string in _strings_in(argument):
                    add(string, 1)
        # 4. text built in a local variable, or the default of a `heading` parameter
        if isinstance(node, (ast.Assign, ast.AugAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            names = {t.id for t in targets if isinstance(t, ast.Name)}
            if names & MESSAGE_VARIABLES:
                for string in _strings_in(node.value):
                    add(string, 1)
            if "heading" in names:
                for string in _strings_in(node.value):
                    add(string, 3)
        if isinstance(node, ast.FunctionDef):
            positional = [*node.args.posonlyargs, *node.args.args]
            defaults = [None] * (len(positional) - len(node.args.defaults)) + list(node.args.defaults)
            for argument, default in zip(positional, defaults, strict=True):
                if argument.arg == "heading" and default is not None:
                    add(default, 3)
        # 3. result sentences built in the listed functions
        if isinstance(node, ast.FunctionDef) and node.name in MESSAGE_FUNCTIONS.get(module, ()):
            for string in _strings_in(ast.Module(body=node.body, type_ignores=[])):
                text = _render(string) or ""
                # a sentence (starts with a capital) or three words, not a fragment like "a break"
                add(string, 1 if text[:1].isupper() else 3)
    # 2. module-level text constants
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            names = [t.id for t in targets if isinstance(t, ast.Name)]
            if names and not names[0].endswith(WORDING_SUFFIXES) and node.value is not None:
                for string in _strings_in(node.value):
                    add(string, 3)
    seen: set[tuple[str, int]] = set()
    unique: list[tuple[str, int]] = []
    for text, line, _ in sorted(found, key=lambda item: item[1]):
        if (text, line) not in seen:
            seen.add((text, line))
            unique.append((text, line))
    return unique


def code_messages() -> dict[str, list[str]]:
    """Every distinct message in the code, with where it is (`module.py:line`)."""
    messages: dict[str, list[str]] = {}
    for module in MODULES:
        for text, line in extract(module):
            messages.setdefault(text, []).append(f"{module}.py:{line}")
    return messages


def catalogue_messages(path: Path | None = None) -> list[str]:
    """The messages in the catalogue: the first `code span` of each table row."""
    messages: list[str] = []
    for line in (path or CATALOGUE).read_text(encoding="utf-8").splitlines():
        if line.startswith("|") and not line.startswith("|---"):
            match = re.match(r"\|\s*`([^`]+)`", line)
            if match:
                messages.append(" ".join(match.group(1).split()))
    return messages


def check(path: Path | None = None) -> list[str]:
    """Problems found: messages with no entry, entries with no message, and repeated entries."""
    in_code = code_messages()
    entries = catalogue_messages(path)
    problems = [
        f"Not in the catalogue: {text!r} ({', '.join(where)})"
        for text, where in in_code.items()
        if text not in entries
    ]
    problems += [f"Not in the code any more: {text!r}" for text in dict.fromkeys(entries) if text not in in_code]
    problems += [f"Listed more than once: {text!r}" for text in dict.fromkeys(entries) if entries.count(text) > 1]
    return problems


def main() -> int:
    if "--check" in sys.argv[1:]:
        problems = check()
        for problem in problems:
            print(problem)
        if problems:
            print(f"{len(problems)} problem(s). Update docs/error-messages.md.")
            return 1
        print(f"All {len(code_messages())} messages are in docs/error-messages.md.")
        return 0
    for text, where in code_messages().items():
        print(f"{where[0]}\t{text}" + (f"\t(+{len(where) - 1} more)" if len(where) > 1 else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
