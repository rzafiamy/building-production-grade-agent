---
title: "Chapter 34 — Monitoring in Production"
part: "Part VI — Production Engineering"
chapter: 34
page: 46
status: draft
---

*PART VI — PRODUCTION ENGINEERING*

## Chapter 34 — Monitoring in Production

> *"Your agent is running. Your users are using it. Do you know if it's working?"*

> [!NOTE]
> **Chapter Goal:** By the end of this chapter, you will be able to build a production monitoring system for agents: dashboards, alerts, SLOs, and runbooks that tell you when something is wrong and how to fix it.

Deploying an agent to production is a milestone, but it is not the finish line. The moment real users start running real tasks, you enter a new phase of the work: observing what the agent does, understanding whether it is succeeding, and catching problems before they become customer-visible failures.

Monitoring an agent system is harder than monitoring a standard web service. A traditional API either returns a 200 or it doesn't. An agent session might return a 200 with output that is completely wrong, or it might silently exhaust its token budget without completing the task. You cannot treat agent monitoring as a thin wrapper around HTTP response codes. You need to observe the agent's behavior at a semantic level.

This chapter walks you through building a production-grade monitoring system for Lemura agents: what to measure, how to collect it, how to visualize it, how to alert on it, and how to write runbooks that let on-call engineers fix problems at 3am without needing to understand the full codebase.

### 34.1 What Production Monitoring Must Cover

Agent monitoring has four distinct questions to answer. Each question corresponds to a different category of failure. You need instrumentation that can answer all four.

#### 34.1.1 Is the Agent Running?

This is the simplest question, but it is not trivial. "Running" means the session infrastructure is accepting requests, the LLM provider is reachable, and sessions are completing without crashing. Infrastructure-level liveness is a prerequisite for everything else.

Measure this with: session start rate, session completion rate, unhandled exception rate, and LLM API error rate. If sessions are crashing before producing any output, nothing else matters. These metrics are your first line of defense.

You also want a synthetic heartbeat: a lightweight task that runs every five minutes, makes one tool call, and completes. If the heartbeat fails twice consecutively, you fire a SEV-1 alert before any real user encounters the problem. Design the heartbeat task to exercise the critical path — it should call the same LLM provider and at least one key tool that your production sessions use.

#### 34.1.2 Is the Agent Completing Tasks?

A session can complete without completing the user's task. The agent might return output that says "I was unable to do this," or it might produce content that doesn't address the request at all. Task completion rate is your primary business metric, and it is separate from session success rate.

Measure this with a combination of automated signals and human review sampling. Automated signals include: did the agent call the expected terminal tool, did the session reach the expected terminal state, does the output contain the required structured fields? You cannot fully automate task completion measurement because what counts as "complete" is context-dependent. Design your agents to emit explicit completion signals that you can observe programmatically — a final tool call, a structured output field, a confidence marker in the response.

At high volume you need both automated measurement and a human review queue. Sample 2-5% of completed sessions for human review. The humans in that review queue are your ground truth for quality measurement.

#### 34.1.3 Is the Agent Completing Tasks Correctly?

Completion and correctness are different. The agent might complete a task with the wrong answer, or it might address 80% of the request and miss the critical remainder. Correctness monitoring requires either human review or an automated judge.

At scale, you cannot manually review every session. Use LLM-as-judge for automated quality scoring (covered in Chapter 35 in detail), and combine it with user feedback signals: thumbs-up/thumbs-down ratings, whether the user submitted the same task immediately after receiving output (a strong implicit signal that the first result was unsatisfactory), and whether the user explicitly requested corrections.

Track quality scores as a metric, not just as a per-session property. If your average quality score drops from 4.2 to 3.8 over a week, that trend is worth investigating even if no individual session failed catastrophically. Trends tell you about systematic degradation that individual alerts miss.

#### 34.1.4 Is the Agent Within Budget?

