---
title: "Chapter 33 — Scaling Agent Systems"
part: "Part VI — Production Engineering"
chapter: 33
page: 45
status: draft
---

*PART VI — PRODUCTION ENGINEERING*

## Chapter 33 — Scaling Agent Systems

> *"One agent is a tool. A thousand concurrent agents are a platform. The gap between the two is not just infrastructure — it's architecture."*

> [!NOTE]
> **Chapter Goal:** By the end of this chapter, you will understand the unique scaling challenges of agent systems, how to architect for horizontal scale, how to manage shared resources (rate limits, databases, queues), and how to test agent systems under load.

---

### 33.1 How Agent Scaling Differs from API Scaling

Scaling a conventional API is a solved problem: add more stateless servers behind a load balancer, spread the traffic, and you are done. Scaling an agent system is fundamentally different. The differences are not incidental — they stem from the nature of what an agent is.

#### 33.1.1 Stateful Execution vs. Stateless Requests

A REST API request carries all the information needed to produce a response: the HTTP method, the path, the headers, the body. The server processes it in milliseconds and forgets it. An agent session carries state that accumulates across potentially dozens of turns. The history of every tool call, every model response, and every compression event must be available at each turn. A load balancer cannot route consecutive turns in the same session to different workers unless you externalize that state first.

The consequence is that naive horizontal scaling — just spin up more copies of your session process — does not work unless every copy has access to the same external state store. You cannot scale agent workers like you scale web server replicas. You must externalize the session state and make your workers truly stateless before horizontal scaling works correctly.

#### 33.1.2 Variable and Unpredictable Duration

A typical API request takes 10–200ms. Your P99 is probably under 2 seconds. Worker capacity planning is straightforward. A typical agent session might take 30 seconds. But some sessions take 10 minutes, and you cannot always predict which ones in advance. A task description of "analyze this spreadsheet" might resolve in 5 turns or spiral into 50 turns of data exploration depending on what the spreadsheet contains.

This variability makes capacity planning harder. If your workers are sized for average sessions, a batch of unexpectedly long sessions will exhaust the worker pool and queue depth will grow. Design your worker pool with a bounded queue and a maximum job age — drop or dead-letter jobs that have been queued longer than your SLO permits, rather than letting them back up indefinitely.

#### 33.1.3 Cascading LLM Rate Limits

When you run 100 concurrent agent sessions, each session generates model API calls. At 2 calls per turn and 10 turns per session, that is 2,000 API calls across 100 sessions — all hitting the same provider API key. Provider rate limits are expressed in tokens per minute (TPM) and requests per minute (RPM). A single-tenant application that stays well within limits can hit those limits instantly when you scale to concurrent sessions. And unlike a database query that fails immediately when the connection pool is exhausted, a rate-limited LLM call often fails with a 429 after a timeout, meaning your workers are holding positions in the worker pool while waiting for a retry — this is the cascading failure mode.

### 33.2 Horizontal Scaling Patterns

Horizontal scaling works for agent systems when you adopt the right patterns.

#### 33.2.1 Worker Pool Architecture

A worker pool is a fixed or dynamically sized set of worker processes that pull jobs from a shared queue. Each worker handles one agent session at a time. The pool size determines your maximum concurrency. Scale the pool up during peak load, scale it down during off-peak to reduce cost.

Size the pool based on your rate limit budget, not your server capacity. If your API key allows 1,000 RPM and each session generates 5 model calls per minute, you can support at most 200 concurrent sessions. Adding more workers above that ceiling only increases queue wait time — the bottleneck is the provider rate limit, not your compute.

#### 33.2.2 Session Affinity: When a Session Must Stay on One Worker

Session affinity routes all turns of a single session to the same worker. This is only necessary if your session state is in memory on the worker. If you have externalized all session state to Redis or a database (which you should), affinity is unnecessary — any worker can handle any turn.

The only legitimate use case for session affinity in a properly designed system is during in-flight sessions that were started before you fully externalized state. Plan for a migration window, and design all new agent workers as stateless from the start.

#### 33.2.3 Stateless Workers with External State

A stateless worker has no in-memory session state. At the start of each job, it loads session history from the external store. It runs the session (one or more turns). It persists the updated history to the external store. It acknowledges the job in the queue. Then it is ready for the next job.

