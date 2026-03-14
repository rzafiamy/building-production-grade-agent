---
title: "Chapter 22 — Compression Strategies in Depth"
part: "Part IV — Memory and State"
chapter: 22
page: 32
status: draft
---

*PART IV — MEMORY AND STATE*

## Chapter 22 — Compression Strategies in Depth

> *"Compression is a lossy transform. The goal is to lose the right information — not randomly, but strategically."*

> [!NOTE]
> **Chapter Goal:** By the end of this chapter, you will have a complete playbook for context compression: when to use each strategy, how to configure them, how to compose them, and how to measure their effectiveness.

---

### 22.1 A Complete Taxonomy of Compression Approaches

| Strategy | Lossiness | Speed | Cost | Best For |
|---|---|---|---|---|
| Truncation | High (blind) | Instant | Free | Emergency only |
| Rolling Summary | Medium | Slow | LLM call | Long research tasks |
| Sandwich | Low | Medium | LLM call | Mixed tool/conversation |
| Summary Injection | None (re-use) | Fast | Free | Resuming sessions |
| External RAG | Zero | Slow | DB query | Archive retrieval |

This taxonomy is your decision tree. Start at lossiness: how much information can this session afford to lose? Move to cost: can the compression overhead be justified given session volume and latency requirements? Match the strategy to the scenario.

No single strategy handles all cases. The compression playbook is about composing strategies appropriately for each class of session.

### 22.2 Truncation: When You Have No Choice

#### 22.2.1 Safe Truncation Points

Truncation removes messages from the conversation history. Not all positions are equally safe to truncate from. Safe truncation removes from the middle of the history — the oldest compressible turns. Unsafe truncation removes from the beginning (losing system context) or the end (losing current task state).

Lemura's compression strategies implement truncation by specifying preservation counts (`preserveFirst`, `preserveLast`), not by truncating blindly from one end. Any truncation that removes the system prompt, the current user message, or the most recent tool results is unsafe.

#### 22.2.2 What Must Never Be Truncated

System prompt content must never be truncated. Goal and plan state must never be truncated. The current user message and the most recent model response must never be truncated. The most recent tool results that are being actively used must never be truncated.

These are the "sacred" elements from the sandwich pattern. Design all truncation around preserving them.

#### 22.2.3 Implementing Graceful Truncation

Graceful truncation removes the oldest non-sacred turns and generates a brief summary of what was removed. Even a one-sentence note ("Earlier turns summarized: the agent searched for config files and found none") is better than silent removal.

Use truncation as the last line of defense — the strategy that fires when all other strategies have been applied and the context is still over budget. Set its priority higher than any other strategy (e.g., priority 100) so it only fires if all lower-priority strategies were insufficient.

### 22.3 Rolling History Summarization

#### 22.3.1 Summarization Prompt Design

The quality of rolling summaries depends heavily on the prompt used to generate them. A poor summarization prompt produces vague, fact-free summaries. A good one produces dense, fact-rich summaries.

The key instruction: preserve specific values, not just events. Compare:

- Poor: "The agent searched for files and found some results."
- Good: "Found 3 TypeScript files with eval() usage: src/eval.ts:42, src/legacy.ts:87, src/test.ts:12."

The specific identifiers in the second version are what future turns need. `HistoryCompressionStrategy` uses the configured adapter to call the model with a prompt designed to produce this kind of dense summary. The default prompt asks for facts, decisions, and specific values — customize it if your domain needs specific preservation criteria.

#### 22.3.2 Summary Chaining: Summaries of Summaries

In very long sessions, `HistoryCompressionStrategy` fires multiple times, accumulating a chain of summaries. Each subsequent compression event receives the previous summary as context and produces a new summary that incorporates both the new turns and the old summary.

Summary chaining degrades quality over many generations — the third summary of a summary of a summary has lost most of the original detail. For very long sessions (hundreds of turns), supplement rolling summaries with external memory: write key facts to a persistent store as they are discovered rather than relying on the compression chain to preserve them.

#### 22.3.3 Information Preservation Quality

Test rolling summary quality by comparing the original turns with the generated summary and checking for the presence of specific key facts:

```typescript
// Testing summary quality: verify key facts survive compression
const history = session.getHistory();
const compressedTurns = history.filter(t => t.compressed);
const summary = session.getContext().compressionSummary ?? "";

// Check that key findings from early turns appear in the summary
const expectedFacts = [
  "src/auth.ts",         // specific file path
  "SQL injection",       // vulnerability type
  "line 42",             // specific location
];

for (const fact of expectedFacts) {
  if (!summary.includes(fact)) {
    console.warn(`Key fact missing from summary: ${fact}`);
  }
}
```

