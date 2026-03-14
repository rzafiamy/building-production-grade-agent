---
title: "Chapter 23 — State Persistence and Recovery"
part: "Part IV — Memory and State"
chapter: 23
page: 33
status: draft
---

*PART IV — MEMORY AND STATE*

## Chapter 23 — State Persistence and Recovery

> *"In production, processes crash. Networks fail. Users close tabs. Your agent must survive all of this."*

> [!NOTE]
> **Chapter Goal:** By the end of this chapter, you will be able to design agents that persist their state across restarts, recover gracefully from partial failures, implement checkpoint-based resumption, and handle the consistency challenges of distributed execution.

---

### 23.1 Why Statelessness Fails for Agents

#### 23.1.1 The Cost of Restarting from Scratch

A stateless agent has no memory beyond what is in its current context window. When the process stops — a crash, a deploy, a timeout, a user closing a tab — the agent's entire working state evaporates. On the next invocation, it starts from zero.

For a simple Q&A agent, this is fine. For an agent that has spent forty minutes auditing a codebase, discovered twelve vulnerabilities, cross-referenced them against a threat model, and is halfway through writing the remediation report — restarting from zero is catastrophic. The cost is not just the wasted time. It is the token cost of re-running forty minutes of tool calls, the risk of non-deterministic tool results producing different findings on the second run, and the near-certainty that the user will not wait for it.

The math is unforgiving. A 100-turn session at average 1,000 tokens per turn has consumed 100,000 tokens to reach its current state. Restarting means spending another 100,000 tokens to reconstruct what was already known — and probably getting a slightly different answer. For batch processing agents running thousands of such sessions per day, the cost difference between a stateless and stateful restart policy is measurable in dollars.

Beyond cost, statelessness creates correctness problems. Tool calls that modify external state — writing a file, creating a database record, sending a notification — cannot simply be re-run without risk of duplication. An agent that sent a report on turn 60, crashed on turn 61, then re-ran all 61 turns on restart has now sent the same report twice. The stateless restart model assumes that all operations are safely repeatable. Most production tool calls are not.

#### 23.1.2 Partial Completion and Idempotency

Partial completion is the state of an agent that has completed some but not all of its planned steps when it stops. It is the normal outcome of any crash — the agent was in the middle of doing something when the environment failed.

Recovering from partial completion requires answers to three questions:

1. Which steps were completed before the crash?
2. Which steps had side effects that must not be repeated?
3. What is the minimum state needed to resume from the last known good position?

A stateful agent answers all three by having persisted enough state to reconstruct its position. A stateless agent cannot answer any of them.

Idempotency — the property that executing an operation twice produces the same result as executing it once — is the key invariant for building recoverable agents. An agent built on idempotent tool calls can safely restart from any checkpoint: re-running a step that was already completed produces no new side effects. An agent built on non-idempotent tool calls must track which steps have been executed and skip them on retry.

The design goal: every agent that may restart should either use only idempotent tool calls, or explicitly track which non-idempotent calls have been made and refuse to re-run them.

### 23.2 What State Must Be Persisted

Not all agent state is equally important to persist. Some state is expensive to reconstruct but safe to lose; other state is impossible to reconstruct without re-running tools with potentially different outcomes. Knowing the difference determines what goes in the checkpoint.

#### 23.2.1 The Message History

The message history — the full array of turns produced by `session.getHistory()` — is the primary state artifact. It contains every user message, assistant response, tool call, and tool result from the session's beginning to the current position.

Persisting the full history enables a complete reconstruction of where the agent was. The `Turn` format is plain JSON: an array of objects with `role`, `content`, `toolCalls`, and `toolResults` fields. It is safe to serialize with `JSON.stringify()` and restore with `session.loadHistory()`.

The history is also the largest artifact. A 100-turn session with tool results may serialize to hundreds of kilobytes. For very long sessions, persist only the last N turns plus the compression summary (covered in section 23.2.5) rather than the full history — the compression summary captures what came before at a fraction of the size.

#### 23.2.2 The Plan and Its Execution State

If the session uses `ContinuationPlanner`, the plan and the execution state of each step must be persisted separately from the message history. The message history records what the agent said and did; the plan records which steps have been completed, which are in progress, and which have not yet started.

