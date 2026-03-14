---
title: "Chapter 26 — Error Recovery and Resilience"
part: "Part V — Advanced Patterns"
chapter: 26
page: 37
status: draft
---

*PART V — ADVANCED PATTERNS*

## Chapter 26 — Error Recovery and Resilience

> *"The question is not whether your agent will fail. It's what it does next."*

> [!NOTE]
> **Chapter Goal:** By the end of this chapter, you will be able to classify agent errors, implement retry strategies, design fallback behaviors, build recovery flows, and prevent the most common failure cascades in production.

---

### 26.1 Error Classification for Agents

Before you can handle errors, you need to categorize them. Not all errors are alike, and the right response to a transient network hiccup is completely different from the right response to a logic error in your agent's reasoning. Treating every error the same — usually by retrying indefinitely or crashing immediately — produces agents that are either wasteful or fragile.

Four categories cover the vast majority of agent errors you will encounter in production: transient, permanent, semantic, and environmental.

#### 26.1.1 Transient Errors: Retry and Continue

Transient errors are temporary failures that resolve without any change to the system. A network request times out. An API returns a 429 rate-limit response. A database connection is briefly unavailable. If you wait and try again, the operation succeeds.

The defining characteristic of a transient error is that the same request, repeated after a brief delay, has a reasonable probability of success. The error is not caused by anything wrong with the request itself — it is caused by temporary resource pressure or infrastructure state.

Transient errors are safe to retry. In fact, failing to retry transient errors is a significant reliability gap. An agent that gives up after a single network timeout will have a noticeably lower success rate than one that retries with exponential backoff.

#### 26.1.2 Permanent Errors: Fail Fast and Escalate

Permanent errors will not resolve by retrying. An invalid API key returns a 401 every time you call with it. A request for a nonexistent resource returns a 404 regardless of how many times you ask. A malformed request body will fail schema validation on every attempt.

Retrying permanent errors is pure waste. Each retry consumes tokens and time without any chance of success. When you detect a permanent error, fail fast: log the full error details, stop retrying, and escalate to the parent agent or the operator.

Classifying an error as permanent requires careful judgment. A 404 for a resource you expected to exist might be permanent (the resource was deleted) or environmental (the resource was moved). The difference matters for your recovery strategy.

#### 26.1.3 Semantic Errors: The Agent Did Something Wrong

Semantic errors are not infrastructure failures — they are cases where the agent invoked a tool correctly from a technical standpoint but the tool call made no sense given the task. The agent called a file-reading tool with a path that does not exist in the current working directory. It called a data transformation tool with the wrong field names. It called a search tool with a query so vague that the results are useless.

Semantic errors are not retryable in the same way as transient errors. Repeating the exact same tool call will produce the same wrong result. The fix requires changing the agent's approach: use a different query, verify the resource exists first, or ask the user for clarification.

Semantic errors surface in agent outputs that look technically successful but are substantively wrong. Detecting them often requires a validation step on tool results — checking that the returned data matches expected constraints before feeding it into the next reasoning step.

#### 26.1.4 Environmental Errors: The World Changed

Environmental errors occur when an assumption the agent made about external state is no longer true. A file the agent planned to process was moved or deleted between planning and execution. An API endpoint the agent relies on changed its response schema. A database record the agent retrieved was updated by another process before the agent could act on it.

Environmental errors require replanning, not retrying. The original plan was valid when it was created but is no longer valid given the current state of the world. The agent must detect the inconsistency, acknowledge that its plan is stale, and create a revised plan based on the current state.

### 26.2 Retry Strategies

Knowing that a transient error is retryable is the first step. Knowing how to retry without making things worse is the second.

#### 26.2.1 Simple Retry with Backoff

The core principle of retrying with backoff is: do not hammer a struggling service. If a server is under load and returns a 429, immediately retrying adds to its load and delays recovery. Waiting before retrying gives the service time to recover and gives other clients the same chance.

Exponential backoff with jitter is the standard approach. The delay between retries doubles with each attempt. Jitter adds randomness to prevent multiple clients from retrying in synchronized waves.