This pattern is what makes horizontal scaling work. When load spikes, you spin up more workers — they all connect to the same external state store and queue. When load drops, you spin down workers — no sessions are lost because all state is external. The external store (Redis for hot state, Postgres for durable history) is the only shared mutable resource, and you scale it independently of the workers.

### 33.3 Rate Limit Management

Rate limits from LLM providers are the most common scaling bottleneck for agent systems. Manage them proactively.

#### 33.3.1 Provider Rate Limits: TPM, RPM

Every LLM provider enforces rate limits on its API. TPM (tokens per minute) limits how many tokens you can consume across all calls in a rolling minute window. RPM (requests per minute) limits the number of individual API calls. Both limits apply per API key, and both can be hit simultaneously — a session that generates many short tool call messages may hit RPM before TPM, while a session that processes long documents may hit TPM first. <!-- Accurate as of 2026-03 — verify before next edition -->

Know your limits before you scale. Check your provider's documentation, and instrument your system to track both dimensions continuously. When you approach a limit in production, you need to know before the 429s start, not after.

#### 33.3.2 Token Bucket Implementation

A token bucket is a classic rate limiting algorithm. You maintain a bucket with a maximum capacity of N tokens. Tokens refill at a fixed rate (say, 100,000 tokens per minute for your TPM limit). Before making an API call, your worker requests to consume the estimated token count from the bucket. If sufficient tokens are available, the call proceeds. If not, the worker waits until tokens refill.

Implement the token bucket in Redis so it is shared across all workers. The Redis `INCR` command with a TTL-based key provides an atomic counter that resets each minute. For more sophisticated implementations, use a Lua script in Redis to atomically check-and-decrement the bucket without race conditions.

```typescript
// Shared token bucket rate limiter using Redis for multi-worker coordination
import Redis from 'ioredis';

export class TokenBucketRateLimiter {
  private redis: Redis;
  private tpmLimit: number;

  constructor(redis: Redis, tpmLimit: number) {
    this.redis = redis;
    this.tpmLimit = tpmLimit;
  }

  // Request capacity from the bucket; waits if insufficient tokens remain
  async acquire(estimatedTokens: number): Promise<void> {
    const key = `rate_limit:tpm:${this.bucketKey()}`;

    // Atomic check-and-increment using Redis INCRBY with expiry
    const pipeline = this.redis.pipeline();
    pipeline.incrby(key, estimatedTokens);
    pipeline.ttl(key);
    const [[, newCount], [, ttl]] = (await pipeline.exec()) as [
      [null, number],
      [null, number]
    ];

    // Set expiry on first use; key resets every 60 seconds
    if (ttl === -1) {
      await this.redis.expire(key, 60);
    }

    if (newCount > this.tpmLimit) {
      // Exceeded limit: decrement and wait for next window
      await this.redis.decrby(key, estimatedTokens);
      const waitMs = (ttl > 0 ? ttl : 60) * 1000;
      await new Promise((r) => setTimeout(r, waitMs));
      // Retry after waiting for the bucket to refill
      return this.acquire(estimatedTokens);
    }
  }

  // Build a per-minute bucket key based on current time
  private bucketKey(): string {
    const now = Math.floor(Date.now() / 60_000);
    return `${now}`;
  }
}
```

#### 33.3.3 Adaptive Rate Limiting

Static token bucket limits work when your usage is predictable. In practice, provider rate limits can change, your application's usage patterns shift, and you may share an API key across multiple services. Adaptive rate limiting adjusts concurrency based on observed 429 responses.

Track your 429 rate as a rolling metric. When it exceeds a threshold (say, more than 1% of calls in the last minute), reduce the number of active workers by 20% and increase the wait time between retries. When the 429 rate drops to zero and stays there for 5 minutes, gradually restore concurrency. This feedback loop prevents the cascade of retries that makes rate limit storms worse.

#### 33.3.4 Multi-Provider Load Balancing

The most robust solution for rate limit management is distributing requests across multiple providers or multiple API keys for the same provider. A multi-provider adapter presents a unified interface to your session but routes each model call to the provider with the most remaining capacity.