Persist the plan as a serialized array of `ContinuationStep` objects, each with its current `status` (`pending`, `in-progress`, `done`, `skipped`, or `failed`). Use `getReadySteps()` to identify where to continue after loading.

The plan state is small — typically a few kilobytes even for complex multi-step plans — and is the most valuable state for recovery. Knowing which steps are done means the agent can skip them on retry without re-running their tool calls.

#### 23.2.3 Tool Results and Artifacts

Tool results are already captured in the message history as part of the turn record. But large tool results — file contents, API responses, search result sets — may have been compressed out of the context by the time of the checkpoint. The artifact references (file paths, storage keys, database IDs) must survive even if the content has been compressed away.

Design tools to write their outputs to persistent storage and return lightweight references, not raw content. A tool that fetches a 50,000-token API response, stores it to a file, and returns `{ path: "/artifacts/response-42.json" }` produces a checkpoint-friendly tool result. A tool that returns the 50,000-token response inline produces a checkpoint that depends on that response remaining accessible in context.

The principle: artifacts that the agent may need to reference after resumption must be in durable storage. The checkpoint stores the reference, not the content.

#### 23.2.4 Goals and Sub-Goals

The session goal and the completion status of each sub-goal must be persisted. Goals are set via `session.setGoal()`. Completion per sub-goal is tracked in the `Goal` object's `subGoals` array, each entry carrying a `completed` boolean.

Serializing goals is straightforward: store the goal text and the list of completed sub-goal IDs. On resumption, call `session.setGoal()` with the original goal text and use `markSubGoalDone()` for each previously completed sub-goal to restore the completion state.

#### 23.2.5 Compression Summaries

The compression summary stored in `ctx.compressionSummary` represents the distilled content of all turns that have been removed from the active context. It is the bridge between what the agent has done and what the agent currently knows.

If the compression summary is lost on restart, the agent loses the semantic content of all prior compressed turns. It will have the recent turns (from the loaded history) but not the understanding of what happened before them. The agent will appear to have amnesia about early session events.

Persist `ctx.compressionSummary` as part of the checkpoint. Restore it by setting `ctx.compressionSummary` on the `ContextWindow` before the first post-resumption `run()` call:

```typescript
// Restoring compression summary on session resumption
const session = new SessionManager({ adapter, model, maxTokens });
session.loadHistory(checkpoint.turns);

const ctx = session.getContext();
ctx.compressionSummary = checkpoint.compressionSummary ?? "";
// SummaryInjectionStrategy will inject it on the next turn
```

The compression summary is typically a few hundred to a few thousand tokens. It is the highest-value/size-ratio state artifact: small to store, critical to restore.

### 23.3 Checkpoint Architecture

A checkpoint is a snapshot of all persistent state at a specific point in execution. Good checkpoint architecture minimizes the work lost on restart while keeping the overhead of checkpointing itself acceptable.

#### 23.3.1 After-Turn Checkpointing

After-turn checkpointing saves state after every `run()` call completes. This is the most common and generally recommended strategy: the checkpoint always captures the state after a complete ReAct turn, never in the middle of one.

```typescript
// After-turn checkpointing in a session loop
async function runWithCheckpointing(
  sessionId: string,
  tasks: string[],
  store: ICheckpointStore,
): Promise<void> {
  const session = await restoreOrCreate(sessionId, store);

  for (const task of tasks) {
    await session.run(task);

    // Save checkpoint after each completed turn
    await store.save(sessionId, {
      turns: session.getHistory(),
      compressionSummary:
        session.getContext().compressionSummary ?? "",
      savedAt: Date.now(),
    });
  }
}
```

After-turn checkpointing guarantees that a restart loses at most one turn of work. The overhead is one storage write per turn — negligible for sessions where each turn involves seconds of model reasoning and tool execution.

For high-frequency sessions where turns complete in milliseconds, checkpoint after every N turns rather than every turn to reduce I/O overhead. Use a counter in the session loop and save when `turnCount % checkpointInterval === 0`.

#### 23.3.2 Before-Action Checkpointing (for Destructive Tools)

