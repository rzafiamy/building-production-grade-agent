---
title: "Chapter 30 — Observability and Debugging"
part: "Part V — Advanced Patterns"
chapter: 30
page: 41
status: draft
---

*PART V — ADVANCED PATTERNS*

## Chapter 30 — Observability and Debugging

> *"You can't debug what you can't see. Agents that run in the dark fail in the dark."*

> [!NOTE]
> **Chapter Goal:** By the end of this chapter, you will be able to instrument agents for full observability, build effective debugging workflows, trace agent failures to their root cause, and set up alerting for production issues.

---

### 30.1 Why Agent Observability Is Hard

Observability for a REST endpoint is straightforward: you log the request, the response, and the duration. The unit of work is a single HTTP round-trip. For an agent, the unit of work is a session that may span dozens of turns, hundreds of tool calls, and multiple context compressions — none of which are visible to the caller without explicit instrumentation.

#### 30.1.1 Non-Determinism Makes Reproduction Difficult

Given the same input, a deterministic system produces the same output. Agents do not. Temperature, model updates, and floating-point non-determinism at the provider level mean that reproducing a specific failure requires capturing not just the input but the full execution state at the time of failure: the context, the tool results, the turn index, and the compression state.

Without capturing that state, you cannot reproduce the failure reliably. Without reproducing it, you cannot be certain your fix addresses the actual cause rather than a related but distinct issue. This makes agent debugging significantly harder than debugging traditional software — and it is why logging completeness matters more for agents than for almost any other class of software.

#### 30.1.2 Many Steps, Many Failure Points

A 20-turn agent session with 3 tool calls per turn has 60 tool call opportunities, each of which can fail independently, return unexpected output, or succeed in a way the agent misinterprets. The failure that surfaces at turn 18 may have its root cause in turn 4 — a tool result that the agent incorporated into its reasoning in a subtly wrong way, producing a chain of plausible-looking but incorrect actions.

Finding turn 4 in the logs from turn 18 is the core debugging challenge. The observability infrastructure exists to make that traversal possible.

#### 30.1.3 Context Is Both Evidence and Evidence Destroyer

The context window is simultaneously the primary evidence of what went wrong and the first thing that gets destroyed when the session ends. Compression events discard information. Context that fills and is summarized loses detail. A session that ran for 80 turns and compressed three times may have lost the exact content that would explain the failure.

The practical response is to capture the full context at key checkpoints — before compression fires, when critical tool results arrive, and at session completion — rather than relying on reconstructing it after the fact.

### 30.2 The Three Pillars of Agent Observability

Standard observability uses three signal types — logs, traces, and metrics — that map directly onto the agent problem. Each answers a different question.

#### 30.2.1 Logs: The Full Execution Record

Logs answer: what happened? A log entry captures a specific event at a specific point in time. For agents, the critical log events are turn boundaries, tool calls, tool results, compression events, goal injections, and errors. Logs are the raw material for all other observability.

Write structured logs — JSON or equivalent — with consistent field names. Free-text logs are nearly impossible to query at scale. Every log entry should carry: `sessionId`, `turnIndex`, `eventType`, `timestamp`, and the event-specific payload.

#### 30.2.2 Traces: The Causal Chain

Traces answer: how did we get here? A trace connects events into a causal chain: turn 1 caused tool call A, tool call A returned result X, result X caused turn 2's reasoning, and so on. Without traces, you have a bag of events. With traces, you have a story.

In Lemura, the `onTrace` callback provides the trace stream. Every `TraceEvent` carries a `type`, `name`, `input`, `output`, `status`, and `durationMs`. Wire this into your distributed tracing system to get the full session trace in your observability platform.

