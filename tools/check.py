#!/usr/bin/env python3
"""
Book quality checker — "Building Production-Grade Agents"

Validates every content file against the guidelines in:
  guidelines/rules.md
  guidelines/format.md

Usage:
  python tools/check.py                        # check all content files
  python tools/check.py --file content/08-...  # check one file
  python tools/check.py --no-lock              # skip frozen-structure check
  python tools/check.py --update-lock          # regenerate headings_lock.json
  python tools/check.py --stats               # word-count stats only (no errors)

Exit code: 0 = clean, 1 = errors found.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# ── Path setup ────────────────────────────────────────────────────────────────
TOOLS_DIR   = Path(__file__).parent.resolve()
ROOT        = TOOLS_DIR.parent
CONTENT_DIR = ROOT / "content"

sys.path.insert(0, str(TOOLS_DIR))

from checkers.base          import CheckResult, Severity, count_prose_words, is_chapter_file
from checkers.toc           import check_toc
from checkers.frontmatter   import check_frontmatter
from checkers.structure     import check_structure
from checkers.code_blocks   import check_code_blocks
from checkers.terminology   import check_terminology
from checkers.callouts      import check_callouts
from checkers.headings_lock import check_headings_lock, generate_lock

# ── ANSI colours ─────────────────────────────────────────────────────────────
_RED    = "\033[31m"
_YELLOW = "\033[33m"
_GREEN  = "\033[32m"
_CYAN   = "\033[36m"
_BOLD   = "\033[1m"
_RESET  = "\033[0m"
_DIM    = "\033[2m"

def _colour(text: str, code: str) -> str:
    return f"{code}{text}{_RESET}" if sys.stdout.isatty() else text


# ── Per-file check runner ─────────────────────────────────────────────────────

def check_file(path: Path) -> CheckResult:
    result = CheckResult()
    for checker in (
        check_frontmatter,
        check_structure,
        check_code_blocks,
        check_terminology,
        check_callouts,
    ):
        result.merge(checker(path))
    return result


# ── Output helpers ────────────────────────────────────────────────────────────

def _print_result(result: CheckResult, root: Path) -> None:
    for issue in sorted(result.issues, key=lambda i: (str(i.file), i.line)):
        rel = issue.file.relative_to(root) if issue.file.is_absolute() else issue.file
        loc = f"{rel}:{issue.line}" if issue.line else str(rel)
        if issue.severity == Severity.ERROR:
            tag = _colour("[ERROR]", _RED + _BOLD)
        else:
            tag = _colour("[WARN] ", _YELLOW)
        rule = _colour(f"[{issue.rule}]", _DIM)
        print(f"  {tag} {loc}  {rule} {issue.message}")


def _print_stats(files: list[Path]) -> None:
    print(f"\n{'File':<48} {'Words':>6}  {'Status'}")
    print("─" * 65)
    total = 0
    for path in sorted(files):
        text = path.read_text(encoding="utf-8")
        wc   = count_prose_words(text)
        total += wc
        chap = is_chapter_file(path)
        flag = ""
        if chap and wc < 2000:
            flag = _colour("  ← stub", _YELLOW)
        elif chap and wc > 5000:
            flag = _colour("  ← long", _YELLOW)
        name = path.name
        print(f"  {name:<46} {wc:>6}{flag}")
    print("─" * 65)
    print(f"  {'TOTAL':<46} {total:>6}")


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Book quality checker for 'Building Production-Grade Agents'."
    )
    parser.add_argument(
        "--file", "-f", metavar="PATH",
        help="Check a single file instead of all content files."
    )
    parser.add_argument(
        "--no-lock", action="store_true",
        help="Skip the frozen-structure (headings lock) check."
    )
    parser.add_argument(
        "--update-lock", action="store_true",
        help="Regenerate headings_lock.json from the current content state and exit."
    )
    parser.add_argument(
        "--stats", action="store_true",
        help="Print word-count statistics and exit (no quality checks)."
    )
    args = parser.parse_args()

    # ── Update lock mode ──────────────────────────────────────────────────────
    if args.update_lock:
        print(_colour("Updating headings lock...", _CYAN))
        generate_lock(ROOT)
        print(_colour("Done. Commit headings_lock.json along with your structural changes.", _GREEN))
        return 0

    # ── Collect files ─────────────────────────────────────────────────────────
    if args.file:
        target = Path(args.file)
        if not target.exists():
            print(f"Error: file not found: {target}", file=sys.stderr)
            return 1
        files = [target.resolve()]
    else:
        files = sorted(CONTENT_DIR.glob("*.md"))

    # ── Stats-only mode ───────────────────────────────────────────────────────
    if args.stats:
        _print_stats(files)
        return 0

    # ── Run checks ────────────────────────────────────────────────────────────
    total = CheckResult()

    # Book-level checks (run once)
    if not args.file:
        print(_colour("Checking TOC integrity...", _CYAN))
        toc_result = check_toc(ROOT)
        total.merge(toc_result)
        if toc_result.issues:
            _print_result(toc_result, ROOT)

        if not args.no_lock:
            print(_colour("Checking frozen structure (headings lock)...", _CYAN))
            lock_result = check_headings_lock(ROOT)
            total.merge(lock_result)
            if lock_result.issues:
                _print_result(lock_result, ROOT)

    # Per-file checks
    n = len(files)
    print(_colour(f"\nChecking {n} file{'s' if n != 1 else ''}...\n", _CYAN))

    files_with_issues = 0
    for path in files:
        result = check_file(path)
        if result.issues:
            files_with_issues += 1
            rel = path.relative_to(ROOT) if path.is_absolute() else path
            e   = len(result.errors)
            w   = len(result.warnings)
            parts = []
            if e:
                parts.append(_colour(f"{e} error{'s' if e != 1 else ''}", _RED))
            if w:
                parts.append(_colour(f"{w} warning{'s' if w != 1 else ''}", _YELLOW))
            print(f"  {_colour(str(rel), _BOLD)}  ({', '.join(parts)})")
            _print_result(result, ROOT)
            print()
        total.merge(result)

    # ── Summary ───────────────────────────────────────────────────────────────
    e_total = len(total.errors)
    w_total = len(total.warnings)

    print("─" * 70)
    if e_total == 0 and w_total == 0:
        print(_colour("✓ All checks passed — book is clean.", _GREEN + _BOLD))
        return 0

    parts = []
    if e_total:
        parts.append(_colour(f"{e_total} error{'s' if e_total != 1 else ''}", _RED + _BOLD))
    if w_total:
        parts.append(_colour(f"{w_total} warning{'s' if w_total != 1 else ''}", _YELLOW))

    summary = ", ".join(parts) + f" across {files_with_issues} file{'s' if files_with_issues != 1 else ''}"
    print(f"Summary: {summary}")

    if e_total:
        print(_colour("\n✗ FAILED — fix errors before publishing.", _RED + _BOLD))
        return 1
    else:
        print(_colour("\n⚠ Passed with warnings — review before publishing.", _YELLOW))
        return 0


if __name__ == "__main__":
    sys.exit(main())