```typescript
// Demonstrates exponential backoff retry wrapper for tool calls
import { IToolDefinition } from 'lemura';

function isTransientError(error: unknown): boolean {
  if (!(error instanceof Error)) return false;
  const msg = error.message.toLowerCase();
  // Rate limits, network timeouts, temporary server errors
  return (
    msg.includes('429') ||
    msg.includes('503') ||
    msg.includes('timeout') ||
    msg.includes('econnreset') ||
    msg.includes('network')
  );
}

function exponentialBackoff(
  attempt: number,
  baseMs = 1000,
  maxMs = 30_000,
): number {
  const exponential = baseMs * Math.pow(2, attempt);
  const jitter = Math.random() * exponential * 0.25;
  return Math.min(exponential + jitter, maxMs);
}

function withRetry(
  tool: IToolDefinition,
  maxAttempts = 3,
): IToolDefinition {
  return {
    ...tool,
    async execute(params, context) {
      let lastError: unknown;

      for (let attempt = 0; attempt < maxAttempts; attempt++) {
        try {
          return await tool.execute(params, context);
        } catch (err) {
          lastError = err;

          if (!isTransientError(err)) {
            // Permanent or semantic errors: fail fast, no retry
            throw err;
          }

          if (attempt < maxAttempts - 1) {
            const delay = exponentialBackoff(attempt);
            await new Promise((resolve) => setTimeout(resolve, delay));
          }
        }
      }

      throw new Error(
        `Tool ${tool.name} failed after ${maxAttempts} attempts: ` +
          (lastError instanceof Error
            ? lastError.message
            : String(lastError)),
      );
    },
  };
}
```

Wrap your tools with `withRetry` at session construction time. The agent's code remains unchanged — it calls the tool and expects a result. The retry logic is encapsulated in the wrapper, invisible to the agent's reasoning.

#### 26.2.2 Retry with Context Modification

For semantic errors, a plain retry will fail identically. You need to change something about the request. Context modification retries add information to the tool call before the next attempt: the previous error message, a corrective hint, or a narrowed query.

This approach requires your tool's `execute` function to support a modified input. The wrapper catches the semantic error, extracts a hint from the error message, and adjusts the params before retrying. The adjustment is error-specific — a "resource not found" error gets a different hint than a "schema validation failed" error.

#### 26.2.3 Retry Budgets and Circuit Breakers

A retry budget caps the total number of retries your agent is allowed across all tool calls in a session. Once the budget is exhausted, no more retries occur. This prevents a misbehaving tool from consuming the entire session's time budget through repeated failed calls.

A circuit breaker tracks failures for a specific tool over a time window. After N failures in that window, the circuit opens: subsequent calls to that tool fail immediately without attempting execution. After a recovery interval, the circuit moves to a half-open state: one probe call is allowed. If it succeeds, the circuit closes. If it fails, the circuit opens again.

Circuit breakers are especially valuable in multi-agent systems. If a downstream API is failing, you want agents to stop calling it immediately rather than queuing up dozens of timed-out requests.

#### 26.2.4 What Not to Retry

Never retry a tool call that has visible side effects you cannot roll back. If a tool sends an email, posts a message, or deducts from a balance, retrying after a failure may cause the action to occur twice. For side-effecting tools, use idempotency keys when the API supports them, or implement a check-before-act pattern: verify the action has not already occurred before retrying.

### 26.3 Fallback Strategies

When retries are exhausted, fallbacks determine what the agent does next.

#### 26.3.1 Degraded Functionality

Degraded functionality means completing the task with reduced capability. If a rich data source is unavailable, fall back to a simpler one. If a specialized tool fails, fall back to a general-purpose one. The output quality decreases, but the agent produces something useful rather than nothing.

Implement degraded functionality by providing ordered tool alternatives. The primary tool is tried first. If it fails permanently, the agent tries the secondary tool. System prompts should inform the agent about this ordering: "If the `analyze_deep` tool is unavailable, use `analyze_basic` and note the limitation in your output."

#### 26.3.2 Alternative Tool or Approach

An alternative tool approach is more targeted than general degradation. The agent detects that its planned approach is blocked and selects a different approach from its available tool set. A file-reading tool returns a permission error; the agent falls back to requesting the content via an API instead. A database query times out; the agent tries the cached snapshot.

This requires the agent's system prompt to explain what fallback approaches are available. An agent that does not know alternatives exist will not attempt them.

