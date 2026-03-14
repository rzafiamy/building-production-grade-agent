═══════════════════════════════════════════════════════════════════════════════
  WRITING RULES & STYLE GUIDE — "The Autonomous Agent"
═══════════════════════════════════════════════════════════════════════════════

VOICE & TONE
────────────
1.  Write in second person ("you") when addressing the reader directly.
    Use first person plural ("we") when author and reader explore together.
    Avoid passive voice — say who does what.

2.  Confident, not arrogant. Opinionated, not dogmatic. When the author
    doesn't know something, say so. Readers respect honesty over bravado.

3.  No hype. No "revolutionary", "game-changing", "unprecedented". Let the
    technology speak. If an agent can do something impressive, show it —
    don't label it.

4.  Dry wit is acceptable. Sarcasm is not. Humor should make a point, not
    just entertain.

5.  Technical precision always wins over readability. Never sacrifice
    accuracy for a smoother sentence. But then work to make the accurate
    sentence also readable.

STRUCTURE RULES
───────────────
6.  TABLE OF CONTENTS IS FROZEN. The TOC in `content/07-toc.md` defines the
    canonical structure of the book. Writers and maintainers must NEVER add,
    remove, or reorder entries in the TOC. The same applies to the section
    headings inside each page — the H1, H2, and H3 structure is fixed and must
    not be changed. Write content within the existing sections only.

7.  Every chapter opens with a "Chapter Goal" box — 2–4 sentences explaining
    what the reader will know/be able to do by the end. No vague promises.

8.  Every chapter ends with a "Key Takeaways" bullet list — 3–7 items,
    one sentence each. These should be the flashcard version of the chapter.

9.  Every chapter that introduces a concept must show a concrete code example
    before the chapter ends. No concept-only chapters.

10. Use callout boxes for:
    > [!NOTE]     — supplementary information
    > [!WARNING]  — things that will burn you in production
    > [!TIP]      — shortcuts or non-obvious tricks
    > [!DANGER]   — security/data-loss risks
    Use sparingly — maximum 3 callouts per chapter.

11. Section depth: H2 for major sections, H3 for sub-sections, H4 only when
    truly necessary. Never use H5 or H6.

12. Lists: use when there are 3+ parallel items. Prefer prose for 2 items.
    Bullet lists for unordered concepts. Numbered lists for sequences/steps.

CODE EXAMPLES
─────────────
13. All code examples use TypeScript unless explicitly showing a different
    language. Indicate language in fenced code blocks always.

14. Code examples must be complete enough to run or clearly marked with
    `// ... (abbreviated)` if shortened for space. Never show code that
    would fail if copy-pasted without obvious reason.

15. Every code example must have a one-line comment at the top indicating
    what it demonstrates. Example:
    ```typescript
    // Configuring a session with sandwich compression
    ```

16. Prefer showing real Lemura API usage. Only use pseudocode when the
    concept is framework-agnostic AND clearly labeled as pseudocode.

17. Include expected output or behavior after code examples where useful.
    Use `// Output:` comments for inline results.

18. If a code pattern is wrong/dangerous, show it first, label it as
    "Anti-pattern:" and then show the correct version labeled "Better:".

NAMING & TERMINOLOGY
─────────────────────
19. Consistent terminology throughout:
    - "agent" (not "bot", "assistant", "AI system" unless in quotes)
    - "turn" (one full request+response cycle)
    - "tool call" (not "function call" unless in OpenAI-specific context)
    - "context window" (not "context limit" or "token window")
    - "session" (a running agent instance in Lemura)
    - "plan" (a structured sequence of steps)
    - "goal" (the agent's current objective)
    - "compression" (reducing context size)
    - "provider" (the LLM backend: OpenAI, Anthropic, etc.)

20. Acronyms: define on first use, then use freely.
    Example: "ReAct (Reasoning + Acting) loop"

21. Class and API names are always formatted in code: `SessionManager`,
    `ContextManager`, `GoalInjector`. Never in plain text.

PACING & LENGTH
───────────────
22. Chapters: 2,000–5,000 words. Front-matter pages: 200–800 words.
    Appendices: as long as needed for completeness.

23. One idea per paragraph. Paragraphs: 3–6 sentences. No walls of text.

24. When a concept is complex, use this three-step structure:
    a) What it is (definition, one paragraph)
    b) Why it matters (motivation, one paragraph)
    c) How to use it (code + explanation)

25. Never repeat the same concept twice in a chapter. If you need to refer
    back, use "As discussed in Chapter N" — don't re-explain.

26. Cut ruthlessly. If a sentence doesn't add information or move the story
    forward, delete it. Every word must earn its place.

HONESTY & ACCURACY
──────────────────
27. When something is hard, say it's hard. Don't soften engineering reality.

28. When Lemura doesn't support something (yet), say so explicitly and
    suggest the workaround or the roadmap item if known.

29. Do not claim Lemura is the only way. Show why it's a good way, with
    comparisons where helpful.

30. When covering a pattern that has known failure modes, describe the
    failure mode. Readers who know the failure mode can prevent it.

31. Date-sensitive content (model capabilities, pricing, API availability)
    must be marked with a comment: `<!-- Accurate as of 2026-03 — verify -->`

CROSS-REFERENCES
────────────────
32. When referencing another chapter: "See **Chapter 8 — Goal Injection**"
    using the exact chapter title.

33. When referencing Lemura source code: include the file path.
    Example: "see `src/agent/execution/GoalInjector.ts`"

34. When referencing external resources: name them explicitly but do not
    include URLs (they rot). Say: "the OpenAI Function Calling docs" or
    "the MCP specification".

═══════════════════════════════════════════════════════════════════════════════