Token cost is not a reliability concern until it suddenly is. An agent that completes tasks correctly but burns ten times the expected token budget will create a serious financial problem before your users ever notice quality issues. Track cost-per-task as a first-class metric with both a warning threshold and a hard limit.

Cost monitoring also serves as an early warning system for bugs and regressions. If a refactored system prompt suddenly doubles token usage, that shows up in the token economy dashboard immediately — even if task completion rate is unaffected. Cost anomalies are often the first observable signal that something changed in the agent's behavior.

### 34.2 The Agent Monitoring Stack

A production agent monitoring stack has four layers: metrics collection, log aggregation, trace storage, and a visualization layer. **Chapter 30 — Observability and Debugging** covers the foundational instrumentation — how to wire the `onTrace` callback, what events to log, and how to set up distributed tracing for multi-agent systems. This section focuses on the production-specific configuration decisions for each layer.

#### 34.2.1 Metrics Collection

The key Prometheus metric names for a Lemura agent service:

- `agent_session_started_total` — counter
- `agent_session_completed_total` — counter, labeled by `status` (success/failure/timeout)
- `agent_task_completion_rate` — gauge, rolling 1-hour window
- `agent_tokens_prompt_total` — counter
- `agent_tokens_completion_total` — counter
- `agent_cost_per_task_usd` — histogram
- `agent_session_duration_seconds` — histogram
- `agent_turn_count` — histogram
- `agent_tool_call_total` — counter, labeled by `tool_name` and `status`
- `agent_tool_call_duration_seconds` — histogram, labeled by `tool_name`
- `agent_compression_triggered_total` — counter, labeled by `strategy`

Collect these via the `onTrace` callback — the full TypeScript implementation is at the end of this chapter. One production-critical rule on labels: never use high-cardinality values like `sessionId` as label keys. They will explode your metrics storage. Keep label values to bounded sets: `tool_name` is safe; `userId` is not unless you have a small, fixed user set.

#### 34.2.2 Log Aggregation

Every session should emit structured JSON logs. In production, do not log raw LLM output to your default log stream — it floods storage and almost certainly contains sensitive user data. Log a summary: token counts, tool calls made, compression status, and completion outcome. Route full output only to a separate, access-controlled stream used for quality review sampling. Attach `sessionId` to every log line — it is the correlation key when debugging a specific incident across distributed services.

#### 34.2.3 Trace Storage

Sample traces intelligently in production — storing every trace is cost-prohibitive at scale. The recommended strategy: store 100% of traces for sessions that fail, 100% of traces for sessions that exceed your P99 latency threshold, and 5–10% of successful sessions as a baseline. This captures all the interesting cases without unbounded storage growth.

#### 34.2.4 Recommended Tooling

<!-- Accurate as of 2026-03 — verify before next edition -->

For metrics: **Prometheus** with a push gateway for serverless environments. Prometheus has the largest community, excellent Grafana integration, and a rich ecosystem of alerting rules. If you are already invested in Datadog, it is a reasonable alternative with better managed infrastructure but higher cost.

For logs: **Loki** if you are self-hosting with Grafana already deployed — its label-based query model pairs well with structured JSON logs and avoids the cost of full-text indexing. **CloudWatch Logs** if your infrastructure is in AWS — lower operational overhead, native integration with Lambda and ECS.

For traces: **Tempo** (self-hosted, integrates natively with Grafana) or **Jaeger** as a standalone trace store. Both support the OpenTelemetry protocol, which means switching between them requires only an exporter configuration change. Avoid vendor lock-in on the trace format.

For dashboards: **Grafana** is the clear choice if you use Prometheus + Loki + Tempo. It provides a unified view across all three data types and supports alerting directly from dashboard panels.

### 34.3 Key Dashboards

You need four dashboards minimum. Each one answers a different operational question. Build all four before your first production deployment, not after.

#### 34.3.1 The Session Health Dashboard

This is your primary operational dashboard. It shows you whether the agent is working right now. An on-call engineer should be able to determine whether an alert represents a real incident within 30 seconds of opening this dashboard.

