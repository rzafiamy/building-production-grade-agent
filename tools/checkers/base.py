"""Shared types and Markdown utilities for all checkers."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Iterator


# ── Issue types ───────────────────────────────────────────────────────────────

class Severity(Enum):
    ERROR   = "ERROR"
    WARNING = "WARN"


@dataclass
class Issue:
    file:     Path
    line:     int        # 1-based; 0 = whole file
    severity: Severity
    rule:     str
    message:  str


@dataclass
class CheckResult:
    issues: list[Issue] = field(default_factory=list)

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == Severity.ERROR]

    @property
    def warnings(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == Severity.WARNING]

    @property
    def ok(self) -> bool:
        return not self.errors

    def merge(self, other: CheckResult) -> None:
        self.issues.extend(other.issues)

    def error(self, file: Path, line: int, rule: str, message: str) -> None:
        self.issues.append(Issue(file, line, Severity.ERROR, rule, message))

    def warn(self, file: Path, line: int, rule: str, message: str) -> None:
        self.issues.append(Issue(file, line, Severity.WARNING, rule, message))


# ── File classification ───────────────────────────────────────────────────────

def file_number(path: Path) -> int:
    """Return the numeric prefix of a content file (e.g. 08 from 08-ch01-foo.md)."""
    try:
        return int(path.stem.split("-")[0])
    except (ValueError, IndexError):
        return -1


def is_chapter_file(path: Path) -> bool:
    """Chapter files are named XX-chNN-*.md."""
    return re.match(r"^\d+-ch\d+", path.name) is not None


def is_part_intro(path: Path) -> bool:
    return re.match(r"^\d+-part-\d+-intro", path.name) is not None


def is_front_matter(path: Path) -> bool:
    n = file_number(path)
    return 0 <= n <= 7


def is_back_matter(path: Path) -> bool:
    n = file_number(path)
    return 54 <= n <= 60


# ── Markdown parsing helpers ──────────────────────────────────────────────────

_FRONT_MATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def strip_front_matter(text: str) -> tuple[str, dict[str, str]]:
    """Return (body, front_matter_dict). dict is {} if no front matter found."""
    m = _FRONT_MATTER_RE.match(text)
    if not m:
        return text, {}
    fm: dict[str, str] = {}
    for raw_line in m.group(1).splitlines():
        if ":" in raw_line:
            key, _, val = raw_line.partition(":")
            fm[key.strip()] = val.strip().strip('"').strip("'")
    return text[m.end():], fm


def iter_non_code_lines(text: str) -> Iterator[tuple[int, str]]:
    """Yield (line_number, line) for lines outside fenced code blocks."""
    in_fence = False
    for lineno, line in enumerate(text.splitlines(), 1):
        if re.match(r"^\s*```", line):
            in_fence = not in_fence
            continue
        if not in_fence:
            yield lineno, line


def strip_code_blocks(text: str) -> str:
    """Replace code block content with blank lines, preserving line numbers."""
    result: list[str] = []
    in_fence = False
    for line in text.splitlines():
        if re.match(r"^\s*```", line):
            in_fence = not in_fence
            result.append("")
        elif in_fence:
            result.append("")
        else:
            result.append(line)
    return "\n".join(result)


def extract_code_blocks(text: str) -> list[tuple[int, str, str]]:
    """
    Return list of (start_line, language_tag, block_body) for each fenced block.
    language_tag is '' if the opening fence has no tag.
    """
    blocks: list[tuple[int, str, str]] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        m = re.match(r"^\s*```(\w*)", lines[i])
        if m:
            lang = m.group(1)
            start = i + 1  # 1-based line of opening fence
            body_lines: list[str] = []
            i += 1
            while i < len(lines) and not re.match(r"^\s*```\s*$", lines[i]):
                body_lines.append(lines[i])
                i += 1
            blocks.append((start, lang, "\n".join(body_lines)))
        i += 1
    return blocks


def count_prose_words(text: str) -> int:
    """Word count of prose — excludes front matter and code blocks."""
    _, body = strip_front_matter(text) if text.startswith("---") else (text, {})
    # strip_front_matter returns (body, fm) — re-call properly
    body, _ = strip_front_matter(text)
    clean = strip_code_blocks(body)
    # Remove HTML comments
    clean = re.sub(r"<!--.*?-->", "", clean, flags=re.DOTALL)
    # Remove callout markers
    clean = re.sub(r"^>\s*\[!.*?\]", "", clean, flags=re.MULTILINE)
    return len(clean.split())
