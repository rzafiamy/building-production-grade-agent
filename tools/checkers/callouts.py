"""Callout box checker (rule 10, format.md CALLOUT BOXES section).

Verifies:
  - Maximum 3 callouts per chapter file.
  - Only approved callout types: NOTE, WARNING, TIP, DANGER.
  - Callouts are not nested (a callout block does not start another > [!TYPE]).
  - Callout body does not exceed 4 sentences.
"""
from __future__ import annotations

import re
from pathlib import Path

from .base import CheckResult, is_chapter_file, strip_front_matter, iter_non_code_lines

_CALLOUT_OPEN_RE  = re.compile(r"^>\s*\[!(NOTE|WARNING|TIP|DANGER|CAUTION)\]", re.I)
_ANY_CALLOUT_RE   = re.compile(r"^>\s*\[!(\w+)\]", re.I)
_VALID_TYPES      = {"NOTE", "WARNING", "TIP", "DANGER", "CAUTION"}
_MAX_CALLOUTS     = 3
_MAX_BODY_LINES   = 8   # ~4 sentences in block-quote form


def check_callouts(path: Path) -> CheckResult:
    result   = CheckResult()
    text     = path.read_text(encoding="utf-8")
    body, _  = strip_front_matter(text)
    lines    = list(iter_non_code_lines(body))

    callout_count  = 0
    in_callout     = False
    callout_start  = 0
    callout_lines  = 0

    for lineno, line in lines:
        stripped = line.strip()

        # Check for any callout opener
        m_any = _ANY_CALLOUT_RE.match(stripped)
        if m_any:
            ctype = m_any.group(1).upper()

            # Unknown callout type
            if ctype not in _VALID_TYPES:
                result.error(
                    path, lineno, "CALL-001",
                    f"Unknown callout type '[!{ctype}]'. "
                    f"Allowed types: {', '.join(sorted(_VALID_TYPES))} (rule 10)."
                )

            # Nested callout detection
            if in_callout:
                result.error(
                    path, lineno, "CALL-002",
                    f"Nested callout '[!{ctype}]' inside another callout (format.md: never nest callouts)."
                )

            callout_count += 1
            in_callout    = True
            callout_start = lineno
            callout_lines = 0
            continue

        # We're inside a callout (continued blockquote lines start with >)
        if in_callout:
            if stripped.startswith(">"):
                callout_lines += 1
                if callout_lines > _MAX_BODY_LINES:
                    result.warn(
                        path, callout_start, "CALL-003",
                        f"Callout starting at line {callout_start} has more than {_MAX_BODY_LINES} lines. "
                        "Keep callout content to 1–4 sentences (format.md)."
                    )
                    in_callout = False  # warn once, then stop tracking
            else:
                in_callout = False

    # Max callouts per chapter
    if is_chapter_file(path) and callout_count > _MAX_CALLOUTS:
        result.warn(
            path, 0, "CALL-004",
            f"Chapter has {callout_count} callout boxes (max is {_MAX_CALLOUTS} per chapter, rule 10)."
        )

    return result
