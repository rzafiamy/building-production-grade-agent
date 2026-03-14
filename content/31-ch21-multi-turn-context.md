---
title: "Chapter 21 — Multi-Turn Context Management"
part: "Part IV — Memory and State"
chapter: 21
page: 31
status: draft
---

*PART IV — MEMORY AND STATE*

## Chapter 21 — Multi-Turn Context Management

> *"Each turn is a conversation. Each conversation is a story. The agent must know where it is in the story at all times."*

> [!NOTE]
> **Chapter Goal:** By the end of this chapter, you will understand how to manage coherent context across dozens or hundreds of turns, how to handle session handoffs, how to inject historical summaries correctly, and how to test multi-turn behavior.

---

### 21.1 The Multi-Turn Challenge

#### 21.1.1 Each Turn Adds, Nothing Removes (by Default)

The default behavior of any agent session is strictly additive: each turn appends to the context window and nothing is ever removed. User messages, assistant responses, tool calls, and tool results all accumulate. Without active intervention, a session that runs for 100 turns has 100 turns of history in its context on turn 101.

This is the correct default for correctness: the model has access to everything that has happened. It is the wrong default for efficiency: paying for 100 turns of context on turn 101 is expensive, and most of it is not relevant to the current step.

Multi-turn context management is the practice of actively shaping the context so it contains the most useful information at each turn, rather than simply accumulating everything.

#### 21.1.2 Coherence Degradation Over Time

Coherence is the agent's ability to produce responses that are consistent with everything it has established in earlier turns. An agent that told the user at turn 5 that file X does not need changes, and then proposes to modify file X at turn 50, has lost coherence. Coherence degradation is typically caused by attention dilution (the turn 5 statement has low effective weight at turn 50) or by compression (the summary of early turns did not preserve the key statement).

