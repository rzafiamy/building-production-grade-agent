---
title: "Chapter 13 — SessionManager: The Agent Runtime"
part: "Part III — Lemura Framework Deep Dive"
chapter: 13
page: 22
status: draft
---

*PART III — LEMURA FRAMEWORK DEEP DIVE*

## Chapter 13 — SessionManager: The Agent Runtime

> *"The `SessionManager` is where intent meets execution. Everything else is preparation."*

> [!NOTE]
> **Chapter Goal:** By the end of this chapter, you will understand how `SessionManager` orchestrates the ReAct loop, how to control session lifecycle, how to configure all aspects of execution, and what happens internally during each turn.

---

### 13.1 The SessionManager's Role

`SessionManager` is the central class in Lemura. From the outside it looks simple: pass a goal, get a result. From the inside, it orchestrates the full ReAct loop — model calls, tool dispatch, context management, goal injection, plan tracking, compression, and tracing — all transparently.

#### 13.1.1 What It Owns

`SessionManager` owns the session's execution state: the message history, the current `ContextWindow`, the active goal and plan, the `ToolRegistry`, the `SkillInjector`, and the `MCPClientRegistry`. It initializes these on construction and keeps them synchronized throughout the session.

It also owns the loop itself. The `run()` method drives the ReAct cycle: call the model, inspect the response, dispatch tool calls if present, collect results, update context, and repeat. The loop terminates when the model returns a response without tool calls, or when a limit is reached.

#### 13.1.2 What It Delegates

`SessionManager` delegates context preparation to `ContextManager`, goal formatting and injection to `GoalInjector`, plan state tracking to `ContinuationPlanner`, tool execution to `ToolRegistry`, skill content injection to `SkillInjector`, and provider API calls to `IProviderAdapter`.

This delegation means `SessionManager`'s own code is relatively thin. Understanding the subsystems — covered in Chapters 14 through 19 — is the deeper knowledge. This chapter focuses on the interface you interact with directly.

### 13.2 Creating a Session

#### 13.2.1 Constructor and Configuration

`SessionManager` takes a single `SessionConfig` object. Construction is synchronous. No network calls happen at construction time.

```typescript
// Creating a fully configured SessionManager
import {
  SessionManager, OpenAICompatibleAdapter,
  SandwichCompressionStrategy, SummaryInjectionStrategy,
  DefaultLogger, LogLevel,
} from "lemura";

const adapter = new OpenAICompatibleAdapter({
  baseUrl: process.env.LEMURA_BASE_URL!,
  apiKey: process.env.LEMURA_API_KEY!,
  defaultModel: "gpt-4o-mini",
});

const logger = new DefaultLogger();
logger.setLevel(LogLevel.INFO);

const session = new SessionManager({
  adapter,
  model: "gpt-4o-mini",
  maxTokens: 100_000,
  maxIterations: 20,
  maxSteps: 40,
  systemPrompt: "You are a precise code analysis assistant.",
  compressionStrategies: [
    new SummaryInjectionStrategy({ priority: 1 }),
    new SandwichCompressionStrategy(adapter, {
      priority: 20,
      preserveFirst: 4,
      preserveLast: 10,
      triggerThreshold: 0.80,
    }),
  ],
  tools: [readFileTool, listDirTool],
  logger,
  onTrace: (event) => logger.debug("trace", event),
});
```

#### 13.2.2 Initialization and Warmup

When `mcpServers` is configured in `SessionConfig`, the MCP connections are established lazily — on the first call to `session.run()`, not at construction time. This means construction is always fast. If you need MCP connections established eagerly, call `session.run()` (with a no-op message if needed) before accepting production traffic.

### 13.3 Running the Agent

#### 13.3.1 `session.run()`: Fire and Forget

`run(userMessage)` starts the ReAct loop and returns when the session completes — either by natural termination (model produces a final response) or by limit termination (`maxIterations` or `maxSteps` reached). It returns the final assistant response as a string.

```typescript
// Fire-and-forget: run() blocks until the session completes
const result = await session.run(
  "Analyze /src/payments.ts and list all functions with no return type annotation."
);
// result: the model's final analysis
console.log(result);
```

`run()` is the right choice for server-side processing where you want the full result before responding. The call may take seconds to minutes for long sessions — design your API timeouts accordingly.

#### 13.3.2 `session.step()`: One Turn at a Time

`SessionManager` does not expose a public `step()` method. The ReAct loop runs internally within `run()`. If you need turn-by-turn control, use `session.stream()` for streaming token output, or use the `onTurn` and `onTrace` callbacks to observe each turn without interrupting execution.

