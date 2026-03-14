---
title: "Chapter 7 — Context: The Agent's Working Memory"
part: "Part II — Architecture Fundamentals"
chapter: 7
page: 15
status: draft
---

*PART II — ARCHITECTURE FUNDAMENTALS*

## Chapter 7 — Context: The Agent's Working Memory

> *"Context is not just what the model sees. It's everything the agent knows about the world right now."*

> [!NOTE]
> **Chapter Goal:** By the end of this chapter, you will understand what constitutes an agent's context, how the context window works and fails, the different types of context content, and how to architect context management to avoid the most common and costly failures.

---

### 7.1 What Is Context?

#### 7.1.1 The Message Array: The Raw Representation

From the provider's perspective, context is a message array — a list of message objects, each with a role and content. The roles are `system`, `user`, `assistant`, and `tool`. The array is passed to the model on every call, and the model processes the entire array to generate its response. There is no memory outside this array except what you implement explicitly.

This is the most important architectural fact about language model agents: the model sees only what is in the array. Anything not in the array does not exist for the model on that turn. Information that was in the array two turns ago but has been truncated is gone. A goal stated in turn 1 that was compressed out of the context by turn 30 is effectively forgotten.

The message array is the agent's entire working memory. Managing it well is the central engineering challenge of production agent development.

#### 7.1.2 System Prompt vs. Conversation History

The message array has two logical sections that behave differently. The system prompt (one or more `system` role messages at the top of the array) contains durable instructions: the agent's persona, its rules of operation, its goal, and any constraints. The conversation history (the interleaved `user`, `assistant`, and `tool` messages below) contains the transient record of what has happened in the session.

The system prompt is the agent's constitution. It should contain only what must be true for every turn of the session. It should not contain information that changes with session state. Putting dynamic information in the system prompt causes stale information to persist longer than it should.

The conversation history is compressible. The system prompt generally is not — compressing it risks losing critical operating instructions. This distinction is the basis of the sandwich compression pattern: preserve the system prompt and recent history, compress the middle.

#### 7.1.3 Tool Definitions and Their Token Cost

Tool definitions are not free. Every tool definition is serialized as JSON Schema and included in the provider request. A tool with a detailed description and several parameters may cost 150–300 tokens. A session with 20 tools pays 3,000–6,000 tokens per call just for the tool definitions — before any conversation history.

This cost is invisible in simple setups but becomes significant at scale. Trim tool definitions to the minimum. Do not include optional parameters unless they are commonly used. Remove tools that are no longer relevant as the session progresses. At high session volume, reducing the tool definition token cost by 1,000 tokens per call translates directly into reduced cost and faster response times.

### 7.2 The Context Window: Physical Limits and Real Behavior

#### 7.2.1 Token Counting: It's Never What You Expect

A token is not a word. Depending on the tokenizer, "engineering" might be one token or two. Camelcase identifiers often tokenize differently from their snake_case equivalents. JSON structure characters (braces, quotes, commas) all cost tokens. Code-heavy contexts tokenize less efficiently than prose.

The practical implication: never estimate context size in words or lines. Always measure in tokens. Lemura's `adapter.estimateTokens(text)` provides a fast estimate. Use it when designing tool output structures to verify that your expected outputs stay within budget.

The estimate from most tokenizer approximations is within 10% of the actual count for typical prose and code. For precise measurement — important when designing compression triggers — prefer the provider's exact token counting endpoint if one is available.

#### 7.2.2 The Lost-in-the-Middle Problem

Research on long-context language models consistently finds that models pay more attention to content near the beginning and end of the context array than to content in the middle. Information buried in the middle — including tool results from several turns ago or instructions given partway through the session — is retrieved less reliably than information at the edges.

This has a direct design implication: the most important information belongs at the beginning (system prompt) or the end (most recent turn). Goal statements, operating constraints, and critical intermediate results should not be allowed to drift into the middle of the context. Goal injection — re-surfacing the goal at regular intervals — is one mechanism for keeping it salient.

#### 7.2.3 Attention Degradation Over Long Contexts

Beyond lost-in-the-middle, models exhibit general attention degradation over very long contexts. Instructions are followed less consistently. Tool call formatting becomes less reliable. The model may generate responses that are internally consistent but inconsistent with instructions given earlier in the session.

This is not a model bug to be fixed — it is a characteristic of transformer attention that improves incrementally with each model generation but is not eliminated. It is a design constraint: agent sessions that must maintain high reliability over many turns need context management strategies to keep the effective context length manageable, even when the raw window is large.

### 7.3 Anatomy of a Well-Structured Context

#### 7.3.1 The System Prompt Layer

