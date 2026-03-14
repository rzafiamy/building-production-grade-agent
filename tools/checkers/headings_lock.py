"""Frozen structure checker (rule 6).

The headings_lock.json file is the canonical record of:
  - The SHA-256 hash of content/07-toc.md
  - The H1/H2/H3 heading list for every content file

On check:
  - If the TOC hash differs → ERROR (TOC was modified)
  - If headings differ from the lock → ERROR (structure changed)
  - If a new content file appears that isn't in the lock → ERROR
  - If a locked file no longer exists → ERROR

On --update-lock:
  - Rewrite headings_lock.json from the current state of content/
  - This must be a deliberate, reviewed action.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from pathlib import Path

from .base import CheckResult, strip_front_matter

_LOCK_PATH    = Path(__file__).parent.parent / "headings_lock.json"
_HEADING_RE   = re.compile(r"^(#{1,3})\s+(.+)")

# Files whose headings are intentionally not tracked (auto-generated or minimal)
_UNTRACKED = {"07-toc.md"}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _extract_headings(path: Path) -> list[str]:
    """Return a list of H1/H2/H3 heading strings from a file (excluding front matter)."""
    text = path.read_text(encoding="utf-8")
    body, _ = strip_front_matter(text)
    headings: list[str] = []
    in_fence = False
    for line in body.splitlines():
        if re.match(r"^\s*```", line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = _HEADING_RE.match(line)
        if m:
            headings.append(line.rstrip())
    return headings


def _load_lock() -> dict:
    if not _LOCK_PATH.exists():
        return {}
    return json.loads(_LOCK_PATH.read_text(encoding="utf-8"))


# ── Public: generate lock ─────────────────────────────────────────────────────

def generate_lock(root: Path) -> None:
    """Write (or overwrite) headings_lock.json from the current content state."""
    cdir    = root / "content"
    toc     = cdir / "07-toc.md"
    payload: dict = {
        "_meta": {
            "generated": str(date.today()),
            "note": (
                "DO NOT edit manually. "
                "Update only with: python tools/check.py --update-lock"
            ),
        },
        "toc_hash": _sha256(toc) if toc.exists() else "",
        "files": {},
    }

    for md in sorted(cdir.glob("*.md")):
        if md.name in _UNTRACKED:
            continue
        payload["files"][md.name] = {"headings": _extract_headings(md)}

    _LOCK_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"  Lock written → {_LOCK_PATH}")
    print(f"  Tracked {len(payload['files'])} files.")


# ── Public: check against lock ────────────────────────────────────────────────

def check_headings_lock(root: Path) -> CheckResult:
    result = CheckResult()
    cdir   = root / "content"
    toc    = cdir / "07-toc.md"
    lock   = _load_lock()

    if not lock:
        result.error(
            _LOCK_PATH, 0, "LOCK-001",
            "headings_lock.json not found. Run: python tools/check.py --update-lock"
        )
        return result

    # 1. TOC hash must be unchanged
    if toc.exists():
        current_hash = _sha256(toc)
        locked_hash  = lock.get("toc_hash", "")
        if locked_hash and current_hash != locked_hash:
            result.error(
                toc, 0, "LOCK-002",
                "content/07-toc.md has been modified since the lock was last generated. "
                "The TOC structure is frozen (rule 6). "
                "If this change was intentional and reviewed, run: python tools/check.py --update-lock"
            )

    locked_files: dict[str, dict] = lock.get("files", {})

    # 2. Check each locked file
    for fname, entry in locked_files.items():
        fpath = cdir / fname
        if not fpath.exists():
            result.error(
                cdir / fname, 0, "LOCK-003",
                f"File '{fname}' is in the headings lock but no longer exists on disk. "
                "Removing content files is not allowed without updating the lock."
            )
            continue

        current_headings = _extract_headings(fpath)
        locked_headings  = entry.get("headings", [])

        if current_headings != locked_headings:
            added   = set(current_headings) - set(locked_headings)
            removed = set(locked_headings) - set(current_headings)
            details = []
            if added:
                details.append("Added: " + "; ".join(f'"{h}"' for h in sorted(added)))
            if removed:
                details.append("Removed: " + "; ".join(f'"{h}"' for h in sorted(removed)))
            if not details:
                details.append("Order changed")
            result.error(
                fpath, 0, "LOCK-004",
                f"H1/H2/H3 headings in '{fname}' differ from the lock — structure is frozen (rule 6). "
                + " | ".join(details) + ". "
                "To intentionally restructure, run: python tools/check.py --update-lock"
            )

    # 3. Flag new content files not in the lock
    for md in sorted(cdir.glob("*.md")):
        if md.name in _UNTRACKED:
            continue
        if md.name not in locked_files:
            result.error(
                md, 0, "LOCK-005",
                f"New file '{md.name}' is not in headings_lock.json. "
                "Adding new pages is not allowed without updating the lock (rule 6). "
                "Run: python tools/check.py --update-lock (after deliberate review)."
            )

    return result