Run this check on representative sessions to identify gaps in summary quality before deploying to production.

### 22.4 The Sandwich Strategy Fully Explained

#### 22.4.1 The Three Zones: Header, Body, Footer

The sandwich divides the conversation history into three zones:

**Header** (first `preserveFirst` turns): The initial session setup — system context turns, the first user message, the agent's initial response. These establish what the session is about and are typically the most important for session coherence. They should always be preserved verbatim.

**Body** (middle turns): The exploratory phase — tool calls, search results, reasoning chains that led to intermediate conclusions. These are the most compressible. Their semantic content matters; their verbatim representation typically does not.

**Footer** (last `preserveLast` turns): The current active phase — the most recent tool calls, results, and reasoning. These directly inform what happens next. They must be preserved verbatim.

#### 22.4.2 Window Size Configuration

Choose `preserveFirst` and `preserveLast` based on your session's structure:

| Session Type | `preserveFirst` | `preserveLast` |
|---|---|---|
| Short focused tasks | 2–4 | 6–10 |
| Long research tasks | 4–6 | 10–15 |
| Multi-step workflows | 4–8 | 12–20 |
| Code generation/review | 3–5 | 8–12 |

When in doubt, err toward preserving more recent context (larger `preserveLast`). The most recent turns are where the active task state lives.

#### 22.4.3 Triggering and Re-Triggering

`SandwichCompressionStrategy` fires when `tokenCount >= maxTokens * triggerThreshold`. After firing, it compresses the body and updates `ctx.compressionSummary`. The context is smaller immediately after firing.

As the session continues, context accumulates again. The strategy will fire again when the threshold is crossed. On re-triggering, the previous summary is not lost — the new summarization includes the previous summary as context, producing a updated summary that covers all prior body turns.

#### 22.4.4 Adapter Requirement (Why It Needs an LLM)

`SandwichCompressionStrategy` requires an `IProviderAdapter` to generate the body summary. This is the most significant constraint: compression is not free. Each compression event is an LLM call.

Pass a cheaper model adapter to the strategy constructor if cost is a concern. The summarization task does not require frontier model capability — a smaller, faster model generates adequate summaries at lower cost:

```typescript
// Using a small model for compression, large model for reasoning
const cheapAdapter = new OpenAICompatibleAdapter({
  apiKey: process.env.OPENAI_API_KEY!,
  defaultModel: "gpt-4o-mini",   // cheap and fast for summaries
});

const session = new SessionManager({
  adapter: mainAdapter,           // powerful model for reasoning
  model: "gpt-4o",
  maxTokens: 100_000,
  compressionStrategies: [
    new SummaryInjectionStrategy({ priority: 1 }),
    new SandwichCompressionStrategy(cheapAdapter, {  // cheap model for summaries
      priority: 20,
      preserveFirst: 4,
      preserveLast: 10,
    }),
  ],
});
```

### 22.5 Summary Injection: Continuity Without Redundancy

#### 22.5.1 Where the Summary Comes From

`SummaryInjectionStrategy` does not generate a summary. It re-injects a summary that was previously generated and stored in `ctx.compressionSummary`. The source is either a companion compression strategy (`SandwichCompressionStrategy` or `HistoryCompressionStrategy`) that populated the field, or a manually set value (for resuming a session with prior context).

This design is intentional: injection is separated from generation. You can inject a hand-written summary, a summary from a prior session, or a summary generated by a different process — not just a summary from the current session's compression.

#### 22.5.2 Where It Gets Injected

`SummaryInjectionStrategy` injects the summary as a synthetic system turn at the beginning of the turn list, with a configurable label:

```text
[Earlier conversation summary]
The agent audited /src/auth.ts and found 2 SQL injection vulnerabilities...
```

The model reads this as prior context. The label makes the provenance clear: this is a summary, not a live turn. Models handle labeled summaries more reliably than unlabeled ones.

#### 22.5.3 Keeping the Summary Current

On each turn where `shouldApply()` returns true (there is a non-empty `compressionSummary`), `SummaryInjectionStrategy` either adds a new synthetic turn or updates an existing one. It never appends a duplicate. The injected summary is always the most recent value of `ctx.compressionSummary`.

When a companion compression strategy fires and updates `compressionSummary`, the injection strategy picks up the new value on the next turn automatically. No explicit coordination is needed.

### 22.6 Composition Patterns

