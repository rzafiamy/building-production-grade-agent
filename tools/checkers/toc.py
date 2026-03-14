"""TOC integrity checker (rule 6).

Verifies:
- Every file linked in the TOC exists on disk.
- Every content file is either in the TOC or is a known structural file.
- No broken markdown links in the TOC itself.
"""
from __future__ import annotations

import re
from pathlib import Path

from .base import CheckResult

# Files that live in content/ but are intentionally absent from the TOC.
# These are structural/boilerplate pages not linked from the navigation TOC:
#   - The TOC file itself
#   - Standard front-matter pages (copyright, dedication, foreword, title page)
#   - Part intro pages (structural dividers between parts)
#   - Back-matter divider page
_TOC_EXEMPT = {
    "07-toc.md",
    # Front matter not listed in TOC nav
    "01-title-page.md",
    "02-copyright.md",
    "03-dedication.md",
    "04-foreword.md",
    # Part intro divider pages
    "12-part-2-intro.md",
    "19-part-3-intro.md",
    "29-part-4-intro.md",
    "34-part-5-intro.md",
    "42-part-6-intro.md",
    "49-part-7-intro.md",
    # Back matter divider
    "54-part-back-matter.md",
}

_LINK_RE = re.compile(r"\[.*?\]\(([^)]+\.md)\)")


def _parse_toc_links(toc_path: Path) -> list[tuple[str, int]]:
    """Return [(filename, line_number)] for every .md link in the TOC."""
    entries: list[tuple[str, int]] = []
    for lineno, line in enumerate(toc_path.read_text(encoding="utf-8").splitlines(), 1):
        for m in _LINK_RE.finditer(line):
            entries.append((m.group(1), lineno))
    return entries


def check_toc(root: Path) -> CheckResult:
    result  = CheckResult()
    toc     = root / "content" / "07-toc.md"
    cdir    = root / "content"

    if not toc.exists():
        result.error(toc, 0, "TOC-001", "TOC file content/07-toc.md not found")
        return result

    links = _parse_toc_links(toc)
    toc_filenames = {fname for fname, _ in links}

    # 1. Every file referenced in TOC must exist.
    for fname, lineno in links:
        if not (cdir / fname).exists():
            result.error(toc, lineno, "TOC-002", f"TOC references missing file: {fname}")

    # 2. Every content file must appear in TOC (or be explicitly exempted).
    all_content = {f.name for f in cdir.glob("*.md")}
    for name in sorted(all_content - toc_filenames - _TOC_EXEMPT):
        result.error(
            cdir / name, 0, "TOC-003",
            f"File not listed in TOC and not a known structural file: {name}. "
            "Add it to the TOC lock or mark it as exempt."
        )

    return result