Panels to include:
- Session start rate (requests per minute) — line chart, last 3 hours
- Session completion rate — line chart with a 95% SLO reference line, last 3 hours
- Session failure rate — line chart with alert threshold line
- P50/P95/P99 session duration — line chart, last 3 hours
- Sessions currently in progress — single-stat gauge
- Unhandled exception rate — line chart

The health dashboard needs one panel that immediately answers the question "is this bad?" A large, colored single-stat panel showing current session completion rate — green above 95%, yellow 90-95%, red below 90% — makes the dashboard scannable in a high-stress incident moment.

#### 34.3.2 The Token Economy Dashboard

This dashboard tracks the financial and computational cost of running the agent. It is the second dashboard to open when an alert fires for cost anomalies, and it is also your primary tool for detecting prompt engineering regressions before they cause visible quality problems.

Panels to include:
- Total tokens consumed per hour — line chart
- Average tokens per session (prompt + completion breakdown) — stacked bar chart
- Estimated cost per session in USD — histogram
- Cost per session over time — line chart with budget threshold
- Sessions that exceeded maximum token budget — count panel
- Compression trigger rate by strategy — bar chart

When the token economy dashboard shows a spike in prompt tokens, check compression trigger rate immediately. If compression is not firing despite high prompt token counts, you have a compression misconfiguration. If compression is firing but not reducing token counts, you have a more serious architectural problem.

#### 34.3.3 The Error Rate Dashboard

This dashboard breaks down failures by type so you can distinguish infrastructure problems from agent logic problems. These are completely different failure modes that require completely different responses.

Panels to include:
- LLM API error rate by error type (rate limit, timeout, model error) — stacked bar chart
- Tool call error rate by tool — bar chart
- Sessions terminated by max iterations — counter with historical trend
- Sessions terminated by timeout — counter with historical trend
- Compression failures — counter
- Retry rate by component — line chart

A high LLM API error rate points to the provider or your API key configuration. A high tool error rate on a specific tool points to that tool's implementation or its downstream dependency. Sessions terminated by max iterations consistently point to agent loop behavior — the agent is spinning in a loop without making progress. These are distinct failure categories, and conflating them leads to wrong diagnoses.

#### 34.3.4 The Tool Performance Dashboard

This dashboard provides per-tool observability. When you have many tools, a single slow or unreliable tool can degrade the entire agent without the session health dashboard revealing which tool is the culprit.

Panels to include:
- Tool call rate by tool name — stacked line chart
- Tool P50/P95/P99 latency by tool — bar chart, updated hourly
- Tool error rate by tool — bar chart
- Tool call count per session by tool — distribution chart
- Most-called tools — ranked list with trend arrows

> [!TIP]
> When you add a new tool to production, add it to the tool performance dashboard on the same day. Establish a latency and error rate baseline during the first two weeks. Without a baseline, you cannot recognize anomalies later.

### 34.4 Alerting Strategy

Monitoring without alerting is archaeology: you find out what went wrong after the fact, when the damage is already done. But alerting without discipline is equally dangerous: engineers learn to ignore alerts when most of them are false positives or noise. You need both coverage and quality.

#### 34.4.1 What Warrants an Alert (vs. a Log Entry)

An alert requires a human to take action within a defined time window. A log entry is a record for later analysis. If nobody needs to act when a condition is true, it is a log entry, not an alert.

Alert-worthy conditions for agent systems:
- Session completion rate drops below 90% for more than 5 minutes (rolling window)
- LLM API error rate exceeds 10% for more than 2 minutes
- Any session exceeds the maximum token budget by more than 2×
- Compression failure rate exceeds 5% in a 10-minute rolling window
- The synthetic heartbeat fails twice consecutively
- Cost per session exceeds 3× the 7-day P90 baseline for more than 10 minutes

Log-worthy (but not alert-worthy) conditions:
- An individual session reaching max iterations (alert if the rate exceeds threshold, not individual events)
- A single tool call timing out and succeeding on retry
- Compression being triggered (expected behavior)
- A session producing output with a low quality score (feeds evaluation, not incident response)