#### 26.3.3 Human Escalation as a Fallback

Some failures require human judgment. A tool returns ambiguous results that the agent cannot interpret. A required resource is missing and no automated fallback applies. The agent's instructions are contradictory and it cannot resolve the conflict autonomously.

Human escalation is a tool call. Implement an `escalate_to_human` tool that records the escalation reason, packages the current state, and optionally sends a notification. The agent calls it when it determines that automated resolution is not possible. The tool returns a pending state; the human reviews and provides a response; the agent resumes from the pending state.

### 26.4 Self-Healing Agents

A self-healing agent detects its own stuck or looping state and takes corrective action without external intervention.

#### 26.4.1 Detecting When the Agent Is Stuck

An agent is stuck when its behavior is repetitive without progress. The most reliable signal is repeated identical tool calls within a short window of turns. If the agent called `search_files` with the same query three times in the last five turns and received the same result each time, it is stuck.

Detect this in your `onTurn` callback by inspecting the session history. Count occurrences of each tool call signature in the last N turns. A signature is the tool name plus a hash of the parameters. If any signature appears more than a threshold number of times, the agent is looping.

```typescript
// Demonstrates loop detection by counting repeated tool calls
import { SessionManager, Turn } from 'lemura';
import { createHash } from 'crypto';

interface ToolCallSignature {
  name: string;
  paramsHash: string;
}

function extractToolCalls(turn: Turn): ToolCallSignature[] {
  // Extract tool calls from turn history
  const calls: ToolCallSignature[] = [];
  if (!turn.toolCalls) return calls;

  for (const call of turn.toolCalls) {
    const paramsHash = createHash('sha256')
      .update(JSON.stringify(call.parameters))
      .digest('hex')
      .slice(0, 8);
    calls.push({ name: call.name, paramsHash });
  }
  return calls;
}

function detectLoop(
  history: Turn[],
  windowSize = 6,
  repeatThreshold = 3,
): string | null {
  // Look at the last `windowSize` turns
  const recentTurns = history.slice(-windowSize);
  const signatureCounts = new Map<string, number>();

  for (const turn of recentTurns) {
    for (const sig of extractToolCalls(turn)) {
      const key = `${sig.name}:${sig.paramsHash}`;
      signatureCounts.set(key, (signatureCounts.get(key) ?? 0) + 1);
    }
  }

  for (const [key, count] of signatureCounts) {
    if (count >= repeatThreshold) {
      return key; // Return the looping tool call signature
    }
  }

  return null; // No loop detected
}
```

Run `detectLoop` in the `onTurn` callback. When it returns a non-null value, you have a confirmed loop.

#### 26.4.2 The Recovery Prompt: Helping the Agent Unstick

When you detect a loop, inject a recovery prompt into the session before the next turn. The recovery prompt tells the agent directly that it has been repeating a tool call without progress and asks it to try a different approach.

```typescript
// Demonstrates recovery prompt injection when a loop is detected
import {
  SessionManager,
  Turn,
  TraceEvent,
} from 'lemura';

let recoveryInjectionCount = 0;
const MAX_RECOVERY_INJECTIONS = 3;

function buildRecoveryPrompt(loopingCallKey: string): string {
  const [toolName] = loopingCallKey.split(':');
  return (
    `You appear to be repeating calls to \`${toolName}\` without ` +
    `making progress. Try a different approach:\n` +
    `1. Reconsider whether \`${toolName}\` is the right tool here.\n` +
    `2. If the tool is returning insufficient results, try a ` +
    `different query or different parameters.\n` +
    `3. If you are blocked, use the \`escalate_to_human\` tool ` +
    `to request guidance rather than continuing to loop.`
  );
}