```typescript
// Round-robin multi-provider adapter for rate limit distribution
import type { IAdapter, AdapterRequest, AdapterResponse } from 'lemura';
import { OpenAICompatibleAdapter } from 'lemura';

interface ProviderConfig {
  name: string;
  adapter: OpenAICompatibleAdapter;
  weight: number; // Relative weight for weighted round-robin
}

export class MultiProviderAdapter implements IAdapter {
  private providers: ProviderConfig[];
  private currentIndex = 0;
  private callCounts: Map<string, number> = new Map();

  constructor(providers: ProviderConfig[]) {
    this.providers = providers;
    providers.forEach((p) => this.callCounts.set(p.name, 0));
  }

  async complete(request: AdapterRequest): Promise<AdapterResponse> {
    // Simple round-robin selection across healthy providers
    const provider = this.selectProvider();
    this.callCounts.set(
      provider.name,
      (this.callCounts.get(provider.name) ?? 0) + 1
    );

    try {
      return await provider.adapter.complete(request);
    } catch (error: unknown) {
      // On rate limit error, mark provider and retry with next provider
      if (this.isRateLimitError(error)) {
        const fallback = this.selectProvider(provider.name);
        return await fallback.adapter.complete(request);
      }
      throw error;
    }
  }

  private selectProvider(excludeName?: string): ProviderConfig {
    const eligible = excludeName
      ? this.providers.filter((p) => p.name !== excludeName)
      : this.providers;
    const provider = eligible[this.currentIndex % eligible.length];
    this.currentIndex = (this.currentIndex + 1) % eligible.length;
    return provider;
  }

  private isRateLimitError(error: unknown): boolean {
    return (
      error instanceof Error &&
      (error.message.includes('429') ||
        error.message.toLowerCase().includes('rate limit'))
    );
  }

  getCallCounts(): Record<string, number> {
    return Object.fromEntries(this.callCounts);
  }
}
```

### 33.4 Database and Storage at Scale

External state for agent sessions includes session history, checkpoints, logs, and evaluation data. Each has different access patterns and scale requirements.

#### 33.4.1 Session State Storage Under Load

Session history is the most latency-sensitive data your agent workers read and write. At the start of each job, the worker reads the full history. At the end of each turn, it writes the updated history. Under high concurrency, these reads and writes can become a bottleneck.

Use Redis for hot session state — history for sessions currently in progress. Redis provides sub-millisecond read and write latency and supports the data sizes typical of agent histories (typically 10KB–500KB per session). Configure Redis with enough memory to hold all active sessions simultaneously: if you support 1,000 concurrent sessions at an average of 100KB each, you need 100MB of Redis memory for session state alone, plus overhead.

For completed sessions, move history to a cheaper durable store (Postgres, S3) asynchronously after the session ends. Do not let completed session state accumulate in Redis — it consumes memory and increases scan times.

#### 33.4.2 Checkpoint Storage Throughput

Checkpoints are written after every turn in a durable execution pattern. At 1,000 concurrent sessions and 2 turns per second per session, that is 2,000 checkpoint writes per second. This is a meaningful write load. Choose a checkpoint store with sufficient write throughput, or batch checkpoint writes when the strict durable-execution guarantee is not required.

If your tasks can tolerate at-least-once delivery (most can), you can checkpoint every N turns instead of every turn, reducing write load by a factor of N. The tradeoff is that a worker crash between checkpoints means re-running up to N turns from the last checkpoint. For most tasks, re-running 2–3 turns is acceptable.

#### 33.4.3 Log Volume Management

At scale, agent logs can be voluminous. Each turn produces a log entry for the model request, the model response, each tool call, each tool result, and any compression events. At 1,000 sessions with 20 turns each, that is potentially 100,000+ log lines per session batch. Structure your logs so you can query them efficiently.

Use structured JSON logging (not raw text) and ship logs to a log aggregation service. Index on `sessionId`, `turnIndex`, and `eventType` so you can reconstruct a specific session's history from logs when debugging. Set retention policies: keep detailed turn-level logs for 30 days, aggregate metrics for 90 days, summary data indefinitely.

### 33.5 Concurrency Patterns

Within a single session and across sessions, concurrency introduces both opportunity and risk.

#### 33.5.1 Parallel Tool Execution Within a Session

