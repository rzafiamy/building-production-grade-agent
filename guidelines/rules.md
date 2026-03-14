# Writing Rules & Style Guide

*"The Autonomous Agent" — enforced by `tools/check.py`.*

---

## Voice & Tone

**Rule 1.** Write in second person (`you`) when addressing the reader directly.
Use first person plural (`we`) when author and reader explore together. Avoid
passive voice — say who does what.

**Rule 2.** Confident, not arrogant. Opinionated, not dogmatic. When the author
does not know something, say so. Readers respect honesty over bravado.

**Rule 3.** No hype. No "revolutionary", "game-changing", "unprecedented". Let
the technology speak. If an agent can do something impressive, show it — do not
label it.

**Rule 4.** Dry wit is acceptable. Sarcasm is not. Humor should make a point,
not just entertain.

**Rule 5.** Technical precision always wins over readability. Never sacrifice
accuracy for a smoother sentence. But then work to make the accurate sentence
also readable.

---

## Structure Rules

**Rule 6 — The TOC and all section headings are frozen.**
The TOC in `content/07-toc.md` defines the canonical structure of the book.
Writers and maintainers must **never** add, remove, or reorder entries in the
TOC. The same applies to the H1, H2, and H3 headings inside each page — they
are fixed. Write content within existing sections only. Violations are caught
automatically by `tools/check.py`.

**Rule 7.** Every chapter opens with a Chapter Goal callout — 2–4 sentences
explaining what the reader will know or be able to do by the end. No vague
promises.

```markdown
> [!NOTE]
> **Chapter Goal:** By the end of this chapter, you will understand X,
> be able to implement Y, and know when Z applies.
```

**Rule 8.** Every chapter ends with a `## Key Takeaways` bullet list — 3–7
items, one sentence each. These are the flashcard version of the chapter.

**Rule 9.** Every chapter that introduces a concept must show a concrete code
example before the chapter ends. No concept-only chapters.

**Rule 10.** Use callout boxes for asides. Maximum **3 callouts per chapter**.
Never nest callouts.

| Type | Use for |
|------|---------|
| `[!NOTE]` | Supplementary information |
| `[!WARNING]` | Things that will burn you in production |
| `[!TIP]` | Shortcuts or non-obvious tricks |
| `[!DANGER]` | Security or data-loss risks |

**Rule 11.** Section depth: H2 for major sections, H3 for sub-sections, H4 only
when truly necessary. **Never use H5 or H6.**

**Rule 12.** Lists: use when there are 3 or more parallel items. Prefer prose
for 2 items. Bullet lists for unordered concepts. Numbered lists for
sequences and steps.

---

## Code Examples

**Rule 13.** All code examples use TypeScript unless explicitly showing a
different language. Indicate the language in every fenced code block.

**Rule 14.** Code examples must be complete enough to run, or clearly marked
with `// ... (abbreviated)` if shortened for space. Never show code that would
fail if copy-pasted without obvious reason.

**Rule 15.** Every code block must start with a `//` comment describing what it
demonstrates:

```typescript
// Configuring a session with sandwich compression
const session = await lemura.createSession({ compression: "sandwich" });
```

**Rule 16.** Prefer showing real Lemura API usage. Only use pseudocode when the
concept is framework-agnostic, and always label it explicitly:

```pseudocode
// Pseudocode — framework-agnostic illustration
loop:
  thought = llm.think(context)
  if thought.done: break
  result = tools.run(thought.action)
  context.append(result)
```

**Rule 17.** Include expected output or behavior after code examples where
useful. Use `// Output:` comments for inline results.

**Rule 18.** If a code pattern is wrong or dangerous, show it first labeled
`Anti-pattern:`, then show the correct version labeled `Better:`:

```typescript
// Anti-pattern: pushing raw tool output directly into context
context.push({ role: "tool", content: JSON.stringify(largeResult) });
```

```typescript
// Better: compress tool output before adding to context
const summary = await compressor.summarize(largeResult, { maxTokens: 200 });
context.push({ role: "tool", content: summary });
```

---

## Naming & Terminology

**Rule 19.** Use consistent terminology throughout the book:

| Use this | Not this |
|----------|----------|
| `agent` | bot, assistant, AI system (unless quoting) |
| `turn` | round-trip, iteration, cycle |
| `tool call` | function call (unless OpenAI-specific context) |
| `context window` | context limit, token window |
| `session` | run, instance, execution |
| `plan` | task list, steps |
| `goal` | objective, instruction, prompt |
| `compression` | summarization, trimming, pruning |
| `provider` | backend, model, LLM |

**Rule 20.** Acronyms: define on first use, then use freely.
Example: "ReAct (Reasoning + Acting) loop".

**Rule 21.** Class and API names are always formatted in code. Never in plain
text: `SessionManager`, `ContextManager`, `GoalInjector`.

---

## Pacing & Length

**Rule 22.** Target lengths:

| Section type | Word count |
|--------------|-----------|
| Chapters | 2,000–5,000 words |
| Front-matter pages | 200–800 words |
| Appendices | As long as completeness requires |

**Rule 23.** One idea per paragraph. Paragraphs: 3–6 sentences. No walls of
text.

**Rule 24.** When a concept is complex, use this three-step structure:

1. **What it is** — definition, one paragraph
2. **Why it matters** — motivation, one paragraph
3. **How to use it** — code example with explanation

**Rule 25.** Never repeat the same concept twice in a chapter. If you need to
refer back, write "As discussed in Chapter N" — do not re-explain.

**Rule 26.** Cut ruthlessly. If a sentence does not add information or move the
story forward, delete it. Every word must earn its place.

---

## Honesty & Accuracy

**Rule 27.** When something is hard, say it is hard. Do not soften engineering
reality.

**Rule 28.** When Lemura does not support something yet, say so explicitly and
suggest the workaround or the known roadmap item.

**Rule 29.** Do not claim Lemura is the only way. Show why it is a good way,
with comparisons where helpful.

**Rule 30.** When covering a pattern that has known failure modes, describe the
failure mode. Readers who know the failure mode can prevent it.

**Rule 31.** Date-sensitive content (model capabilities, pricing, API
availability) must be marked with a comment immediately after the relevant
paragraph:

```markdown
<!-- Accurate as of 2026-03 — verify before next edition -->
```

---

## Cross-References

**Rule 32.** When referencing another chapter, use the exact title in bold:

> See **Chapter 8 — Planning and Goals: Directing the Agent**

**Rule 33.** When referencing Lemura source code, include the file path:

> see `src/agent/execution/GoalInjector.ts`

**Rule 34.** When referencing external resources, name them explicitly but do
**not** include URLs — they rot. Write "the OpenAI Function Calling docs" or
"the MCP specification", not a link.