The distinction matters because conflating these two categories is how you build an alert system your team learns to ignore.

#### 34.4.2 Alert Severity Levels

Use three severity levels and be consistent about their definitions. The definitions need to be written down and agreed on by the whole team — not left implicit. These align with the SEV-1/SEV-2/SEV-3 incident severity levels defined in **Chapter 36 — Reliability Engineering for Agents**.

**SEV-1 — Critical:** The agent is effectively unavailable for a meaningful portion of users. Requires immediate response, any time of day or night. Examples: session completion rate below 50%, LLM provider fully unreachable, unhandled exceptions affecting all sessions.

**SEV-2 — High:** The agent is degraded but partially operational. Requires response within 30 minutes during business hours, 1 hour off-hours. Examples: completion rate between 50-90%, a high-traffic tool failing at elevated error rate, latency P99 exceeding 10 minutes.

**SEV-3 — Warning:** An anomaly that needs investigation but is not immediately causing user harm. Requires acknowledgment and triage within 4 hours during business hours. Examples: cost per session exceeding 2× baseline, latency SLO softly breached, compression trigger rate anomalously high.

Never escalate a SEV-3 condition to SEV-1 because it feels urgent in the moment. The severity definitions must be stable or your on-call team cannot build reliable intuitions about what requires them to wake up.

#### 34.4.3 Alert Routing and On-Call

Route SEV-1 alerts to your on-call rotation via pager — PagerDuty and OpsGenie are both mature options. Route SEV-2 alerts to the on-call channel in your team's chat system and email. Route SEV-3 alerts to a dedicated monitoring channel where they can be triaged during business hours without interrupting anyone.

Keep your on-call rotation to engineers who have enough context to act on the alerts they receive. An engineer who has never looked at the agent codebase cannot respond effectively to a 3am SEV-1. Every engineer in the rotation must have read all SEV-1 runbooks before their rotation starts. Make this a formal requirement, not a suggestion.

Document your escalation path clearly. If the on-call engineer cannot resolve a SEV-1 within 30 minutes, who do they call? If the LLM provider is down, what is the business decision authority for switching to a backup provider or suspending the service?

#### 34.4.4 Avoiding Alert Fatigue

Alert fatigue is the state where engineers have been conditioned by too many low-quality alerts to treat all alerts as noise. It is one of the most dangerous states your on-call rotation can enter, because when a real SEV-1 fires, it gets the same mental response as the twenty false-positive SEV-2s that preceded it.

Prevent alert fatigue by:
- Requiring that every new alert has a named owner who commits to responding to it
- Reviewing alert volume monthly and suppressing or deleting noisy alerts before they accumulate
- Setting alert thresholds based on 30 days of historical data, not intuition
- Using rolling window averages instead of point-in-time measurements — agent systems have natural variance that generates false positives when evaluated point-in-time
- Requiring a post-mortem for any alert that fires more than five times in a week without a corresponding real incident

> [!WARNING]
> If your team starts silencing alerts instead of resolving or deleting them, your alert system has already failed. Audit your alert history every sprint. Delete every alert that has not resulted in a real action in the past 30 days. Fewer, better alerts are more valuable than comprehensive but noisy coverage.

### 34.5 Service Level Objectives for Agents

An SLO is a commitment about the reliability of your system expressed as a target percentage over a rolling time window. SLOs are the contract between your team and your users. They also define your error budget — the space you have to take risks, ship experiments, and accept occasional failures in exchange for moving fast.

#### 34.5.1 Defining SLOs for Non-Deterministic Systems

The fundamental challenge: with a standard web API, you define success as "HTTP 200 returned in less than 500ms." With an agent, you need to define what success means, and that definition involves subjective judgment.

Start with the structural success criteria you can measure automatically without human review:
- Did the session complete without an unhandled exception?
- Did the agent call the expected terminal tool or produce output in the expected format?
- Was the session completed within the maximum time limit?
- Did the output pass basic validation (required fields present, valid JSON, etc.)?