Some tool calls are irreversible: sending an email, deleting a record, submitting a form, writing to a production database. For these, after-turn checkpointing is not enough — if the crash happens mid-turn, after the destructive tool call but before the turn completes and is checkpointed, the operation has executed but the session state does not yet record it.

Before-action checkpointing saves state immediately before executing any destructive tool call. Implement it in the tool's `execute()` function:

```typescript
// Before-action checkpoint for a destructive tool
const sendReportTool: IToolDefinition = {
  name: "send_report",
  description: "Send the final audit report to stakeholders.",
  parameters: {
    type: "object",
    properties: {
      recipients: { type: "array", items: { type: "string" } },
      reportPath: { type: "string" },
    },
    required: ["recipients", "reportPath"],
  },
  async execute(params, context) {
    // Checkpoint before the irreversible action
    await context.scratchpad?.write(
      context.sessionId,
      JSON.stringify({ sentReport: true, path: params.reportPath }),
    );

    await emailService.send(params.recipients, params.reportPath);
    return { sent: true, recipients: params.recipients };
  },
};
```

The before-action checkpoint does not need to save the full session history — it saves the outcome of the action. On recovery, the agent can check the scratchpad for evidence that the action was already completed and skip it.

#### 23.3.3 Checkpoint Storage Options

The checkpoint store must be:

- **Durable**: survives the process crash that the checkpoint is designed to protect against
- **Fast enough**: the write overhead must not dominate turn execution time
- **Accessible on restart**: the new process can reach the same store as the old one

Three storage options cover the majority of use cases:

**Redis** — best for short-lived sessions (hours to days) where fast read/write is important. Use `SET session:{id}:checkpoint {json} EX {ttl}`. Set the TTL to match your session lifetime; enable `appendonly yes` for crash safety.

**PostgreSQL** — best for long-lived sessions and when you need to query across checkpoints (e.g., "find all sessions in progress when the deploy happened"). Store the checkpoint JSON in a `jsonb` column with the session ID and timestamp as indexed fields. Write the checkpoint in a transaction alongside any business records the session creates.

**File system** — best for local development and batch processing on single machines. Write the checkpoint to a file at a known path (`/checkpoints/{sessionId}.json`). Use atomic writes (write to a temp file, then rename) to avoid partial writes on crash. Simple, fast, and requires no external dependencies.

### 23.4 Resumption Strategies

A checkpoint captures state; a resumption strategy defines how to use it. Three strategies cover the range of scenarios.

#### 23.4.1 Full Resume: From Last Checkpoint

Full resume reconstructs the session exactly as it was at the last checkpoint: same history, same compression summary, same goal. The agent continues as if the crash never happened.

```typescript
// Full resume from last checkpoint
async function restoreOrCreate(
  sessionId: string,
  store: ICheckpointStore,
): Promise<SessionManager> {
  const session = new SessionManager({
    adapter,
    model: "gpt-4o-mini",
    maxTokens: 100_000,
    compressionStrategies: [
      new SummaryInjectionStrategy({ priority: 1 }),
      new SandwichCompressionStrategy(adapter, {
        priority: 20,
        preserveFirst: 4,
        preserveLast: 10,
      }),
    ],
  });

  const checkpoint = await store.load(sessionId);
  if (checkpoint) {
    session.loadHistory(checkpoint.turns);
    session.getContext().compressionSummary =
      checkpoint.compressionSummary ?? "";
    console.log(
      `Resumed session ${sessionId} ` +
      `from turn ${checkpoint.turns.length}`,
    );
  }

  return session;
}
```

Full resume is appropriate when:
- The session history is not too large to reload (under a few hundred turns)
- The agent's last incomplete turn should be retried from the beginning
- All tool calls in the session are idempotent or have been tracked as before-action checkpoints

Full resume has one subtle risk: if the agent was mid-turn when it crashed, the partial turn is not in the checkpoint (checkpointing happens after complete turns). On resumption, the agent will retry the interrupted turn. If that turn contained a non-idempotent tool call that partially executed, full resume may cause a duplicate.

This is why before-action checkpointing and tool-level idempotency are not optional for production agents — they are what makes full resume safe.

#### 23.4.2 Partial Resume: Replaying From a Step

