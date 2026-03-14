---
title: "Chapter 17 — ToolResponseProcessor: Compressing Tool Output"
part: "Part III — Lemura Framework Deep Dive"
chapter: 17
page: 26
status: draft
---

*PART III — LEMURA FRAMEWORK DEEP DIVE*

## Chapter 17 — ToolResponseProcessor: Compressing Tool Output

> *"A tool that returns 50,000 tokens of JSON will eat your context window in two calls. The ToolResponseProcessor is the gatekeeper."*

> [!NOTE]
> **Chapter Goal:** By the end of this chapter, you will understand how `ToolResponseProcessor` intercepts and compresses large tool results, how to configure its budget and thresholds, and how to write custom response processors for domain-specific compression.

---

### 17.1 The Tool Result Explosion Problem

#### 17.1.1 How Tool Results Grow Without Bound

A tool that fetches a URL might return 15,000 tokens of HTML. A tool that runs a static analyzer might return 8,000 tokens of findings. A tool that queries a database might return 20,000 tokens of JSON records. Each result enters the context window as a `tool` role message and stays there for the rest of the session unless explicitly removed.

Without intervention, three such tool calls consume 43,000 tokens — about a third of a 128K context window — in a handful of turns. The remaining turns must fit in the remaining 85K tokens, including the model's reasoning, future tool calls, and the system prompt.

This is the tool result explosion: a few large tool calls dominate the context and leave insufficient room for the session to make progress. The explosion happens gradually (each individual result seems manageable) but its cumulative effect is rapid context exhaustion.

#### 17.1.2 Why This Breaks Agents Silently

Context exhaustion caused by tool result accumulation often manifests as reasoning failures, not context errors. The model still has tokens available; it just has very poor signal-to-noise in the context because most of the tokens are large, raw tool results from many turns ago.

The model's quality of reasoning degrades as the context fills with stale, verbose tool output. Responses become less focused, tool calls become less precise, and the agent may start repeating work it already did because the context is too noisy to recognize the duplication. These symptoms look like model quality problems but are actually context quality problems.

### 17.2 What ToolResponseProcessor Does

`ToolResponseProcessor` (see `src/agent/execution/ToolResponseProcessor.ts`) intercepts each tool result before it enters the context window. It evaluates the result's size and content, decides whether compression is needed, and applies it.

#### 17.2.1 Interception: Seeing the Result Before the Context Does

`SessionManager` calls `processor.evaluate()` and `processor.compress()` on each tool result after execution, before appending the result to the conversation history. This makes compression invisible to the rest of the system — from `ContextManager`'s perspective, tool results are already sized appropriately.

This is a different layer from `ContextManager` compression. `ContextManager` operates on the accumulated history after the fact. `ToolResponseProcessor` operates on individual results at entry time. Both are necessary: the processor prevents large results from entering; the context strategies handle results that slipped through or accumulated over time.

#### 17.2.2 Budget Enforcement: Token Limits per Result

The processor enforces per-result token budgets based on the result's size classification. Results smaller than `smallMaxTokens` pass through unchanged. Results larger than `largeMaxTokens` are considered oversized and receive aggressive compression.

#### 17.2.3 Compression: Summarizing Large Results

The processor's compression is structural, not semantic. It does not call an LLM to summarize. Instead:

- **Oversized results** (> ~4,000 tokens equivalent): keep the first ~4,000 characters and last ~2,000 characters, discard the middle with a note
- **Large results** (> `largeMaxTokens`): keep the first N lines and last M lines, discard the middle
- **Small/medium results**: pass through unchanged

This structural compression is fast (no LLM call), cheap (no token cost), and sufficient for most cases. The model receives a representative sample of the result — the beginning (where structure is usually defined) and the end (where summaries often appear) — with a clear indication that content was omitted.

### 17.3 Configuration

#### 17.3.1 `budgetPercent`: Fraction of Context for Tool Results

