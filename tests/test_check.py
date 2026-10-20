"""Tests for skills/sembr-reformat/scripts/check.py.

Run with `python3 -m unittest discover -s tests`.
"""

from __future__ import annotations

import importlib.util
import io
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "skills/sembr-reformat/scripts/check.py"
spec = importlib.util.spec_from_file_location("check", SCRIPT)
check = importlib.util.module_from_spec(spec)
sys.modules["check"] = check  # dataclasses look the module up by name
spec.loader.exec_module(check)


def run(path: str, before: str, after: str, width: int = 80) -> check.Report:
    return check.check(path, before, after, width)


UDHR = (
    "All human beings are born free and equal in dignity and rights. "
    "They are endowed with reason and conscience "
    "and should act towards one another in a spirit of brotherhood.\n"
)
UDHR_SEMBR = (
    "All human beings are born free and equal in dignity and rights.\n"
    "They are endowed with reason and conscience\n"
    "and should act towards one another in a spirit of brotherhood.\n"
)


class MarkdownTests(unittest.TestCase):
    def test_accepts_a_reflow(self):
        report = run("a.md", "# Title\n\n" + UDHR, "# Title\n\n" + UDHR_SEMBR)
        self.assertEqual(report.errors, [])
        self.assertEqual(report.warnings, [])

    def test_rejects_changed_words(self):
        after = UDHR_SEMBR.replace("equal in", "equal")
        report = run("a.md", UDHR, after)
        self.assertEqual(len(report.errors), 1)
        self.assertIn("words changed", report.errors[0])

    def test_rejects_a_new_list_item(self):
        before = "Rates rose by 5 - 10 percent this year.\n"
        after = "Rates rose by 5\n- 10 percent this year.\n"
        report = run("a.md", before, after)
        self.assertTrue(any("block marker" in e for e in report.errors), report.errors)

    def test_rejects_joined_list_items(self):
        before = "- one\n- two\n"
        after = "- one - two\n"
        report = run("a.md", before, after)
        self.assertTrue(any("joined" in e for e in report.errors), report.errors)

    def test_rejects_text_joined_onto_a_heading(self):
        before = "# Title\nSome text here.\n"
        after = "# Title Some text here.\n"
        report = run("a.md", before, after)
        self.assertTrue(any("heading" in e for e in report.errors), report.errors)

    def test_rejects_a_new_hard_break(self):
        before = "One sentence here. Another one.\n"
        after = "One sentence here.  \nAnother one.\n"
        report = run("a.md", before, after)
        self.assertTrue(any("hard line break" in e for e in report.errors), report.errors)

    def test_rejects_a_changed_code_block(self):
        before = "Text.\n\n```\na b\nc\n```\n"
        after = "Text.\n\n```\na\nb c\n```\n"
        report = run("a.md", before, after)
        self.assertTrue(any("code block" in e for e in report.errors), report.errors)

    def test_rejects_a_removed_blank_line(self):
        before = "One paragraph.\n\nAnother paragraph.\n"
        after = "One paragraph.\nAnother paragraph.\n"
        report = run("a.md", before, after)
        self.assertTrue(any("blocks changed" in e for e in report.errors), report.errors)

    def test_accepts_block_quotes_and_list_paragraphs(self):
        before = (
            "> It works. Then it stops.\n\n"
            "- It works. Then it stops.\n\n"
            "    A second paragraph in the item. It has two sentences.\n"
        )
        after = (
            "> It works.\n> Then it stops.\n\n"
            "- It works.\n  Then it stops.\n\n"
            "    A second paragraph in the item.\n    It has two sentences.\n"
        )
        report = run("a.md", before, after)
        self.assertEqual(report.errors, [])

    def test_ignores_front_matter_and_tables(self):
        before = "---\ntitle: A. B\n---\n\n| a | b |\n|---|---|\n\nText. More.\n"
        after = "---\ntitle: A. B\n---\n\n| a | b |\n|---|---|\n\nText.\nMore.\n"
        report = run("a.md", before, after)
        self.assertEqual(report.errors, [])

    def test_warns_about_long_lines(self):
        before = " ".join(["word"] * 25) + ".\n"
        after = " ".join(["word"] * 20) + "\n" + " ".join(["word"] * 5) + ".\n"
        report = run("a.md", before, after)
        self.assertEqual(report.errors, [])
        self.assertTrue(any("columns" in w for w in report.warnings), report.warnings)

    def test_warns_about_sentences_left_on_one_line(self):
        report = run("a.md", "One two. Three four. Five.\n", "One two. Three four.\nFive.\n")
        self.assertTrue(any("sentence continues" in w for w in report.warnings), report.warnings)

    def test_does_not_flag_abbreviations(self):
        report = run(
            "a.md", "Use a tool, e.g. Ruff, and more.\n", "Use a tool,\ne.g. Ruff, and more.\n"
        )
        self.assertEqual(report.warnings, [])