The system prompt layer contains the durable operating context: the agent's purpose, its constraints, its persona, and its tool usage guidelines. It is the first thing the model sees and it frames everything that follows.

A well-structured system prompt has a clear hierarchy: who the agent is, what it is trying to achieve in this session type, what tools it has and when to use each, what it should never do, and how it should format its outputs. Separate these concerns into labeled sections within the prompt. Models parse labeled sections more reliably than undifferentiated prose.

Keep the system prompt under 1,000 tokens for most agents. Every token in the system prompt is paid on every turn. A 2,000-token system prompt costs an extra 40,000 tokens over a 20-turn session compared to a 1,000-token system prompt.

#### 7.3.2 The Goal and Plan Layer

When the session has an explicit goal set via `session.setGoal()`, Lemura's `GoalInjector` injects a formatted goal block into the context according to the configured injection frequency. This goal block sits between the system prompt and the conversation history, or is prepended to the current user turn, depending on the `injectionPosition` setting.

The goal layer is what prevents goal drift in long sessions. Without it, the original goal may be 50 turns back in the conversation history — effectively invisible to attention — while the model is focused on the most recent tool results. Goal injection keeps the original intent as a prominent signal throughout the session.

#### 7.3.3 The Conversation History Layer

The conversation history is the largest and most dynamic part of the context. Every turn adds to it: user messages, assistant responses, tool calls, and tool results. In a 20-turn session with tool-heavy turns, this layer can easily reach 30,000–50,000 tokens.

Good context architecture is designed around the fact that this layer must be compressible without losing information that is critical to the session's success. Compression strategies operate on this layer. Critical information — goal, key discoveries, decisions made — should be either preserved outside this layer or explicitly marked as important when summarizing.

#### 7.3.4 The Tool Results Layer

Tool results exist within the conversation history as `tool` role messages. They are often the single largest contributor to context growth. A session that calls 30 tools with an average result of 1,000 tokens adds 30,000 tokens of tool results before any other content.

Tool result management has two components: at the tool design level, returning only what the model needs; at the compression level, summarizing or discarding old tool results that are no longer relevant. Both are necessary. Tool design sets the per-call cost; compression sets the accumulation rate.

### 7.4 Context Growth Over Time

#### 7.4.1 How Fast Does Context Grow?

Context growth is approximately linear in turns, but the coefficient varies enormously by tool set. A text-only session where the model reasons without calling tools adds roughly 200–500 tokens per turn. A tool-heavy session where each turn includes a tool call with a 2,000-token result adds 2,500–4,000 tokens per turn.

For practical planning: a 20-turn session with moderate tool use (1,500 tokens average tool result per turn) consumes roughly 40,000 tokens of context. At 40 turns, that doubles. At 60 turns, a 128K context window starts to fill. These numbers are illustrative but close enough for initial capacity planning.

#### 7.4.2 The Tool Result Explosion Problem

The most severe context growth cases come from search and retrieval tools that return large payloads. A web search tool that returns the full text of three web pages may add 15,000 tokens in a single turn. A code analysis tool that returns the full output of a static analyzer may add 5,000 tokens. A database query that returns 1,000 rows may add 10,000 tokens.

These are not edge cases — they are the natural behavior of tools designed without token efficiency in mind. Preventing the tool result explosion requires designing every tool with a `maxTokens` return budget and summarizing or paginating results that would exceed it.

#### 7.4.3 When Context Becomes an Anchor, Not a Memory

There is a subtler failure mode beyond exhaustion: the context becomes so long that the model spends most of its attention on old, irrelevant content rather than on the current task. The context is technically within the window limit, but the signal-to-noise ratio has collapsed. Old tool results, superseded decisions, and abandoned approaches all contribute noise that degrades the quality of reasoning on the current turn.

This is the case for aggressive compression even before the context window is full. The goal is not to use as much of the context window as possible; it is to have the most relevant information as efficiently represented as possible. Compression that removes irrelevant old content improves reasoning quality even if the context was not approaching its limit.

### 7.5 Context Management Strategies (Preview)

This section introduces the strategies covered in depth in **Chapter 9 — Compression: The Hidden Challenge**. The preview here establishes why each exists.

#### 7.5.1 Truncation

Truncation removes messages from the beginning of the conversation history when the context exceeds a threshold. It is the simplest strategy and the most destructive. The model loses access to everything that was removed. Initial instructions, early discoveries, and the context of decisions made early in the session are all gone.

Truncation is appropriate as a last-resort safety net — the strategy that fires if everything else fails — but not as a primary compression approach.

#### 7.5.2 Summarization