Then layer on quality criteria that require sampling:
- Does the output address the user's actual request? (Human review or LLM-as-judge)
- Is the information in the output factually correct? (Human review)
- Did the agent complete the task with a reasonable number of steps? (Automated)

Use rolling window averages over 7-day and 30-day windows, not point-in-time measurements. An agent that completes 98% of tasks in a given hour may drop to 91% in the next hour due to a model provider blip or a spike in hard tasks. A 7-day window absorbs this natural variance while still detecting genuine degradation.

Define your SLOs before you launch, not after your first incident. The post-incident moment is the wrong time to be negotiating what "good enough" means.

#### 34.5.2 Task Completion Rate SLO

**Definition:** The percentage of sessions that reach a successful terminal state, measured over a rolling 7-day window.

**Target:** ≥95% (a 5% error budget per week)

**Measurement:** Track the `status` label on `agent_session_completed_total`. A session counts as successful if it completes without an unhandled exception, calls the designated terminal tool or produces output in the expected format, and does not terminate due to max iterations or context exhaustion.

**Error budget arithmetic:** At 95% SLO with 1,000 sessions per day, your weekly error budget is 350 failed sessions. Track your budget burn rate as a metric. When you have consumed 50% of your weekly error budget by midweek, pause risky deployments and investigate before you breach the SLO.

#### 34.5.3 Latency P50/P95/P99 SLO

**Definition:** Time from session start to session completion, measured at three percentiles.

**Starting targets:**
- P50 ≤ 30 seconds
- P95 ≤ 120 seconds
- P99 ≤ 300 seconds

These numbers are reasonable starting points for a mid-complexity agent making 5-10 tool calls per session. Do not use them as absolute numbers — establish your real baseline from the first two weeks of production traffic and set your SLO as a multiplier on that baseline. If your P95 in production is 45 seconds, a 120-second P95 SLO is so loose it provides no signal.

**Measurement:** Track `agent_session_duration_seconds` as a Prometheus histogram. Compute quantiles in Grafana using `histogram_quantile()`.

#### 34.5.4 Cost per Task SLO

**Definition:** The total LLM token cost (prompt + completion, converted to USD) per successfully completed session, measured as a P90 over a rolling 7-day window.

**Target:** ≤ [established-baseline] × 2.0

Set your baseline from the first two weeks of production data. The initial baseline becomes your benchmark; the SLO is a 2× multiplier on it. This bounds runaway cost growth while allowing natural variation.

**Measurement:** Track `agent_cost_per_task_usd` as a histogram and compute the P90 in Grafana. Use P90 rather than the mean — a few expensive outlier sessions are expected and acceptable; the P90 catches systematic regressions where the entire distribution shifts.

### 34.6 Production Runbooks

A runbook is a step-by-step guide for responding to a specific alert. A good runbook has exactly four sections: detection signal (what triggered this alert), triage steps (determine how bad the situation is), mitigation (stop the bleeding immediately), and follow-up (root cause analysis after the incident is resolved).

Write runbooks before you need them. The engineer woken up at 3am to respond to a SEV-1 alert should not need to think — they should execute a known procedure. Every SEV-1 and SEV-2 alert must have a corresponding runbook that lives in your team's documentation system.

#### 34.6.1 Agent Loop Detected

**Detection signal:** `agent_session_duration_seconds` P99 exceeds 600 seconds, or `agent_turn_count` P99 exceeds 40 turns, or the rate of sessions with `status=max_iterations_reached` exceeds 10% in a 10-minute window.

**Triage steps:**
1. Pull session IDs for the past 30 minutes that hit max iterations from the error rate dashboard.
2. Inspect the turn-by-turn log for one of these sessions. Are the tool calls repetitive? Is the agent calling the same tool with the same arguments repeatedly?
3. Determine whether this is isolated to a specific task type or affects all task types uniformly.
4. Check whether the pattern started after a recent deployment.

