---
title: "Chapter 14 — ContextManager and Context Strategies"
part: "Part III — Lemura Framework Deep Dive"
chapter: 14
page: 23
status: draft
---

*PART III — LEMURA FRAMEWORK DEEP DIVE*

## Chapter 14 — ContextManager and Context Strategies

> *"Context management is the difference between an agent that runs for five turns and one that runs for five hundred."*

> [!NOTE]
> **Chapter Goal:** By the end of this chapter, you will understand Lemura's `ContextManager`, how to compose multiple strategies, how the priority and trigger system works, and how to choose the right strategy for your use case.

---

### 14.1 The ContextManager's Job

`ContextManager` has one job: ensure that the `ContextWindow` passed to the model is within the token budget and contains the most useful information possible. It does this by running a stack of `IContextStrategy` implementations in priority order before each model call.

#### 14.1.1 Building the Message Array for Each Turn

Before `SessionManager` calls `adapter.complete()`, it calls `ContextManager.prepare(ctx, safetyMargin)`. This method iterates the registered strategies in ascending priority order, calling `shouldApply()` on each. Every strategy that returns `true` gets called with `apply()`, which receives the current `ContextWindow` and returns a modified one.

The process continues until the context is below `maxTokens * safetyMargin` (default 0.95). If a strategy fires and the context is still above the threshold, the next strategy in the priority queue gets a chance. This means strategies compose as a fallback chain: a lighter strategy fires first, and a more aggressive one fires only if the lighter one was insufficient.

#### 14.1.2 Deciding When and How to Compress

`shouldApply()` is each strategy's self-evaluation function. It receives the current `ContextWindow` and returns a boolean. `SandwichCompressionStrategy.shouldApply()` checks whether `tokenCount >= maxTokens * triggerThreshold`. `HistoryCompressionStrategy.shouldApply()` checks the same ratio using its `triggerAtPercent`.

A strategy that reports `false` from `shouldApply()` is skipped entirely on that turn — no work is done. This means compression is not called on every turn, only when thresholds are crossed. The common case (context well within budget) has zero overhead.

### 14.2 The `IContextStrategy` Interface

Every compression strategy implements `IContextStrategy`, defined in `src/types/context.ts`:

```typescript
// The IContextStrategy contract every compression strategy must implement
import { IContextStrategy, ContextWindow } from "lemura/types";

interface IContextStrategy {
  name: string;
  priority: number;        // lower runs first
  shouldApply(ctx: ContextWindow): boolean;
  apply(ctx: ContextWindow): Promise<ContextWindow>;
}
```

#### 14.2.1 `priority`: Execution Order

Lower priority numbers run first. `SummaryInjectionStrategy` defaults to priority 1 because it must always run before any compression strategy. Compression strategies default to 20–30.

When writing a custom strategy, choose a priority that places it in the right position relative to built-in strategies. A pre-processing strategy that limits tool result sizes (before compression is needed) might run at priority 5. A last-resort truncation fallback might run at priority 100.

#### 14.2.2 `triggerThreshold`: When to Fire

The threshold is expressed as a fraction of `maxTokens` in the `shouldApply()` method. Strategies are responsible for their own trigger logic — the `ContextManager` does not impose a global threshold. This allows each strategy to have its own sensitivity: a lightweight strategy can fire early at 70%, while an expensive LLM-call strategy fires only at 85%.

#### 14.2.3 `compress()`: The Core Method

The `apply()` method receives the full `ContextWindow` and returns a new `ContextWindow`. The contract is simple: return a context window that either has fewer tokens or has restructured content that will result in fewer tokens when serialized. The method is `async` because most meaningful compression involves an LLM call.

Strategies must not mutate the input `ContextWindow` in place. Return a new object (use spread syntax or `Object.assign`) to avoid corrupting the session's state.

#### 14.2.4 Returning a Compressed Result

The returned `ContextWindow` should always include a `compressionSummary` field if the strategy performed lossy compression. This field is what `SummaryInjectionStrategy` reads and re-injects. Without it, the compressed content is simply gone from the model's view.

### 14.3 Strategy Composition

#### 14.3.1 Running Multiple Strategies

Configure multiple strategies in `SessionConfig.compressionStrategies`:

```typescript
// Composing three strategies: inject, sandwich, and rolling history
import {
  SandwichCompressionStrategy,
  HistoryCompressionStrategy,
  SummaryInjectionStrategy,
} from "lemura/context";

const session = new SessionManager({
  adapter,
  model: "gpt-4o-mini",
  maxTokens: 128_000,
  compressionStrategies: [
    new SummaryInjectionStrategy({ priority: 1 }),
    new SandwichCompressionStrategy(adapter, {
      priority: 20,
      preserveFirst: 4,
      preserveLast: 10,
      triggerThreshold: 0.80,
    }),
    new HistoryCompressionStrategy(adapter, {
      priority: 30,
      windowSize: 6,
      triggerAtPercent: 0.90,
    }),
  ],
});
```