```typescript
// Capturing all trace events into structured logs
import { SessionManager } from 'lemura';
import type { TraceEvent } from 'lemura';

function createObservableSession(config: Parameters<typeof SessionManager>[0]) {
  return new SessionManager({
    ...config,
    onTrace: (event: TraceEvent) => {
      // Emit every trace event as a structured log entry
      logger.info('agent.trace', {
        sessionId: event.sessionId,
        type: event.type,
        name: event.name,
        status: event.status,
        durationMs: event.durationMs,
        input: sanitize(event.input),   // strip PII before logging
        output: sanitize(event.output),
        metadata: event.metadata,
        timestamp: Date.now(),
      });

      // Also emit as an OpenTelemetry span
      const span = tracer.startSpan(`lemura.${event.type}.${event.name}`);
      span.setAttributes({ sessionId: event.sessionId ?? '' });
      if (event.status === 'error') span.setStatus({ code: SpanStatusCode.ERROR });
      if (event.status === 'done' || event.status === 'error') span.end();
    },
  });
}
```

#### 30.2.3 Metrics: The Aggregated View

Metrics answer: how is the system behaving across all sessions? A single session's logs tell you what happened in that session. Metrics tell you whether the pattern repeats across 1,000 sessions — whether the average session length is growing, whether the tool error rate is spiking, whether compression is firing more frequently than your baseline.

Emit metrics as counters and histograms. Use Prometheus or an equivalent time-series database. The key metrics are defined in section 30.5.

### 30.3 What to Log

Log less than you think, but more completely. The most common observability mistake with agents is logging high-level summaries and discarding the detail. When something breaks, the detail is what you need.

#### 30.3.1 Every Turn: Input, Output, Token Count

Log the full turn boundary event: what the user or system sent, what the model returned, and how many tokens were consumed. Token counts per turn are essential for cost attribution and for detecting sessions that are consuming tokens faster than expected.

```typescript
// Turn boundary log event structure
interface TurnLogEvent {
  sessionId: string;
  turnIndex: number;
  inputTokens: number;
  outputTokens: number;
  totalContextTokens: number;        // Total context size at this turn
  compressionOccurred: boolean;      // Was context compressed before this turn?
  finishReason: 'stop' | 'tool_call' | 'max_tokens' | 'error';
  durationMs: number;
  timestamp: number;
}
```

#### 30.3.2 Every Tool Call: Name, Args, Result, Latency

Tool calls are the primary agent action. Log every call with its full argument set and the first 2,000 characters of the result. Log the latency from call initiation to result return — this is where you find slow tools that are degrading session performance.

```typescript
// Tool call log event with sanitized args and truncated result
interface ToolCallLogEvent {
  sessionId: string;
  turnIndex: number;
  toolCallId: string;
  toolName: string;
  args: Record<string, unknown>;   // Sanitize PII before logging
  resultPreview: string;           // First 2000 chars of result
  resultTokens: number;
  success: boolean;
  errorMessage?: string;
  latencyMs: number;
  timestamp: number;
}
```

#### 30.3.3 Every Compression Event

Compression events are inflection points in the session's information state. After compression, the context has different content than before. Log the compression event with: which strategy fired, how many tokens were removed, what the pre- and post-compression token counts were, and a hash of the generated summary (so you can verify it was stored correctly).

#### 30.3.4 Goal State at Each Turn

If goal injection is enabled, log the current goal state with each turn: the goal statement, which sub-goals have been marked complete, and whether the goal was injected on this turn. This lets you trace goal drift — the gradual shift between what the agent started doing and what it ends up doing in long sessions.

#### 30.3.5 Errors and Recovery Actions

Log every error with full context: the error type, message, stack trace, the session state at the time of the error, and the recovery action taken (if any). For `LemuraToolTimeoutError`, log which tool timed out and after how many milliseconds. For `LemuraMaxIterationsError`, log the final turn state so you can inspect what the agent was doing when the limit was reached.

### 30.4 Distributed Tracing for Multi-Agent Systems

When agents call other agents — in orchestrator-subagent patterns — the trace must span multiple sessions. Without cross-session trace linkage, you cannot see the causal chain from user request to final output when that chain passes through three agents.

#### 30.4.1 Trace IDs Across Agent Boundaries

