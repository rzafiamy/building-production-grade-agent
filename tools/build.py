#!/usr/bin/env python3
"""
Book builder — "Building Production-Grade Agents"

Collects all content files in numeric order, runs word-count stats,
and optionally concatenates them into a single build/book.md artifact.

Usage:
  python tools/build.py              # stats + build to build/book.md
  python tools/build.py --stats      # stats only, no output file
  python tools/build.py --out PATH   # write to a custom path
  python tools/build.py --check-order  # verify file numbering has no gaps
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

TOOLS_DIR   = Path(__file__).parent.resolve()
ROOT        = TOOLS_DIR.parent
CONTENT_DIR = ROOT / "content"
BUILD_DIR   = ROOT / "build"

sys.path.insert(0, str(TOOLS_DIR))

from checkers.base import count_prose_words, is_chapter_file, is_front_matter, is_back_matter

_GREEN  = "\033[32m"
_YELLOW = "\033[33m"
_CYAN   = "\033[36m"
_BOLD   = "\033[1m"
_DIM    = "\033[2m"
_RESET  = "\033[0m"

def c(text: str, code: str) -> str:
    return f"{code}{text}{_RESET}" if sys.stdout.isatty() else text


# ── File ordering ─────────────────────────────────────────────────────────────

def _sort_key(path: Path) -> int:
    try:
        return int(path.stem.split("-")[0])
    except (ValueError, IndexError):
        return 999


def collect_files() -> list[Path]:
    return sorted(CONTENT_DIR.glob("*.md"), key=_sort_key)


def check_order(files: list[Path]) -> list[str]:
    """Return a list of gap/duplicate warnings in the file numbering sequence."""
    problems: list[str] = []
    seen: dict[int, str] = {}
    prev = -1
    for f in files:
        try:
            n = int(f.stem.split("-")[0])
        except (ValueError, IndexError):
            problems.append(f"Cannot parse number prefix: {f.name}")
            continue
        if n in seen:
            problems.append(f"Duplicate prefix {n:02d}: {seen[n]} and {f.name}")
        seen[n] = f.name
        if prev >= 0 and n != prev + 1:
            problems.append(f"Gap in numbering: {prev:02d} → {n:02d} (missing {prev+1:02d}–{n-1:02d})")
        prev = n
    return problems


# ── Stats ─────────────────────────────────────────────────────────────────────

def _label(path: Path) -> str:
    if is_chapter_file(path):   return "chapter"
    if is_front_matter(path):   return "front  "
    if is_back_matter(path):    return "back   "
    return "part   "


def print_stats(files: list[Path]) -> dict[str, int]:
    """Print per-file word counts and return totals by category."""
    totals: dict[str, int] = {"chapter": 0, "front  ": 0, "back   ": 0, "part   ": 0}

    print(f"\n  {'#':<4} {'File':<44} {'Type':<8} {'Words':>6}")
    print("  " + "─" * 68)

    for path in files:
        try:
            n = int(path.stem.split("-")[0])
        except (ValueError, IndexError):
            n = -1
        text  = path.read_text(encoding="utf-8")
        wc    = count_prose_words(text)
        label = _label(path)

        flag = ""
        if is_chapter_file(path):
            if wc < 2000:
                flag = c("  ← stub", _YELLOW)
            elif wc > 5000:
                flag = c("  ← long", _YELLOW)

        totals[label] = totals.get(label, 0) + wc
        print(f"  {n:02d}   {path.name:<44} {label} {wc:>6}{flag}")

    total_words = sum(totals.values())
    print("  " + "─" * 68)
    print(f"  {'':4} {'TOTAL':<44} {'':8} {total_words:>6}")
    print()
    print(f"  Front matter:  {totals.get('front  ', 0):>6} words")
    print(f"  Part intros:   {totals.get('part   ', 0):>6} words")
    print(f"  Chapters:      {totals.get('chapter', 0):>6} words")
    print(f"  Back matter:   {totals.get('back   ', 0):>6} words")
    print(f"  {'─'*22}")
    print(f"  Total:         {total_words:>6} words")

    return totals


# ── Build ─────────────────────────────────────────────────────────────────────

def build_book(files: list[Path], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    separator = "\n\n---\n\n"
    parts: list[str] = []

    for path in files:
        text = path.read_text(encoding="utf-8")
        parts.append(text.strip())

    combined = separator.join(parts) + "\n"
    out_path.write_text(combined, encoding="utf-8")

    size_kb = out_path.stat().st_size / 1024
    print(f"\n  {c('Built →', _GREEN)} {out_path}  ({size_kb:.1f} KB, {len(files)} files)")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build and inspect 'Building Production-Grade Agents'."
    )
    parser.add_argument("--stats",       action="store_true", help="Print stats only, skip build.")
    parser.add_argument("--check-order", action="store_true", help="Verify file numbering and exit.")
    parser.add_argument("--out",         metavar="PATH", help="Output path (default: build/book.md).")
    args = parser.parse_args()

    files = collect_files()
    print(c(f"\nCollected {len(files)} content files from {CONTENT_DIR}", _CYAN))

    # Order check
    problems = check_order(files)
    if problems:
        print(c("\nFile ordering problems:", _YELLOW))
        for p in problems:
            print(f"  ⚠  {p}")
    if args.check_order:
        return 0 if not problems else 1

    # Stats
    print_stats(files)

    if args.stats:
        return 0

    # Build
    out = Path(args.out) if args.out else BUILD_DIR / "book.md"
    build_book(files, out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
