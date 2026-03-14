---
title: "Chapter 20 — Memory Architecture for Long-Running Agents"
part: "Part IV — Memory and State"
chapter: 20
page: 30
status: draft
---

*PART IV — MEMORY AND STATE*

## Chapter 20 — Memory Architecture for Long-Running Agents

> *"The context window is RAM. Summary memory is a cache. External storage is disk. Use them at the right layer."*

> [!NOTE]
> **Chapter Goal:** By the end of this chapter, you will understand the three tiers of agent memory, how to architect memory systems for agents that run for hours or days, and how to integrate external memory stores with Lemura sessions.

---

### 20.1 Why Single-Context Memory Fails for Long Tasks

#### 20.1.1 The Physical Limit

The context window is a fixed-size buffer. Even the largest context windows available today — 200K, 1M tokens — have hard limits. A session that generates 2,000 tokens of context per turn will fill a 200K window in 100 turns. An agent working a 500-step research task with tool calls cannot fit its entire history in any currently available context window.

The common response is to compress. Compression helps. But compression is lossy, and there is a limit to how much can be compressed before the agent loses the thread of what it was doing. Beyond that limit, you need a different architecture.

#### 20.1.2 The Degradation Problem

Even before the hard limit, quality degrades. As described in **Chapter 7 — Context: The Agent's Working Memory**, attention degrades over long contexts. Instructions given in turn 1 have lower effective weight at turn 100. Tool results from turn 5 may be effectively invisible by turn 50. The model is not ignoring them — it simply cannot attend to everything in a very long context equally.

This degradation means that even a session that stays within the context window will produce lower-quality results at turn 100 than at turn 10. Memory architecture is also about quality, not just survival: keeping the most relevant information actively present rather than buried in a long, noisy history.

#### 20.1.3 The Cost Problem

Token cost scales linearly with context size on every model call. A session at turn 100 with 80,000 tokens of context costs 8x more per model call than a session at turn 10 with 10,000 tokens. For an agent running 24 hours with 1,000 tool calls, context cost dominates the total expense.

Memory architecture that keeps the active context lean — offloading to compression and external storage — directly reduces per-call cost. This is not an optimization for edge cases; it is the difference between an economically viable production agent and one that cannot be run at scale.

### 20.2 The Three-Tier Memory Architecture

The memory hierarchy has three tiers, each with different speed, cost, capacity, and lossiness characteristics. Good memory architecture uses each tier for what it is good at.

#### 20.2.1 Tier 1: In-Context Memory (Working Memory)

In-context memory is what the model sees on the current call: system prompt, goal block, recent turns, active tool results. It is fast (no retrieval needed), expensive (every token is billed), and limited (bounded by `maxTokens`).

The in-context tier should contain only what the model needs right now: the current goal and plan, the most recent tool results, the most recent reasoning, and any facts that are being actively used in the current step. Everything else belongs in a lower tier.

#### 20.2.2 Tier 2: Summary Memory (Compressed Cache)

Summary memory is the accumulated compression of what happened in earlier turns. It is stored in `ctx.compressionSummary` and re-injected by `SummaryInjectionStrategy` on each turn. It is cheaper than raw context (compressed representations are much smaller than originals), partially lossy (details are lost in summarization), and unlimited in principle (you can accumulate summaries indefinitely).

The summary tier is the primary mechanism for maintaining long-session coherence. A well-generated summary captures the semantic content of past turns — what was decided, what was found, what was tried — without the token cost of preserving every detail.

#### 20.2.3 Tier 3: External Memory (Persistent Store)

External memory is everything outside the process: vector databases, key-value stores, file systems, relational databases, structured session logs. It is slow (requires a retrieval step), theoretically lossless (full content is preserved), and unlimited in capacity.

External memory enables two capabilities that the other tiers cannot: retrieving specific facts from very long histories without putting the entire history in context, and sharing memory across sessions (session A can retrieve notes written by session B).

### 20.3 What Goes in Each Tier

#### 20.3.1 In-Context: Goals, Recent History, Active Tool Results

The in-context tier should contain:
- The system prompt and skill content (always present)
- The current goal and plan state (always present, injected by `GoalInjector`)
- The most recent N turns (preserved by compression strategies)
- Any identifiers or facts that will be used in the current or next tool call

The in-context tier should not contain:
- Full results from tool calls made 20 turns ago
- Detailed reasoning from early turns that led to completed sub-goals
- Raw data that has already been processed

