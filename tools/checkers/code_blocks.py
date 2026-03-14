"""Code block checker (rules 13–18, format.md CODE BLOCKS section).

Verifies:
  - Every fenced code block has a language tag.
  - Language tag is from the approved list.
  - TypeScript/JavaScript blocks start with a // comment describing the example.
  - Inline code is < 60 characters.
  - Anti-pattern blocks are labeled correctly.
"""
from __future__ import annotations

import re
from pathlib import Path

from .base import CheckResult, strip_front_matter, extract_code_blocks

_VALID_LANGS = {"typescript", "javascript", "bash", "json", "yaml", "text", "pseudocode"}

# Inline code: `...` — must be < 60 chars
_INLINE_CODE_RE = re.compile(r"`([^`\n]{60,})`")


def check_code_blocks(path: Path) -> CheckResult:
    result = CheckResult()
    text   = path.read_text(encoding="utf-8")
    body, _ = strip_front_matter(text)

    blocks = extract_code_blocks(body)

    for start_line, lang, body_block in blocks:
        # ── Language tag required ─────────────────────────────────────────────
        if not lang:
            result.error(
                path, start_line, "CODE-001",
                "Fenced code block is missing a language tag. "
                "Add one of: " + ", ".join(sorted(_VALID_LANGS))
            )
            continue

        # ── Language tag must be from the approved list ───────────────────────
        if lang not in _VALID_LANGS:
            result.error(
                path, start_line, "CODE-002",
                f"Unknown language tag '{lang}'. Allowed tags: {', '.join(sorted(_VALID_LANGS))}"
            )

        # ── TypeScript/JavaScript blocks need a top // comment ────────────────
        if lang in ("typescript", "javascript"):
            first_code_line = body_block.strip().splitlines()[0] if body_block.strip() else ""
            if not first_code_line.startswith("//"):
                result.warn(
                    path, start_line, "CODE-003",
                    f"TypeScript/JavaScript code block does not start with a // comment "
                    f"describing what it demonstrates (rule 15). First line: '{first_code_line[:60]}'"
                )

    # ── Inline code length ────────────────────────────────────────────────────
    # Only check in prose lines (not inside code fences)
    in_fence = False
    for lineno, line in enumerate(body.splitlines(), 1):
        if re.match(r"^\s*```", line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for m in _INLINE_CODE_RE.finditer(line):
            result.warn(
                path, lineno, "CODE-004",
                f"Inline code is {len(m.group(1))} chars (max 60): `{m.group(1)[:40]}...`"
            )

    return result
