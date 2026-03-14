---
title: "Chapter 36 — Reliability Engineering for Agents"
part: "Part VI — Production Engineering"
chapter: 36
page: 48
status: draft
---

*PART VI — PRODUCTION ENGINEERING*

## Chapter 36 — Reliability Engineering for Agents

> *"Reliability is not a feature you add at the end. It's an architecture decision you make at the beginning."*

> [!NOTE]
> **Chapter Goal:** By the end of this chapter, you will understand how to apply Site Reliability Engineering (SRE) principles to agent systems, define meaningful SLOs, establish incident response procedures, and build a reliability culture for your team.

---

### 36.1 Applying SRE Principles to Agents

Site Reliability Engineering emerged from the observation that software systems behave reliably only when reliability is treated as an engineering discipline — with measurement, targets, budgets, and consequences for missing them. The same insight applies to agent systems, with some significant adaptations required by the nature of agentic execution.

#### 36.1.1 Where Standard SRE Applies

The structural SRE practices transfer directly to agents. Define service level objectives. Measure against them continuously. Maintain an error budget. Require post-mortems for budget exhaustion. Hold reliability reviews before launching new features. These practices work for agent systems because agents are software systems first.

Agents also benefit directly from the infrastructure SRE provides: load shedding under high traffic, circuit breakers for degraded dependencies, capacity planning, and runbook-driven incident response. None of these concepts require modification to apply to an agent service.

#### 36.1.2 Where Agents Break the SRE Model

Standard SRE assumes deterministic success criteria: an HTTP request either returns 200 or it does not. Agents break this assumption. A session that runs to completion may have technically succeeded (no errors) but produced output that does not satisfy the user's intent. A session that ended with `LemuraMaxIterationsError` may have actually completed the task by turn 18 before the agent failed to recognize completion and looped for 32 more turns.

This non-determinism means that availability and latency — the two metrics SRE was designed around — are insufficient for agents. You need a third category of reliability metric: quality. A session that is available (no errors) and fast (within SLA latency) but produces wrong output is a reliability failure that standard SRE would report as a success.

#### 36.1.3 Non-Determinism and Error Budgets

Error budgets work by defining the acceptable rate of failure. If your SLO is 99% availability, your error budget is 1% — you can tolerate failures up to that rate without taking corrective action.

For agents, the "error" must include quality failures, not just technical failures. If your goal completion SLO is 90%, your error budget includes both technical failures (errors, timeouts) and quality failures (the agent completed without error but produced the wrong output). Measuring only technical failures makes your error budget misleading — a 99.9% technically-available agent with 30% quality failures is not a reliable system.

Define your error budget as: `1 - (goal_completion_rate × (1 - technical_failure_rate))`. This combined metric captures both dimensions.

### 36.2 Defining SLOs for Agent Systems

SLOs are commitments to users about service behavior. Define them as observable, measurable properties — not aspirations. "The agent will be helpful" is not an SLO. "The agent will complete the stated task with verified correctness in at least 88% of sessions" is an SLO.

The three SLOs every agent service needs — task completion rate, end-to-end latency, and cost per task — are defined with specific targets and measurement approaches in **Chapter 34 — Monitoring in Production** (sections 34.5.2–34.5.4). This section covers the SRE-specific framing: how to define "success" for agent tasks, and how error budgets work when success is non-deterministic.

#### 36.2.1 Defining "Completed" for Your Agent Type

The hardest part of SLOs for agents is defining what "success" means. Use proxy metrics that correlate with user-perceived quality and that can be measured automatically. Choose proxies that cannot be trivially gamed.

| Agent Type | Completion Definition |
|------------|----------------------|
| Coding agent | Test suite passes with no new errors |
| Research agent | `write_report` called with all required fields |
| Workflow agent | All plan steps at `done` status |
| Conversational agent | LLM-as-judge score ≥ 4.0 on task fulfilment dimension |

<!-- Accurate as of 2026-03 — verify before next edition -->

Set your initial task completion SLO target at 5 percentage points below your measured baseline. If your baseline is 87% task completion, the SLO is 82%. This absorbs normal variance while alerting on systematic degradation. Apply the same principle to your latency and cost SLOs.

#### 36.2.2 Error Budgets and Their Meaning

Your error budget is the amount of reliability you can afford to "spend" over a measurement period (typically 30 days) before you are required to stop shipping new changes and focus on reliability work instead.

Error budget mechanics: if your goal completion SLO is 90% and you measured 87% completion over the past 30 days, you have spent 300% of your budget (3 percentage points against a 10-point budget). Budget exhaustion is an organizational signal: the team should shift from feature work to reliability work until the budget is restored.