**Mitigation:**
- If it started after a recent deployment: roll back to the previous version immediately.
- If it is isolated to a specific task type: block that task type temporarily, routing requests to a fallback error message or human queue.
- If it is broad and systemic: reduce `maxIterations` to 15 as an emergency brake while you investigate the root cause.

**Follow-up:** Review the system prompt and plan generation logic for the affected task types. Loop behavior almost always indicates either that a required tool is not returning what the agent expects, or that the agent's termination condition is ambiguous — it does not know when to stop.

#### 34.6.2 High Token Usage Alert

**Detection signal:** `agent_cost_per_task_usd` P90 exceeds 3× baseline over a 10-minute window, or total hourly token spend exceeds 2× the 7-day hourly average.

**Triage steps:**
1. Open the token economy dashboard. Is the spike in prompt tokens, completion tokens, or both?
2. If prompt tokens are elevated: check whether context compression is firing. If compression is not triggering, check the `triggerAtPercent` value on your `HistoryCompressionStrategy` — if it is set too close to 1.0, compression triggers only after most of the budget is consumed.
3. If completion tokens are elevated: check whether a recent system prompt change is causing the model to produce much longer outputs than before.
4. Check whether the spike is correlated with a specific task type or is uniform across all tasks.

**Mitigation:**
- Temporarily lower `maxCompletionTokens` to cap completion length at a safe value.
- If a specific task type is the culprit, route it to a separate session pool with tighter limits.
- If compression is not firing despite high prompt token counts, check for a misconfigured `triggerAtPercent`.

**Follow-up:** Review the compression strategy configuration and add a `ToolResponseProcessor` for any tool returning verbose output. Test the change on your evaluation dataset before redeploying.

#### 34.6.3 Tool Failure Spike

**Detection signal:** `agent_tool_call_total{status="error"}` for any specific `tool_name` exceeds 20% over a 5-minute window.

**Triage steps:**
1. Use the tool performance dashboard to identify which tool is failing.
2. Read the error messages from the structured logs for that tool. Is this a timeout, an authentication failure, a downstream API error, or a bug in the tool's implementation?
3. If the tool calls an external API, check that API's status page immediately.

**Mitigation:**
- If the external dependency is down: disable the tool temporarily via a feature flag and configure the agent to respond gracefully when the tool is unavailable.
- If authentication failure: rotate the credential and redeploy. Document the rotation in your audit trail.
- If timeout: increase the tool's timeout threshold and add retry logic with exponential backoff if not already present.

**Follow-up:** Every tool that makes an external API call should have retry logic with exponential backoff and jitter. If this tool does not, add it before returning to normal operations. No tool should fail on the first transient error.

#### 34.6.4 Context Compression Failure

**Detection signal:** `agent_compression_triggered_total` is increasing but `agent_tokens_prompt_total` per session is not decreasing, or explicit compression error messages appear in structured logs.

**Triage steps:**
1. Check logs for compression-specific error messages. Is the compression strategy's LLM call failing? Check the API key and endpoint configuration for the adapter used by compression.
2. Check the `preserveFirst` and `preserveLast` configuration on your `SandwichCompressionStrategy`. If the sum of these values equals or exceeds the total turn count, compression cannot remove any turns and will silently fail to reduce context size.
3. Check whether the `triggerAtPercent` threshold on `HistoryCompressionStrategy` is configured correctly.

**Mitigation:**
- If the compression LLM call is failing: switch to `SummaryInjectionStrategy` only, which does not require an LLM call and will at least prevent unbounded context growth.
- If `preserveFirst` + `preserveLast` is too large: reduce `preserveLast` temporarily to create space for compression to operate.
- As an emergency brake: lower `maxTokens` to force sessions to terminate before exhausting the full context window.

**Follow-up:** Add a startup-time validation check that verifies your compression configuration is mathematically consistent before the agent starts serving traffic. Compression misconfiguration is easy to introduce and invisible until you are under production load.

---

Here is the Prometheus metrics collector that plugs directly into Lemura's `onTrace` callback:

```typescript
// prometheusCollector.ts — wire Lemura trace events to Prometheus metrics
import { Registry, Counter, Histogram } from 'prom-client';
import type { TraceEvent } from 'lemura';

export function createAgentMetricsCollector(registry: Registry) {
  const sessionStarted = new Counter({
    name: 'agent_session_started_total',
    help: 'Total agent sessions started',
    registers: [registry],
  });

  const sessionCompleted = new Counter({
    name: 'agent_session_completed_total',
    help: 'Total agent sessions completed',
    labelNames: ['status'] as const,
    registers: [registry],
  });

  const sessionDuration = new Histogram({
    name: 'agent_session_duration_seconds',
    help: 'Agent session duration in seconds',
    buckets: [5, 15, 30, 60, 120, 300, 600],
    registers: [registry],
  });

  const turnCount = new Histogram({
    name: 'agent_turn_count',
    help: 'Number of LLM turns per session',
    buckets: [1, 3, 5, 10, 20, 30, 50],
    registers: [registry],
  });

  const tokensTotal = new Counter({
    name: 'agent_tokens_total',
    help: 'Total tokens consumed',
    labelNames: ['type'] as const,
    registers: [registry],
  });

  const toolCallTotal = new Counter({
    name: 'agent_tool_call_total',
    help: 'Total tool calls by name and status',
    labelNames: ['tool_name', 'status'] as const,
    registers: [registry],
  });

  const toolDuration = new Histogram({
    name: 'agent_tool_call_duration_seconds',
    help: 'Tool call latency in seconds',
    labelNames: ['tool_name'] as const,
    buckets: [0.1, 0.5, 1, 2, 5, 10, 30],
    registers: [registry],
  });

  const compressionTriggered = new Counter({
    name: 'agent_compression_triggered_total',
    help: 'Times context compression was triggered',
    labelNames: ['strategy'] as const,
    registers: [registry],
  });

  // Track in-progress timing by session and tool call
  const startTimes = new Map<string, number>();

  function onTrace(event: TraceEvent): void {
    switch (event.type) {
      case 'session_start':
        sessionStarted.inc();
        startTimes.set(event.sessionId, Date.now());
        break;

      case 'session_end': {
        const t0 = startTimes.get(event.sessionId);
        if (t0 !== undefined) {
          sessionDuration.observe((Date.now() - t0) / 1000);
          startTimes.delete(event.sessionId);
        }
        sessionCompleted.labels(event.status ?? 'unknown').inc();
        if (event.turnCount !== undefined) {
          turnCount.observe(event.turnCount);
        }
        break;
      }

      case 'token_usage':
        tokensTotal.labels('prompt').inc(event.promptTokens ?? 0);
        tokensTotal.labels('completion').inc(event.completionTokens ?? 0);
        break;

      case 'tool_call_start': {
        const key = `${event.sessionId}:${event.toolCallId}`;
        startTimes.set(key, Date.now());
        break;
      }

      case 'tool_call_end': {
        const key = `${event.sessionId}:${event.toolCallId}`;
        const t0 = startTimes.get(key);
        if (t0 !== undefined) {
          toolDuration.labels(event.toolName).observe(
            (Date.now() - t0) / 1000,
          );
          startTimes.delete(key);
        }
        toolCallTotal
          .labels(event.toolName, event.error ? 'error' : 'success')
          .inc();
        break;
      }

      case 'compression_triggered':
        compressionTriggered.labels(event.strategy ?? 'unknown').inc();
        break;
    }
  }

  return { onTrace };
}
```

And here is a runbook-style diagnostic function you can invoke when investigating a suspicious session:

