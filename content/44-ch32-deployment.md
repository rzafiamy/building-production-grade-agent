---
title: "Chapter 32 — Deployment Strategies"
part: "Part VI — Production Engineering"
chapter: 32
page: 44
status: draft
---

*PART VI — PRODUCTION ENGINEERING*

## Chapter 32 — Deployment Strategies

> *"How you deploy an agent determines how it fails. Plan for failure before you plan for success."*

> [!NOTE]
> **Chapter Goal:** By the end of this chapter, you will understand the deployment topologies for agent systems, how to choose the right execution environment, how to handle long-running agents in serverless and container environments, and how to implement safe rollouts.

---

### 32.1 Deployment Topologies

Before you choose an execution environment, choose a topology. A topology is the high-level shape of how work flows into your agent and how results flow out. There are four common topologies for production agent systems. The right one depends on your latency requirements, task duration, and the nature of the work.

#### 32.1.1 Synchronous: Request → Agent → Response

The synchronous topology is the simplest: a client sends an HTTP request, the agent runs to completion, and the server returns the result in the response body. No queues, no polling, no out-of-band communication. This pattern works well for tasks that complete in under 30 seconds and where the client can hold an open connection for that duration.

Use synchronous deployment for interactive agent interfaces where the user is waiting at a screen, for internal tooling where latency expectations are flexible, and for agents with tight iteration loops where polling overhead would dominate the user experience. Set a generous HTTP timeout at the load balancer — at least 60 seconds — and ensure your provider SDK has its own timeout configured shorter than the HTTP timeout so a hung provider call does not hold the connection open indefinitely.

#### 32.1.2 Asynchronous: Submit → Poll → Retrieve

The asynchronous topology decouples submission from execution. A client POSTs a task and receives a job ID immediately. A background worker picks up the job, runs the agent session, and stores the result. The client polls `GET /jobs/{id}/status` until the status changes from `running` to `completed`, then fetches the result from `GET /jobs/{id}/result`.

This topology is the right default for agents that may run for minutes. It tolerates provider slowdowns gracefully, allows the client to do other work while waiting, and supports retry logic at both the submission and execution layers. The tradeoff is complexity: you need a job store (a database or cache), a queue, a worker process, and a status API in addition to the agent logic itself.

#### 32.1.3 Event-Driven: Trigger → Agent → Publish

In the event-driven topology, the agent does not respond to HTTP requests at all. It listens for events on a message bus — a new document uploaded to S3, a row inserted into a database, a webhook from an external service — runs a session in response, and publishes its output as a new event. Downstream consumers pick up the agent's output and continue processing.

This topology integrates well with existing event-driven architectures and enables complex pipelines where multiple agents process events in sequence. Its weakness is observability: tracing a problem back through an event chain is harder than tracing an HTTP request through a call graph. Invest in correlation IDs that propagate through every event and every agent session from the start.

#### 32.1.4 Scheduled: Cron → Agent → Store

The scheduled topology runs the agent on a time-based trigger: hourly, daily, or weekly. The agent performs a recurring task — generating a report, scanning a data source for anomalies, syncing information between systems — and stores its output in a database or object store. There is no live caller waiting for a response.

Scheduled agents are simple to reason about and cheap to operate at low frequencies. The main risk is silent failure: if the 2am agent job crashes and nobody is watching, the failure may not surface for hours. Configure alerting on scheduled job completion, not just on errors — a missing completion is just as problematic as an explicit failure.

### 32.2 Execution Environments

Once you know your topology, choose an execution environment. Each environment has a different cost structure, operational model, and set of constraints.

#### 32.2.1 Serverless (Lambda, Cloud Run): Benefits and Limits

Serverless functions are attractive for their operational simplicity: no servers to manage, automatic scaling to zero, and per-invocation billing. For short-running agents (under 15 minutes), they are a reasonable choice. AWS Lambda supports up to 15 minutes of execution time; Google Cloud Run supports up to 60 minutes. <!-- Accurate as of 2026-03 — verify before next edition -->

The limits become painful for long-running agents. Serverless functions lose all in-memory state on termination — there is no persistent connection pool, no warm in-memory cache, and no guarantee that a follow-up invocation will run on the same instance. Cold starts add latency to the first request after a period of inactivity. And because each invocation is isolated, you cannot hold a stateful session object in memory across multiple turns that span invocation boundaries.

To run agents serverlessly despite these limits, use the durable execution pattern described in section 32.3.3.

#### 32.2.2 Containers (Docker, K8s): The Long-Running Sweet Spot