Assign a root trace ID to every user request. Propagate that trace ID into every agent session that processes the request, directly or indirectly. When a parent agent spawns a child agent, the child session's `sessionId` becomes a child span under the parent session's span.

```typescript
// Propagating trace context from orchestrator to sub-agent
function createSubAgentSession(
  parentTraceId: string,
  parentSpanId: string,
  config: SessionConfig
) {
  return new SessionManager({
    ...config,
    sessionId: `${parentTraceId}-sub-${crypto.randomUUID()}`,
    onTrace: (event: TraceEvent) => {
      // Tag every sub-agent event with parent trace context
      emitSpan({
        traceId: parentTraceId,
        parentSpanId,
        spanId: crypto.randomUUID(),
        name: `lemura.${event.type}.${event.name}`,
        attributes: {
          'agent.session_id': event.sessionId ?? '',
          'agent.turn': event.metadata?.turn ?? 0,
        },
        status: event.status,
        startTime: event.startedAt ?? Date.now(),
        duration: event.durationMs ?? 0,
      });
    },
  });
}
```

#### 30.4.2 Parent-Child Spans for Tool Calls

Each tool call within a session should become a child span of the session's turn span. This gives you a waterfall view of the session: which tools were called during which turns, how long each tool took relative to the turn, and where time was spent.

The tool call span should carry the tool name and the result status as span attributes, so you can filter the trace to show only tool calls or only failed tool calls.

#### 30.4.3 OpenTelemetry Integration

OpenTelemetry (OTel) is the standard for distributed tracing. Wire Lemura's `onTrace` callback into an OTel `Tracer` so that your agent sessions appear as first-class traces in your observability platform alongside your other services.

<!-- Accurate as of 2026-03 — verify before next edition -->

```typescript
// OpenTelemetry integration for Lemura session traces
import { trace, SpanStatusCode, context, propagation } from '@opentelemetry/api';

const tracer = trace.getTracer('lemura-agent', '1.0.0');
const activeSpans = new Map<string, ReturnType<typeof tracer.startSpan>>();

function buildOtelSession(config: SessionConfig, parentContext?: object) {
  return new SessionManager({
    ...config,
    onTrace: (event: TraceEvent) => {
      const spanKey = `${event.sessionId}:${event.name}`;

      if (event.status === 'running') {
        // Start a new span for this event
        const ctx = parentContext
          ? trace.setSpan(context.active(), parentContext as any)
          : context.active();
        const span = tracer.startSpan(`agent.${event.type}.${event.name}`, {}, ctx);
        span.setAttribute('session.id', event.sessionId ?? '');
        activeSpans.set(spanKey, span);
      } else if (event.status === 'done' || event.status === 'error') {
        const span = activeSpans.get(spanKey);
        if (span) {
          if (event.status === 'error') {
            span.setStatus({ code: SpanStatusCode.ERROR, message: String(event.output) });
          }
          span.end();
          activeSpans.delete(spanKey);
        }
      }
    },
  });
}
```

### 30.5 Key Metrics to Track

Emit these metrics from every production agent session. They are the minimum required to detect the common failure modes before users notice them.

#### 30.5.1 Turns per Session

A counter and a histogram. The counter tracks total turns across all sessions. The histogram shows the distribution of turns per session, which tells you whether sessions are converging quickly or running long.

Alert when the 95th percentile of turns per session exceeds your expected maximum. A session that runs significantly longer than usual is either doing more work than expected or looping — and you need to tell the difference.

#### 30.5.2 Token Usage per Turn and Total

Track both per-turn input tokens and cumulative total tokens per session. Per-turn token counts reveal context growth rate: if tokens are growing by 2,000 per turn with no compression events, the context will overflow in 30 turns for a typical 64K context window. Cumulative total tokens are your direct cost signal.