This mechanism matters because it makes reliability a business-visible constraint, not just an engineering concern. When the error budget is healthy, the team can ship features aggressively. When it is exhausted, the signal is clear and the response is defined.

### 36.3 Incident Response for Agent Failures

Agent incidents follow the same general lifecycle as software incidents, with agent-specific detection signals and investigation techniques.

#### 36.3.1 Detection: Knowing Something Is Wrong

The detection signals defined in **Chapter 30 — Observability and Debugging** and **Chapter 34 — Monitoring in Production** are the inputs to incident detection. An incident is declared when:

- A quality alert fires and remains active for more than 15 minutes
- A cost spike alert fires at more than 3× expected hourly spend
- A tool failure rate alert fires at more than 25% failure rate for a critical tool
- A session duration alert fires and is associated with user-facing errors

Each alert should route to a Slack channel or PagerDuty rotation, not just appear silently in a dashboard. An alert that nobody sees is not an alert.

#### 36.3.2 Triage: How Bad Is It?

The first five minutes of an incident are triage: determine severity (how many users are affected, how severely), confirm the alert is real (not a monitoring artifact), and establish the blast radius.

Severity guide for agent incidents:

| Severity | Condition | Response Time |
|----------|-----------|---------------|
| SEV-1 | Goal completion rate < 50% or all sessions failing | Immediate — all hands |
| SEV-2 | Goal completion rate down 15–50% or major tool unavailable | 15 minutes |
| SEV-3 | Goal completion rate down 5–15% or isolated tool degradation | 1 hour |
| SEV-4 | Quality degradation detected, no immediate user impact | Next business day |

Triage answers three questions: is this impacting users right now? Is it getting worse? Do we know the proximate cause?

#### 36.3.3 Mitigation: Stop the Bleeding

Mitigation is not the same as resolution. Mitigation stops the harm while investigation continues. Agent-specific mitigations:

- **Rate limiting:** Reduce traffic to the affected agent to limit the blast radius of quality failures
- **Fallback mode:** Switch to a simpler, more reliable model or a rule-based fallback for the affected task type
- **Feature flag:** Disable the specific feature or tool that is causing failures
- **Rollback:** Revert to the previous agent version if a recent deployment is the cause

> [!WARNING]
> Do not attempt root cause analysis during mitigation. Stopping the harm and investigating the cause are sequential, not parallel. An engineer trying to both mitigate and investigate simultaneously typically does neither well.

#### 36.3.4 Investigation: Root Cause Analysis

Once mitigation is in place, investigate the root cause. For agent incidents, root cause analysis follows the turn-level debugging process from **Chapter 30**: identify the first wrong turn, trace backward to the cause, and determine whether the cause is in the model, the tools, the context management, the system prompt, or the external dependencies.

The most common root causes of agent quality incidents in production:

1. **Model provider update:** The underlying model changed behavior silently — a new version was deployed by the provider without notice. Check provider changelogs and run your golden dataset against both the old and new model behavior.

2. **Tool regression:** A dependency the agent uses changed its response format or started returning errors at an elevated rate. Check tool call success rates by tool name in the incident timeframe.

3. **Prompt regression:** A recent system prompt or goal template change interacted unexpectedly with real-world task distributions that were not in the A/B test sample.

4. **Context overflow:** Real-world tasks are longer or more complex than the test distribution, causing context overflow in sessions that the test suite handled correctly.

5. **Cost-triggered throttling:** The agent is being rate-limited by the provider because of a cost spike, causing degraded performance that looks like quality failure.

#### 36.3.5 Prevention: Post-Mortem Actions

Every SEV-1 and SEV-2 incident requires a post-mortem within 48 hours. The post-mortem produces action items — specific, owned, time-bound engineering tasks — that prevent the same incident from recurring.

The most valuable action items are the ones that close detection gaps: "we did not know this was happening until users reported it" is the most dangerous finding in a post-mortem. The action item should be: "add automated detection for this condition so it surfaces within 5 minutes, not 2 hours."

### 36.4 Graceful Degradation

An agent that is unavailable is worse than an agent that is degraded. Design your agent to degrade gracefully under the conditions that are most likely to occur in production: model provider latency, tool failures, and context overflow.

#### 36.4.1 Identifying Degradation Points

List every external dependency your agent has, in order of failure likelihood:
1. The model provider API
2. Each tool's external dependency (database, HTTP API, filesystem)
3. The context compression adapter (which calls the model)
4. The session storage system

For each dependency, define: what happens to the session if this dependency fails, and what the fallback behavior should be.

#### 36.4.2 Fallback Behaviors at Each Layer

**Model provider failover:** If the primary provider returns errors, fail over to a secondary provider or a smaller, locally-hosted model. The output quality may be lower, but completing the task at degraded quality is better than not completing it at all. See **Chapter 10 — Provider Adapters** for the implementation.

