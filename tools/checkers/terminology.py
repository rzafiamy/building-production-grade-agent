"""Terminology and style checker (rules 2–4, 19–21, 34).

Verifies (in prose only — code blocks are skipped):
  - No hype words: revolutionary, game-changing, unprecedented, etc.
  - Consistent terminology: "agent" not "bot"; "tool call" not "function call";
    "context window" not "context limit" / "token window".
  - Forbidden Markdown formatting: ~~strikethrough~~, <u>underline</u>.
  - No HTTP/HTTPS URLs in prose (rule 34: name resources, don't link them).
  - Date-sensitive content (model versions, pricing) has a nearby date marker.
"""
from __future__ import annotations

import re
from pathlib import Path

from .base import CheckResult, strip_front_matter, iter_non_code_lines

# ── Banned words / phrases ────────────────────────────────────────────────────
# (rule, pattern, message, severity)
_BANNED: list[tuple[str, re.Pattern, str, str]] = [
    ("TERM-001", re.compile(r"\brevolutionary\b", re.I),
     'No hype language: "revolutionary" (rule 3). Let the technology speak.', "ERROR"),

    ("TERM-002", re.compile(r"\bgame[- ]changing\b", re.I),
     'No hype language: "game-changing" (rule 3).', "ERROR"),

    ("TERM-003", re.compile(r"\bunprecedented\b", re.I),
     'No hype language: "unprecedented" (rule 3).', "ERROR"),

    ("TERM-004", re.compile(r"\bgroundbreaking\b", re.I),
     'No hype language: "groundbreaking" (rule 3).', "ERROR"),

    ("TERM-005", re.compile(r"\btransformative\b", re.I),
     'No hype language: "transformative" (rule 3).', "WARNING"),

    # "bot" as standalone word — but not in "robot" or quoted context
    ("TERM-006", re.compile(r'(?<!["\'])(\bbot\b)(?!["\'])'),
     'Use "agent" not "bot" (rule 19). If quoting another source, wrap in quotes.', "WARNING"),

    # "function call" — wrong unless explicitly in OpenAI context
    ("TERM-007", re.compile(r"\bfunction call\b", re.I),
     'Use "tool call" not "function call" (rule 19), unless describing OpenAI-specific API.', "WARNING"),

    # "context limit" or "token window"
    ("TERM-008", re.compile(r"\bcontext limit\b", re.I),
     'Use "context window" not "context limit" (rule 19).', "WARNING"),

    ("TERM-009", re.compile(r"\btoken window\b", re.I),
     'Use "context window" not "token window" (rule 19).', "WARNING"),
]

# ── Forbidden Markdown formatting ─────────────────────────────────────────────
_STRIKETHROUGH_RE = re.compile(r"~~.+?~~")
_UNDERLINE_RE     = re.compile(r"<u>.+?</u>", re.I)
_SUPERSCRIPT_RE   = re.compile(r"\^\S+\^")

# ── URL check ─────────────────────────────────────────────────────────────────
_URL_RE = re.compile(r"https?://\S+")

# ── Date-sensitive model/pricing references ───────────────────────────────────
_MODEL_VERSION_RE = re.compile(
    r"\b(gpt-[34][\w.-]*|claude-[23][\w.-]*|gemini[\w.-]*|o[134]-[\w-]+)\b", re.I
)
_DATE_MARKER_RE   = re.compile(r"<!--\s*Accurate as of", re.I)


def check_terminology(path: Path) -> CheckResult:
    result = CheckResult()
    text   = path.read_text(encoding="utf-8")
    body, _ = strip_front_matter(text)

    has_date_marker   = bool(_DATE_MARKER_RE.search(body))
    flagged_model_ver = False

    for lineno, line in iter_non_code_lines(body):
        # Skip pure callout markers and HTML comments
        stripped = line.strip()
        if stripped.startswith("<!--") or stripped.startswith("---"):
            continue

        # Banned words / phrases
        for rule, pattern, message, sev in _BANNED:
            if pattern.search(line):
                if sev == "ERROR":
                    result.error(path, lineno, rule, message)
                else:
                    result.warn(path, lineno, rule, message)

        # Forbidden formatting
        if _STRIKETHROUGH_RE.search(line):
            result.error(
                path, lineno, "TERM-010",
                "Strikethrough (~~text~~) is forbidden in body text (format.md)."
            )
        if _UNDERLINE_RE.search(line):
            result.error(
                path, lineno, "TERM-011",
                "HTML underline (<u>text</u>) is forbidden in body text (format.md)."
            )
        if _SUPERSCRIPT_RE.search(line):
            result.error(
                path, lineno, "TERM-012",
                "Superscript (^text^) is forbidden in body text (format.md)."
            )

        # No URLs in prose (rule 34)
        for m in _URL_RE.finditer(line):
            result.error(
                path, lineno, "TERM-013",
                f"URL found in prose: {m.group()[:80]}. "
                "Name the resource explicitly instead of linking it (rule 34). "
                "URLs rot and are forbidden in body text."
            )

        # Date-sensitive model version mentions
        if not flagged_model_ver and _MODEL_VERSION_RE.search(line):
            flagged_model_ver = True

    # If model versions are mentioned anywhere, a date marker must appear in the file
    if flagged_model_ver and not has_date_marker:
        result.warn(
            path, 0, "TERM-014",
            "File references specific model versions but has no date marker. "
            "Add <!-- Accurate as of YYYY-MM — verify --> near model references (rule 31)."
        )

    return result