Summarization replaces a window of messages with a generated summary. The summary is an LLM call itself, adding latency and cost, but preserving the semantic content of the compressed turns. A well-generated summary captures key facts, decisions, and outcomes in 10–20% of the original token count.

The risk is information loss. Summaries inevitably lose detail. For most agent tasks, losing detail about the reasoning behind a tool call is acceptable. Losing the result of a critical tool call — a file path that will be used later, a key fact that must be cited in the output — is not.

#### 7.5.3 Compression

Compression in the Lemura sense refers to the combined pattern of summarization + selective preservation: keep the beginning (system prompt, goal) and the end (recent turns), summarize the middle, and inject the summary as a synthetic message at the top of the history so the model always has access to it. This is the sandwich pattern.

#### 7.5.4 External Memory with Retrieval

For sessions that must span very long horizons — hours, multiple sessions, or more turns than any context window can hold — external memory with retrieval augments the context window with a long-term store. Facts from old sessions are stored in a vector database or structured store and retrieved on demand when relevant.

This adds significant engineering complexity: embedding generation, retrieval quality evaluation, storage management, and retrieval latency. It is the right choice for genuinely long-horizon agents but overkill for most task-completion agents with bounded session lengths.

### 7.6 Context in Lemura: The ContextManager

#### 7.6.1 The IContextStrategy Interface

`ContextManager` is Lemura's context management system. It maintains the `ContextWindow` — the full state of the context including turns, system prompt, scratchpad, and compression summary — and applies configured compression strategies before each provider call.

Each compression strategy implements `IContextStrategy`:

```typescript
// Implementing a custom context strategy
import { IContextStrategy, ContextWindow } from "lemura/types";

class MaxToolResultSizeStrategy implements IContextStrategy {
  readonly name = "max_tool_result_size";
  readonly priority = 5; // runs early, before summarization

  constructor(private readonly maxTokensPerResult: number) {}

  shouldApply(ctx: ContextWindow): boolean {
    // Check if any tool result exceeds the budget
    return ctx.turns.some(
      (t) => t.role === "tool" && t.tokenCount > this.maxTokensPerResult
    );
  }

  async apply(ctx: ContextWindow): Promise<ContextWindow> {
    // Truncate oversized tool results to the budget
    const updated = ctx.turns.map((t) => {
      if (t.role !== "tool" || t.tokenCount <= this.maxTokensPerResult) return t;
      const truncated =
        typeof t.content === "string"
          ? t.content.slice(0, this.maxTokensPerResult * 4) + "\n[... truncated]"
          : t.content;
      return { ...t, content: truncated, tokenCount: this.maxTokensPerResult };
    });
    return { ...ctx, turns: updated };
  }
}
```

#### 7.6.2 Priority-Based Strategy Selection

Multiple strategies can be configured on a session. They run in priority order: lower priority numbers run first. `SummaryInjectionStrategy` at priority 1 always runs before any compression strategy, ensuring the accumulated summary is visible in the context before the model is called. Compression strategies run at higher priority numbers (20–30) and fire when their `shouldApply` condition is met.

The priority system allows composing strategies that work together: inject the summary first, then check if compression is needed, then apply it if so. Each strategy sees the context as modified by earlier strategies — they compose correctly as long as their priorities are set correctly.

#### 7.6.3 Trigger Thresholds and When Compression Fires

Each compression strategy defines its own trigger condition in `shouldApply`. `SandwichCompressionStrategy` fires when the context exceeds a fraction of `maxTokens` (default 80%). `HistoryCompressionStrategy` fires at a configured percentage threshold.

Setting the threshold too high (firing at 95%) leaves little room for the current turn's output and risks hitting the hard limit. Setting it too low (firing at 50%) wastes compression overhead on sessions that would have stayed well within budget. A threshold of 75–80% is a good starting point for most agents; adjust based on observed turn-by-turn context growth for your specific tool set.

---

## Key Takeaways

- The message array is the agent's entire working memory — the model sees only what is in the array on each call; anything removed or never added does not exist for the model.
- The context window has physical limits and behavioral limits: the lost-in-the-middle problem and attention degradation over long contexts degrade performance well before the hard token limit is reached.
- A well-structured context has four layers: system prompt (durable instructions), goal and plan (injected to prevent drift), conversation history (compressible), and tool results (the primary driver of context growth).
- Tool results are the main source of context explosion; every tool should return only what the model needs, structured as named JSON fields, with large results summarized before returning.
- Lemura's `ContextManager` applies `IContextStrategy` implementations in priority order before each provider call; `SummaryInjectionStrategy` at priority 1 ensures the accumulated compression summary is always visible.
