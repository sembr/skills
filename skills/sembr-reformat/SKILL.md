---
name: sembr-reformat
description: Reformat prose using Semantic Line Breaks (SemBr) from https://sembr.org while preserving rendered output and meaning. Use when asked to reflow plain text or compatible markup (Markdown, AsciiDoc, reStructuredText, LaTeX, Org, MediaWiki) into semantic one-thought-per-line formatting, or when improving prose diffs and editorial readability.
---

# Reformat With SemBr

Apply Semantic Line Breaks to prose without changing what readers see.
Preserve wording, punctuation, and intent.

## Reformat Workflow

1. Identify prose regions that support soft-wrapped lines.
2. Skip regions where line breaks are syntactically significant:
   - fenced code blocks and indented code blocks
   - tables
   - YAML frontmatter
   - URLs or markup tokens that must stay contiguous
3. Rewrite only line wrapping, not content.
4. Keep paragraphs and list structures intact.
5. Return full rewritten text unless asked for a targeted excerpt.

## SemBr Rules

Apply these rules in order:

1. Break after every sentence ending in `.`, `!`, or `?`.
2. Prefer a break after independent clauses ending in `,`, `;`, `:`, or `—`.
3. Optionally break after dependent clauses when it clarifies structure.
4. Insert a break before an enumerated or itemized list.
5. Optionally add breaks between list items to group related items.
6. Never break inside a hyphenated word.
7. Allow breaks around hyperlinks and before inline markup when helpful.
8. Target 80 columns when possible; allow longer lines for URLs, code spans, or unavoidable markup.

## Quality Checks

After rewriting a file,
run `scripts/check.py` from this skill's directory:

```console
python3 scripts/check.py path/to/file.md
```

It compares the file with its version at `HEAD`
and fails if anything other than line breaks changed:
a word, a code line or code block, a table,
or a break that changes how the text renders,
such as a new list item, a joined heading, or a hard line break.
In source files, it checks that only comments were rewrapped.
It also warns about changed lines over 80 columns
and sentences that continue on the same line.
Fix each error and warning, then run it again.
Pass `--before <file>` to compare with a saved copy instead,
or run it with no files to check every file changed since `HEAD`.
It needs Python 3.9 or later and no other packages.

If the script isn't available, verify by hand:

- Rendering-equivalence: no hard-break syntax added accidentally.
- Meaning-equivalence: no word changes or punctuation edits.
- Structure-equivalence: headings, lists, and block boundaries unchanged.
- Diff-friendliness: edits are mostly line-wrap changes.

## Output Style

Use minimal explanation.
Return reformatted text directly.
If any segment cannot be safely reformatted, leave it unchanged and add a one-line note.