#### 20.3.2 Summary: Compressed History, Completed Step Summaries

The summary tier should contain:
- A compressed representation of all turns that were removed from in-context memory
- The key facts, decisions, and findings from those turns
- The status of completed sub-goals

A good summary is dense with facts: identifiers, conclusions, values found. A poor summary is dense with process: "I then called the search tool, which returned results, and I analyzed them." The process is implied by the fact that the agent is still running; the facts are what need to be preserved.

#### 20.3.3 External: All History, Artifacts, Structured Data

The external tier should contain:
- The complete session history (for audit, debugging, and resumption)
- Artifacts produced by the agent (generated files, reports, analysis outputs)
- Structured data retrieved during the session that may be needed again
- Cross-session knowledge (facts that are relevant across multiple sessions on the same domain)

### 20.4 External Memory Integration

#### 20.4.1 Vector Stores for Semantic Retrieval

A vector store enables semantic retrieval: given a query, find the stored content most semantically similar to the query. For agents that must retrieve specific facts from a large corpus — past session outputs, domain documentation, a knowledge base — vector retrieval is the right mechanism.

The integration pattern in Lemura uses `IRAGAdapter` (see `src/types/rag.ts`). Implement the adapter for your vector store and pass it to `SessionConfig.ragAdapter`. Tools that need semantic retrieval receive the adapter through `ToolContext.ragAdapter`.

#### 20.4.2 Key-Value Stores for Structured State

Key-value stores are appropriate for structured state that is looked up by exact key: session checkpoints, configuration values, computed aggregates. Redis is the common choice for session state that needs fast access; PostgreSQL JSON columns work well for persistent structured state.

Lemura's `IScratchpadAdapter` interface (see `src/types/storage.ts`) is the integration point for persistent scratchpad storage across session turns:

```typescript
// Custom Redis scratchpad adapter for cross-session persistence
import { IScratchpadAdapter } from "lemura/types";
import { createClient } from "redis";

class RedisScratchpadAdapter implements IScratchpadAdapter {
  private client = createClient({ url: process.env.REDIS_URL });

  async read(sessionId: string): Promise<string | undefined> {
    await this.client.connect().catch(() => {}); // idempotent
    return (await this.client.get(`scratchpad:${sessionId}`)) ?? undefined;
  }

  async write(sessionId: string, content: string): Promise<void> {
    await this.client.connect().catch(() => {});
    await this.client.set(`scratchpad:${sessionId}`, content);
  }

  async clear(sessionId: string): Promise<void> {
    await this.client.connect().catch(() => {});
    await this.client.del(`scratchpad:${sessionId}`);
  }
}
```

#### 20.4.3 File Systems for Artifacts

Artifacts produced by the agent — generated reports, modified code files, exported data — should be written to persistent storage by the tools that produce them. The agent does not need to keep artifact content in context after writing it; it only needs the path or identifier to reference it in future tool calls or in the final output.

Design artifact-producing tools to return lightweight references, not artifact content:

```typescript
// Tool that writes an artifact and returns only the reference
async execute(params) {
  const content = generateReport(params.data);
  const path = `/artifacts/${params.reportId}.md`;
  await fs.writeFile(path, content);
  return { status: "written", path, bytes: content.length };
  // Not: return { content } — no need to hold 10,000 tokens in context
}
```

### 20.5 Memory Retrieval Strategies

#### 20.5.1 Recency-Based Retrieval

The simplest retrieval strategy: always keep the most recent N items. This is what `SandwichCompressionStrategy` implements for in-context memory — preserve the last `preserveLast` turns verbatim. Recency-based retrieval is appropriate when the most recent context is almost always the most relevant.

#### 20.5.2 Relevance-Based Retrieval (RAG)

Retrieval-augmented generation (RAG) retrieves content based on semantic similarity to the current task. It is more sophisticated than recency but adds latency (embedding generation + vector search) and requires that the stored content be embedded in advance.

RAG is appropriate when:
- The knowledge corpus is large and static (documentation, codebases)
- Recency is not a reliable proxy for relevance
- The agent needs to reference information from much earlier in a long session

#### 20.5.3 Entity-Based Retrieval

Entity-based retrieval stores and retrieves information keyed to entities — file names, function names, issue IDs, person names. When the agent encounters an entity in its current task, it retrieves the stored knowledge about that entity.

This pattern is effective for agents working on large codebases or complex domains where the same entities appear across many turns. Storing per-entity notes in a key-value store and retrieving them when the entity is mentioned is simpler and more reliable than semantic search for this use case.

