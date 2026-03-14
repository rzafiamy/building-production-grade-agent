═══════════════════════════════════════════════════════════════════════════════
  GOAL & INSPIRATION — "The Autonomous Agent"
  A Complete Guide to Building Reliable AI Agents with Lemura
═══════════════════════════════════════════════════════════════════════════════

CORE GOAL
─────────
Write the definitive practitioner's book on building autonomous AI agents in
2026. Not a survey paper. Not a "hello world" tutorial. A real engineering
guide that takes experienced developers from zero to production-grade agents —
with all the hard-won knowledge that exists nowhere else in one place.

This book exists because:
  • Autonomous agents are the most powerful software paradigm since the web —
    but almost every production attempt fails silently or expensively.
  • The internet is flooded with toy demos and shallow tutorials. Nobody
    writes about what actually breaks at 3am and why.
  • Lemura was built to solve the real problems. This book explains both the
    problems AND the solutions, using Lemura as the reference implementation.

THE READER WE ARE WRITING FOR
──────────────────────────────
A senior engineer or technical lead who:
  • Knows TypeScript/Python and can read source code
  • Has tried building an agent before and hit walls (loops, cost, failures)
  • Is responsible for shipping something real, not a demo
  • Has 2-3 hours to read, not 2-3 days
  • Respects honesty over hype

We are NOT writing for:
  • Beginners learning to code
  • Business stakeholders wanting a high-level overview
  • Academics seeking formal proofs

THE PROMISE TO THE READER
──────────────────────────
By the end of this book, the reader will be able to:
  1. Understand WHY agents fail (context limits, cost spirals, hallucinated
     tool calls, infinite loops, lack of recovery) and HOW to prevent each.
  2. Design agent architectures that are observable, testable, and debuggable.
  3. Use Lemura's full API — SessionManager, context strategies, goal
     injection, continuation planning, MCP, skills — with confidence.
  4. Apply proven patterns for multi-agent systems, human-in-the-loop flows,
     cost optimization, and production reliability.
  5. Ship autonomous agents that actually work under real load.

INSPIRATION
───────────
The Pragmatic Programmer showed us that great engineering is about habits,
not heroics. The Art of Unix Programming showed us that philosophy matters
in systems. DDIA showed us that distributed systems have hard truths you
cannot ignore.

This book should be that for agentic AI — unafraid of the hard truths,
deeply practical, and written by someone who has felt the pain.

The Lemura framework is the reference implementation — every pattern in the
book has a concrete API call behind it. But the principles are universal.
A reader who finishes this book could apply everything to a different
framework, because they understand WHY not just HOW.

WHAT THIS BOOK IS NOT
──────────────────────
  • Not a marketing document for Lemura
  • Not a collection of GPT wrapper tips
  • Not a theoretical AI/ML textbook
  • Not a prompt engineering guide (though prompt design is covered where
    it intersects with agent architecture)
  • Not a "10 things about ChatGPT" blog post

MAINTENANCE NOTES FOR THE WRITER
──────────────────────────────────
When updating this book:
  1. Always check current Lemura API against src/ — never document what
     doesn't exist.
  2. Update the version reference in the preface when Lemura releases.
  3. The "2026 landscape" sections will age — flag them with a date comment
     if they need periodic review.
  4. Code examples must be tested against the actual Lemura package. Do not
     write example code from memory.
  5. Each chapter should stand alone as a reference — a reader who skips to
     chapter 15 should not be lost.
  6. Never sacrifice honesty for positivity. If something is hard, say so.
     If there's no good solution yet, say that too.

TARGET LENGTH
─────────────
  40–70 pages (one markdown file per page/section)
  ~3,000–5,000 words per chapter
  Code examples preferred over long prose explanations
  Diagrams as ASCII art where useful

═══════════════════════════════════════════════════════════════════════════════
