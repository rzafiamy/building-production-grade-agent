---
title: "Chapter 15 — Goal Injection: Keeping the Agent on Track"
part: "Part III — Lemura Framework Deep Dive"
chapter: 15
page: 24
status: draft
---

*PART III — LEMURA FRAMEWORK DEEP DIVE*

## Chapter 15 — Goal Injection: Keeping the Agent on Track

> *"A model with a 200,000-token context window can still forget what it was doing by turn twenty. Goal injection is your insurance."*

> [!NOTE]
> **Chapter Goal:** By the end of this chapter, you will understand how goal drift happens, how Lemura's `GoalInjector` prevents it, how to configure injection frequency and position, and how sub-goal tracking works.

---

### 15.1 Why Goals Drift

Goal drift is not a model defect. It is a predictable consequence of how transformer attention works combined with how context grows during a session. Understanding the mechanics makes the preventive measures obvious.

#### 15.1.1 The Recency Bias Problem

Language model attention is not uniform across the context window. Models attend more strongly to content near the current position — the most recent turns — than to content far back. In a 30-turn session, the user's original goal stated in turn 1 is 30 messages behind the model's current focal point. Its effective influence on the model's next action has weakened significantly even if it is technically present in the context.

This is recency bias: the model behaves as if recent context is more relevant than old context. For most tasks that is correct — recent tool results are more relevant than old ones. For the goal, it is exactly wrong. The goal is the most important piece of information in the session, but the model treats it as just another piece of old context.

#### 15.1.2 Tool Results Burying the Goal

Each tool call appends tool result content to the conversation history. In a tool-heavy session, turn 10 might contain 2,000 tokens of tool results from five tool calls. By turn 20, the original user message — containing the goal — is buried under 20,000 tokens of accumulated history.

The model's attention at turn 20 is concentrated on the most recent 5,000 tokens or so, which contain recent tool results and the model's recent reasoning. The goal from turn 1 has low effective weight.

#### 15.1.3 Compounding Drift Over Many Turns

Small deviations from the goal compound. If the model at turn 10 pursues a slightly different interpretation of the goal than it had at turn 1, the tool calls it makes at turn 10 reinforce that interpretation. The model at turn 20 reasons from the results of those tool calls and drifts further. By turn 30, the model may be working on a coherent task that is meaningfully different from the original goal.

This compounding is why goal injection must be continuous, not just one-time. Stating the goal once at the beginning is insufficient. Restating it regularly keeps it as a strong signal throughout.

### 15.2 The GoalInjector

`GoalInjector` (see `src/agent/execution/GoalInjector.ts`) manages goal formatting and injection for a session. `SessionManager` creates a `GoalInjector` automatically when `enableGoalPlanning` is true or when `session.setGoal()` is called.

#### 15.2.1 What It Does

`GoalInjector` formats the goal as a structured text block and injects it into the context at a configured position and frequency. It tracks which sub-goals have been completed and updates the block accordingly. It also tracks turn count for frequency-based injection decisions.

#### 15.2.2 The Injection Block: What Gets Injected

The formatted goal block includes the main goal statement, the decomposition as pending sub-goals, the already-completed sub-goals, and the success criteria:

```text
[CURRENT GOAL]
Audit /src for SQL injection vulnerabilities.

Sub-goals:
→ List all TypeScript files in /src
→ Identify files that construct SQL queries
✓ Check each query for unparameterized user input
→ Report findings with file path and line number

Success criteria:
- All files in /src have been checked
- Vulnerabilities are listed with exact locations
```

The model sees this block on every turn that triggers injection. The `→` prefix marks pending sub-goals; `✓` marks completed ones. As the session progresses and the agent completes sub-goals, the block updates to reflect current state.

#### 15.2.3 `getFormattedBlock()`: The Injected Content

The `getFormattedBlock()` method on `GoalInjector` returns the formatted string shown above. `SessionManager` calls this method and places the result in the context according to the configured injection position. You can call it directly if you need to incorporate the goal block into a custom context assembly.

### 15.3 Injection Position

The injection position controls where in the message array the goal block appears. Different positions have different trade-offs.

#### 15.3.1 `pre_system`: Before the System Prompt

Injecting before the system prompt places the goal at the very beginning of the context — maximum salience in terms of position but unusual semantically, since the model expects operational instructions at the start, not task-specific goals.

This position is rarely the right choice. The system prompt provides the agent's identity and operating rules; placing the goal before it disrupts the expected reading order.

#### 15.3.2 `post_system`: After the System Prompt