**Tool failure fallback:** When a non-critical tool fails, the agent should continue without it and note the limitation in its output. When a critical tool fails (e.g., `run_tests` in a coding agent), the agent should escalate to a human rather than proceeding. Define which tools are critical and which are optional in your session configuration.

**Compression failure fallback:** If the compression strategy fails to reduce context sufficiently, fail gracefully rather than submitting a request that will exceed the context window. Return the partial result the agent has produced so far rather than losing all progress.

```typescript
// Graceful degradation configuration: secondary provider + tool timeouts
import { SessionManager } from 'lemura';

async function createResilientSession(
  primaryAdapter: IProviderAdapter,
  fallbackAdapter: IProviderAdapter
): Promise<SessionManager> {
  let activeAdapter = primaryAdapter;

  // Health-check the primary adapter before creating the session
  const primaryHealthy = await primaryAdapter.healthCheck().catch(() => false);
  if (!primaryHealthy) {
    console.warn('Primary provider unavailable — using fallback');
    activeAdapter = fallbackAdapter;
  }

  return new SessionManager({
    adapter: activeAdapter,
    model: activeAdapter === primaryAdapter ? 'gpt-4o-2024-08-06' : 'gpt-4o-mini',
    maxTokens: 128000,
    toolRegistryTimeoutMs: 10_000,  // 10s timeout per tool — fail fast
    maxIterations: 25,
    onTrace: (event) => {
      if (event.type === 'error' && event.name === 'adapter_error') {
        // Switch to fallback adapter mid-session if primary degrades
        sloTracker.recordDegradation({ reason: 'adapter_failure' });
      }
    },
  });
}
```

#### 36.4.3 User Communication During Degradation

When the agent is degraded, tell users. A user who waits 10 minutes for an agent running in degraded mode does not know whether the agent is working, broken, or stuck. Define user-facing messages for each degradation level:

- **Partial degradation:** "Some tools are temporarily unavailable. Results may be incomplete."
- **Fallback mode:** "The agent is operating in limited mode due to high demand. Response quality may be reduced."
- **Unavailable:** "The agent is temporarily unavailable. Please try again in a few minutes."

These messages are better than silence. Users who know the system is degraded adjust their expectations and are less likely to report a support issue for expected degradation behavior.

### 36.5 Dependency Reliability

Your agent is only as reliable as its least reliable dependency. Map and manage dependency reliability explicitly.

#### 36.5.1 LLM Provider Outages and Failover

Major model providers experience outages. These are typically partial and short (minutes to an hour), but they affect all customers simultaneously. Your agent will see elevated error rates and latency during provider outages, and there is nothing you can do at the session level to prevent it.

Design for provider outages with:
- A secondary provider configured as a fallback (different provider, not just different endpoint of the same provider)
- A circuit breaker that triggers failover after 3 consecutive adapter errors within 60 seconds
- A status page for your own users that surfaces provider status without exposing internal architecture

<!-- Accurate as of 2026-03 — verify before next edition -->

#### 36.5.2 Tool Dependency Failures

Tools call external services — databases, HTTP APIs, file systems — that can fail independently. Each tool should have:

- A defined timeout (set in `IToolDefinition.timeoutMs`)
- A clear error response when the external service is unavailable (not an unhandled exception)
- Retry logic for transient failures (typically 3 retries with exponential backoff)
- A fallback behavior or explicit escalation when retries are exhausted

```typescript
// Tool with retry logic and graceful failure mode
import type { IToolDefinition } from 'lemura';

function withRetry(tool: IToolDefinition, maxRetries = 3): IToolDefinition {
  return {
    ...tool,
    async execute(params, context) {
      let lastError: Error | undefined;
      for (let attempt = 0; attempt <= maxRetries; attempt++) {
        try {
          return await tool.execute(params, context);
        } catch (err) {
          lastError = err as Error;
          if (attempt < maxRetries) {
            // Exponential backoff: 500ms, 1000ms, 2000ms
            await new Promise((r) => setTimeout(r, 500 * Math.pow(2, attempt)));
          }
        }
      }
      // Return a structured error after all retries exhausted
      return {
        success: false,
        error: `${tool.name} unavailable after ${maxRetries} retries: ${lastError?.message}`,
        retryable: false,
      };
    },
  };
}
```

#### 36.5.3 Third-Party API Stability

Third-party APIs change. A tool that worked correctly for three months may start failing because the API changed its response format, deprecated an endpoint, or introduced a new authentication requirement. This is a routine maintenance issue that you need to detect quickly.

Add API contract tests for every external API your tools depend on. Run these tests on a nightly schedule. When a contract test fails, you have detected an API change before it affects users. Alert on contract test failures the same way you alert on production failures — they will become production failures within hours if not addressed.

