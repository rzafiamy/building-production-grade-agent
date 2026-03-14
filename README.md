# Building Production-Grade Agents

**The Autonomous Agent: Engineering Reliable AI Systems with Lemura**

*By Rija ZAFIAMY — AI Engineer, Software Architect*

![Book Cover](assets/cover.png)

> A complete practitioner's guide to building autonomous AI agents in 2026 —
> not a toy tutorial. A real engineering book for engineers who ship.

---

## About

In 2026, autonomous agents are the most powerful software paradigm since the
web. Almost every production attempt fails silently or expensively. The internet
is flooded with demos and shallow tutorials. Nobody writes about what breaks at
3 AM and why.

**The Autonomous Agent** is the engineering guide that fixes this. It takes
senior developers from zero to production-grade agents — covering the hard-won
knowledge that exists nowhere else in one place. Every pattern has a concrete
API call behind it using the **Lemura** framework as the reference
implementation. Every failure mode is described, not softened.

---

## Who This Is For

This book is written for engineers who are responsible for shipping real
products. Specifically:

- Senior engineers and tech leads who have tried building agents and hit walls
- Architects looking for an honest, pragmatic approach — not an AI hype guide
- Developers who need to understand *why* agents fail, not just *how* to start them

This book is **not** for absolute beginners, business stakeholders wanting a
high-level overview, or anyone looking for prompt engineering tips.

---

## What You Will Learn

By the end of this book you will be able to:

1. **Prevent the common failures** — context limits, cost spirals, hallucinated
   tool calls, infinite loops — and understand why each happens.
2. **Design observable, testable, debuggable** agent architectures from the start.
3. **Use the full Lemura API** — `SessionManager`, context strategies, goal
   injection, continuation planning, MCP, and skills — with confidence.
4. **Apply production patterns** for multi-agent systems, human-in-the-loop
   flows, cost optimization, and reliability engineering.
5. **Ship agents that hold up** under real load, real failures, and real users.

---

## Book Structure

| Part | Title | Chapters |
|------|-------|----------|
| I    | The Agentic Revolution | 1–4 |
| II   | Architecture Fundamentals | 5–10 |
| III  | Lemura Framework Deep Dive | 11–19 |
| IV   | Memory and State | 20–23 |
| V    | Advanced Patterns | 24–30 |
| VI   | Production Engineering | 31–36 |
| VII  | Real-World Applications | 37–40 |

Full table of contents: [content/07-toc.md](content/07-toc.md)

---

## Repository Structure

```text
.
├── content/                 Book source — one .md file per page
│   ├── 00-cover.md
│   ├── 07-toc.md            Canonical table of contents (frozen)
│   ├── 08-ch01-*.md         Chapter files (08–53)
│   └── 55-appendix-a-*.md  Back matter (55–60)
│
├── guidelines/              Authoring standards — read before writing
│   ├── goal.md              Book goal, target reader, promise to the reader
│   ├── rules.md             Writing rules and style guide (34 rules)
│   └── format.md            Markdown format and layout specification
│
├── tools/                   Quality tooling (Python, no dependencies)
│   ├── check.py             Main quality checker — run before every commit
│   ├── build.py             Book assembler and word-count reporter
│   ├── pre-commit           Git hook — install once, blocks bad commits
│   ├── headings_lock.json   Frozen structure snapshot (do not edit manually)
│   └── checkers/            Individual rule checker modules
│
└── assets/                  Images, cover art
```

---

## Tools

All tools require Python 3.11+ and zero external dependencies.

### Quality Checker

The checker enforces every rule in `guidelines/rules.md` and
`guidelines/format.md`. It must pass (zero errors) before publishing.

```bash
# Check all 61 content files
python tools/check.py

# Check a single file during writing
python tools/check.py --file content/08-ch01-the-agent-moment.md

# Word-count table (no rule checks)
python tools/check.py --stats

# Skip the frozen-structure check (for exploratory edits)
python tools/check.py --no-lock
```

**Exit codes:** `0` = clean or warnings only. `1` = one or more errors.
Errors block publishing. Warnings are advisory.

#### What is checked