Partial resume uses the plan execution state to identify which steps were completed before the crash and replay only the incomplete ones. Instead of resuming the session at the turn level, it resumes at the step level.

This strategy requires that the agent uses `ContinuationPlanner` and that the plan step completion state is persisted in the checkpoint:

```typescript
// Partial resume using plan step state
const checkpoint = await store.load(sessionId);

if (checkpoint?.planSteps) {
  // Restore the plan with prior step completions
  const plan = checkpoint.planSteps.map(step => ({
    ...step,
    // Completed steps keep their status; others reset to pending
    status: step.status === "done" ? "done" : "pending",
  }));

  session.setPlan(plan);
  session.loadHistory(checkpoint.turns);

  const completedSteps = plan
    .filter(s => s.status === "done")
    .map(s => s.stepId);
  console.log(`Skipping completed steps: ${completedSteps}`);
}
```

Partial resume is appropriate when:
- The plan is long (many steps) and repeating completed steps would waste significant resources
- Individual steps are expensive (slow tools, costly API calls)
- The session history has grown large and a full reload would consume most of the context budget

The trade-off: partial resume is more complex to implement and requires careful step-level idempotency tracking. For short plans (under 10 steps), full resume is usually simpler and adequate.

#### 23.4.3 Summary Resume: Starting Fresh with Context

Summary resume abandons the original session history and starts a new session, injecting a summary of the prior session's progress as initial context. The new session does not attempt to replay completed turns — it simply knows what was done and continues from there.

```typescript
// Summary resume: new session with prior context injected
async function summaryResume(
  sessionId: string,
  store: ICheckpointStore,
  remainingTask: string,
): Promise<string> {
  const checkpoint = await store.load(sessionId);
  if (!checkpoint) throw new Error("No checkpoint found");

  // Generate a summary of the prior session
  const summary = checkpoint.compressionSummary ||
    await generateSummary(checkpoint.turns, adapter);

  const newSession = new SessionManager({
    adapter,
    model: "gpt-4o-mini",
    maxTokens: 100_000,
    compressionStrategies: [
      new SummaryInjectionStrategy({
        priority: 1,
        label: "Prior session summary",
      }),
    ],
  });

  // Inject prior context without reloading turns
  newSession.getContext().compressionSummary = summary;

  const result = await newSession.run(remainingTask);
  return result.output ?? "";
}
```

Summary resume is appropriate when:
- The prior session was very long and reloading the history would fill the context
- A crash happened late in the session and most work is captured in the compression summary
- The session is resuming days or weeks after the original run, when the prior context is largely stale

Summary resume loses the verbatim turn history, which is why it should be used as a fallback — when the history is too large, too old, or unavailable — rather than as the primary strategy.

### 23.5 Idempotency in Tool Calls

#### 23.5.1 Why Tool Idempotency Matters During Recovery

When an agent resumes from a checkpoint and retries a turn, every tool call in that turn executes again. For read-only tools (search, read file, fetch API), this is harmless. For write tools (create record, send message, deploy artifact), re-execution may cause duplicates.

The agent cannot know, in the general case, whether a tool call from a prior run executed before the crash. It knows only that the call is in its pending plan. Without idempotency, every recovery attempt risks doubling the side effects of the interrupted turn.

Idempotency is the invariant that eliminates this risk: a tool call that has already executed, when called again with the same parameters, produces the same result without additional side effects. Building idempotency into tool design is what makes recovery safe by default.

#### 23.5.2 Idempotency Keys

An idempotency key is a stable identifier for a specific tool call instance. The first call with a given key performs the operation and stores the result. Subsequent calls with the same key return the stored result without re-performing the operation.

Generate idempotency keys by combining the session ID, step ID, and a stable hash of the tool parameters:

