"""Front matter checker (format.md — FRONT MATTER FORMAT section).

Each .md file must begin with YAML front matter containing:
  - title   (all files)
  - status  (all files; must be: draft | review | final)
  - part    (chapter files)
  - chapter (chapter files; must be a number)
  - page    (chapter files; must be a number matching the file prefix)
"""
from __future__ import annotations

from pathlib import Path

from .base import CheckResult, is_chapter_file, strip_front_matter, file_number

_VALID_STATUS = {"draft", "review", "final"}


def check_frontmatter(path: Path) -> CheckResult:
    result = CheckResult()
    text   = path.read_text(encoding="utf-8")
    body, fm = strip_front_matter(text)

    if not fm:
        result.error(path, 0, "FM-001", "Missing YAML front matter (--- block)")
        return result

    # title is required for every file
    if "title" not in fm or not fm["title"]:
        result.error(path, 0, "FM-002", "Front matter missing required field: title")

    # status is required and must be a known value
    status = fm.get("status", "")
    if not status:
        result.error(path, 0, "FM-003", "Front matter missing required field: status")
    elif status not in _VALID_STATUS:
        result.error(
            path, 0, "FM-004",
            f"Front matter status '{status}' is invalid. Must be one of: {', '.join(sorted(_VALID_STATUS))}"
        )

    # Chapter files have additional required fields
    if is_chapter_file(path):
        if "part" not in fm or not fm["part"]:
            result.error(path, 0, "FM-005", "Chapter file missing front matter field: part")

        if "chapter" not in fm:
            result.error(path, 0, "FM-006", "Chapter file missing front matter field: chapter")
        else:
            if not fm["chapter"].isdigit():
                result.error(path, 0, "FM-007", f"Front matter 'chapter' must be a number, got: {fm['chapter']}")

        if "page" not in fm:
            result.error(path, 0, "FM-008", "Chapter file missing front matter field: page")
        else:
            if not fm["page"].isdigit():
                result.error(path, 0, "FM-009", f"Front matter 'page' must be a number, got: {fm['page']}")
            elif int(fm["page"]) != file_number(path):
                result.warn(
                    path, 0, "FM-010",
                    f"Front matter 'page: {fm['page']}' does not match file prefix {file_number(path)}"
                )

    return result
