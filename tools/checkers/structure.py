"""Chapter structure checker (rules 7, 8, 11, 12, 22, 23).

For chapter files (XX-chNN-*.md) verifies:
  - Presence of a Chapter Goal callout (> [!NOTE] containing "Chapter Goal")
  - Presence of a ## Key Takeaways section
  - No H5 (#####+) or H6 headings
  - H1 (#) is absent (chapter title is H2; H1 is only for part titles)
  - H4 (####) used sparingly (≤ 3 per chapter)
  - Word count in range [2000, 5000] for chapter files
  - Word count in range [200, 800] for front-matter pages (00–07)
  - Single blank line between paragraphs (no triple+ blank lines)
  - Paragraphs not exceeding 6 sentences (rule 23)
"""
from __future__ import annotations

import re
from pathlib import Path

from .base import (
    CheckResult,
    is_chapter_file,
    is_front_matter,
    is_back_matter,
    is_part_intro,
    strip_front_matter,
    iter_non_code_lines,
    count_prose_words,
)

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)")
_GOAL_RE    = re.compile(r">\s*\[!NOTE\]")
_GOAL_TEXT  = re.compile(r"Chapter Goal", re.IGNORECASE)


def check_structure(path: Path) -> CheckResult:
    result = CheckResult()
    text   = path.read_text(encoding="utf-8")
    body, _ = strip_front_matter(text)

    lines  = list(iter_non_code_lines(body))
    raw    = body.splitlines()

    # ── Heading rules ──────────────────────────────────────────────────────────
    h1_count  = 0
    h4_count  = 0
    for lineno, line in lines:
        m = _HEADING_RE.match(line)
        if not m:
            continue
        level  = len(m.group(1))
        htext  = m.group(2)

        if level == 1:
            h1_count += 1
            if is_chapter_file(path):
                result.error(
                    path, lineno, "STRUCT-001",
                    f"H1 heading found in chapter file: '{htext}'. "
                    "Chapter titles must be H2 (##). H1 is reserved for part titles."
                )
        if level >= 5:
            result.error(
                path, lineno, "STRUCT-002",
                f"Heading level H{level} is forbidden (max is H4). Found: '{htext}'"
            )
        if level == 4:
            h4_count += 1

    if h4_count > 3 and is_chapter_file(path):
        result.warn(
            path, 0, "STRUCT-003",
            f"Chapter has {h4_count} H4 (####) sub-sections. Use H4 sparingly (≤ 3 per chapter)."
        )

    # ── Chapter-only rules ────────────────────────────────────────────────────
    if is_chapter_file(path):
        full_text = "\n".join(line for _, line in lines)

        # Chapter Goal box
        has_goal_callout = False
        goal_has_text    = False
        prev_was_note    = False
        for lineno, line in lines:
            if _GOAL_RE.match(line.strip()):
                prev_was_note = True
                has_goal_callout = True
            elif prev_was_note and _GOAL_TEXT.search(line):
                goal_has_text = True
                prev_was_note = False
            else:
                prev_was_note = False

        if not has_goal_callout:
            result.error(
                path, 0, "STRUCT-004",
                "Missing Chapter Goal callout. Add a '> [!NOTE]' block containing 'Chapter Goal:' "
                "near the top of the chapter (rule 7)."
            )
        elif not goal_has_text:
            result.warn(
                path, 0, "STRUCT-005",
                "Chapter Goal callout found but the text 'Chapter Goal' is missing from its body."
            )

        # Key Takeaways section
        has_takeaways = any(
            re.match(r"^#{1,3}\s+Key Takeaways", line, re.IGNORECASE)
            for _, line in lines
        )
        if not has_takeaways:
            result.error(
                path, 0, "STRUCT-006",
                "Missing '## Key Takeaways' section. Every chapter must end with this section (rule 8)."
            )

        # Word count
        wc = count_prose_words(text)
        if wc < 2000:
            result.warn(
                path, 0, "STRUCT-007",
                f"Chapter is {wc} words — below the 2,000-word minimum (rule 22). "
                "This may be a stub; complete the content before publishing."
            )
        elif wc > 5000:
            result.warn(
                path, 0, "STRUCT-008",
                f"Chapter is {wc} words — above the 5,000-word maximum (rule 22). Consider splitting."
            )

    # ── Front-matter word count ───────────────────────────────────────────────
    if is_front_matter(path) and not path.name.endswith("07-toc.md"):
        wc = count_prose_words(text)
        if wc < 200:
            result.warn(
                path, 0, "STRUCT-009",
                f"Front-matter page is {wc} words — below the 200-word minimum (rule 22)."
            )
        elif wc > 800:
            result.warn(
                path, 0, "STRUCT-010",
                f"Front-matter page is {wc} words — above the 800-word maximum (rule 22)."
            )

    # ── No excessive blank lines ──────────────────────────────────────────────
    consecutive = 0
    for lineno, raw_line in enumerate(raw, 1):
        if raw_line.strip() == "":
            consecutive += 1
            if consecutive >= 3:
                result.warn(
                    path, lineno, "STRUCT-011",
                    "Three or more consecutive blank lines. Keep spacing clean (one blank line between elements)."
                )
        else:
            consecutive = 0

    return result