```typescript
// Generating a stable idempotency key for a tool call
import { createHash } from "crypto";

function idempotencyKey(
  sessionId: string,
  stepId: string,
  params: object,
): string {
  const hash = createHash("sha256")
    .update(JSON.stringify(params))
    .digest("hex")
    .slice(0, 16);
  return `${sessionId}:${stepId}:${hash}`;
}

// Using the key in a tool implementation
const createRecordTool: IToolDefinition = {
  name: "create_record",
  description: "Create a record in the audit log.",
  parameters: {
    type: "object",
    properties: {
      recordType: { type: "string" },
      content:    { type: "string" },
    },
    required: ["recordType", "content"],
  },
  async execute(params, context) {
    const key = idempotencyKey(
      context.sessionId,
      context.currentStepId ?? "adhoc",
      params,
    );

    // Check if this call already executed
    const cached = await context.scratchpad?.read(
      `idempotency:${key}`,
    );
    if (cached) return JSON.parse(cached);

    // Execute and cache the result
    const result = await db.createRecord(params);
    await context.scratchpad?.write(
      `idempotency:${key}`,
      JSON.stringify(result),
    );
    return result;
  },
};
```

Idempotency key storage uses the scratchpad adapter as the backing store, which means it naturally scopes to the session and persists across restarts.

#### 23.5.3 Checking Before Acting

For tools where an idempotency key mechanism is impractical — typically third-party integrations that do not expose idempotency key support — implement the check-before-act pattern: before executing the operation, check whether it has already been performed.

```typescript
// Check-before-act pattern for non-idempotent tools
const deployTool: IToolDefinition = {
  name: "deploy_artifact",
  description: "Deploy an artifact to the staging environment.",
  parameters: {
    type: "object",
    properties: {
      artifactId: { type: "string" },
      environment: { type: "string" },
    },
    required: ["artifactId", "environment"],
  },
  async execute(params, context) {
    const deployKey =
      `deploy:${params.artifactId}:${params.environment}`;

    // Check if already deployed in this session
    const existing = await context.scratchpad?.read(deployKey);
    if (existing) {
      return {
        status: "already_deployed",
        ...JSON.parse(existing),
      };
    }

    const result = await deploymentService.deploy(
      params.artifactId,
      params.environment,
    );
    await context.scratchpad?.write(
      deployKey,
      JSON.stringify({ deployedAt: Date.now(), ...result }),
    );
    return result;
  },
};
```

Check-before-act is weaker than true idempotency: it protects against duplicate execution within a session but not against duplicate execution across sessions or invocations where the scratchpad is not shared. For operations where duplicates are truly dangerous (financial transactions, irreversible infrastructure changes), use a proper idempotency key backed by a durable external store.

### 23.6 Implementing Persistence with Lemura

#### 23.6.1 Session Serialization

A Lemura session's complete persistent state consists of four serializable pieces: the turn history, the compression summary, the goal, and the plan step statuses.

```typescript
// Full session state serialization
interface SessionCheckpoint {
  sessionId:          string;
  savedAt:            number;
  turns:              ReturnType<SessionManager["getHistory"]>;
  compressionSummary: string;
  goal?:              string;
  planSteps?:         Array<{
    stepId: string;
    status: string;
    outputKey?: string;
    resolvedOutput?: unknown;
  }>;
}

function serializeSession(
  session: SessionManager,
  sessionId: string,
  planSteps?: ContinuationStep[],
): SessionCheckpoint {
  const ctx = session.getContext();
  return {
    sessionId,
    savedAt:            Date.now(),
    turns:              session.getHistory(),
    compressionSummary: ctx.compressionSummary ?? "",
    planSteps: planSteps?.map(s => ({
      stepId:         s.stepId,
      status:         s.status,
      outputKey:      s.outputKey,
      resolvedOutput: s.resolvedOutput,
    })),
  };
}
```

Serialize the checkpoint to JSON and store it. The format is intentionally flat — no circular references, no class instances — so it round-trips cleanly through `JSON.stringify()` and `JSON.parse()`.

One important detail: `session.getHistory()` may include turns with tool results already compressed by `ToolResponseProcessor`. The compressed form is smaller but sufficient for resumption — the model needs only the summary, not the original tool result.

#### 23.6.2 Restoring a Session from a Checkpoint

Restoring a session from a checkpoint is the inverse of serialization: create a new `SessionManager`, populate it from the saved state, and it is ready to continue.

