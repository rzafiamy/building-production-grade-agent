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
import subprocess
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


def build_pdf(md_path: Path, pdf_path: Path) -> None:
    """Convert the combined Markdown file to PDF using Chrome headless."""
    print(f"  {c('Generating PDF via Chrome...', _CYAN)}")

    html_path = pdf_path.with_suffix(".html")
    css_path  = pdf_path.with_suffix(".css")

    # Premium print-first CSS with modern typography and stable pagination
    css_content = """
    @import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:wght@400;600;700&family=Fraunces:wght@600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');
    :root {
        --ink: #121318;
        --muted: #5d6670;
        --rule: #e3e6eb;
        --accent: #2563eb;
        --paper: #ffffff;
    }
    * { box-sizing: border-box; }
    html { -webkit-font-smoothing: antialiased; }
    body {
        font-family: 'Source Serif 4', ui-serif, Georgia, serif;
        color: var(--ink);
        background: var(--paper);
        line-height: 1.35;
        font-size: 10pt;
        margin: 0;
        padding: 0;
        hyphens: auto;
        text-rendering: optimizeLegibility;
        font-kerning: normal;
        font-variant-ligatures: common-ligatures;
    }
    h1, h2, h3, h4, h5 {
        font-family: 'Fraunces', ui-serif, Georgia, serif;
        color: var(--ink);
        margin: 1.6em 0 0.5em;
        font-weight: 700;
        line-height: 1.2;
        page-break-after: avoid;
        break-after: avoid-page;
    }
    h1 { font-size: 22pt; letter-spacing: -0.01em; }
    h2 { font-size: 15.5pt; border-bottom: 1px solid var(--rule); padding-bottom: 0.15em; }
    h3 { font-size: 12.5pt; color: #1b2530; }
    h4 { font-size: 11.5pt; color: #1b2530; }
    p { margin: 0 0 0.6em; orphans: 2; widows: 2; }
    a { color: var(--accent); text-decoration: none; }
    a:hover { text-decoration: underline; }
    ul, ol { margin: 0 0 1em 1.25em; }
    li { margin: 0.25em 0; }
    hr { border: 0; border-top: 1px solid var(--rule); margin: 2em 0; }
    blockquote {
        margin: 1.2em 0;
        padding: 0.65em 1em;
        border-left: 3px solid var(--accent);
        background: #f6f8ff;
        color: #2b3340;
        font-style: italic;
        break-inside: avoid;
        page-break-inside: avoid;
    }
    pre, code {
        font-family: 'IBM Plex Mono', ui-monospace, SFMono-Regular, Menlo, monospace;
    }
    pre {
        background: #f5f7fb;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 10px 12px;
        overflow-x: auto;
        font-size: 8.5pt;
        line-height: 1.35;
        break-inside: avoid;
        page-break-inside: avoid;
    }
    code {
        background: #eef2ff;
        padding: 0.12em 0.3em;
        border-radius: 5px;
        font-size: 0.92em;
        color: #1f2937;
    }
    table {
        width: 100%;
        border-collapse: collapse;
        margin: 1em 0;
        font-size: 9.5pt;
        break-inside: avoid;
        page-break-inside: avoid;
    }
    th, td {
        border: 1px solid #e2e8f0;
        padding: 8px 10px;
        text-align: left;
        vertical-align: top;
    }
    th { background: #f1f5f9; font-weight: 600; }
    img { max-width: 100%; height: auto; border-radius: 8px; }
    .page-break { break-before: page; page-break-before: always; }

    @page {
        size: 8.5in 11in;
        margin: 0.6in 0.6in 0.7in;
    }
    @media screen {
        body {
            background: #f3f4f6;
            max-width: 980px;
            padding: 40px;
            margin: 16px auto;
            box-shadow: 0 10px 30px rgba(16, 24, 40, 0.08);
            border-radius: 12px;
        }
    }
    @media print {
        body { margin: 0; }
        a { color: #1a1a1a; text-decoration: none; }
        .no-print { display: none; }
        h2 { border-bottom-color: #d8dde5; }
    }
    """

    try:
        css_path.write_text(css_content, encoding="utf-8")

        # 1. MD -> HTML
        cmd_html = [
            "pandoc",
            str(md_path),
            "-o", str(html_path),
            "--standalone",
            "--toc",
            "--toc-depth=2",
            "--css", str(css_path),
            "--metadata", "title=Building Production-Grade Agents",
            "--highlight-style=tango",
        ]
        subprocess.run(cmd_html, check=True, capture_output=True)

        # 2. HTML -> PDF
        # We use google-chrome if available
        chrome_bin = "google-chrome" # or "chromium-browser"
        cmd_pdf = [
            chrome_bin,
            "--headless",
            "--disable-gpu",
            "--no-sandbox",
            f"--print-to-pdf={pdf_path}",
            "--no-pdf-header-footer",
            str(html_path)
        ]
        subprocess.run(cmd_pdf, check=True, capture_output=True)

        # Cleanup
        if html_path.exists(): html_path.unlink()
        if css_path.exists():  css_path.unlink()

        if pdf_path.exists():
            size_mb = pdf_path.stat().st_size / (1024 * 1024)
            print(f"  {c('Built →', _GREEN)} {pdf_path}  ({size_mb:.2f} MB)")

    except subprocess.CalledProcessError as e:
        print(f"  {c('Error during PDF generation:', _YELLOW)}\n{e.stderr.decode() if e.stderr else e}")
    except Exception as e:
        print(f"  {c('An unexpected error occurred:', _YELLOW)} {e}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build and inspect 'Building Production-Grade Agents'."
    )
    parser.add_argument("--stats",       action="store_true", help="Print stats only, skip build.")
    parser.add_argument("--check-order", action="store_true", help="Verify file numbering and exit.")
    parser.add_argument("--out",         metavar="PATH", help="Output path for Markdown (default: build/book.md).")
    parser.add_argument("--pdf",         action="store_true", help="Generate PDF version as well.")
    parser.add_argument("--pdf-out",     metavar="PATH", help="Output path for PDF (default: build/book.pdf).")
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

    # Build Markdown
    out = Path(args.out) if args.out else BUILD_DIR / "book.md"
    build_book(files, out)

    # Build PDF if requested
    if args.pdf:
        pdf_out = Path(args.pdf_out) if args.pdf_out else BUILD_DIR / "book.pdf"
        build_pdf(out, pdf_out)

    return 0


if __name__ == "__main__":
    sys.exit(main())