When the model issues multiple tool calls in the same turn — which modern models do frequently when parallel execution is beneficial — you can run them concurrently with `Promise.all` rather than awaiting them in sequence. This reduces turn latency proportionally to the number of parallel calls.

Be careful with shared state. If two tool calls in the same turn both write to the same external resource, you need a locking mechanism or a design that eliminates the shared write. In practice, tool calls within a single turn are usually independent (search this and read that file), so `Promise.all` is safe.

#### 33.5.2 Concurrent Sessions with Shared Resources

Multiple concurrent sessions sharing a database table or a Redis key introduce contention. A rate limiter bucket is the most obvious example — hundreds of workers incrementing the same Redis counter simultaneously requires atomic operations. Any resource that multiple sessions read and write must be protected against concurrent modification.

Design your shared resources for high concurrency from the start. Use Redis atomic operations (`INCR`, Lua scripts) rather than read-modify-write cycles. Use database row-level locking rather than table-level locking. Prefer append-only data structures (event logs) over mutable records where the concurrency pattern allows it.

#### 33.5.3 Mutex and Locking for Shared State

For shared state that cannot be made atomic with simple Redis primitives, implement a distributed lock. Redis provides the Redlock algorithm for this purpose. Acquire the lock, perform the critical section, release the lock. Set a short lock timeout (a few seconds) to prevent deadlock when a worker crashes while holding a lock.

Use distributed locks sparingly — they are a source of latency and a potential deadlock risk. Before implementing a lock, ask whether the shared resource can be redesigned to eliminate the need for mutual exclusion.

### 33.6 Load Testing Agent Systems

You cannot know whether your architecture handles scale until you test it under realistic load. Load testing an agent system is different from load testing an API.

#### 33.6.1 Simulating Realistic Agent Workloads

A realistic agent workload includes sessions of variable duration, tasks drawn from the distribution you expect in production, tool calls with realistic latency, and a mix of short and long sessions. Do not load test with a single simple task repeated 1,000 times — that produces misleadingly optimistic results because it will likely be cached at the provider level and will not exercise the tail of your duration distribution.

Build a workload generator that samples from a task distribution: 60% simple tasks (2–5 turns), 30% moderate tasks (6–15 turns), 10% complex tasks (16–50 turns). Run sessions at your target concurrency for at least 30 minutes — long enough for queue depth, memory, and rate limits to reach steady state.

#### 33.6.2 Finding the Breaking Point

Run the workload at increasing concurrency levels: 50 sessions, 100, 200, 500. At each level, measure queue depth, session latency (P50, P95, P99), error rate, and provider 429 rate. The breaking point is the concurrency level where one of these metrics degrades unacceptably. Common breaking points are the provider rate limit (429s spike), the external state store (Redis latency increases), or the worker pool memory (OOM on workers running long sessions).

Once you know the breaking point, design your system to never reach it in production. Set your autoscaling upper bound at 70% of the breaking point, and alert at 50% so you have time to respond before the system degrades.

#### 33.6.3 Profiling Under Load

Use APM tooling (Datadog, New Relic, or OpenTelemetry with a supported backend) to profile your workers under load. You want to know: where does time go in a typical session? Which tool calls are slowest? How much time does Redis state loading consume? Is the model API call the dominant latency, or is it something else?

In most agent systems, the model API call dominates session latency by a wide margin. But at high concurrency, state loading latency from Redis can become a second bottleneck that is invisible at low scale. Profile under load to catch this before it surprises you in production.

### 33.7 Cost Scaling: Budget at Scale

Token costs scale linearly with usage. At 1,000 sessions per day, you can eyeball costs manually. At 100,000 sessions per day, you need systematic cost management.

#### 33.7.1 Per-Tenant Cost Allocation

Tag every token usage event with the tenant or user ID responsible for it. Lemura's `onTrace` callback fires for every trace event, including `turn_end` events that carry token usage data. In your `onTrace` handler, emit a billing event to your cost tracking system with the tenant ID, the session ID, the turn index, and the input and output token counts.