Maintaining coherence over long sessions requires both compression strategies (to keep the context efficient) and goal injection (to keep the agent's intentions stable). Neither alone is sufficient.

### 21.2 Designing for Multi-Turn from the Start

#### 21.2.1 Session Boundaries: When to Start Fresh

A session should have a clear scope. When the scope changes significantly — a new task, a new user, a fundamentally different goal — start a new session rather than extending the existing one. Attempting to reuse a session for a very different task introduces incoherence: the model's prior context is wrong for the new task and may produce incorrect outputs that are influenced by the old context.

Signs that a session should end and a new one begin:
- The original goal has been fully achieved
- The user has asked for something completely unrelated to the current session
- The context contains more than 50 turns and the task has naturally concluded

Signs that a session should continue:
- The same goal is still being pursued
- The user is asking follow-up questions about the session's output
- A prior step's output is needed for the current step

#### 21.2.2 Continuity Signals: Telling the Agent It's Continuing

When resuming a session from a saved state or providing context from a prior session, tell the model explicitly that it is continuing rather than starting fresh. Include a brief orientation message at the start of the resumed session:

```typescript
// Injecting a continuity signal when resuming a long session
session.loadHistory(savedHistory);
const result = await session.run(
  "Continuing from where we left off. Previous progress: " +
  "audit of /src/auth is complete (3 issues found). " +
  "Next: audit /src/payments."
);
```

The model interprets the session differently depending on whether it perceives itself as starting a new task or continuing an existing one. The continuity signal reduces the chance of the model re-doing work that was already completed.

#### 21.2.3 The Session Handoff Protocol

A session handoff transfers the essential state from a completed session to a new one. This is necessary when a task requires more turns than any single session can efficiently handle, or when sessions must run across multiple invocations (batch processing, scheduled jobs).

The handoff protocol:
1. At session end, call `session.getHistory()` to get the full turn history
2. Use a compression model to generate a summary of the completed session's key outputs
3. Start a new session with the summary as context and the remaining tasks as the new goal
4. Use `session.loadHistory()` if the last N turns need to be available verbatim

### 21.3 Context Window Budget Allocation

#### 21.3.1 The Budget Equation

The context window has a fixed token budget. Every component that uses tokens comes out of the same budget:

```text
maxTokens = system_prompt
          + skill_content
          + goal_block
          + compression_summary
          + recent_turns
          + current_input
          + model_response (reserve)
```

Planning the allocation prevents surprises. If your system prompt is 1,000 tokens, skills are 2,000, goal block is 500, and the model response reserve is 2,000, you have 94,500 tokens for history, compression summary, and current input in a 100K session.

#### 21.3.2 Allocating Across: System, Goals, History, Current Input

A practical allocation for a 100K context session:

| Component | Allocation | Notes |
|-----------|-----------|-------|
| System prompt | 1,000–2,000 | Fixed; invest in quality over quantity |
| Skill content | 1,000–3,000 | Scales with `skillTokenBudget` |
| Goal block | 300–800 | Depends on sub-goal count |
| Compression summary | 500–2,000 | Grows as sessions lengthen |
| Recent turns (last 10) | 10,000–30,000 | Largest variable component |
| Current input | 500–5,000 | Depends on task |
| Model response reserve | 2,000–4,000 | Set via `maxCompletionTokens` |

Set `triggerThreshold` on your compression strategies to fire before recent turns consume the full remaining budget.

#### 21.3.3 Dynamic Budget Adjustment

For sessions where the current input size varies dramatically (sometimes a short question, sometimes a large file for review), leave more headroom in the budget rather than filling it optimally. A compression trigger that fires at 80% of the budget gives the current input enough room even when it is large.

### 21.4 Injecting Prior Session Context

#### 21.4.1 Session Summary Injection

When continuing work from a prior session, inject a summary of the prior session as a synthetic system turn at the beginning of the new session's history:

```typescript
// Resuming a long project with prior session context
const priorSummary = await generateSessionSummary(lastSession.getHistory());

const newSession = new SessionManager({
  adapter,
  model: "gpt-4o-mini",
  maxTokens: 100_000,
  compressionStrategies: [
    new SummaryInjectionStrategy({ priority: 1, label: "Prior session summary" }),
  ],
});

// Inject the prior summary as the initial compression summary
const ctx = newSession.getContext();
ctx.compressionSummary = priorSummary;
// SummaryInjectionStrategy will inject it on the first turn

const result = await newSession.run("Continue auditing /src/payments.");
```

#### 21.4.2 Structured State Injection

For agents that maintain structured state — a list of discovered issues, a map of file statuses, a plan with tracked completion — serialize the state to a compact JSON representation and inject it as a system turn:

```typescript
// Injecting structured state from a prior session
const state = {
  filesAudited: ["src/auth.ts", "src/session.ts"],
  issuesFound: [
    { file: "src/auth.ts", line: 42, severity: "high", type: "sqli" },
  ],
  remainingFiles: ["src/payments.ts", "src/billing.ts"],
};

const result = await session.run(
  `Audit state:\n${JSON.stringify(state, null, 2)}\n\n` +
  "Continue with the remaining files."
);
```

Keep injected state compact — the JSON should be readable in a few hundred tokens. If the state is very large, compress it before injecting.

#### 21.4.3 Using `SummaryInjectionStrategy`

`SummaryInjectionStrategy` is designed precisely for this use case. When configured with `label: "Prior session summary"`, it injects a clearly labeled summary block at the beginning of the turn list. The model reads the label and understands this is prior context, not current instructions.

Set `ctx.compressionSummary` on the `ContextWindow` before the first `run()` call to pre-populate the injected summary. `SummaryInjectionStrategy` then maintains and updates the summary as new compression events fire during the session.

### 21.5 Multi-Session Agents

#### 21.5.1 Persisting Session State Between Runs

For agents that run on a schedule or process tasks from a queue, the session state must be persisted between runs. After each `run()`, serialize the session history and store it:

```typescript
// Persisting and restoring session history across runs
async function runWithPersistence(sessionId: string, task: string) {
  const session = new SessionManager({ adapter, model, maxTokens });

  // Restore prior history if available
  const savedHistory = await db.getSessionHistory(sessionId);
  if (savedHistory) {
    session.loadHistory(savedHistory);
  }

  const result = await session.run(task);

  // Persist the updated history
  await db.saveSessionHistory(sessionId, session.getHistory());

  return result;
}
```

#### 21.5.2 Session Metadata and ID Tracking

Assign a stable `sessionId` in `SessionConfig` for sessions that persist across runs. The `sessionId` flows through all trace events and is available in tool contexts via `context.sessionId`. Use it as the key for all storage operations (history, scratchpad, artifacts) so every stored item is attributable to a specific session.

#### 21.5.3 Loading Previous Session Context

`session.loadHistory(turns)` populates the conversation history from a saved array of `Turn` objects. The `Turn` format matches `session.getHistory()` output, making save/restore a symmetric operation.

When loading history from a very long prior session, consider loading only the last N turns plus the compression summary rather than the full history. A 500-turn history loaded verbatim will fill the context immediately; a summary plus the last 20 turns provides coherence at a fraction of the token cost.

### 21.6 Testing Multi-Turn Behavior

#### 21.6.1 Simulating Long Sessions in Tests

Long sessions take time and cost money to run live. For testing, create synthetic conversation histories that represent the state of a long session without actually running it:

```typescript
// Creating a synthetic long-session history for testing compression behavior
function createSyntheticHistory(turnCount: number): Turn[] {
  return Array.from({ length: turnCount }, (_, i) => ({
    role: i % 2 === 0 ? "user" : "assistant",
    content: `Turn ${i}: synthetic content for testing.`,
    tokenCount: 100,
    turnIndex: i,
    compressed: false,
  }));
}

const session = new SessionManager({ adapter, model, maxTokens: 10_000 });
session.loadHistory(createSyntheticHistory(50));
// Now test compression behavior by triggering a run
```

This lets you test compression triggers, goal injection, and coherence-related behavior without running 50 real turns.

#### 21.6.2 Detecting Coherence Drift

Coherence drift is best detected by evaluating model outputs at regular intervals during a long session and checking for contradictions with earlier stated facts or decisions. For automated testing, run a "coherence check" at the end of a long simulated session:

```typescript
// Coherence check: verify the agent remembers key facts from early turns
const result = await session.run(
  "Without using any tools, tell me what files we decided NOT to modify. " +
  "List only files, no explanation."
);

const forbidden = ["src/legacy.ts", "src/vendor.ts"];
for (const file of forbidden) {
  assert(result.includes(file), `Coherence failure: agent forgot ${file}`);
}
```

#### 21.6.3 Regression Testing After Compression Changes

Compression changes that improve token efficiency often degrade coherence. Run your coherence test suite after any change to compression configuration to detect regressions. A change that reduces context size by 20% but causes the agent to forget a critical decision is not an improvement.

> [!WARNING]
> Never tune compression aggressively on a development task and then deploy without running coherence tests on production-representative tasks. Development tasks are typically shorter and more forgiving than production tasks. Compression that preserves everything needed for a 20-turn dev session may lose critical information in a 100-turn production session.

---

## Key Takeaways

- Multi-turn context management is active, not passive: shape the context at each turn to contain the most relevant information, rather than letting it accumulate unchecked.
- Session boundaries matter: start a new session when the goal changes fundamentally rather than extending the existing one with conflicting context.
- Budget allocation is a planning exercise: know how many tokens each component uses and configure compression triggers to fire with enough headroom for current input and model response.
- Use `session.loadHistory()` to restore prior session state and `SummaryInjectionStrategy` to inject prior session summaries; together they enable multi-session agents with coherent long-horizon behavior.
- Test coherence drift explicitly with synthetic long sessions; compression changes that improve efficiency often degrade coherence and require specific regression testing.