### 36.6 Building a Reliability Culture

Tools and processes are necessary for reliability but not sufficient. Reliability requires a cultural commitment from the team — an agreement that preventing failures is as important as shipping features, and that the team is collectively responsible for the system's behavior in production.

#### 36.6.1 Blameless Post-Mortems

The blameless post-mortem is the foundational practice of reliability culture. When something goes wrong, the team analyzes what happened and why — focusing on the system conditions that allowed the failure, not on the individual who made the change that caused it.

Blameless post-mortems work because most production failures are system failures, not individual failures. A system that allows a single change to cause a production incident without detection has failed — regardless of who made the change. The post-mortem should ask: why did our process not catch this? Why did our monitoring not alert sooner? What system change would prevent this class of incident?

Write post-mortems in a shared document. Publish them internally after every SEV-1 and SEV-2 incident. Review them in a retrospective meeting with the full team. The most valuable post-mortems become reference documents that new team members read to understand the failure landscape of the system.

#### 36.6.2 Reliability Reviews Before Launch

Before launching a new agent or a significant change to an existing one, conduct a reliability review. The review answers: what are the failure modes of this change? How will we detect them? What is the mitigation plan? Have we tested the failure paths?

A reliability review does not need to be a long meeting. It can be a one-page document that the engineer fills out and the team lead reviews. The value is in the act of answering the questions systematically — it surfaces assumptions about failure handling that are often wrong or untested.

Required questions for every reliability review:
1. What happens when the LLM provider is unavailable?
2. What happens when each tool fails?
3. What is the maximum cost for a single session, and is that bounded?
4. How will we detect quality degradation within 15 minutes of deployment?
5. What is the rollback procedure and how long does it take?

#### 36.6.3 On-Call Rotation and Runbooks

Every production agent service needs an on-call rotation: a team member who is responsible for responding to alerts during their on-call period. On-call should rotate weekly across the team — no single person should be permanently responsible for production health.

Runbooks are the on-call engineer's guide to specific failure conditions. Write a runbook for every recurring alert type. A runbook answers: what does this alert mean, what is the typical cause, how do I diagnose it, and what are the standard mitigations? A well-written runbook lets any team member handle an incident without requiring the engineer who built the system.

Runbook template for agent incidents:

```text
## Alert: Agent Goal Completion Rate Drops Below SLO

### What it means
Goal completion rate for [agent_name] has dropped below [X]% for 15+ minutes.

### Typical causes (check in this order)
1. Model provider incident — check provider status page
2. Recent deployment — check deploy log for changes in past 2 hours
3. Tool failure — check tool_call_success_rate metric by tool_name
4. Real-world task shift — check if task distribution has changed (longer inputs, new task types)

### Diagnostic steps
1. Pull the last 20 failed sessions: `SELECT * FROM sessions WHERE completed=false ORDER BY created_at DESC LIMIT 20`
2. Identify the common failure turn: which turn does the session typically fail on?
3. Check the tool call log for that turn: which tool was called last before failure?

### Standard mitigations
- Provider outage: activate fallback provider via feature flag `AGENT_USE_FALLBACK_PROVIDER=true`
- Recent deployment regression: run `./scripts/rollback-agent.sh [agent_name]`
- Tool failure: disable affected tool via `./scripts/disable-tool.sh [tool_name]`

### Escalation
If mitigation does not restore completion rate within 30 minutes, page the on-call lead.
```

---

## Key Takeaways

- Apply standard SRE practices to agents with one critical adaptation: add quality (goal completion rate) as a third reliability dimension alongside availability and latency. Technically-available agents that produce wrong output are reliability failures.
- Define three SLOs (fully specified in **Chapter 34**): task completion rate, end-to-end latency by percentile, and cost per successful task. Set initial targets 5 percentage points below your measured baseline.
- Define "completed" with a precise, ungameable proxy metric for your agent type before setting the SLO number — vague success criteria make the SLO meaningless.
- The combined error budget formula is `1 - (goal_completion_rate × (1 - technical_failure_rate))`. Separate technical and quality failures in your budget accounting.
- Incident response is sequential: mitigate first, investigate second. Never attempt root cause analysis before harm is stopped.
- The five most common root causes of agent quality incidents are model provider updates, tool regressions, prompt regressions, context overflow with real-world data, and cost-triggered throttling. Check them in this order.
- Design for graceful degradation at every dependency layer: provider failover, tool fallbacks, compression failure handling. A degraded agent is better than an unavailable one.
- Reliability culture requires blameless post-mortems, reliability reviews before launch, on-call rotation with written runbooks, and contract tests for every external API dependency.