Containers are the best default for production agent deployments. A containerized worker can hold a session in memory for as long as needed, maintain warm connection pools to external services, and run tasks that span hours without hitting platform-imposed timeouts. Docker Compose works for small deployments; Kubernetes is the right choice once you need multiple replicas, rolling updates, and resource quotas.

For batch agent workloads — process this queue of 10,000 documents overnight — use Kubernetes Jobs, which run a defined number of pod completions and shut down when done. For always-on serving agents — handle incoming requests from users — use Kubernetes Deployments with a Horizontal Pod Autoscaler that scales based on queue depth or CPU utilization.

#### 32.2.3 Edge: When Latency Is Everything

Edge deployment runs your agent logic in geographically distributed locations close to end users. Platforms like Cloudflare Workers and Vercel Edge Functions offer sub-50ms cold starts and global distribution. The tradeoff is severe: edge environments have strict memory limits, no filesystem access, and execution time limits measured in tens of milliseconds to a few seconds. That is insufficient for a multi-turn agent session.

The practical use case for edge in agent systems is the API gateway layer: route requests at the edge, enforce authentication and rate limits, and forward to a regional container-based worker for actual execution. Do not try to run `SessionManager` at the edge directly.

#### 32.2.4 Bare Metal: For Maximum Control

Bare metal or dedicated virtual machines give you maximum control over resources, no noisy-neighbor interference, and no platform-imposed execution time limits. The operational overhead is significant: you manage the OS, the runtime, security patching, and capacity planning yourself. For most teams, containers on managed Kubernetes provide 95% of the control with much lower operational burden. Reserve bare metal for cases where token throughput is so high that multi-tenant cloud infrastructure becomes a bottleneck.

### 32.3 Long-Running Agent Challenges in Serverless

If you must use serverless — because your organization standardizes on it or because cost at low scale justifies it — you need to work around three specific challenges.

#### 32.3.1 Timeout Limits

Platform timeouts are hard ceilings. AWS Lambda's 15-minute limit is not negotiable. If your agent reliably completes in under 10 minutes, you have comfortable headroom. If it sometimes runs for 20 minutes, serverless is the wrong execution environment unless you redesign the execution model. Do not assume that a task that takes 5 minutes in development will always take 5 minutes in production — LLM latency spikes, slow tool calls, and large context windows can multiply execution time in unpredictable ways.

#### 32.3.2 Cold Starts and State Loss

A cold start is when a serverless platform creates a new instance of your function from scratch because no warm instance is available. For a Node.js function with several dependencies, this adds 200ms–2s of latency. More importantly, all in-memory state from the previous invocation is gone. If you stored session history in a local variable, it does not survive a cold start.

The implication is clear: never store agent state in a local variable in a serverless function. Always persist it to an external store — Redis, DynamoDB, Postgres — before the function returns, and always reload it at the start of the next invocation.

#### 32.3.3 The Durable Execution Pattern

Durable execution solves the serverless limitation by checkpointing session state after every turn. Each Lambda invocation handles a batch of turns, writes the updated session history to a checkpoint store, and re-enqueues the job for the next batch if the session is not yet complete. The session is reassembled from the checkpoint at the start of each invocation.

```typescript
// Durable agent worker with per-turn checkpointing
import { SessionManager, OpenAICompatibleAdapter } from 'lemura';
import { getCheckpoint, saveCheckpoint } from './checkpointStore';
import { enqueueJob } from './jobQueue';

interface AgentJob {
  jobId: string;
  task: string;
  maxTurnsPerInvocation: number;
}

export async function durableAgentWorker(job: AgentJob): Promise<void> {
  const { jobId, task, maxTurnsPerInvocation } = job;

  // Load any previously checkpointed history for this job
  const checkpoint = await getCheckpoint(jobId);

  const adapter = new OpenAICompatibleAdapter({
    apiKey: process.env.OPENAI_API_KEY!,
    baseURL: 'https://api.openai.com/v1',
  });

  const session = new SessionManager({
    adapter,
    model: 'gpt-4o-2024-08-06',
    sessionId: jobId,
    maxIterations: maxTurnsPerInvocation,
  });

  // Restore prior session history if this is a resumed invocation
  if (checkpoint?.history) {
    session.loadHistory(checkpoint.history);
  }

  // Run the session for up to maxTurnsPerInvocation turns
  const result = await session.run(checkpoint ? '__continue__' : task);

  // Persist the updated history to the checkpoint store
  const updatedHistory = session.getHistory();
  await saveCheckpoint(jobId, {
    history: updatedHistory,
    completedAt: result.output ? new Date().toISOString() : null,
  });

  // If the session is not finished, re-enqueue for the next invocation
  if (!result.output) {
    await enqueueJob({ ...job, task: '__continue__' });
  }
}
```