```typescript
// ToolResponseProcessor with size-tier token budgets
import { ToolResponseProcessor } from "lemura";

const processor = new ToolResponseProcessor({
  smallMaxTokens: 200,    // results under 200 tokens: pass through
  mediumMaxTokens: 800,   // results up to 800 tokens: pass through
  largeMaxTokens: 2000,   // results above 2000: compress
  budgetPercent: 0.15,    // tool results may use at most 15% of maxTokens
});

const session = new SessionManager({
  adapter,
  model: "gpt-4o-mini",
  maxTokens: 100_000,
  toolResponseProcessor: processor,
});
```

#### 17.3.2 Thresholds: When to Compress vs. Pass Through

The `sizeClass` evaluation uses the configured token budgets:
- `'small'`: result tokens ≤ `smallMaxTokens` → no compression
- `'medium'`: result tokens ≤ `mediumMaxTokens` → no compression
- `'large'`: result tokens ≤ `largeMaxTokens` → structural compression
- `'oversized'`: result tokens > `largeMaxTokens` → aggressive compression

Calibrate these thresholds to your tool set. If your search tool typically returns 1,500 tokens per result and that is always useful in full, set `largeMaxTokens` to 2,000 and accept the results without compression. If your database tool returns 10,000 tokens per query and most of it is raw records the model does not need, set `largeMaxTokens` to 1,000 and compress aggressively.

#### 17.3.3 Per-Tool Configuration

The `ToolResponseProcessor` API in Lemura applies the same configuration globally. For per-tool budgets, configure the tool's `execute()` method to return a pre-processed result within your desired token budget. The tool implementation is the most precise place to control result size because it has domain knowledge about what is important to preserve.

### 17.4 Compression Strategies for Tool Output

#### 17.4.1 Truncation: Fast and Lossy

Structural truncation (head + tail) is what `ToolResponseProcessor` applies natively. It is fast, free (no LLM call), and sufficient when:
- The tool result has a clear head/tail structure (API responses with header + records)
- The model needs the overall shape of the result, not every detail
- You can afford some information loss

Head+tail truncation is not suitable when the critical information is in the middle of a long result. For those cases, use summarization or structured extraction.

#### 17.4.2 Summarization: Slower but Semantic

For tool results where structural truncation would discard critical information, use an LLM call to summarize before returning. This is most appropriate in the tool's `execute()` method, not in the processor:

```typescript
// Tool that summarizes its own output when it is too large
import { IToolDefinition, ToolContext } from "lemura/types";

const searchWebTool: IToolDefinition = {
  name: "search_web",
  description: "Search the web and return a summary of the top results.",
  parameters: {
    type: "object",
    properties: { query: { type: "string" } },
    required: ["query"],
  },
  async execute(params, context: ToolContext) {
    const { query } = params as { query: string };
    const rawResults = await fetchSearchResults(query);

    // If results exceed budget, summarize with the session adapter
    const rawText = JSON.stringify(rawResults);
    if (rawText.length > 4000 && context.adapter) {
      const response = await context.adapter.complete({
        model: "",
        messages: [{
          role: "user",
          content: `Summarize these search results in 300 words:\n${rawText}`,
        }],
        tools: [],
      });
      return { query, summary: response.content, resultCount: rawResults.length };
    }

    return { query, results: rawResults };
  },
};
```

#### 17.4.3 Structured Extraction: Best for JSON/Data

When tool results are structured (JSON objects, database records, API responses), extract only the fields the model needs rather than summarizing. A database query returning 1,000 records when the model only needs counts and aggregate values should extract those values before returning:

```typescript
// Structured extraction: return only what the model needs
async execute(params, context) {
  const records = await db.query(params.sql);
  return {
    count: records.length,
    sample: records.slice(0, 5),        // first 5 for structure
    summary: `${records.length} records returned`,
  };
  // Not: return { records } — 1000 full record objects
}
```

### 17.5 Preserving Key Information

#### 17.5.1 What Must Survive Compression

Some fields must survive any compression applied to a tool result:

- **Identifiers**: file paths, record IDs, URLs — the model uses these to make subsequent tool calls
- **Error messages**: when the tool failed, the error description is all the model has to work with
- **Status indicators**: "success", "no results found", "permission denied" — the model's next action depends on these
- **Counts and aggregates**: "1,247 records found" is important context even if the records themselves are compressed

#### 17.5.2 Anchors: Fields That Are Always Kept

The cleanest way to ensure critical fields survive compression is to separate them from compressible content in the tool's return structure:

```typescript
// Separating anchor fields from compressible content
async execute(params, context) {
  const result = await runQuery(params);
  return {
    // Anchor fields: always small, always critical
    status: result.error ? "error" : "success",
    count: result.rows.length,
    error: result.error?.message,
    // Compressible content: can be truncated or summarized
    data: result.rows.slice(0, 20), // top 20 rows max
  };
}
```

Structural tool results that separate anchors from bulk content are resilient to compression at any layer.

### 17.6 Custom Response Processors

For domain-specific compression needs that `ToolResponseProcessor`'s structural approach does not cover, implement the `IToolResponseProcessor` interface (or provide a compatible object with `evaluate()` and `compress()` methods):

```typescript
// Custom processor that uses regex to extract key fields from log output
class LogOutputProcessor {
  evaluate(response: string, tool: IToolDefinition) {
    const tokens = Math.ceil(response.length / 4);
    return {
      sizeClass: tokens > 2000 ? "oversized" : "medium" as const,
      shouldCompress: tokens > 2000,
      suggestedMaxTokens: 500,
      relevanceScore: 1,
      answered: !response.includes("ERROR"),
      answeredPartially: false,
      errorDetected: response.includes("ERROR"),
      suggestedAction: "continue" as const,
    };
  }

  compress(response: string) {
    // Extract only ERROR and WARN lines from log output
    const critical = response
      .split("\n")
      .filter(l => /ERROR|WARN|FATAL/.test(l))
      .slice(0, 50)
      .join("\n");
    return critical || "[No errors or warnings found]";
  }
}

const session = new SessionManager({
  adapter,
  model: "gpt-4o-mini",
  maxTokens: 80_000,
  toolResponseProcessor: new LogOutputProcessor(),
});
```

### 17.7 Debugging Tool Response Compression

#### 17.7.1 Logging Before and After

To see what the processor is doing, instrument the `onTrace` callback. Compression events for individual tool results are emitted as `event.type === 'tool_result'` with metadata showing the original and compressed sizes:

```typescript
// Logging tool result sizes for debugging compression behavior
const session = new SessionManager({
  adapter,
  model: "gpt-4o-mini",
  maxTokens: 80_000,
  onTrace: (event) => {
    if (event.type === "tool_result") {
      const orig = event.metadata?.originalTokens as number;
      const comp = event.metadata?.compressedTokens as number;
      if (orig !== comp) {
        console.log(`[${event.name}] ${orig} → ${comp} tokens`);
      }
    }
  },
});
```

#### 17.7.2 Detecting When Compression Causes Errors

When compression causes the model to lose a critical identifier or fact, the symptom is the model attempting to use an identifier it cannot actually have (hallucinating it) or the model reporting "I could not find the information" when the information was present in the original result.

Check the trace: compare the original tool result with what was injected into the context. If a key field is missing from the compressed version, adjust the compression configuration or restructure the tool output to separate anchors from compressible bulk content.

---

## Key Takeaways

- `ToolResponseProcessor` intercepts tool results before they enter the context window, applying structural compression (head + tail) to oversized results at entry time.
- This is a different layer from `ContextManager` compression: the processor handles individual results at entry time; context strategies handle accumulated history.
- Calibrate size thresholds (`smallMaxTokens`, `mediumMaxTokens`, `largeMaxTokens`) to your specific tools — default values may be too aggressive or too lenient for your tool set.
- The best tool result compression happens in the tool's `execute()` method where domain knowledge is available; separate anchor fields (identifiers, status, counts) from compressible bulk content.
- Use `onTrace` to compare original and compressed result sizes; when compression causes the model to lose critical information, the anchor fields pattern is the fix.