```typescript
// Complete session restoration from checkpoint
async function restoreSession(
  checkpoint: SessionCheckpoint,
  config: Omit<SessionConfig, "sessionId">,
): Promise<SessionManager> {
  const session = new SessionManager({
    ...config,
    sessionId: checkpoint.sessionId,
  });

  // Restore turn history
  if (checkpoint.turns.length > 0) {
    session.loadHistory(checkpoint.turns);
  }

  // Restore compression summary
  if (checkpoint.compressionSummary) {
    session.getContext().compressionSummary =
      checkpoint.compressionSummary;
  }

  // Restore plan if present
  if (checkpoint.planSteps && checkpoint.planSteps.length > 0) {
    const restoredSteps: ContinuationStep[] =
      checkpoint.planSteps.map(s => ({
        stepId:      s.stepId,
        status:      s.status as ContinuationStep["status"],
        description: "",   // re-filled from plan definition
        toolName:    "",
        outputKey:   s.outputKey,
        resolvedOutput: s.resolvedOutput,
      }));
    session.setPlan(restoredSteps);
  }

  return session;
}
```

After `restoreSession()` returns, the session is ready to continue. Call `run()` as normal — it will see the restored history and compression summary as if no interruption occurred.

#### 23.6.3 Integration with Redis, PostgreSQL, Files

Each storage backend requires a small adapter that implements the checkpoint store interface. The interface is minimal: `save`, `load`, and `delete`.

**Redis** — appropriate for sessions with a defined lifetime and fast read requirements:

```typescript
// Redis checkpoint store adapter
import { createClient } from "redis";

class RedisCheckpointStore {
  private client = createClient({
    url: process.env.REDIS_URL,
  });

  async save(id: string, cp: SessionCheckpoint): Promise<void> {
    await this.client.connect().catch(() => {});
    await this.client.set(
      `checkpoint:${id}`,
      JSON.stringify(cp),
      { EX: 86_400 },  // 24-hour TTL
    );
  }

  async load(id: string): Promise<SessionCheckpoint | null> {
    await this.client.connect().catch(() => {});
    const raw = await this.client.get(`checkpoint:${id}`);
    return raw ? JSON.parse(raw) : null;
  }

  async delete(id: string): Promise<void> {
    await this.client.connect().catch(() => {});
    await this.client.del(`checkpoint:${id}`);
  }
}
```

**PostgreSQL** — appropriate when checkpoints must be queryable and long-lived:

```typescript
// PostgreSQL checkpoint store (using pg)
import { Pool } from "pg";

class PgCheckpointStore {
  private pool = new Pool({ connectionString: process.env.DATABASE_URL });

  async save(id: string, cp: SessionCheckpoint): Promise<void> {
    await this.pool.query(
      `INSERT INTO session_checkpoints (session_id, data, saved_at)
       VALUES ($1, $2, to_timestamp($3 / 1000.0))
       ON CONFLICT (session_id)
       DO UPDATE SET data = $2, saved_at = to_timestamp($3 / 1000.0)`,
      [id, cp, cp.savedAt],
    );
  }

  async load(id: string): Promise<SessionCheckpoint | null> {
    const result = await this.pool.query(
      "SELECT data FROM session_checkpoints WHERE session_id = $1",
      [id],
    );
    return result.rows[0]?.data ?? null;
  }
}
```

**File system** — appropriate for local development and single-machine batch jobs:

```typescript
// File system checkpoint store
import { writeFile, readFile, unlink } from "fs/promises";
import { join } from "path";

class FileCheckpointStore {
  constructor(private dir: string) {}

  private path(id: string): string {
    return join(this.dir, `${id}.checkpoint.json`);
  }

  async save(id: string, cp: SessionCheckpoint): Promise<void> {
    const tmp = this.path(id) + ".tmp";
    await writeFile(tmp, JSON.stringify(cp));
    await writeFile(this.path(id), JSON.stringify(cp));
  }

  async load(id: string): Promise<SessionCheckpoint | null> {
    try {
      const raw = await readFile(this.path(id), "utf-8");
      return JSON.parse(raw);
    } catch {
      return null;
    }
  }

  async delete(id: string): Promise<void> {
    await unlink(this.path(id)).catch(() => {});
  }
}
```

All three adapters implement the same interface. Swap them by changing the constructor call in your session factory — the rest of the session code is identical.