The checkpoint store must be fast (Redis is the right choice) and must support atomic writes so a crash mid-turn does not corrupt the history. Each saved checkpoint should include the turn index so you can detect and recover from infinite re-queue loops.

### 32.4 Queue-Based Agent Systems

Queue-based systems decouple task submission from execution and provide natural back-pressure when demand exceeds worker capacity.

#### 32.4.1 Task Queues for Agent Jobs

A task queue holds pending agent jobs. Workers poll the queue, claim a job (with a visibility timeout or lock), run the session, and acknowledge completion. If a worker crashes mid-task, the visibility timeout expires and another worker picks up the job. SQS, RabbitMQ, and Redis Streams all work well for this pattern.

Configure the visibility timeout to be at least 150% of your P99 session duration. If most sessions complete in 5 minutes but some take 10, set the visibility timeout to 15 minutes. A timeout too short causes duplicate execution; a timeout too long delays recovery when workers crash.

#### 32.4.2 Priority Queues

Not all agent tasks are equal. A user waiting at a browser for a research result deserves faster service than a background batch job processing yesterday's data. Implement priority by using multiple queues — one for high-priority interactive tasks, one for standard tasks, one for background batch work — and configure your workers to drain the high-priority queue before accepting work from lower-priority queues.

Alternatively, use a priority queue implementation (Redis Sorted Sets work well) that assigns a numeric priority score to each job at submission time. Workers always pull the highest-scoring job available.

#### 32.4.3 Dead Letter Queues for Failed Jobs

Any job that fails more than N times should be moved to a dead letter queue (DLQ) automatically. The DLQ preserves the original job for investigation without letting it loop through the retry mechanism indefinitely. Configure an alert when the DLQ depth exceeds zero — every item in the DLQ represents a task your agent could not complete, and those failures deserve investigation within your defined SLO window.

> [!WARNING]
> A DLQ without monitoring is a graveyard. Tasks pile up silently while users wait. Alert on DLQ depth and review items within your support SLA. Do not let the DLQ become an archive that nobody reads.

### 32.5 Safe Rollout Strategies

Deploying a new agent version is not like deploying a static web page. A bad system prompt update can silently degrade output quality across all sessions. A new tool can introduce permissions that were not security-reviewed. Safe rollout strategies let you discover problems before they affect all users.

#### 32.5.1 Canary Deployments for Agents

A canary deployment routes a small percentage of traffic — typically 1–5% — to the new agent version while the majority continues on the current version. You monitor key metrics (task completion rate, error rate, average turn count, user satisfaction signals) on the canary slice for a defined period before expanding. If the canary metrics are equal to or better than the control, you gradually increase the canary percentage: 5% → 20% → 50% → 100%. If any metric degrades beyond your threshold, you roll back the canary immediately.

#### 32.5.2 Shadow Mode Testing

Shadow mode runs the new agent version in parallel with the current version on every request. The current version's output is returned to the user; the new version runs silently in the background. You compare the two outputs on quality metrics without exposing any user to the new version's behavior. Shadow mode is the safest way to validate a significant change — like a new model version or a major system prompt rewrite — before any user sees it.

The cost of shadow mode is doubled token spend during the testing period. Budget for this explicitly and set a time limit: shadow mode for one week, then make a deployment decision based on the comparison data.

#### 32.5.3 Feature Flags for Agent Behavior

Feature flags let you change agent behavior without a code deployment. Store a flag in your configuration service that controls which system prompt, which tool set, or which model version the agent uses. To test a new behavior, enable the flag for a specific percentage of users or a specific user segment. Disable it instantly if problems arise — no deployment, no rollback, just a flag flip.

```typescript
// Feature flag-driven agent configuration at session creation time
import { getFlag } from './featureFlags';
import { SessionManager, OpenAICompatibleAdapter } from 'lemura';

interface SessionConfig {
  userId: string;
  task: string;
}

const SYSTEM_PROMPTS = {
  control: 'You are a helpful research assistant.',
  variant_a: 'You are a concise research assistant. Be brief.',
};

export async function createAgentSession(
  config: SessionConfig
): Promise<SessionManager> {
  // Evaluate the feature flag for this specific user at session creation
  const flagValue = await getFlag('research_agent_prompt', config.userId);
  const systemPrompt =
    SYSTEM_PROMPTS[flagValue as keyof typeof SYSTEM_PROMPTS] ??
    SYSTEM_PROMPTS.control;

  const adapter = new OpenAICompatibleAdapter({
    apiKey: process.env.OPENAI_API_KEY!,
    baseURL: 'https://api.openai.com/v1',
  });

  return new SessionManager({
    adapter,
    model: 'gpt-4o-2024-08-06',
    sessionId: `${config.userId}-${Date.now()}`,
    systemPrompt,
  });
}
```