```typescript
// Per-tenant token cost tracking via the onTrace callback
import { SessionManager, OpenAICompatibleAdapter } from 'lemura';
import type { TraceEvent } from 'lemura';
import { emitCostEvent } from './costTracker';

interface TenantSessionOptions {
  tenantId: string;
  userId: string;
  task: string;
}

// Cost per 1M tokens in USD — verify current pricing with provider
const INPUT_COST_PER_1M = 0.15;
const OUTPUT_COST_PER_1M = 0.60;

export async function runTenantSession(
  options: TenantSessionOptions
): Promise<string> {
  const { tenantId, userId, task } = options;

  const adapter = new OpenAICompatibleAdapter({
    apiKey: process.env.OPENAI_API_KEY!,
    baseURL: 'https://api.openai.com/v1',
  });

  const session = new SessionManager({
    adapter,
    model: 'gpt-4o-2024-08-06',
    sessionId: `${tenantId}-${userId}-${Date.now()}`,

    onTrace: (event: TraceEvent) => {
      // Capture token usage at the end of each turn for billing
      if (
        event.type === 'turn_end' &&
        event.metadata?.inputTokens !== undefined
      ) {
        const inputTokens = event.metadata.inputTokens as number;
        const outputTokens = event.metadata.outputTokens as number;
        const costUsd =
          (inputTokens / 1_000_000) * INPUT_COST_PER_1M +
          (outputTokens / 1_000_000) * OUTPUT_COST_PER_1M;

        // Emit a structured cost event tagged with tenant and session info
        emitCostEvent({
          tenantId,
          userId,
          sessionId: event.sessionId,
          turnIndex: event.turnIndex,
          inputTokens,
          outputTokens,
          costUsd,
          timestamp: new Date().toISOString(),
        });
      }
    },
  });

  const result = await session.run(task);
  return result.output ?? '';
}
```

#### 33.7.2 Aggregate Budget Controls

Set per-tenant monthly budget limits and enforce them before running sessions. When a tenant is within 20% of their budget, send a warning notification. When they reach 100%, reject new session requests with a clear error rather than silently failing mid-session. A session that starts but gets cut off midway is a worse experience than one that is rejected upfront with a clear explanation.

Implement budget controls at the session creation layer, not inside the session. Check the tenant's remaining budget before instantiating `SessionManager`. If budget is exhausted, return an error immediately. This prevents charges from accruing before the check completes.

#### 33.7.3 Cost Anomaly Detection

Even with budget limits, unexpected cost patterns are worth detecting early. A tenant whose usage spikes 3× their 7-day rolling average in a single hour is either experiencing a legitimate usage surge (a product launch, a batch job) or has been compromised and is being used for prompt injection attacks that generate excessive token consumption.

> [!TIP]
> Alert on cost anomalies at the tenant level, not just at the aggregate level. An aggregate budget limit protects you financially; per-tenant anomaly detection protects you from abuse and helps you identify legitimate customers who need a plan upgrade before they hit a wall.

Implement anomaly detection as a scheduled job that runs every 15 minutes. For each tenant, compute their token usage in the last hour and compare it to their 7-day hourly average. If the ratio exceeds your threshold, emit an alert to your on-call channel and temporarily reduce that tenant's concurrency limit while you investigate.

---

## Key Takeaways

- Agent systems are stateful and long-running — they do not scale like stateless API servers. Externalize all session state to Redis or a database before you attempt horizontal scaling.
- Provider rate limits (TPM and RPM) are the first scaling bottleneck. Implement a shared token bucket in Redis to enforce rate limits across all workers, and track 429 rates to trigger adaptive back-off.
- Multi-provider load balancing distributes requests across multiple API keys or providers, multiplying your effective rate limit ceiling. Implement a round-robin adapter with automatic failover on 429 errors.
- Use Redis for hot session state (active sessions), and move completed sessions to durable storage asynchronously. Size your Redis cluster to hold all active sessions in memory simultaneously.
- Run parallel tool calls within a session using `Promise.all` when the calls are independent. Be careful with shared state — use Redis atomic operations or distributed locks where mutual exclusion is required.
- Load test with realistic workloads: variable task duration, mixed session lengths, real tool latency. Find your breaking point and set autoscaling ceilings at 70% of it.
- Tag every token usage event with tenant and user IDs via `onTrace`. Enforce per-tenant budget limits at session creation, and alert on anomalous usage spikes using a rolling average comparison.