```typescript
// Emit token usage metrics from the onTrace callback
onTrace: (event: TraceEvent) => {
  if (event.type === 'tool_result' && event.metadata?.usage) {
    const usage = event.metadata.usage as { inputTokens: number; outputTokens: number };
    metrics.histogram('agent.tokens.input_per_turn', usage.inputTokens, {
      sessionId: event.sessionId,
    });
    metrics.histogram('agent.tokens.output_per_turn', usage.outputTokens, {
      sessionId: event.sessionId,
    });
  }
  if (event.type === 'compression') {
    metrics.counter('agent.compression.events_total', 1, { sessionId: event.sessionId });
    metrics.histogram('agent.compression.tokens_removed', event.metadata?.tokensRemoved ?? 0);
  }
},
```

#### 30.5.3 Tool Call Success Rate

Track tool calls by tool name, and track whether each call succeeded or failed. Tool success rate is the leading indicator for most agent failures: when a critical tool starts failing more than expected, session quality degrades before any user-facing metric changes.

Emit: `agent_tool_calls_total{tool_name, status}` — a counter labeled by tool name and success/failure status.

#### 30.5.4 Compression Trigger Frequency

Track how often compression fires per session. Compression firing at turn 8 in a session that typically runs to turn 20 indicates that your context is filling significantly faster than your baseline — usually because a tool is returning much larger results than expected.

Alert when compression triggers in the first third of a typical session's turn count.

#### 30.5.5 Goal Completion Rate

Track the percentage of sessions that result in goal completion (the agent reports the task done) versus sessions that end with an error, a loop break, or an escalation. This is your top-level quality metric. Everything else — token counts, tool success rates, compression frequency — serves this one.

Define goal completion carefully for your use case. For a coding agent, it is "tests pass after the session ends." For a research agent, it is "`write_report` was called." For a workflow agent, it is "all plan steps reached `done` status."

### 30.6 Debugging Agent Failures

When something goes wrong, you need to find the first wrong turn as quickly as possible. The following workflow applies to the majority of agent failures.

#### 30.6.1 Reconstructing the Session from Logs

Start with the session ID. Pull all log events for that session ID, sorted by turn index and timestamp. This gives you the linear execution record: what happened, in what order.

Look first at the final turn — what state was the agent in when the session ended? Then look at the last tool call before the failure — what did the tool return, and how did the model respond? Work backward from the failure point until you find the turn where the agent's reasoning first diverged from the expected path.

#### 30.6.2 Identifying the First Wrong Turn

The first wrong turn is often not where the error surfaces — it is three to five turns earlier, where the agent made an assumption based on a misleading tool result or a compression artifact. Look for:

- A tool result that returned partial or empty data and the agent treated it as complete
- A compression event that removed context the agent later referenced incorrectly
- A goal injection that used stale sub-goal state
- A model response that expressed high confidence about something it could not have known from the available context

The first wrong turn is typically the one where the agent's output was plausible-looking but subtly incorrect. All subsequent turns were internally consistent but based on a wrong premise.

#### 30.6.3 The "Turn Replay" Technique

Once you have identified the likely first wrong turn, replay it: reconstruct the exact context the model received at that turn (from logs) and call the model again with the same context. If you get the same wrong response, the issue is in the context or the model behavior. If you get a different response, the issue was non-determinism — and you need to design a test that catches this class of failure reliably.

Turn replay is only possible if you logged the full context at each turn or can reconstruct it from turn-by-turn deltas. This is why logging completeness matters.

#### 30.6.4 Prompting the Agent to Explain Its Reasoning

For failures where the execution log shows what happened but not why the model made a specific decision, ask the model directly. Reconstruct the context at the failure point and add a diagnostic prompt: "Review the reasoning that led to your last action. Explain step by step why you chose that action and what evidence in the context supported it."

This technique does not always work — non-determinism means the model's explanation may not match its original reasoning — but it often surfaces incorrect assumptions that are present in the context and visible once you know where to look.

> [!TIP]
> Keep a "debug session" configuration that sets `temperature: 0` and logs the full model response (not just the parsed tool calls). The raw response often contains reasoning text that reveals why the model chose a specific action, even when that text was not surfaced to the caller.

### 30.7 Session Replay and Post-Mortems

A session replay system records enough state at each turn to reconstruct and re-run any past session. It is the agent equivalent of a system call recorder — not used in normal operation, but invaluable when something goes wrong.