### 20.6 Memory Consistency

#### 20.6.1 The Write-After-Read Problem

Memory consistency becomes an issue when multiple agents (or multiple sessions of the same agent) share external memory. Agent A reads a value, makes a decision based on it, then writes an updated value. Agent B reads the same value in the window between Agent A's read and write. Agent B's decision is based on stale data.

For most agent workloads, this is manageable with simple strategies: use optimistic locking (include a version field in stored values and reject writes with wrong version), partition memory by session ID (no sharing), or accept eventual consistency for non-critical state.

#### 20.6.2 Keeping Tiers in Sync

When a compression event moves content from in-context to summary memory, the in-context tier and the summary tier can temporarily diverge. `SummaryInjectionStrategy` closes this gap by re-injecting the summary on the next turn, but there is always one turn where the compressed content is gone and the summary has not yet been re-injected.

Design compression triggers to avoid firing mid-step: ideally, compression fires at the end of a ReAct turn, after the model has produced its response, not in the middle of a tool result chain.

#### 20.6.3 Memory Invalidation

Facts stored in external memory become stale. A file path stored in the vector database may no longer exist. A cached API response may be outdated. An entity's known status may have changed.

Include timestamps on stored memory entries. When retrieving, check whether the entry is within an acceptable staleness window. For entries that may change, implement a `refresh()` path in the retrieval tool that verifies the stored fact before returning it.

### 20.7 Implementing a Memory Tool in Lemura

#### 20.7.1 `remember()` and `recall()` Tool Pattern

The simplest external memory integration is a pair of tools: `remember` stores a fact, `recall` retrieves it. The model calls `remember` when it discovers something it will need later and calls `recall` when it needs to access a previously stored fact.

```typescript
// Simple in-session key-value memory tools
import { IToolDefinition } from "lemura/types";

const store = new Map<string, string>();

const rememberTool: IToolDefinition = {
  name: "remember",
  description: "Store a fact for later recall. Use for file paths, " +
               "identifiers, and decisions that will be needed in later steps.",
  parameters: {
    type: "object",
    properties: {
      key:   { type: "string", description: "A short identifier for the fact" },
      value: { type: "string", description: "The fact to remember" },
    },
    required: ["key", "value"],
  },
  async execute(params) {
    const { key, value } = params as { key: string; value: string };
    store.set(key, value);
    return { stored: key };
  },
};

const recallTool: IToolDefinition = {
  name: "recall",
  description: "Retrieve a previously stored fact by its key.",
  parameters: {
    type: "object",
    properties: {
      key: { type: "string", description: "The key used when storing the fact" },
    },
    required: ["key"],
  },
  async execute(params) {
    const { key } = params as { key: string };
    const value = store.get(key);
    return value
      ? { key, value }
      : { error: true, message: `No fact stored for key: ${key}` };
  },
};
```

For production use, replace the in-process `Map` with a persistent adapter (`RedisScratchpadAdapter`, a database, or a file) so facts survive session restarts.

#### 20.7.2 Integrating with ContextManager

Lemura's built-in short-term memory (STM) tools integrate directly with the context system when `stmRegistry` is provided in `SessionConfig`. The STM tools (`read_chunk`, `search_chunk`, `write_scratchpad`, etc.) use the session's `ShortTermMemoryRegistry` as their storage backend and are automatically registered when the registry is configured.

> [!TIP]
> For agents that need to pass specific values between steps (file paths, IDs, query results), use `ContinuationPlanner`'s `outputKey` and `inputMapping` first — it is the right tool for structured data flow within a single session plan. Use `remember`/`recall` tools for ad-hoc facts that arise outside the plan structure.

---

## Key Takeaways

- The three-tier memory hierarchy maps to different trade-offs: in-context (fast, expensive, limited), summary (medium cost, lossy, unlimited), external (slow, lossless, unlimited) — use each tier for what it is good at.
- Quality degrades and cost increases as the active context grows; memory architecture is about keeping the context lean and relevant, not just staying under the hard limit.
- Use `IRAGAdapter` for semantic retrieval, `IScratchpadAdapter` for structured session state, and artifact-writing tools for large output artifacts — each has a specific integration point in Lemura.
- The `remember`/`recall` tool pattern is the simplest external memory integration; back it with a persistent adapter for production use.
- Memory consistency requires attention for shared-memory multi-agent scenarios; partition by session ID or use optimistic locking to avoid stale reads.