| Category | Rules enforced |
|----------|---------------|
| **TOC integrity** | All TOC links resolve; no orphaned content files |
| **Frozen structure** | H1/H2/H3 headings match `headings_lock.json`; TOC file unchanged |
| **Front matter** | Required YAML fields (`title`, `status`, `part`, `chapter`, `page`) and valid values |
| **Chapter structure** | Chapter Goal callout present; Key Takeaways section present; no H5/H6 headings; word count in range |
| **Code blocks** | Language tag required; tag from approved list; TypeScript/JS blocks start with `//` description comment |
| **Terminology** | Banned hype words; correct terms (`agent`, `tool call`, `context window`); no URLs in prose |
| **Callouts** | Maximum 3 per chapter; approved types only; no nesting |
| **Date markers** | Model version references have `<!-- Accurate as of YYYY-MM — verify -->` |

### Book Builder

Assembles all content files in order, reports word counts, and handles exports (Markdown and PDF).

```bash
# Full stats + build concatenated book to build/book.md
python tools/build.py

# build/book.md + generate build/book.pdf (requires Google Chrome/Chromium)
python tools/build.py --pdf

# Word-count report only (no output file written)
python tools/build.py --stats

# Verify file numbering has no gaps or duplicates
python tools/build.py --check-order

# Write outputs to custom paths
python tools/build.py --out draft.md --pdf --pdf-out draft.pdf
```

### Frozen Structure

The TOC and all H1/H2/H3 heading structures are locked. Writers write content
*inside* existing sections — they never add, remove, or reorder sections.

```bash
# After a deliberate, reviewed structural change: regenerate the lock
python tools/check.py --update-lock
```

> [!WARNING]
> Always commit `tools/headings_lock.json` alongside any structural change.
> The lock is the record of what was intentionally changed and when.

### Git Pre-commit Hook

The hook runs `check.py` automatically on every `git commit` that touches
`content/` or `guidelines/`. Commits with errors are rejected.

```bash
# Install once per clone
cp tools/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

To bypass in an emergency (not recommended):

```bash
git commit --no-verify
```

---

## Writer's Workflow

### First time

```bash
# 1. Clone and install the hook
git clone <repo>
cd building-production-grade-agent
cp tools/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit

# 2. Read the guidelines before writing anything
open guidelines/goal.md
open guidelines/rules.md
open guidelines/format.md
```

### Writing a chapter

```bash
# Check the chapter you're working on as you write
python tools/check.py --file content/08-ch01-the-agent-moment.md

# Check the full book before committing
python tools/check.py

# Review word counts
python tools/check.py --stats
```

### Chapter file template

Every chapter file must follow this structure, in this order:

```markdown
---
title: "Chapter N — Title"
part: "Part X — Part Name"
chapter: N
page: NN
status: draft
---

*PART X — PART NAME*

## Chapter N — Title

> *"Epigraph quote here."*

> [!NOTE]
> **Chapter Goal:** By the end of this chapter, you will...

---

### N.1 First Section

### N.2 Second Section

---

## Key Takeaways

- Takeaway one.
- Takeaway two.
```

### Rules at a glance

- Write in second person (`you`) when addressing the reader directly.
- No hype. No "revolutionary", "game-changing", "unprecedented". Show, don't label.
- Every chapter needs a **Chapter Goal** callout and a **Key Takeaways** section.
- All code blocks need a language tag and a `//` description comment (TypeScript/JS).
- Use `agent`, `tool call`, `context window` — not `bot`, `function call`, `token window`.
- No URLs in prose. Name resources; don't link them.
- The TOC and section headings are frozen. Write content inside sections, never restructure.

Full rules: [guidelines/rules.md](guidelines/rules.md)

---

## Technology Stack

| Layer | Choice |
|-------|--------|
| Language | TypeScript |
| Runtime | Node.js 18+ |
| Agent framework | Lemura v1.3+ |
| Authoring format | Markdown (CommonMark + GFM) |
| Quality tooling | Python 3.11+, stdlib only |
| Export targets | GitHub, VitePress, Docusaurus, Pandoc/PDF |

---

## License

Book content and code examples are published under the **MIT License**.

---

*First Edition — 2026. Written for Lemura v1.3+.*