### 23.7 Distributed Agents and Consistency

Multi-instance agents introduce consistency challenges that single-process agents do not face. When two instances of the same agent can read and write the same checkpoint store, simple read-modify-write patterns break.

#### 23.7.1 The Dual-Write Problem

The dual-write problem occurs when two processes independently read the same checkpoint, make progress, and both write their updated state back to the same key. The second write silently overwrites the first. If the two processes were working on different parts of the same session, the second write loses everything the first process did.

The standard solution is optimistic concurrency control: include a version number in the checkpoint and use a conditional write that only succeeds if the stored version matches the expected version.

```typescript
// Optimistic locking for concurrent checkpoint writes
interface VersionedCheckpoint extends SessionCheckpoint {
  version: number;
}

class OptimisticCheckpointStore {
  async save(
    id: string,
    cp: VersionedCheckpoint,
    expectedVersion: number,
  ): Promise<boolean> {
    const result = await this.pool.query(
      `UPDATE session_checkpoints
       SET data = $1, version = $2
       WHERE session_id = $3 AND version = $4`,
      [cp, cp.version, id, expectedVersion],
    );
    // Returns false if the version didn't match (concurrent write)
    return (result.rowCount ?? 0) > 0;
  }
}
```

If `save()` returns `false`, the calling process lost the race. It should reload the checkpoint, merge its progress, and retry. For most agent workloads — where session IDs are unique and instances do not intentionally share sessions — the dual-write problem only arises during unexpected overlapping retries. Optimistic locking catches these cases without requiring heavy distributed locks.

#### 23.7.2 Leader Election for Long-Running Jobs

For agents that run for hours as scheduled jobs, the risk of two instances running the same session simultaneously is real: the first instance may not have shut down cleanly when the second was scheduled to start.

Leader election ensures that only one instance is actively running any given session at a time. The simplest implementation uses an advisory lock in the checkpoint store: before starting a session, the instance must acquire a lock on the session ID. If the lock is already held, the instance backs off.

```typescript
// Simple session lease using Redis SET NX EX
async function acquireSessionLease(
  sessionId: string,
  instanceId: string,
  ttlSeconds: number,
): Promise<boolean> {
  const result = await redisClient.set(
    `lease:${sessionId}`,
    instanceId,
    { NX: true, EX: ttlSeconds },
  );
  return result === "OK";
}

async function releaseSessionLease(
  sessionId: string,
  instanceId: string,
): Promise<void> {
  const current = await redisClient.get(`lease:${sessionId}`);
  if (current === instanceId) {
    await redisClient.del(`lease:${sessionId}`);
  }
}
```

The lease TTL (`ttlSeconds`) should be longer than the maximum expected time between checkpoint writes. If the instance crashes without releasing the lease, the lease expires automatically and the next instance can acquire it. If the instance is still running and writing checkpoints, it renews the lease with each checkpoint write.

Lease-based leader election prevents the most common distributed agent problem: two instances racing to complete the same session, producing duplicate side effects, and corrupting the checkpoint with conflicting writes.

> [!WARNING]
> Distributed consistency is hard to get right and easy to get subtly wrong. If your agent does not run in multiple instances and does not share checkpoint stores across sessions, you do not need any of this. Add distributed consistency mechanisms only when you have concrete evidence of concurrent access — not as a preemptive measure.

---

## Key Takeaways

- Stateless agents lose all progress on crash; stateful agents with checkpoints lose at most one turn — design every production agent for persistence from the start.
- Persist four artifacts per checkpoint: turn history (`session.getHistory()`), compression summary (`ctx.compressionSummary`), goal text, and plan step statuses — together they fully reconstruct session state.
- Choose the resumption strategy to match the situation: full resume for most cases, partial (plan-step) resume for expensive multi-step plans, summary resume when the history is too large or too old.
- Build idempotency into every tool that has side effects — either through idempotency keys backed by the scratchpad adapter, or through check-before-act patterns — so that retry on recovery never duplicates operations.
- Use optimistic locking or session leases when multiple agent instances may access the same checkpoint store; for single-instance deployments, the simpler file or Redis adapters are sufficient without concurrency machinery.