class SourceTests(unittest.TestCase):
    def test_accepts_a_comment_reflow(self):
        before = (
            "#!/bin/bash\n"
            "# Build the release. Then upload it to the server, which can take a while.\n"
            "set -euo pipefail\n"
        )
        after = (
            "#!/bin/bash\n"
            "# Build the release.\n"
            "# Then upload it to the server,\n"
            "# which can take a while.\n"
            "set -euo pipefail\n"
        )
        report = run("release.sh", before, after)
        self.assertEqual(report.errors, [])

    def test_rejects_changed_code(self):
        before = "# Comment.\nset -e\n"
        after = "# Comment.\nset -eu\n"
        report = run("release.sh", before, after)
        self.assertTrue(any("code changed" in e for e in report.errors), report.errors)

    def test_rejects_changed_comment_words(self):
        before = "# Upload the build.\nexit 0\n"
        after = "# Upload\n# the release.\nexit 0\n"
        report = run("release.sh", before, after)
        self.assertTrue(any("words changed" in e for e in report.errors), report.errors)

    def test_rejects_comments_moved_across_code(self):
        before = "# One.\nx = 1\n# Two.\n"
        after = "# One. Two.\nx = 1\n"
        report = run("a.py", before, after)
        self.assertTrue(report.errors)

    def test_accepts_swift_doc_comments(self):
        before = (
            "/// Returns the sum. It never overflows, because it saturates.\n"
            "///\n"
            "/// - Parameter x: The first value.\n"
            "func add(_ x: Int) -> Int { x }\n"
        )
        after = (
            "/// Returns the sum.\n"
            "/// It never overflows,\n"
            "/// because it saturates.\n"
            "///\n"
            "/// - Parameter x: The first value.\n"
            "func add(_ x: Int) -> Int { x }\n"
        )
        self.assertEqual(run("a.swift", before, after).errors, [])

    def test_rejects_a_new_doc_list_item(self):
        before = "/// Values from 1 - 10 are allowed.\nlet x = 1\n"
        after = "/// Values from 1\n/// - 10 are allowed.\nlet x = 1\n"
        report = run("a.swift", before, after)
        self.assertTrue(any("block marker" in e for e in report.errors), report.errors)

    def test_accepts_block_comments(self):
        before = "/**\n * Returns the sum. It never overflows.\n */\nfunction add() {}\n"
        after = "/**\n * Returns the sum.\n * It never overflows.\n */\nfunction add() {}\n"
        self.assertEqual(run("a.js", before, after).errors, [])


class OtherFormatTests(unittest.TestCase):
    def test_rejects_text_joined_after_a_latex_comment(self):
        before = "Some text % a comment\nmore text.\n"
        after = "Some text % a comment more text.\n"
        report = run("a.tex", before, after)
        self.assertTrue(any("% comment" in e for e in report.errors), report.errors)

    def test_accepts_plain_text(self):
        self.assertEqual(run("a.txt", UDHR, UDHR_SEMBR).errors, [])


class CommandLineTests(unittest.TestCase):
    def git(self, *args: str) -> None:
        subprocess.run(["git", *args], cwd=self.dir, check=True, capture_output=True)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name
        self.git("init", "-q")
        self.git("config", "user.email", "test@example.com")
        self.git("config", "user.name", "Test")
        Path(self.dir, "doc.md").write_text(UDHR)
        self.git("add", "doc.md")
        self.git("commit", "-q", "-m", "Add doc")
        self.cwd = os.getcwd()
        os.chdir(self.dir)

    def tearDown(self):
        os.chdir(self.cwd)
        self.tmp.cleanup()

    def main(self, *args: str) -> tuple[int, str]:
        out = io.StringIO()
        with redirect_stdout(out):
            status = check.main(list(args))
        return status, out.getvalue()

    def test_compares_with_head(self):
        Path("doc.md").write_text(UDHR_SEMBR)
        self.assertEqual(self.main("doc.md")[0], 0)
        Path("doc.md").write_text(UDHR_SEMBR.replace("free", "frее"))
        status, out = self.main("doc.md")
        self.assertEqual(status, 1)
        self.assertIn("FAIL", out)

    def test_checks_changed_files_by_default(self):
        Path("doc.md").write_text(UDHR_SEMBR)
        status, out = self.main()
        self.assertEqual(status, 0)
        self.assertIn("doc.md: ok", out)

    def test_compares_with_a_before_file(self):
        Path("before.md").write_text(UDHR)
        Path("after.md").write_text(UDHR_SEMBR)
        self.assertEqual(self.main("after.md", "--before", "before.md")[0], 0)


if __name__ == "__main__":
    unittest.main()