For human-in-the-loop patterns where you need to pause and inject human input mid-session, see **Chapter 27 — Human-in-the-Loop**. The pattern there uses the existing tool infrastructure rather than a separate step mechanism.

#### 13.3.3 Async Iteration with `session.stream()`

`stream(userMessage)` returns an async iterable that yields string deltas as the final response is generated. Tool calls and tool results execute synchronously as before — the streaming applies only to the final text response.

```typescript
// Streaming the final response token by token
for await (const delta of session.stream("Explain the auth module architecture")) {
  process.stdout.write(delta);
}
process.stdout.write("\n");
```

Use `stream()` for user-facing agents where you want the response to appear progressively. The underlying tool execution is unchanged — the streaming only affects how the final answer is delivered.

### 13.4 Setting Goals and Plans

#### 13.4.1 `session.setGoal(goal: string)`

`setGoal()` configures the `GoalInjector` for the session. The goal is injected into the context at the frequency and position configured in `SessionConfig`. Call it before `run()` to establish the session's goal before execution begins.

The `setGoal()` method accepts an object with `statement`, `decomposition`, and `successCriteria` fields (the `id`, `injectionFrequency`, and `injectionPosition` fields are managed by `SessionManager`):

```typescript
// Setting a structured goal before running the session
session.setGoal({
  statement: "Audit /src for SQL injection vulnerabilities.",
  decomposition: [
    "List all TypeScript files in /src",
    "Identify files that construct SQL queries",
    "Check each query for unparameterized user input",
    "Report findings with file path and line number",
  ],
  successCriteria: [
    "All files in /src have been checked",
    "Vulnerabilities are listed with exact locations",
    "False positives are noted and explained",
  ],
});

const result = await session.run("Audit /src for SQL injection vulnerabilities.");
```

#### 13.4.2 `session.setPlan(steps: PlanStep[])`

`setPlan()` configures a `ContinuationPlanner` for the session. The plan is tracked alongside the goal and provides the model with a structured execution agenda. See **Chapter 16 — ContinuationPlanner: Multi-Step Execution** for the full `ContinuationStep` interface.

#### 13.4.3 Updating Goals Mid-Session

Both `setGoal()` and `setPlan()` can be called at any point during a session, including after `run()` has started (from a callback). The `GoalInjector` and `ContinuationPlanner` are replaced with the new values on the next turn.

Use mid-session goal updates when a tool result significantly changes the task scope, or when a user interrupts to redirect the agent.

### 13.5 Session Lifecycle Events

Lemura provides two callback channels for observing session execution.

#### 13.5.1 `onTurn` / `onTurnEnd`

`onTurn` fires after each turn is added to the conversation history. It receives a `Turn` object with the role, content, token count, and any tool calls or tool results.

```typescript
// Logging each turn as it completes
const session = new SessionManager({
  adapter,
  model: "gpt-4o-mini",
  maxTokens: 80_000,
  onTurn: (turn) => {
    console.log(`[${turn.role}] tokens: ${turn.tokenCount}`);
  },
});
```

#### 13.5.2 `onToolCall` / `onToolResult`

Tool call events are delivered through `onTrace` rather than separate callbacks. Subscribe to `event.type === 'tool_call'` and `event.type === 'tool_result'` in the `onTrace` handler to observe tool execution.

#### 13.5.3 `onContextCompressed`

Context compression events are also delivered through `onTrace` as `event.type === 'compression'`. The event includes the compression strategy name, the token count before and after, and the generated summary if applicable.

#### 13.5.4 `onComplete` / `onError`

Session completion and error events are observable via `onTrace` as `event.type === 'system'` with `event.name === 'session_complete'` or `event.name === 'session_error'`. For simpler needs, `await session.run()` resolves on completion and throws on error.

### 13.6 What Happens Inside a Turn

Understanding the turn lifecycle helps you diagnose unexpected behavior and configure the session correctly.

#### 13.6.1 Pre-Turn: Goal and Plan Injection

Before each model call, `SessionManager` checks whether goal injection should fire for this turn. If `goalInjectionFrequency` is `'always'` (the default), the formatted goal block is prepended to the system prompt or added as a pre-turn message on every turn. If it is `'every_N_turns'`, the `GoalInjector.shouldInjectThisTurn()` method decides.

Plan status is also formatted and injected if a `ContinuationPlanner` is active. The model sees which steps are pending, running, and complete on every turn that triggers goal injection.

#### 13.6.2 Context Assembly