#### 22.6.1 Sandwich + Summary Injection

The standard production configuration. `SummaryInjectionStrategy` at priority 1 injects the accumulated summary. `SandwichCompressionStrategy` at priority 20 fires when the context reaches 80% of `maxTokens`. This covers most long-session use cases with minimal configuration.

```typescript
// Standard production compression configuration
compressionStrategies: [
  new SummaryInjectionStrategy({ priority: 1 }),
  new SandwichCompressionStrategy(adapter, {
    priority: 20,
    preserveFirst: 4,
    preserveLast: 10,
    triggerThreshold: 0.80,
  }),
],
```

#### 22.6.2 History + Summary Injection

For sessions where gradual, incremental compression is preferred over a single large compression event:

```typescript
// Smooth incremental compression for gradual growth
compressionStrategies: [
  new SummaryInjectionStrategy({ priority: 1 }),
  new HistoryCompressionStrategy(adapter, {
    priority: 30,
    windowSize: 8,
    triggerAtPercent: 0.75,
  }),
],
```

Each trigger summarizes the oldest 8 uncompressed turns. Context grows, compresses incrementally, and never has a sudden large spike in compression overhead.

#### 22.6.3 Three-Layer Compression for Very Long Tasks

For sessions expected to run 200+ turns (hours-long batch processing, exhaustive multi-file audits), layer all three strategies for defense in depth:

```typescript
// Three-layer compression for very long sessions
compressionStrategies: [
  new SummaryInjectionStrategy({ priority: 1 }),
  new HistoryCompressionStrategy(adapter, {
    priority: 20,
    windowSize: 6,
    triggerAtPercent: 0.65,
  }),
  new SandwichCompressionStrategy(adapter, {
    priority: 30,
    preserveFirst: 4,
    preserveLast: 15,
    triggerThreshold: 0.80,
  }),
],
```

`HistoryCompressionStrategy` fires first at 65% to keep context manageable incrementally. `SandwichCompressionStrategy` fires at 80% as a larger cleanup if incremental compression was not sufficient. `SummaryInjectionStrategy` ensures the accumulated summary is always visible.

### 22.7 Measuring Compression Effectiveness

#### 22.7.1 Token Reduction Ratio

The primary efficiency metric: tokens after compression divided by tokens before. A 3:1 compression ratio means the body that took 9,000 tokens is now represented in 3,000 tokens. Measure this by comparing `ctx.tokenCount` before and after a compression event.

```typescript
// Measuring compression ratio from trace events
onTrace: (event) => {
  if (event.type === "compression") {
    const before = event.metadata?.tokensBefore as number;
    const after = event.metadata?.tokensAfter as number;
    const ratio = (before / after).toFixed(1);
    console.log(`Compression ratio: ${ratio}:1`);
  }
},
```

A ratio below 2:1 suggests the compression is not worth the overhead. A ratio above 5:1 may indicate information loss. 3:1 to 4:1 is typically healthy.

#### 22.7.2 Task Completion Rate Before/After

Run your standard evaluation task set against sessions with and without compression. If task completion rate is the same, compression is preserving the information necessary for the task. If it is lower, compression is losing something critical.

This is the most important measurement because it directly tests the end-to-end impact on agent behavior.

#### 22.7.3 Goal Retention Score

A focused test: set a goal with 5 specific facts in it (file paths, values, decisions), run a session that triggers compression, then ask the agent to list the facts without using any tools. Count how many facts it retrieves correctly from the compressed context.

A perfect score means compression preserved all goal-relevant information. Scores below 80% indicate the compression is too aggressive for fact-dense sessions.

> [!TIP]
> Start with the sandwich + summary injection configuration in section 22.6.1. Measure task completion rate on representative sessions. Only add more aggressive compression or additional strategies if you are seeing context-related failures. Premature compression configuration is the second most common source of subtle agent quality problems — after insufficient compression.

---

## Key Takeaways

- Truncation is the most destructive compression — use it only as a last resort with carefully specified preservation zones (system prompt, goal, recent turns must never be truncated).
- Rolling summaries degrade in quality over multiple compression generations; for sessions longer than 200 turns, complement summaries with external memory for key facts.
- The sandwich strategy provides the best quality-to-cost trade-off for most agents: preserve the oldest and newest turns verbatim, compress the middle.
- Summary injection is the glue that makes compression useful: without it, compressed context is stored but invisible to the model.
- Measure compression effectiveness with task completion rate before/after — efficiency metrics (token reduction ratio) are necessary but not sufficient.