function configureLoopRecovery(session: SessionManager): void {
  const originalOnTurn = session['config']?.onTurn;

  session['config'] = {
    ...session['config'],
    onTurn: async (turn: Turn) => {
      if (originalOnTurn) await originalOnTurn(turn);

      if (recoveryInjectionCount >= MAX_RECOVERY_INJECTIONS) return;

      const history = session.getHistory();
      const loopKey = detectLoop(history);

      if (loopKey) {
        recoveryInjectionCount++;
        const recoveryPrompt = buildRecoveryPrompt(loopKey);
        const ctx = session.getContext();
        ctx.compressionSummary =
          (ctx.compressionSummary ?? '') +
          `\n\n[System recovery notice, injection ` +
          `${recoveryInjectionCount}/${MAX_RECOVERY_INJECTIONS}]:\n` +
          recoveryPrompt;
      }
    },
  };
}
```

#### 26.4.3 Injecting Error Context for Self-Correction

Beyond loop detection, you can inject error context to help the agent correct specific mistakes. When a tool returns a validation error, include the error message and the input that caused it in the next turn's context. The agent can read this information and adjust its next tool call accordingly.

This is most effective when error messages are specific and actionable. A message like "field 'userId' must be a UUID, received '12345'" tells the agent exactly what to fix. A message like "invalid input" gives it nothing to work with.

#### 26.4.4 Limits of Self-Healing

Self-healing has hard limits. Do not inject recovery prompts more than three times per session. Beyond three injections, the additional prompts begin to confuse the model. The context window accumulates a history of failed recoveries, and the model's attention is split between the original task and the growing list of recovery notices.

When recovery injections are exhausted and the agent is still looping, escalate or fail. Continuing to inject prompts past the limit wastes tokens and produces increasingly incoherent behavior. A clean failure with a clear error message is always better than an incoherent success.

> [!WARNING]
> Never inject more than three recovery prompts in a single session. After three injections, the accumulated recovery context degrades model performance. If the agent is still stuck, surface the failure explicitly rather than continuing to inject guidance that will not help.

### 26.5 Failure Cascades and How to Prevent Them

A failure cascade occurs when one agent's failure triggers failures in other agents, which trigger further failures, until the entire system is in a degraded state. Cascades are particularly dangerous in multi-agent systems where agents depend on each other's outputs.

#### 26.5.1 How One Failure Becomes Many

The most common cascade pattern starts with a shared dependency. Many agents rely on the same downstream service. That service goes down. Every agent that calls it starts failing. Their supervisors start receiving error results. The supervisors retry, adding more load. The downstream service, already struggling, receives more traffic and stays down longer.

The second cascade pattern is data poisoning. An agent in an early pipeline stage produces incorrect output due to a semantic error. The next stage accepts that output as ground truth. Its output is wrong in a different way. By the final stage, the output bears no resemblance to what was wanted.

#### 26.5.2 Bulkhead Pattern for Agent Isolation

The bulkhead pattern prevents one agent's failure from consuming resources needed by others. Each agent session has its own failure budget: a maximum number of errors it is allowed before it is terminated. When a session exceeds its budget, it fails in isolation. Other sessions continue unaffected.

In Lemura, implement bulkheads by setting tight `maxIterations` limits on worker sessions. A worker that exceeds its iteration limit stops. The supervisor receives an error result, marks that subtask as failed, and continues with other subtasks. The supervisor's failure budget is independent of any single worker's.

#### 26.5.3 Timeout Hierarchies

Timeouts at every level prevent a slow component from blocking the entire system. Worker sessions have short timeouts. Supervisor sessions have longer timeouts that account for multiple worker calls. Orchestrator sessions have the longest timeouts that account for the full multi-level workflow.

The rule is that a parent's timeout must always exceed the sum of its children's timeouts plus coordination overhead. A supervisor that times out before its workers finish will leave orphaned worker sessions running after the supervisor has reported failure.

### 26.6 Recovery from Specific Failure Modes

General strategies matter, but production failures are specific. Each failure mode has a targeted recovery approach.

#### 26.6.1 Recovering from Goal Drift

Goal drift occurs when an agent gradually deviates from its original goal over a long session. The agent remains productive and coherent at each individual turn, but after many turns its actions no longer serve the original objective.

Detect goal drift by comparing the agent's current actions to its stated goal at regular intervals. Use the `onTurn` callback to compute a rough semantic distance between the goal and the last few tool calls. If the agent is supposed to be auditing a codebase but has spent the last ten turns searching documentation instead, it has drifted.

Recovery: inject a goal reminder via the scratchpad. Append to `ctx.compressionSummary` a reminder of the original goal and a note that the agent should return to it. This is lighter-weight than a full recovery prompt and sufficient to reorient an agent that has drifted without looping.

#### 26.6.2 Recovering from a Stuck Loop

The stuck loop recovery flow is described in section 26.4. The key decision point is when to give up on self-healing. If the loop persists after three recovery injections, stop the session, return the partial results accumulated before the loop started, and include a structured failure indicator in the output.

#### 26.6.3 Recovering from a Bad Tool Result

A bad tool result is one that passes technical validation — the tool returned without throwing — but contains incorrect, incomplete, or misleading information. The agent accepts it as valid and proceeds on false premises.

Prevention is the primary defense: validate tool outputs with schema checks and range checks before they enter the agent's reasoning. When a tool returns a JSON object, verify it has the required fields. When a tool returns a count, verify the count is within plausible bounds.

When bad tool results slip through validation, recovery depends on how far the agent has propagated the error. If caught early, a corrective context injection can redirect the agent. If the error has propagated through many turns, the safest recovery is to checkpoint, clear the corrupted reasoning, and restart from the last known-good state.

#### 26.6.4 Recovering from Context Overflow

Context overflow occurs when the session approaches its maximum token budget and compression strategies have been exhausted or are insufficient. The agent can no longer process new information without losing critical context.

The immediate response is to compress proactively. Call `session.getContext()` and populate `ctx.compressionSummary` with a concise summary. Then call `session.loadHistory()` with only the most recent turns. `SandwichCompressionStrategy` and `HistoryCompressionStrategy` do this automatically at their configured thresholds, but you can also trigger it proactively when you detect the token count approaching a critical level.

If compression cannot reclaim enough space, you must split the remaining work into a new session. Pass the current summary as the new session's initial context.

### 26.7 Resilience Testing

You cannot rely on production incidents alone to discover your agent's failure modes. Build resilience tests that deliberately trigger failures and verify that recovery behaves correctly.

#### 26.7.1 Chaos Engineering for Agents

Chaos engineering applies controlled failure injection to identify weaknesses before they surface in production. For agents, the equivalent is fault injection at the tool level: make tools fail in specific ways and verify that the agent recovers correctly.

A fault injection wrapper intercepts tool calls and occasionally injects failures based on a configurable fault specification. You can specify failure probability, error type, and failure duration. Running the same agent task under multiple fault configurations tells you which failure modes the agent handles gracefully and which cause it to produce wrong output or loop indefinitely.

#### 26.7.2 Simulating Failure in Tests

Resilience tests are deterministic, not probabilistic. Rather than random fault injection, you inject specific failures at specific points in the workflow and assert specific recovery behaviors.

Test the following scenarios for every tool your agent depends on:

- The tool throws a transient error on the first call and succeeds on the second. Assert that the agent completes the task and the retry occurred exactly once.
- The tool throws a permanent error. Assert that the agent fails fast, includes the error in its output, and does not retry.
- The tool returns a result with a missing required field. Assert that validation catches it and the agent either requests a corrected result or falls back to an alternative approach.
- The tool hangs for longer than the session timeout. Assert that the session terminates cleanly and returns a partial result rather than hanging indefinitely.

Write these as ordinary unit tests or integration tests. The `SessionManager` constructor accepts a `tools` array; you can pass mock tool implementations that simulate any failure mode you need to test.

---

## Key Takeaways

- Classify errors before deciding how to handle them. Transient errors are retryable. Permanent errors are not. Semantic errors require a different approach. Environmental errors require replanning.
- Retry transient errors with exponential backoff and jitter. Fail fast on permanent errors. Never retry side-effecting tools without idempotency guarantees.
- Use circuit breakers to prevent retries from adding load to a struggling downstream service. A circuit breaker opens after N failures and probes for recovery after an interval.
- Detect stuck loops by counting repeated identical tool call signatures in the last N turns. Inject a recovery prompt when a loop is confirmed.
- Never inject more than three recovery prompts per session. Additional injections degrade model performance rather than improving recovery.
- Apply the bulkhead pattern to give each agent session an independent failure budget. One session's failure should not affect others.
- Validate tool outputs before they enter the agent's reasoning chain. Schema checks and range checks catch bad results before they propagate.
- Build resilience tests that inject specific failures at specific points and assert specific recovery behaviors. Do not rely on production incidents to discover failure modes.