`ContextManager.prepare()` is called to assemble the final message array. This applies all configured `IContextStrategy` implementations in priority order. If context is above the threshold, compression fires here — before the model call, not after.

The resulting `ContextWindow` has a `tokenCount` that is safely within `maxTokens`. The message array is built from the window's system prompt, turns, and any injected summary.

#### 13.6.3 LLM Call via Adapter

The assembled message array, the session's tool definitions, and `maxCompletionTokens` are passed to `adapter.complete()`. The adapter translates these to the provider's wire format, makes the HTTP call, and returns a normalized `CompletionResponse`.

The response contains the model's text content, any tool calls (as structured `{ id, name, arguments }` objects), the finish reason, and token usage. Token usage is recorded for session-level cost tracking.

#### 13.6.4 Tool Call Dispatch and Result Collection

If the `CompletionResponse` contains tool calls, `SessionManager` dispatches them to `ToolRegistry.execute()` (or `executeParallel()` if `parallelToolCalls: true`). Each call goes through the `ToolFirewall` first if configured — rejected calls are reported back to the model as denial messages.

`ToolResponseProcessor` processes each result before it enters the context window. Oversized results are compressed. The processed results are assembled into tool result messages and appended to the conversation history.

#### 13.6.5 Post-Turn: State Update and Compression Check

After tool results are collected, `ContinuationPlanner` updates step statuses based on which tool names were called and what they returned. Sub-goals are checked for completion if `enableGoalPlanning` is active.

The next ReAct turn begins immediately unless a termination condition is met: the response had no tool calls (natural completion), `maxIterations` is reached, or `maxSteps` is exhausted.

### 13.7 Controlling Execution

#### 13.7.1 Max Iterations

`maxIterations` is a hard ceiling on the number of ReAct turns. When reached, `SessionManager` returns the last model response without further tool calls. The response may be incomplete — callers should check whether the session terminated naturally or by limit. The `onTrace` callback receives a `session_complete` event with a `reason` field indicating `'max_iterations'` vs `'natural'`.

#### 13.7.2 Abort and Pause

There is no built-in pause mechanism in `SessionManager`. The `run()` method is a single async call that runs to completion. For abort behavior, use `AbortController` if your Node.js version supports canceling fetch requests, or implement a wrapper that tracks an external flag and checks it in the `onTrace` callback.

#### 13.7.3 Resuming a Session

To resume a session after it completes, call `session.run()` again with a new user message. The session's history is preserved between `run()` calls. Each call to `run()` starts a new user turn on top of the existing history.

To resume a session from a previously saved state, use `session.loadHistory()` with the serialized turn array, then call `run()`. See **Chapter 23 — State Persistence and Recovery** for the full checkpoint and restore pattern.

### 13.8 Session State and Introspection

At any point before, during (from callbacks), or after a session, you can inspect its state:

```typescript
// Inspecting session state after a run
const result = await session.run("Analyze the API surface.");

// Full context snapshot
const ctx = session.getContext();
console.log(`Turns: ${ctx.turns.length}, tokens: ${ctx.tokenCount}`);

// Conversation history as Turn[]
const history = session.getHistory();
const toolCalls = history.filter(t => t.toolCalls?.length);
console.log(`Tool calls made: ${toolCalls.length}`);

// Live tool registry — add tools based on what was discovered
session.tools.register(newToolBasedOnAnalysis);

// Live skill injector — activate domain expertise mid-session
session.skills.enableSkill("security-analysis");
```

`getContext()` returns a shallow copy of the `ContextWindow` — the same object the model sees on the next turn, with compression summaries, system prompt, and full turn history. `getHistory()` returns the raw `Turn[]` array, suitable for serialization and storage.

> [!TIP]
> When debugging a session that produced an unexpected result, call `session.getHistory()` after `run()` completes and inspect the tool calls and tool results turn by turn. The history contains every tool call the model made, every argument it passed, and every result it received. Unexpected behavior almost always has a visible cause somewhere in that sequence.

---

## Key Takeaways

- `SessionManager` is a thin orchestrator: it wires the subsystems together and drives the ReAct loop, delegating context preparation, goal injection, tool dispatch, and compression to specialized components.
- `run()` blocks until session completion and returns the final response string; `stream()` yields the same response token by token for progressive display.
- The turn lifecycle is: goal/plan injection → context assembly → model call → tool dispatch → result processing → plan update → repeat.
- `setGoal()` and `setPlan()` can be called before or during a session; the changes take effect on the next turn.
- Use `session.getHistory()` post-run for debugging; the full tool call and result sequence is always available and is the first place to look when output is unexpected.
