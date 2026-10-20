#!/usr/bin/env python3
"""Check that a SemBr reformat changed only line breaks.

Compares each file with an earlier version
(by default, the version committed at HEAD)
and fails if anything other than line breaks changed:
a word, a code line, a code block, a table,
or a line break that changes how the text renders.
It also warns about changed lines over the width
and sentences that continue on the same line.

Usage:
    python3 check.py [FILE ...] [--rev REV] [--before PATH] [--width N]

With no files, it checks every file that differs from REV.
Exit status: 0 when only line breaks changed, 1 otherwise, 2 for usage errors.
Requires Python 3.9 or later and no other packages.
If markdown-it-py is installed, Markdown files are also compared as rendered HTML.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field

PROSE = {
    ".md": "markdown",
    ".markdown": "markdown",
    ".mdx": "markdown",
    ".txt": "text",
    ".text": "text",
    "": "text",
    ".adoc": "asciidoc",
    ".asciidoc": "asciidoc",
    ".rst": "rst",
    ".tex": "latex",
    ".org": "org",
    ".wiki": "mediawiki",
    ".mediawiki": "mediawiki",
}

HASH = "#"
SLASH = "//"
COMMENT_MARKERS = {
    **dict.fromkeys(
        ".sh .bash .zsh .fish .py .rb .pl .r .ps1 .yaml .yml .toml .nix .cmake .mk".split(), HASH
    ),
    **dict.fromkeys(
        ".swift .rs .js .mjs .cjs .ts .tsx .jsx .go .c .h .cc .cpp .hpp .m .mm .java .kt .kts "
        ".scala .cs .dart .zig .php".split(),
        SLASH,
    ),
    **dict.fromkeys(".lua .sql .hs .elm".split(), "--"),
    **dict.fromkeys(".el .lisp .clj .scm".split(), ";"),
}
COMMENT_NAMES = {"Makefile": HASH, "Dockerfile": HASH, "Gemfile": HASH, "Rakefile": HASH}

# Line starts that begin a new block, by format.
# A line break must not create one of these, and must keep the ones that exist.
BLOCK_STARTS = {
    "markdown": re.compile(
        r"([-+*]|\d{1,9}[.)])(\s|$)"  # list items
        r"|#{1,6}(\s|$)"  # headings
        r"|[>|<]"  # block quotes, tables, HTML
        r"|```|~~~"  # code fences
        r"|[-=*_](\s*[-=*_])*\s*$"  # thematic breaks and setext underlines
        r"|\[\^[^\]]*\]:"  # footnote definitions
        r"|\[[^\]]+\]:\s"  # link reference definitions
    ),
    "asciidoc": re.compile(r"([*.-]+|\d+\.)\s|[=|\[]|-{4}|\.{4}|\+{4}|/{4}|:\w"),
    "rst": re.compile(r"([-*+]|#\.|\d+[.)]|\(\d+\))\s|\.\.\s|::|[=\-~^\"'`#*+]{3,}\s*$|\|"),
    "latex": re.compile(r"\\(item|begin|end|section|subsection|chapter|par)\b|%"),
    "org": re.compile(r"\*+\s|[-+]\s|\d+[.)]\s|#\+|\||:\w+:"),
    "mediawiki": re.compile(r"[*#:;=|{]|-{4}"),
    "text": None,
}

# Line starts that can interrupt a paragraph.
# Joining such a line to the line before it changes the document.
INTERRUPTS = {
    **BLOCK_STARTS,
    "markdown": re.compile(
        r"([-+*]|\d{1,9}[.)])\s+\S"  # list items
        r"|#{1,6}(\s|$)"  # headings
        r"|>"  # block quotes
        r"|```|~~~"  # code fences
        r"|[-=*_](\s*[-=*_])*\s*$"  # thematic breaks and setext underlines
        r"|<(script|pre|style|textarea|!--|\?|![A-Z]|/?(address|article|aside|blockquote|"
        r"details|div|dl|fieldset|figure|footer|form|h[1-6]|header|hr|li|main|nav|ol|p|"
        r"section|table|ul)[\s/>])",  # HTML blocks
        re.IGNORECASE,
    ),
}

FENCES = {
    "markdown": (re.compile(r"^\s*(`{3,}|~{3,})"), None),
    "asciidoc": (re.compile(r"^(-{4,}|\.{4,}|\+{4,}|/{4,}|\|===)\s*$"), None),
    "latex": (
        re.compile(r"^\s*\\begin\{(verbatim|lstlisting|minted|comment)\*?\}"),
        r"\\end\{%s\*?\}",
    ),
    "org": (re.compile(r"^\s*#\+begin_(\w+)", re.IGNORECASE), r"(?i)#\+end_%s"),
}

ABBREVIATIONS = set(
    "mr. mrs. ms. dr. prof. sr. jr. st. vs. etc. e.g. i.e. cf. al. fig. no. vol. "
    "approx. inc. ltd. co. u.s. u.k.".split()
)
SENTENCE = re.compile(r"(\S+[.!?])([\"'\u2019\u201d)\]]*)\s+([\"'\u2018\u201c(\[]*[A-Z0-9])")
URLISH = re.compile(r"://|`|\]\(|<[a-z]")


@dataclass
class Report:
    path: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def error(self, line: int, message: str) -> None:
        self.errors.append(f"line {line}: {message}")

    def warn(self, line: int, message: str) -> None:
        self.warnings.append(f"line {line}: {message}")


@dataclass
class Line:
    number: int  # 1-based line number in its file
    text: str  # content without container prefixes
    prefix: str = ""  # block-quote markers or comment marker
    raw: str = ""  # the whole line as it appears in the file


# Reading files


def git(args: Sequence[str], cwd: str) -> str:
    result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout


def read_before(path: str, rev: str) -> str:
    directory, name = os.path.split(os.path.abspath(path))
    return git(["show", f"{rev}:./{name}"], directory)


def changed_files(rev: str) -> list[str]:
    root = git(["rev-parse", "--show-toplevel"], os.getcwd()).strip()
    names = git(["diff", "--name-only", "--diff-filter=M", rev, "--"], root).split("\n")
    return [os.path.relpath(os.path.join(root, n)) for n in names if n]


# Words and line starts


def words_of(lines: Sequence[Line]) -> tuple[list[str], list[int], list[int]]:
    """Returns the words of a block, the index of each line's first word,
    and the line number that each word is on."""
    words: list[str] = []
    starts: list[int] = []
    numbers: list[int] = []
    for line in lines:
        parts = line.text.split()
        if not parts:
            continue
        starts.append(len(words))
        words.extend(parts)
        numbers.extend([line.number] * len(parts))
    return words, starts, numbers


def unescaped_percent(text: str) -> bool:
    return re.search(r"(?<!\\)%", text) is not None


def compact(prefix: str) -> str:
    return re.sub(r"\s+", "", prefix)


def check_block(
    report: Report,
    fmt: str,
    before: Sequence[Line],
    after: Sequence[Line],
    hard_breaks: bool,
) -> bool:
    """Checks one block whose lines may have been rewrapped.
    Returns False if its words differ."""
    before = [line for line in before if line.text.split()]
    after = [line for line in after if line.text.split()]
    b_words, b_starts, b_numbers = words_of(before)
    a_words, a_starts, a_numbers = words_of(after)
    if b_words != a_words:
        index = next(
            (i for i, (x, y) in enumerate(zip(b_words, a_words)) if x != y),
            min(len(b_words), len(a_words)),
        )
        line = a_numbers[min(index, len(a_numbers) - 1)] if a_numbers else 0
        old = " ".join(b_words[max(0, index - 3) : index + 3])
        new = " ".join(a_words[max(0, index - 3) : index + 3])
        report.error(line, f"words changed: {old!r} became {new!r}")
        return False

    pattern = BLOCK_STARTS.get(fmt)
    interrupts = INTERRUPTS.get(fmt)
    b_lines = dict(zip(b_starts, before))
    a_lines = dict(zip(a_starts, after))
    # Each line keeps a prefix that the block already used,
    # so a lazy continuation line may gain its block-quote marker.
    prefixes = {compact(line.prefix) for line in before}
    for start, line in a_lines.items():
        text = line.text.lstrip()
        if start not in b_lines and pattern and pattern.match(text):
            report.error(line.number, f"a new line starts like a block marker: {text[:40]!r}")
        if compact(line.prefix) not in prefixes:
            report.error(line.number, "the block-quote or comment prefix changed")
    for start, line in b_lines.items():
        if start not in a_lines and interrupts and interrupts.match(line.text.lstrip()):
            report.error(
                a_numbers[start],
                f"a line that started a block was joined to the line before: {b_words[start]!r}",
            )

    # A heading is one line, so the line after it must still start a line.
    if fmt == "markdown":
        for index, line in enumerate(before[:-1]):
            if re.match(r"#{1,6}(\s|$)", line.text.lstrip()) and b_starts[index + 1] not in a_lines:
                report.error(
                    a_numbers[b_starts[index + 1]],
                    "text was joined onto a heading",
                )

    def line_ends(starts: list[int], count: int) -> list[int]:
        return [s - 1 for s in starts[1:]] + [count - 1]

    b_ends = line_ends(b_starts, len(b_words))
    a_ends = line_ends(a_starts, len(a_words))
    if hard_breaks:

        def hard(line: Line) -> bool:
            return line.text.endswith("  ") or line.text.rstrip().endswith("\\")

        b_hard = {end for end, line in zip(b_ends, before) if hard(line)}
        for end, line in zip(a_ends, after):
            if hard(line) and end not in b_hard:
                report.error(line.number, "the line now ends in a hard line break")
    if fmt == "latex":
        b_comment = {end for end, line in zip(b_ends, before) if unescaped_percent(line.text)}
        for end in b_comment - set(a_ends):
            report.error(a_numbers[end], "text was joined after a % comment")
    return True


def lint_lines(report: Report, lines: Sequence[Line], unchanged: set, width: int) -> None:
    for line in lines:
        full = line.raw.rstrip()
        if full.strip() in unchanged:
            continue
        if len(full) > width and not URLISH.search(full) and len(line.text.split()) > 1:
            report.warn(line.number, f"{len(full)} columns, over {width}")
        for match in SENTENCE.finditer(line.text):
            token = match.group(1).lower().lstrip("\"'(\u201c\u2018[")
            if token in ABBREVIATIONS or re.fullmatch(r"([a-z]\.)+", token):
                continue
            report.warn(
                line.number, f"a sentence continues on the same line after {match.group(1)!r}"
            )
            break


# Prose files


@dataclass
class Item:
    kind: str  # "block" or "verbatim"
    lines: list[Line]
    raw: str = ""


QUOTE = re.compile(r"^(\s{0,3}>\s?)+")
LIST_ITEM = re.compile(r"\s*([-+*]|\d{1,9}[.)])\s")


def items_of(text: str, fmt: str) -> list[Item]:
    """Splits a prose file into blocks separated by blank lines
    and verbatim regions that must not change."""
    lines = text.split("\n")
    items: list[Item] = []
    i = 0
    if fmt == "markdown" and lines and lines[0].strip() == "---":
        end = next((j for j in range(1, len(lines)) if lines[j].strip() == "---"), None)
        if end is not None:
            items.append(Item("verbatim", [], "\n".join(lines[: end + 1])))
            i = end + 1
    fence = FENCES.get(fmt)
    block: list[Line] = []
    in_list = [False]  # whether indented blocks belong to a list

    def flush() -> None:
        if block:
            items.append(Item("block", list(block)))
            if fmt == "markdown":
                if any(LIST_ITEM.match(line.text) for line in block):
                    in_list[0] = True
                elif not block[0].raw[:1].isspace():
                    in_list[0] = False
            block.clear()

    while i < len(lines):
        raw = lines[i]
        stripped = QUOTE.sub("", raw) if fmt == "markdown" else raw
        opened = fence[0].match(stripped) if fence else None
        if opened:
            flush()
            if fence[1]:
                closer = re.compile(fence[1] % re.escape(opened.group(1)))
            elif fmt == "asciidoc":
                closer = re.compile("^" + re.escape(opened.group(1)) + r"\s*$")
            else:
                marker = opened.group(1)
                char = marker[0]
                closer = re.compile(rf"^\s*{re.escape(char)}{{{len(marker)},}}\s*$")
            j = i + 1
            while j < len(lines):
                inner = QUOTE.sub("", lines[j]) if fmt == "markdown" else lines[j]
                if closer.search(inner):
                    break
                j += 1
            items.append(Item("verbatim", [], "\n".join(lines[i : j + 1])))
            i = j + 1
            continue
        if not stripped.strip():
            # A blank line, or a block-quote line with nothing in it, ends a block.
            flush()
            i += 1
            continue
        table = raw.lstrip().startswith("|") or (fmt == "rst" and raw.lstrip().startswith("+-"))
        indented = fmt == "markdown" and not block and re.match(r"(\t| {4})", raw)
        if table or indented:
            flush()
            j = i
            while (
                j < len(lines)
                and lines[j].strip()
                and (
                    (table and (lines[j].lstrip().startswith(("|", "+"))))
                    or (indented and re.match(r"(\t| {4})", lines[j]))
                )
            ):
                j += 1
            if in_list[0]:
                # An indented paragraph after a list item belongs to the list.
                for k in range(i, j):
                    block.append(Line(k + 1, lines[k], "", lines[k]))
                flush()
            else:
                items.append(Item("verbatim", [], "\n".join(lines[i:j])))
            i = j
            continue
        if fmt == "markdown":
            prefix = QUOTE.match(raw)
            quote = prefix.group(0) if prefix else ""
            block.append(Line(i + 1, raw[len(quote) :], quote, raw))
        else:
            block.append(Line(i + 1, raw, "", raw))
        i += 1
    flush()
    return items


def rendered(text: str) -> str | None:
    try:
        from markdown_it import MarkdownIt  # type: ignore
    except ImportError:
        return None
    html = MarkdownIt("commonmark").enable(["table", "strikethrough"]).render(text)
    parts = re.split(r"(<pre[\s\S]*?</pre>)", html)
    return "".join(p if p.startswith("<pre") else re.sub(r"[ \t\r\n]+", " ", p) for p in parts)


def check_prose(report: Report, fmt: str, before: str, after: str, width: int) -> None:
    b_items, a_items = items_of(before, fmt), items_of(after, fmt)
    if [i.kind for i in b_items] != [i.kind for i in a_items]:
        report.errors.append(
            f"the blocks changed: {len(b_items)} before, {len(a_items)} after "
            "(a blank line, code block, or table was added, removed, or moved)"
        )
        return
    unchanged = {line.strip() for line in before.split("\n")}
    for b, a in zip(b_items, a_items):
        if a.kind == "verbatim":
            if a.raw != b.raw:
                first = a.raw.split("\n", 1)[0]
                report.errors.append(
                    f"a code block, table, or front matter changed: {first[:60]!r}"
                )
            continue
        if check_block(report, fmt, b.lines, a.lines, hard_breaks=fmt == "markdown"):
            lint_lines(report, a.lines, unchanged, width)
    if fmt == "markdown" and not report.errors:
        b_html, a_html = rendered(before), rendered(after)
        if b_html is None:
            report.notes.append("rendering not compared; markdown-it-py is not installed")
        elif b_html != a_html:
            report.errors.append("the rendered HTML changed")


# Source files


def comment_lines(text: str, marker: str) -> list[tuple[str, Line | None]]:
    """Labels each line as code (with its exact text) or as a comment line."""
    out: list[tuple[str, Line | None]] = []
    in_block = False
    for number, raw in enumerate(text.split("\n"), 1):
        stripped = raw.lstrip()
        indent = raw[: len(raw) - len(stripped)]
        if marker == SLASH and in_block:
            if stripped.startswith("*/"):
                in_block = False
                out.append((raw, None))
                continue
            body = stripped
            closing = body.rstrip().endswith("*/")
            if closing:
                body = body.rstrip()[:-2]
                in_block = False
            star = re.match(r"\*(?!/)\s?", body)
            prefix = indent + ("*" if star else "")
            content = body[star.end() :] if star else body
            out.append(("", Line(number, content, prefix, raw)))
            if closing:
                out.append(("*/", None))
            continue
        if marker == SLASH and stripped.startswith("/*") and "*/" not in stripped:
            opener = re.match(r"/\*+\s?", stripped)
            out.append(
                ("", Line(number, stripped[opener.end() :], indent + opener.group(0).strip(), raw))
            )
            in_block = True
            continue
        if stripped.startswith(marker) and not (
            marker == HASH and stripped.startswith("#!") and number == 1
        ):
            run = re.match(re.escape(marker[0]) + r"+[!/]?", stripped)
            body = stripped[run.end() :]
            content = body[1:] if body.startswith(" ") else body
            out.append(("", Line(number, content, indent + run.group(0), raw)))
            continue
        out.append((raw, None))
    return out


def comment_runs(labeled: list[tuple[str, Line | None]]) -> tuple[list[str], list[list[Line]]]:
    """Returns the code lines and the runs of comment lines between them.
    A comment line with no text separates runs, like a blank line in prose."""
    code: list[str] = []
    runs: list[list[Line]] = []
    current: list[Line] = []
    for raw, line in labeled:
        if line is None or not line.text.strip():
            if current:
                runs.append(current)
                current = []
            code.append(raw if line is None else f"<empty comment {line.prefix.strip()}>")
        else:
            current.append(line)
    if current:
        runs.append(current)
    return code, runs


def check_source(report: Report, marker: str, before: str, after: str, width: int) -> None:
    b_code, b_runs = comment_runs(comment_lines(before, marker))
    a_code, a_runs = comment_runs(comment_lines(after, marker))
    if b_code != a_code:
        index = next(
            (i for i, (x, y) in enumerate(zip(b_code, a_code)) if x != y),
            min(len(b_code), len(a_code)),
        )
        old = b_code[index] if index < len(b_code) else "<end of file>"
        new = a_code[index] if index < len(a_code) else "<end of file>"
        report.errors.append(f"code changed: {old.strip()[:60]!r} became {new.strip()[:60]!r}")
        return
    if len(b_runs) != len(a_runs):
        report.errors.append("comments were split or joined across code or empty comment lines")
        return
    unchanged = {line.strip() for line in before.split("\n")}
    for b, a in zip(b_runs, a_runs):
        if check_block(report, "markdown", b, a, hard_breaks=False):
            lint_lines(report, a, unchanged, width)


# Main


def kind_of(path: str) -> tuple[str, str]:
    name = os.path.basename(path)
    ext = os.path.splitext(name)[1].lower()
    if name in COMMENT_NAMES:
        return "source", COMMENT_NAMES[name]
    if ext in COMMENT_MARKERS:
        return "source", COMMENT_MARKERS[ext]
    return "prose", PROSE.get(ext, "text")


def check(path: str, before: str, after: str, width: int) -> Report:
    report = Report(path)
    kind, detail = kind_of(path)
    if before == after:
        report.notes.append("unchanged")
    elif kind == "source":
        check_source(report, detail, before, after, width)
    else:
        check_prose(report, detail, before, after, width)
    before_lines = set(before.split("\n"))
    for number, line in enumerate(after.split("\n"), 1):
        if line != line.rstrip() and line not in before_lines:
            report.warn(number, "trailing whitespace")
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "files", nargs="*", help="files to check (default: files changed since REV)"
    )
    parser.add_argument(
        "--rev", default="HEAD", help="git revision to compare with (default: HEAD)"
    )
    parser.add_argument("--before", help="compare with this file instead of a git revision")
    parser.add_argument(
        "--width", type=int, default=80, help="recommended line length (default: 80)"
    )
    args = parser.parse_args(argv)

    try:
        files = args.files or changed_files(args.rev)
    except RuntimeError as error:
        print(f"check.py: {error}", file=sys.stderr)
        return 2
    if args.before and len(files) != 1:
        print("check.py: --before needs exactly one file", file=sys.stderr)
        return 2
    if not files:
        print("No changed files.")
        return 0

    failed = False
    for path in files:
        try:
            with open(path, encoding="utf-8") as f:
                after = f.read()
            if args.before:
                with open(args.before, encoding="utf-8") as f:
                    before = f.read()
            else:
                before = read_before(path, args.rev)
        except (OSError, RuntimeError, UnicodeDecodeError) as error:
            print(f"{path}: cannot compare: {error}")
            failed = True
            continue
        report = check(path, before.replace("\r\n", "\n"), after.replace("\r\n", "\n"), args.width)
        status = "FAIL" if report.errors else "ok"
        detail = "; ".join(report.notes)
        print(f"{path}: {status}" + (f" ({detail})" if detail else ""))
        for message in report.errors:
            print(f"  error: {message}")
        for message in report.warnings:
            print(f"  warning: {message}")
        failed = failed or bool(report.errors)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