`'system_prompt'` (Lemura's label for this position) appends the goal block to the end of the system prompt. The model reads the system prompt as a unified block, so the goal becomes part of the durable operational context.

This is the recommended position for most agents. The goal is in the system prompt tier — the highest-attention position at the beginning of the context — and it is visible on every turn without appearing in the conversation history where it would push other content down.

#### 15.3.3 `pre_turn`: Before the Latest User Message

`'pre_turn'` injects the goal as a synthetic system message immediately before the current user turn. This places it at the end of the context, near the model's focal point.

Use `pre_turn` when the goal changes frequently, when the session spans many turns and the system prompt is getting crowded, or when you want the goal to be especially prominent at the model's current attention position.

#### 15.3.4 Choosing the Right Position

For most agents: use `'system_prompt'` (post-system) with `goalInjectionFrequency: 'always'`. The goal is injected once into the system prompt block and refreshed on every turn. It occupies the highest-attention position with predictable placement.

Switch to `'pre_turn'` if you find the model is ignoring the goal despite injection — placing it immediately before the current turn increases its weight at the cost of adding it to the conversation history.

### 15.4 Injection Frequency

#### 15.4.1 `goalInjectionN`: Every N Turns

When `goalInjectionFrequency` is `'every_N_turns'`, the goal is injected once every `goalInjectionN` turns (default: 3). Between injections, the goal is not explicitly present in the constructed context.

This is a cost-saving measure for long sessions where the model rarely drifts and you want to minimize the token overhead of goal injection. For sessions shorter than 30 turns, the savings are negligible — use `'always'`.

#### 15.4.2 `shouldInjectThisTurn()`: The Logic

`GoalInjector.shouldInjectThisTurn(turnIndex, compressionOccurred, injectionN)` returns `true` when:

- `injectionFrequency` is `'always'`
- `injectionFrequency` is `'every_N_turns'` and `turnIndex % injectionN === 0`
- `injectionFrequency` is `'on_compression'` and `compressionOccurred` is `true`
- It is the first turn (`turnIndex === 0`) — always inject on the first turn

The `compressionOccurred` flag is set when `ContextManager` fires a compression strategy. Injection on compression ensures the goal is visible immediately after old context is discarded — the moment when goal drift is most likely.

#### 15.4.3 Always Inject on First Turn

Regardless of the configured frequency, `GoalInjector` always injects on the first turn. The first turn establishes the goal in the model's initial context; skipping it for frequency-based injection would defeat the purpose.

### 15.5 Sub-Goal Tracking

#### 15.5.1 What Is a Sub-Goal?

Sub-goals are the decomposition of the main goal into concrete, verifiable steps. They are listed in the `decomposition` field of the `Goal` interface. A sub-goal is a single sentence that the model can evaluate as complete or incomplete given the current session state.

Good sub-goals: "Read /src/payments.ts and identify validation functions." Bad sub-goals: "Work on the code." The first is evaluable; the second is not.

#### 15.5.2 Setting and Completing Sub-Goals

Sub-goals are initialized via `session.setGoal()`:

```typescript
// Setting a goal with sub-goals that will be tracked and injected
session.setGoal({
  statement: "Refactor the auth module to use JWT.",
  decomposition: [
    "Read the current session management code",
    "Identify all places that use cookie-based auth",
    "Replace session storage with JWT generation",
    "Update middleware to verify JWT",
    "Run tests to confirm behavior is unchanged",
  ],
  successCriteria: [
    "No session storage imports remain in /src/auth",
    "JWT is issued on login and verified on each request",
    "All auth tests pass",
  ],
});
```

As sub-goals are completed, mark them via `GoalInjector.markSubGoalDone()`. `SessionManager` exposes this through the goal planning flow when `enableGoalPlanning` is true; for manual control, access the injector through the session's internal state (or call `session.setGoal()` with an updated `decomposition` list that omits completed sub-goals).

#### 15.5.3 How Sub-Goals Appear in the Injected Block

The injected block shows pending sub-goals with `→` and completed sub-goals with `✓`. The model can see its progress at a glance. When all sub-goals are marked complete, the block's summary section confirms success criteria have been met and the model should produce its final response.

### 15.6 Advanced Goal Patterns

#### 15.6.1 Dynamic Goal Updates

Goals can be updated mid-session by calling `session.setGoal()` again. This replaces the `GoalInjector` with a new one using the updated goal. The next turn's injected block will reflect the new goal.

Use dynamic updates when a tool result significantly changes the task scope: if the agent discovers that the codebase is larger than expected, the goal can be narrowed to a specific subdirectory. If an early search returns unexpected results, the goal can be updated to address what was actually found.

#### 15.6.2 Goal Confirmation with the Agent

For complex tasks, you can use a preliminary turn to have the agent confirm its understanding of the goal before executing:

```typescript
// Two-phase session: confirm goal, then execute
const session = new SessionManager({ adapter, model, maxTokens });

// Phase 1: ask the model to restate the goal
const confirmation = await session.run(
  "I need you to audit the /src/payments directory for PCI-DSS compliance issues. " +
  "Before starting, restate the goal and your planned approach in 3 sentences."
);

// Review confirmation, then proceed
session.setGoal({
  statement: "Audit /src/payments for PCI-DSS compliance.",
  decomposition: [/* ... */],
  successCriteria: [/* ... */],
});

const auditResult = await session.run("Now execute the audit.");
```

This pattern catches goal misunderstandings before the model spends 20 turns on the wrong task.

#### 15.6.3 Goal Versioning for Long Sessions

For sessions that span multiple user interactions or resume from a saved state, maintain goal versions. When the goal changes substantially, record the old goal as completed and create a new one. This gives the model a clear before/after signal rather than an updated goal that might be interpreted as a correction.

> [!TIP]
> For sessions longer than 30 turns, use `goalInjectionFrequency: 'always'` with `goalInjectionPosition: 'pre_turn'`. Paying the extra tokens on every turn is a small cost compared to the cost of a 30-turn session that drifts off-goal and must be re-run. Goal injection tokens are the cheapest insurance in agent engineering.

---

## Key Takeaways

- Goal drift is caused by recency bias and tool result accumulation; the original goal loses effective attention weight as the session grows.
- `GoalInjector` prevents drift by formatting the goal (with sub-goals and success criteria) as a structured block and re-injecting it at a configured frequency and position.
- The `'system_prompt'` injection position is the right default for most agents; use `'pre_turn'` when you want the goal maximally prominent at the current attention position.
- Always inject on the first turn and on compression events — the first turn establishes the goal, compression events are when the model most needs re-orientation.
- Sub-goal tracking keeps the agent aware of its progress; marking sub-goals as complete updates the injected block and keeps the model focused on remaining work.