```typescript
// sessionDiagnostic.ts — analyze a loaded session for anomalies
import type { Turn } from 'lemura';

interface ToolStats {
  count: number;
  errors: number;
  totalDurationMs: number;
}

interface DiagnosticReport {
  sessionId: string;
  turnCount: number;
  totalPromptTokens: number;
  totalCompletionTokens: number;
  toolStats: Record<string, ToolStats>;
  compressionEventCount: number;
  maxIterationsReached: boolean;
  estimatedCostUsd: number;
  anomalies: string[];
}

function diagnoseSession(
  sessionId: string,
  turns: Turn[],
  promptCostPer1k: number,
  completionCostPer1k: number,
): DiagnosticReport {
  // Walk the turn history and accumulate diagnostic data
  const report: DiagnosticReport = {
    sessionId,
    turnCount: turns.length,
    totalPromptTokens: 0,
    totalCompletionTokens: 0,
    toolStats: {},
    compressionEventCount: 0,
    maxIterationsReached: false,
    estimatedCostUsd: 0,
    anomalies: [],
  };

  const toolCallSequence: string[] = [];

  for (const turn of turns) {
    report.totalPromptTokens += turn.tokenUsage?.promptTokens ?? 0;
    report.totalCompletionTokens += turn.tokenUsage?.completionTokens ?? 0;
    if (turn.compressionApplied) report.compressionEventCount++;

    for (const call of turn.toolCalls ?? []) {
      const stats = report.toolStats[call.name] ?? {
        count: 0,
        errors: 0,
        totalDurationMs: 0,
      };
      stats.count++;
      if (call.error) stats.errors++;
      stats.totalDurationMs += call.durationMs ?? 0;
      report.toolStats[call.name] = stats;
      toolCallSequence.push(call.name);
    }
  }

  report.estimatedCostUsd =
    (report.totalPromptTokens / 1000) * promptCostPer1k +
    (report.totalCompletionTokens / 1000) * completionCostPer1k;

  // Detect repetitive tool call loop (5 consecutive same-tool calls)
  for (let i = 0; i <= toolCallSequence.length - 5; i++) {
    const window = toolCallSequence.slice(i, i + 5);
    if (window.every((t) => t === window[0])) {
      report.anomalies.push(
        `Loop detected: "${window[0]}" called 5+ times consecutively`,
      );
      break;
    }
  }

  // Detect high per-tool error rate
  for (const [name, stats] of Object.entries(report.toolStats)) {
    if (stats.count >= 3 && stats.errors / stats.count > 0.5) {
      report.anomalies.push(
        `High error rate on "${name}": ` +
          `${stats.errors}/${stats.count} calls failed`,
      );
    }
  }

  // Detect compression firing but not helping
  if (
    report.compressionEventCount > 0 &&
    report.totalPromptTokens / report.turnCount > 50_000
  ) {
    report.anomalies.push(
      `Compression fired ${report.compressionEventCount}x but ` +
        `average prompt tokens/turn remains high`,
    );
  }

  if (report.turnCount >= 45) {
    report.maxIterationsReached = true;
    report.anomalies.push('Session approached max iterations limit');
  }

  return report;
}

export { diagnoseSession, DiagnosticReport };
```

## Key Takeaways

- Agent monitoring requires four distinct observation categories: liveness, completion, correctness, and cost. Each requires different instrumentation and catches different failure modes.
- Collect metrics via the `onTrace` callback to separate observability concerns from business logic. Wire it once at session setup.
- Build four dashboards before launch: session health (is it working?), token economy (what is it costing?), error rates (what is failing and why?), and tool performance (which tool is the problem?).
- Use rolling window averages for SLO measurement — point-in-time measurements generate false positives from natural variance in non-deterministic agent behavior.
- Three SLOs for agents: task completion rate ≥95% over 7 days; P95 latency ≤120 seconds; cost per session ≤2× baseline P90.
- Three alert severity levels: SEV-1 = agent effectively down, SEV-2 = completion rate SLO breached, SEV-3 = cost or latency anomaly. Keep the definitions stable and aligned with the incident severity framework in **Chapter 36 — Reliability Engineering for Agents**.
- Every SEV-1 and SEV-2 alert needs a runbook in four parts: detection signal, triage steps, mitigation, follow-up. Write them before your first production incident.