The minimum state required for replay is: the session config (adapter, model, tools, system prompt), the initial user message, and the full turn history including tool results. With these, you can instantiate a new `SessionManager`, load the history via `session.loadHistory()`, and either re-run from the beginning or inject the history up to a specific turn and run from there.

```typescript
// Session replay from a stored execution record
async function replaySession(
  record: SessionExecutionRecord,
  replayFromTurn: number = 0
): Promise<string> {
  const session = new SessionManager({
    ...record.config,
    sessionId: `replay-${record.sessionId}`,
  });

  if (replayFromTurn > 0) {
    // Load history up to the replay point
    const historySlice = record.turns.slice(0, replayFromTurn);
    session.loadHistory(historySlice);
  }

  // Resume from the replay point with the original input
  const originalInput = record.turns[replayFromTurn]?.content as string ?? record.initialMessage;
  return session.run(originalInput);
}
```

Post-mortems for agent failures follow the same structure as SRE post-mortems: timeline, impact, root cause, contributing factors, action items. The agent-specific additions are: the turn at which the failure originated (not just when it was detected), the compression state at failure, and the specific tool result or model response that was the proximate cause.

Keep post-mortems blameless and specific. "The model hallucinated" is not a root cause. "The model was given a context that contained contradictory information about the customer's account status, which it resolved incorrectly" is a root cause with an actionable fix.

### 30.8 Alerting and SLOs for Agents

Define alerts that fire early enough to be actionable. The most useful alerts for agent systems are:

**Session duration alert:** Fire when a session's turn count exceeds 150% of the expected maximum for that agent type. This is an early signal of looping before the session times out.

**Tool failure rate alert:** Fire when the rolling 5-minute error rate for any tool exceeds 10%. Tool failures cascade into session failures with a lag of 5–10 turns.

**Cost spike alert:** Fire when total token consumption for the hour exceeds 200% of the hourly average. Cost spikes typically indicate runaway sessions or an unexpected increase in input size.

**Goal completion rate alert:** Fire when the goal completion rate drops below your SLO threshold for 15 consecutive minutes. This is your user-facing quality signal.

```typescript
// SLO tracking via session outcome logging
onTrace: (event: TraceEvent) => {
  if (event.type === 'system' && event.name === 'session_complete') {
    const outcome = event.metadata?.outcome as 'completed' | 'error' | 'max_iterations';
    metrics.counter('agent.sessions.completed_total', 1, {
      outcome,
      agentType: config.agentType,
    });

    // Report to SLO dashboard
    sloTracker.record({
      service: config.agentType,
      success: outcome === 'completed',
      latencyMs: event.durationMs ?? 0,
    });
  }
},
```

Set your SLO targets based on measured baselines, not guesses. Run your agent on a representative sample of real tasks, measure the actual goal completion rate, and set your SLO at 5–10 percentage points below the measured baseline. This gives you an error budget that reflects real variability without tolerating systematic degradation.

---

## Key Takeaways

- Agent observability requires capturing three signals: structured logs (what happened), distributed traces (causal chain across turns and agents), and aggregated metrics (system-wide patterns). Each answers a different debugging question.
- Log every turn boundary, every tool call with its full arguments and result, every compression event, and every error with full context. Logging summaries and discarding detail is the most common observability mistake.
- The `onTrace` callback is Lemura's primary observability hook — it emits every significant session event as a structured `TraceEvent`. Wire it into your logging and distributed tracing infrastructure from day one.
- The first wrong turn is rarely where the failure surfaces. Work backward from the error to find the turn where the agent's reasoning first diverged — typically a misleading tool result, a compression artifact, or a context inconsistency.
- Turn replay — reconstructing the exact context at a specific turn and re-running the model — is the most effective debugging technique for non-deterministic agent failures.
- Define four core alerts: session duration anomaly, tool failure rate spike, cost spike, and goal completion rate drop. Set SLO thresholds from measured baselines, not guesses.
