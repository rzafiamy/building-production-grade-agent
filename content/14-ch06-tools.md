---
title: "Chapter 6 — Tools: The Agent's Hands"
part: "Part II — Architecture Fundamentals"
chapter: 6
page: 14
status: draft
---

*PART II — ARCHITECTURE FUNDAMENTALS*

## Chapter 6 — Tools: The Agent's Hands

> *"A model without tools is a brain without a body. Powerful, but unable to act in the world."*

> [!NOTE]
> **Chapter Goal:** By the end of this chapter, you will be able to design effective tools for agents, understand the JSON Schema contract, implement robust tool handlers with validation and error handling, and know which tool design patterns lead to reliable vs. unreliable agent behavior.

---

### 6.1 What Is a Tool?

#### 6.1.1 The JSON Schema Contract

A tool is a named, typed operation that an agent can call. From the model's perspective, a tool is a JSON Schema object: a name, a description, and a parameters schema. The model reads the name and description to decide whether to call the tool. It reads the parameters schema to know what arguments to provide.

This contract is entirely declarative. The model never sees the tool's implementation — only its specification. It infers everything about when and how to call the tool from the name, description, and parameters alone. This is why the specification is the most important part of the tool: a poorly written description or an ambiguous parameter schema will produce incorrect calls regardless of how well the implementation is written.

In Lemura, the `IToolDefinition` interface captures this contract:

```typescript
// The complete IToolDefinition interface — name, description, schema, and executor
import { IToolDefinition, ToolContext } from "lemura/types";

const readFileTool: IToolDefinition = {
  name: "read_file",
  description:
    "Read the full text content of a file at the given path. " +
    "Returns the file content as a string. " +
    "Fails with an error message if the path does not exist or is not readable.",
  parameters: {
    type: "object",
    properties: {
      path: {
        type: "string",
        description: "Absolute or relative path to the file to read.",
      },
    },
    required: ["path"],
  },
  async execute(params: unknown, context: ToolContext): Promise<unknown> {
    const { path } = params as { path: string };
    // validation and execution below
    const content = await fs.readFile(path, "utf-8");
    return { content, path, bytes: content.length };
  },
};
```

#### 6.1.2 How the Model Decides to Call a Tool

When the model produces a response in a tool-enabled session, it decides for each turn whether to call a tool and, if so, which one. That decision is driven entirely by the description. The model matches the description against its current task state: "I need to read a file" → matches `read_file`; "I need to search the web" → matches `web_search`.

Overlapping descriptions cause ambiguity. If you have both a `read_file` tool and a `get_document` tool that do similar things, the model will choose inconsistently. Name conflicts are even worse — the model may call the wrong tool entirely. Keep the tool set lean and make each tool's purpose distinct and non-overlapping.

#### 6.1.3 The Tool Call Lifecycle