Here, `SummaryInjectionStrategy` (priority 1) runs on every turn that has a summary to inject. `SandwichCompressionStrategy` (priority 20) fires at 80% of `maxTokens`. If the sandwich compression does not bring the context below the threshold (unusual but possible with very large tool results), `HistoryCompressionStrategy` (priority 30) fires at 90% as an additional pass.

#### 14.3.2 How Priority Determines Order

Strategies run in ascending priority order. Lower numbers run first. After each strategy that reports `shouldApply() === true` and fires, `ContextManager` rechecks whether the budget is now satisfied. If it is, subsequent strategies are skipped even if they would have fired.

This means: put cheap, lightweight strategies at lower priority numbers (they run first and often solve the problem without needing the expensive ones); put expensive LLM-call strategies at higher priority numbers (they only run when cheaper approaches were insufficient).

#### 14.3.3 Chaining vs. Fallback

Strategies can be designed to always cooperate (chaining) or to act as fallbacks. `SummaryInjectionStrategy` is a cooperating strategy — it does not reduce context size, it just ensures the summary is visible. It always fires when there is a summary, regardless of context size. Compression strategies are fallbacks — they fire when the context is too large.

You can design custom strategies for either pattern. A strategy that always fires (returning `true` from `shouldApply`) and does lightweight work is a cooperating strategy. A strategy with a threshold in `shouldApply` is a fallback.

### 14.4 `SandwichCompressionStrategy` In Depth

#### 14.4.1 The Sandwich Explained

The sandwich strategy preserves the first `preserveFirst` turns and the last `preserveLast` turns verbatim. The turns in between are passed to an LLM call that generates a compressed summary. The summary is stored in `ctx.compressionSummary`, and the middle turns are removed from the `turns` array.

The preserved beginning typically contains the initial setup turns — the first user message, any system-level tool calls, and the agent's initial response. The preserved end contains the most recent activity — the turns that directly inform the model's next action. The compressed middle is the part that the model would attend to least anyway.

#### 14.4.2 Configuration Options

| Field | Default | Purpose |
|-------|---------|---------|
| `preserveFirst` | required | Number of oldest turns to keep verbatim |
| `preserveLast` | required | Number of newest turns to keep verbatim |
| `triggerThreshold` | `0.80` | Fire when context reaches this fraction of `maxTokens` |
| `summaryMaxTokens` | unlimited | Cap on the generated summary length |
| `priority` | `20` | Execution order in the strategy stack |

For most agents, `preserveFirst: 4` and `preserveLast: 10` are good starting values. Increase `preserveLast` if your agent's tool calls produce long result chains where 10 turns is not enough recent context. Increase `preserveFirst` if your agent has an extended setup phase that must remain visible.

#### 14.4.3 When to Use It

Use `SandwichCompressionStrategy` when:
- Your sessions have a mix of setup turns (that need to be preserved) and exploratory middle turns (that are compressible)
- Tool results vary dramatically in size and you want one compression event to handle a large spike
- You need to preserve the goal and plan (which appear in the earliest turns) along with the most recent state

### 14.5 `HistoryCompressionStrategy` In Depth

#### 14.5.1 Rolling Window Summarization

`HistoryCompressionStrategy` takes a different approach: instead of one large compression event, it compresses incrementally. On each trigger, it summarizes the oldest `windowSize` uncompressed turns. Subsequent triggers summarize the next oldest window, accumulating the summary across multiple compression events.

This produces a gradually shrinking history rather than a sudden jump. The session always has a rolling summary of everything that happened before the most recent turns.

#### 14.5.2 Summary Quality and Length

The quality of rolling summaries depends on the model used for summarization. A stronger model produces more reliable summaries that preserve critical facts. A weaker model may drop important identifiers or mischaracterize tool results.

For sessions where the details of tool results matter (file paths, query results, specific values), use a capable model for the `HistoryCompressionStrategy` adapter argument. For sessions where only the semantic content of what happened matters, a smaller model is sufficient and cheaper.

#### 14.5.3 When to Use It

Use `HistoryCompressionStrategy` when:
- Your sessions grow gradually and you want smooth, incremental compression
- The distinction between "beginning of session" and "middle of session" is not meaningful for your task
- You prefer gradual quality degradation over sudden compression events

### 14.6 `SummaryInjectionStrategy` In Depth

#### 14.6.1 Re-injecting Compressed Summaries

`SummaryInjectionStrategy` reads `ctx.compressionSummary` and injects it as a synthetic system turn at the beginning of the turn list. Without this strategy, compression summaries are stored in the `ContextWindow` but never appear in the message array the model sees.