#### 32.5.4 Rollback Procedures

Every deployment must have a documented rollback procedure, and that procedure must be tested before it is needed. For container deployments, rolling back means pointing the Kubernetes deployment to the previous image tag — a command that takes 30 seconds. For model version changes, rollback means reverting the model version in your `SessionManager` configuration. For system prompt changes, rollback means reverting the prompt in your configuration store.

Document the rollback procedure in your runbook. Run a rollback drill quarterly. When an incident happens at 3am, the on-call engineer should be able to roll back in under five minutes without reading documentation from scratch.

### 32.6 Configuration Management

Agent configuration — model versions, system prompts, tool settings, resource limits — is as critical as application code. Manage it with the same discipline.

#### 32.6.1 Environment-Specific Configs

Maintain separate configurations for development, staging, and production environments. Development might use a cheaper model and a smaller `maxTokens` to keep iteration fast. Staging uses the same model and configuration as production but connects to non-production data sources. Production uses fully validated configuration with audited tool permissions and production API keys.

Store environment-specific configuration in environment variables or a configuration service (AWS Parameter Store, HashiCorp Vault, or Google Cloud Secret Manager). Never commit environment-specific values to version control. Use a configuration schema validator to catch misconfigurations before deployment.

#### 32.6.2 Secrets Management

API keys for LLM providers, database credentials, and tool API keys are secrets. They must never appear in source code, logs, or container images. Inject secrets at runtime through environment variables, mounted secrets volumes in Kubernetes, or a secrets manager SDK. Rotate secrets regularly, and revoke any key that appears in a log or commit immediately.

Audit which services have access to which secrets. An agent tool that needs read access to a customer database should not use the same database credential as the service that writes to it. Principle of least privilege applies to your agent tools just as it applies to human users.

#### 32.6.3 Model Version Pinning

Never use an unversioned model alias (like `gpt-4o` or `claude-3-sonnet`) in production. Unversioned aliases point to the provider's latest deployment of that model family. When the provider updates the model, your agent's behavior changes without any action on your part — and without any signal in your code. <!-- Accurate as of 2026-03 — verify before next edition -->

Always pin to a specific, dated model version in your `SessionManager` configuration. When you are ready to upgrade, test the new version through your evaluation suite and canary deployment before updating the pinned version in production. Treat a model version upgrade as a deployment that requires the same scrutiny as a code change.

### 32.7 Infrastructure as Code for Agent Systems

All infrastructure for your agent system — queues, databases, container definitions, secrets references, load balancer rules, autoscaling policies — should be expressed as code and stored in version control. Terraform, Pulumi, and AWS CDK are all viable choices. The principle is the same: infrastructure changes go through code review, leave a history, and can be reviewed, tested, and rolled back.

Define your agent worker as a Kubernetes Deployment manifest or a Terraform resource, not as a series of console clicks. Define your SQS queue, your Redis cluster, and your DLQ as Infrastructure as Code resources. When you need to replicate your production environment for load testing or disaster recovery, you should be able to do so with a single command.

Store agent configuration — system prompts, tool definitions, model version — alongside the infrastructure code. A single pull request that updates both the system prompt and the Kubernetes deployment manifest gives reviewers the full context: what changed, why it changed, and what infrastructure it runs on.

> [!TIP]
> Treat your system prompt as infrastructure code, not application logic. Version it in your IaC repository, review it with the same rigor as a Terraform change, and never update it in production without a corresponding change in version control.

---

## Key Takeaways

- Choose your topology before choosing your execution environment. Synchronous works for sub-30-second tasks; asynchronous is the right default for anything longer.
- Serverless imposes hard timeout limits and loses in-memory state between invocations. The durable execution pattern (checkpoint after each turn, re-enqueue if incomplete) lets you run long agent sessions on serverless infrastructure.
- Containers are the sweet spot for production agent deployment: no timeout limits, warm connection pools, and straightforward scaling with Kubernetes.
- Queue-based systems decouple task submission from execution and provide natural back-pressure. Configure dead letter queues and alert on DLQ depth.
- Canary deployments and shadow mode testing let you validate agent behavior changes before exposing all users to them. Never deploy a significant change — new model version, new system prompt, new tool — without a safe rollout strategy.
- Pin model versions in production. Never use unversioned aliases. Treat a model upgrade as a deployment.
- All infrastructure and configuration should be code in version control. This includes system prompts.