A tool call goes through five stages: generation (the model produces the tool call), validation (the arguments are checked against the schema), execution (the tool's `execute` method runs), result injection (the result is added to the context as a tool result message), and observation (the model reads the result on the next turn).

Failures can happen at any stage. Schema validation catches type mismatches. Execution can throw for any operational reason. Result injection is transparent. Observation quality depends on how informative the result is. Engineers own every stage except generation.

### 6.2 Designing Tools That Agents Use Correctly

#### 6.2.1 The Name Is a Prompt

The tool name is the most concise signal the model has. It should be a verb-noun combination that unambiguously describes the action: `read_file`, `search_web`, `create_issue`, `send_email`. Avoid nouns alone (`file`, `search`) — they are ambiguous about what is being done. Avoid vague verbs (`process_item`, `handle_task`) — they give the model no signal.

Use underscores rather than camelCase for tool names in OpenAI-compatible APIs — several providers and model families parse snake_case more reliably. Name the tool from the model's perspective: `read_file` means "I am reading a file," not "the tool reads files." That framing helps the model reason about when to call it.

#### 6.2.2 The Description Is a Contract

The description should answer three questions: what does the tool do, when should it be called, and what does it return. A good description is 1–3 sentences. A description that answers all three questions in one sentence is ideal.

Include what the tool does not do or cannot do if the boundary is non-obvious. "Returns the first 1,000 lines of the file; use `read_file_chunk` for files larger than 10,000 lines" prevents the model from calling the wrong tool on a large file.

#### 6.2.3 Parameter Design: Precision Over Flexibility

Parameters should be as specific as possible. Prefer enums over free-form strings when the valid values are enumerable. Prefer specific types (file path, ISO 8601 date, integer page number) over generic strings. A parameter that accepts "any string" gives the model a blank canvas to fill with hallucinations. A parameter that accepts one of `["json", "csv", "markdown"]` cannot be hallucinated.

Mark all required parameters as `required` in the schema. Do not make a parameter optional if it is always used — optional parameters invite the model to omit them and then produce behavior the implementation does not handle.

#### 6.2.4 Idempotency and Side Effects

Classify every tool as read-only or side-effecting before you write a line of implementation code. Read-only tools (read, search, list, count) can be called any number of times without consequence. Side-effecting tools (write, delete, send, create) change state.

Make read-only tools freely callable and idempotent. Make side-effecting tools require explicit parameters that make the intended effect unambiguous and, where possible, reversible. An `append_to_file` tool is safer than a `write_file` tool because appending is less destructive than overwriting. A `create_draft_email` tool is safer than a `send_email` tool because drafts can be reviewed before sending.

### 6.3 Tool Categories

#### 6.3.1 Read Tools (Safe, Idempotent)

Read tools observe state without changing it. File readers, directory listers, database queries, API lookups, search operations. These are the cheapest tools to design and the easiest to test. They should make up the majority of any tool set.

Design read tools to return structured results, not raw blobs. A file reader that returns `{ content: string, path: string, bytes: number, encoding: string }` gives the model structured information. A file reader that returns the raw file content as a string forces the model to parse metadata from the content — or lose it.

#### 6.3.2 Write Tools (Destructive, Needs Confirmation)

Write tools change state: creating, modifying, deleting, sending. They require more care in design than read tools because their failures are harder to reverse.

Write tools should validate their inputs completely before executing. They should confirm the intended effect in their result: "File /src/config.ts written successfully: 42 lines, 1,204 bytes." They should fail explicitly with a descriptive error rather than silently producing a partial result.

For high-risk write operations in production systems, consider integrating with Lemura's `ToolFirewall` to require explicit confirmation before execution.

#### 6.3.3 Search Tools (Probabilistic Results)

Search tools return ranked, probabilistic results. The model needs to know that "no results found" is a valid outcome and that results should be evaluated, not accepted uncritically. Include relevance signals in the result when available: a search tool that returns `{ results: [{ title, url, snippet, relevanceScore }] }` helps the model distinguish strong matches from weak ones.

Search tools are a common injection vector. If the search queries an external source (web, database, file system), the results may contain adversarial content. Keep search tool result handling as simple and structured as possible, and log all search results for audit.

#### 6.3.4 Composition Tools (Call Other Agents)

A composition tool spawns a sub-agent or calls another session. This is the building block of multi-agent systems. Design these with the same contract clarity as any other tool — the sub-agent's goal, constraints, and expected output format should all be specified in the tool parameters.

Composition tools have the highest blast radius of any tool category. A sub-agent has its own tool set and its own loop, and failures in the sub-agent propagate back to the parent. Test composition tools more thoroughly than any other category.

### 6.4 Tool Output Design

#### 6.4.1 What the Model Needs to See

The model's reasoning on the next turn depends on the tool result it receives on this turn. The result should answer the question the model was trying to answer when it called the tool. If the model called `read_file` to check whether a function exists, the result should make it easy to determine whether the function exists — not require the model to parse a 500-line file to find out.

Keep results token-efficient. Tool results accumulate in the context window. A result that provides 200 tokens of useful information in 2,000 tokens of raw output is wasting 1,800 tokens that could have been used for something else. Summarize large results before returning them. Return only the fields the model is likely to use.

#### 6.4.2 Structured vs. Unstructured Output

Prefer structured output (JSON objects with named fields) over unstructured strings. The model can more reliably extract specific fields from a JSON object than from a prose description. "The file has 342 lines" is interpretable; `{ "lines": 342 }` is unambiguous.

Unstructured output is acceptable for content that is inherently prose — web page content, file contents that will be read directly, user-generated text. Even here, wrap the content in a structure: `{ "content": "...", "source": "...", "retrieved_at": "..." }`.

#### 6.4.3 Error Messages as Tool Output

Error messages are tool output. When a tool fails, the result should be an informative error — not an exception, not a null, not an empty string. The model reads error messages and reasons about them. "File not found: /src/config.ts" is actionable. An unhandled exception stack trace is noise.

Structure error results consistently: `{ "error": true, "message": "File not found: /src/config.ts", "code": "ENOENT" }`. This lets the model distinguish between "no result" and "error" and reason appropriately about each.

#### 6.4.4 Handling Large Tool Results

Large tool results are the primary cause of context window exhaustion. A search result that returns 10,000 words of web content, a file read that returns a 1,000-line source file, a database query that returns thousands of rows — these fill the context window in a handful of turns.

The right solution is not to truncate blindly but to summarize intelligently before returning. A web search tool should return a structured summary of the most relevant results, not the full HTML of every page. A file read tool should support a range parameter so the model can request specific sections rather than the whole file. Design for token efficiency from the start.

### 6.5 Tool Implementation Patterns

#### 6.5.1 Validation Before Execution

Every tool should validate its inputs before executing. This means: check required parameters are present, check types match the schema, check semantic validity (the path exists, the ID is resolvable, the date is in the future), and return an informative error if any check fails.

Do not rely on the schema validation provided by the framework as your only defense. Schema validation catches type mismatches but not semantic errors. A path parameter that passes schema validation can still be a non-existent path, a path outside the allowed directory, or a path to a file the agent should not read.

#### 6.5.2 Timeout and Retry Logic

Tools that call external systems need timeouts. An HTTP request to an external API that hangs indefinitely will stall the agent session indefinitely. Set a timeout on every external call. When the timeout fires, return a structured error: `{ "error": true, "message": "Request timed out after 10s", "code": "TIMEOUT" }`.

Retries add resilience for transient failures (network errors, rate limits) but must be bounded. A tool that retries indefinitely on a rate limit error will consume the entire iteration budget on a single tool call. Set a maximum retry count and use exponential backoff. If all retries are exhausted, return an error.

#### 6.5.3 Logging for Observability

Every tool execution should log: the tool name, the input arguments (sanitized of sensitive data), the execution duration, and the outcome (success/error). This logging is the foundation for detecting loops (same tool called repeatedly), diagnosing failures (which tool failed and why), and auditing side effects (what the agent actually did).

Lemura's `ToolContext` provides a `logger` field. Use it inside tool implementations rather than a global logger, so tracing correlates correctly with the session.

#### 6.5.4 The Dry-Run Pattern

For high-risk side-effecting tools, implement a dry-run mode: a parameter that, when set to `true`, causes the tool to execute all validation and pre-flight checks but not commit the side effect. Return the same result structure as a real run, but annotated: `{ "dryRun": true, "wouldCreate": [...], "wouldDelete": [...] }`.

This gives the model — and any human reviewer — a preview of what the tool will do before it does it. Dry-run is particularly valuable for tools that modify files, databases, or external services.

### 6.6 Anti-Patterns in Tool Design

#### 6.6.1 Tools That Do Too Much

A tool that does multiple unrelated things is a tool that the model will use incorrectly. `process_document` that reads a file, summarizes it, and writes the summary is three tools in one. The model cannot call half of it. It cannot retry only the failing part. It cannot reason about what went wrong if the tool fails mid-way.

Break composite operations into single-responsibility tools. If the operation is always called in sequence (read → summarize → write), wrap it in a higher-level tool with a name that describes the composite operation explicitly: `summarize_document_to_file`.

#### 6.6.2 Ambiguous Parameters

A parameter named `target` is ambiguous. A parameter named `destination_file_path` is not. A parameter named `mode` with no enum constraint is ambiguous. A parameter named `compression_mode` that accepts `["gzip", "brotli", "none"]` is not.

Ambiguous parameters produce hallucinated arguments. The model fills ambiguity with plausible-sounding values. Those values are frequently wrong. Every parameter name and description should be specific enough that there is only one correct interpretation.

#### 6.6.3 Returning Raw Exceptions

Unhandled exceptions in tool implementations produce stack traces as tool results. Stack traces are not informative for the model — they are informative for the engineer debugging the tool. The model will attempt to reason about a stack trace as if it were a structured error message and produce confused responses.

Wrap every tool implementation in a try/catch. In the catch block, log the full exception for engineering observability, and return a structured error result for the model. The model and the engineer should each see what is useful to them.

### 6.7 Registering Tools in Lemura

Lemura's `ToolRegistry` manages the tool set available to a session. Tools can be provided at construction time or registered dynamically after the session is created.

```typescript
// Registering tools at construction and dynamically via session.tools
import { SessionManager, OpenAICompatibleAdapter } from "lemura";
import { IToolDefinition } from "lemura/types";

// Static registration at construction time
const session = new SessionManager({
  adapter,
  model: "gpt-4o-mini",
  maxTokens: 100_000,
  tools: [readFileTool, listDirTool], // available from the first turn
});

// Dynamic registration after construction
// session.tools is the live ToolRegistry
session.tools.register(searchWebTool); // added mid-session if needed
session.tools.unregister("list_dir");  // removed mid-session to reduce scope

const result = await session.run("Search for recent CVEs in the lodash package.");
```

Dynamic tool registration is useful for agents that need different tool sets at different stages of a task: broad search tools early in the session, narrow write tools late. Reducing the available tool set as the session progresses reduces the chance of the model calling a tool that is no longer relevant.

---

## Key Takeaways

- A tool is a JSON Schema contract: name, description, and parameters define how the model calls it; the implementation is invisible to the model.
- The description is the most important part of the tool — it is what the model reads to decide whether and how to call the tool; ambiguous descriptions produce incorrect calls.
- Classify every tool as read-only or side-effecting before implementation; side-effecting tools require explicit validation, informative errors, and optional dry-run or confirmation mechanisms.
- Tool results accumulate in the context window — return only the fields the model needs, structure results as JSON objects with named fields, and summarize large results before returning them.
- Wrap every tool execution in try/catch; the model should receive a structured error object, never a raw exception stack trace.
- Register tools at construction time for the core tool set; use `session.tools.register()` and `session.tools.unregister()` to dynamically adjust the tool set as the session progresses.