This strategy is always required when using any compression strategy that stores output in `compressionSummary`. Configuring `SandwichCompressionStrategy` without `SummaryInjectionStrategy` means the model has no access to the compressed history — the turns are gone and the summary is invisible.

#### 14.6.2 Keeping the Summary Fresh

Each time `SandwichCompressionStrategy` or `HistoryCompressionStrategy` fires, it updates `ctx.compressionSummary` with a new value. `SummaryInjectionStrategy` picks this up on the next turn and injects the updated summary. The injected summary is always the most recent compression output.

`SummaryInjectionStrategy` is idempotent: if a summary turn already exists at the top of the turn list, it updates it in place rather than appending a second one. You will never end up with duplicate summary turns.

#### 14.6.3 When to Use It

Always use `SummaryInjectionStrategy` when using `SandwichCompressionStrategy` or `HistoryCompressionStrategy`. Set its priority to 1 (or any value lower than the companion compression strategy) so it runs before compression on turns where both fire.

### 14.7 Building a Custom Strategy

#### 14.7.1 Implementing `IContextStrategy`

A custom strategy that limits tool result sizes to a token budget — preventing the tool result explosion before it requires full compression:

```typescript
// Custom strategy: cap individual tool results at a token budget
import { IContextStrategy, ContextWindow } from "lemura/types";

export class ToolResultCapStrategy implements IContextStrategy {
  readonly name = "tool_result_cap";
  readonly priority = 5; // runs before any compression strategy

  constructor(private readonly maxTokensPerResult: number) {}

  shouldApply(ctx: ContextWindow): boolean {
    return ctx.turns.some(
      (t) => t.role === "tool" && t.tokenCount > this.maxTokensPerResult
    );
  }

  async apply(ctx: ContextWindow): Promise<ContextWindow> {
    const updated = ctx.turns.map((turn) => {
      if (turn.role !== "tool" || turn.tokenCount <= this.maxTokensPerResult) {
        return turn;
      }
      const budget = this.maxTokensPerResult * 4; // rough char estimate
      const content =
        typeof turn.content === "string"
          ? turn.content.slice(0, budget) + "\n[truncated]"
          : turn.content;
      return { ...turn, content, tokenCount: this.maxTokensPerResult };
    });

    const newCount = updated.reduce((s, t) => s + t.tokenCount, 0);
    return { ...ctx, turns: updated, tokenCount: newCount };
  }
}
```

#### 14.7.2 Testing Your Strategy

Test each strategy in isolation with a synthetic `ContextWindow`:

```typescript
// Unit test for ToolResultCapStrategy
import { ToolResultCapStrategy } from "./ToolResultCapStrategy";

const strategy = new ToolResultCapStrategy(500);

const oversizedContext: ContextWindow = {
  systemPrompt: "You are a test agent.",
  scratchpad: "",
  compressionSummary: undefined,
  metadata: {},
  maxTokens: 10_000,
  tokenCount: 9_500,
  turns: [{
    role: "tool", content: "x".repeat(10_000),
    tokenCount: 2_500, turnIndex: 0, compressed: false,
  }],
};

const result = await strategy.apply(oversizedContext);
console.assert(result.turns[0].tokenCount === 500);
```

Always test both the happy path (strategy reduces context as expected) and edge cases (context with no oversized results should be returned unchanged by `shouldApply`).

### 14.8 Strategy Selection Guide

| Scenario | Recommended Strategy |
|---|---|
| Short tasks (< 20 turns) | None needed |
| Long research tasks | `HistoryCompressionStrategy` |
| Tasks with large tool outputs | `SandwichCompressionStrategy` |
| Both | Compose both |
| Returning to a previous session | `SummaryInjectionStrategy` |

For most production agents, the right starting configuration is `SummaryInjectionStrategy` at priority 1 paired with `SandwichCompressionStrategy` at priority 20. Add `HistoryCompressionStrategy` at priority 30 if you see the sandwich triggering too infrequently (long sessions with gradual growth) or if you want smoother incremental compression. Add a custom `ToolResultCapStrategy` at priority 5 if individual tool results regularly exceed 1,000 tokens.

---

## Key Takeaways

- `ContextManager.prepare()` runs configured strategies in ascending priority order before each model call; strategies that report `shouldApply() === false` are skipped with no overhead.
- Always pair `SummaryInjectionStrategy` (priority 1) with any compression strategy that writes to `ctx.compressionSummary` — without it, the summary is generated but never visible to the model.
- `SandwichCompressionStrategy` preserves the oldest and newest turns, compresses the middle — best for sessions with distinct setup, exploratory, and conclusion phases.
- `HistoryCompressionStrategy` compresses incrementally with a rolling window — better for sessions where context grows gradually and you want smooth degradation.
- Custom strategies should implement `IContextStrategy`, return a new `ContextWindow` without mutating the input, and be tested in isolation with synthetic context fixtures.
