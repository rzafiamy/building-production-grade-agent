---
title: "Chapter 27 — Human-in-the-Loop"
part: "Part V — Advanced Patterns"
chapter: 27
page: 38
status: draft
---

*PART V — ADVANCED PATTERNS*

## Chapter 27 — Human-in-the-Loop

> *"Autonomous does not mean unsupervised. The best agents know when to ask."*

> [!NOTE]
> **Chapter Goal:** By the end of this chapter, you will understand when and how to involve humans in agent execution, how to design effective approval workflows, how to implement pause-and-resume sessions, and how to balance autonomy with oversight.

Fully autonomous agents are compelling in theory. In practice, production systems run across a wide spectrum of human involvement — and the most reliable agents are the ones that know precisely when they need a human in the decision loop. This chapter teaches you to design that loop deliberately rather than letting it happen by accident.

### 27.1 Why Human-in-the-Loop?

The phrase "human-in-the-loop" gets used broadly. In the context of autonomous agents, it means something specific: a mechanism that pauses agent execution, presents information to a human, collects a decision or clarification, and then continues execution based on that input. Understanding why you need such a mechanism is the prerequisite to designing it well.

#### 27.1.1 Irreversible Actions Need Human Approval

The most obvious case for human oversight is irreversible action. When an agent sends an email, deletes a database record, submits a payment, or deploys code to production, there is no undo. A single misunderstanding about scope — the agent thought it was authorized to delete all records from 2023, not just one — can create significant damage.

The operational rule is simple: if an action cannot be reversed within your recovery window, a human should confirm it before execution. This is not a failure of agent capability. It is a correct calibration of where human judgment adds the most value.

Every production agent you build should carry a mental model of its action inventory: which tools are reversible reads, which are reversible writes, and which are permanent mutations. That classification directly informs where you place approval gates.

#### 27.1.2 Ambiguous Goals Need Human Clarification

Agents receive goals as natural language. Natural language is imprecise. "Clean up the old reports" could mean archive them, delete them, summarize them, or move them to a different folder. An agent that picks one interpretation and executes confidently is not demonstrating competence — it is guessing with consequences.

The right behavior for an ambiguous goal is to ask before acting. The cost of a clarification round-trip is almost always lower than the cost of executing the wrong interpretation. Well-designed agents surface ambiguity early, ask targeted questions, and only proceed when they have sufficient signal.

#### 27.1.3 High-Stakes Decisions Need Human Judgment

Some decisions are not ambiguous, and they are not irreversible, but they carry enough consequence that human judgment adds real value. Choosing which vendor to contact for a large purchase, determining how to respond to an angry customer, or selecting which feature to prioritize in a roadmap — these are tasks where an agent might produce a technically correct answer but miss organizational context, political nuance, or ethical dimension that a skilled human would naturally apply.

Building in a review step for high-stakes decisions is not a crutch. It is an acknowledgment that current language models do not have access to everything a skilled human brings to a judgment call. The decision about what qualifies as "high-stakes" belongs to you, the system designer. Make it explicit and document it.

#### 27.1.4 The Autonomy Dial: Full Control to Full Autonomy

Think of agent autonomy as a dial with five positions:

**Level 1 — Fully Manual:** The agent suggests an action; the human executes it. The agent is effectively a recommendation engine.

**Level 2 — Approve All:** The agent plans actions; the human approves each one before execution. Every step is confirmed.

**Level 3 — Approve Destructive:** The agent auto-executes reads and reversible operations; it pauses and requests approval for destructive or irreversible actions.

**Level 4 — Notify Only:** The agent executes all actions and notifies the human after each significant step. The human can intervene but is not blocking execution.

**Level 5 — Fully Autonomous:** The agent executes end-to-end without any human checkpoints. Post-hoc review is the only oversight mechanism.

Most production agents targeting real business workflows belong at **Level 3**. Level 3 gives you the efficiency of autonomous execution for the majority of actions while preserving meaningful human oversight at exactly the points where it matters most. You can tune your system along this dial based on the trust you have in the agent, the consequence of errors, and the availability of human reviewers.

### 27.2 Patterns for Human Involvement

There are four distinct patterns for incorporating human involvement in agent workflows. Each has different characteristics in terms of latency, oversight depth, and operational complexity.

#### 27.2.1 Approve-Before-Execute

The agent pauses execution, presents its planned action to a human, and waits for an explicit approval signal before proceeding. This is the synchronous blocking pattern and provides the highest level of oversight.

Use this pattern for irreversible actions, high-value transactions, communications sent on behalf of a user, and any action that the agent itself flags as high-risk. The user experience cost is latency — the agent cannot proceed until a human responds. Design your timeout behavior before you deploy, because the timeout policy is as important as the approval mechanism itself.

#### 27.2.2 Notify-and-Continue

The agent executes an action and simultaneously dispatches a notification. The human receives information but is not blocking execution. The human can trigger an intervention — cancel, rollback, escalate — within a defined window, but inaction implies acceptance.

This pattern works well for medium-risk operations where intervention is possible but not required. Sending a draft message that can be recalled within five minutes, making a reversible database write, or triggering a workflow that has a cancellation path are all good candidates. The critical design requirement is that the intervention window must be long enough for a human to actually act.

#### 27.2.3 Review-After-Complete

The agent completes an entire workflow autonomously and presents the output for human review before the results are committed or acted upon. The human sees the full work product and can approve, reject, or request revisions.

This is the standard pattern for agents that produce documents, reports, or structured outputs. It maximizes agent efficiency — no mid-task interruptions — while still giving humans a veto over the final result. The risk is that the agent may have taken intermediate steps during execution that are not easily undone even if the final output is rejected. Make sure your intermediate steps are reversible before relying on this pattern.

#### 27.2.4 Exception-Based Escalation

The agent runs fully autonomously and only surfaces to a human when it encounters a predefined exception condition: confidence below a threshold, a tool returning an unexpected error, a detected anomaly in inputs, or a risk score above a cutoff. Most runs complete without human involvement.

This pattern is appropriate for well-understood, high-volume tasks where the agent has a strong track record. The operational requirement is that you have clear exception definitions and reliable detection. An exception-based system that escalates too rarely is creating unmonitored risk. One that escalates too frequently defeats the purpose of automation.

### 27.3 Implementing Pause and Await

Turning the approve-before-execute pattern into working code requires a specific implementation approach. The agent needs a mechanism to pause mid-execution, persist its state, wait for an external signal, and resume cleanly.

#### 27.3.1 The Approval Tool Pattern

The cleanest way to implement synchronous approval in Lemura is to give the agent a `request_approval` tool. When the agent determines that an action requires human approval, it calls this tool. The tool blocks until it receives a response, then returns the approval decision to the agent as a tool result. The agent continues from there.

```typescript
// request_approval tool: blocks until human responds or timeout fires
import { IToolDefinition } from 'lemura';

interface PendingApproval {
  resolve: (approved: boolean) => void;
  timer: ReturnType<typeof setTimeout>;
}

const pendingApprovals = new Map<string, PendingApproval>();

export const requestApprovalTool: IToolDefinition = {
  name: 'request_approval',
  description:
    'Pauses execution and requests human approval before proceeding ' +
    'with a potentially sensitive or irreversible action.',
  parameters: {
    type: 'object',
    properties: {
      action_description: {
        type: 'string',
        description: 'Plain-language description of the action to approve.',
      },
      risk_level: {
        type: 'string',
        enum: ['low', 'medium', 'high'],
        description: 'Assessed risk level of the action.',
      },
      timeout_seconds: {
        type: 'number',
        description:
          'How long to wait before auto-denying. Default: 300.',
      },
    },
    required: ['action_description', 'risk_level'],
  },
  async execute(params, context) {
    const approvalId = `${context.sessionId}-${Date.now()}`;
    const timeoutMs = (params.timeout_seconds ?? 300) * 1000;

    const approved = await new Promise<boolean>((resolve) => {
      const timer = setTimeout(() => {
        // Safe default on timeout: deny and escalate
        pendingApprovals.delete(approvalId);
        resolve(false);
      }, timeoutMs);

      pendingApprovals.set(approvalId, { resolve, timer });

      // Notify human via your preferred channel
      notifyHuman({
        approvalId,
        sessionId: context.sessionId,
        actionDescription: params.action_description,
        riskLevel: params.risk_level,
        timeoutMs,
      });
    });

    return {
      approvalId,
      approved,
      respondedAt: new Date().toISOString(),
    };
  },
};

// Called by your web handler when the human clicks Approve or Deny
export function resolveApproval(
  approvalId: string,
  approved: boolean,
): void {
  const pending = pendingApprovals.get(approvalId);
  if (!pending) return; // Already timed out
  clearTimeout(pending.timer);
  pendingApprovals.delete(approvalId);
  pending.resolve(approved);
}

// Replace with your actual notification mechanism
function notifyHuman(payload: {
  approvalId: string;
  sessionId: string;
  actionDescription: string;
  riskLevel: string;
  timeoutMs: number;
}): void {
  // Send Slack message, email, push notification, etc.
  console.log('[APPROVAL REQUESTED]', JSON.stringify(payload));
}
```

The key design decision here is the pending approvals store, keyed by `approvalId`. When the human responds through whatever UI or webhook you provide, your handler calls `resolveApproval`, which unblocks the promise and returns the decision to the agent. The agent then receives either `{ approved: true }` or `{ approved: false }` as its tool result and decides how to proceed based on that signal.

The agent's behavior after receiving the approval result is driven by the system prompt. Include explicit instructions: if `approved` is false, the agent should explain the denial to the user and either stop or propose an alternative path. If `approved` is true, the agent should proceed with the planned action immediately.

#### 27.3.2 Session Suspension and Resumption

The approval tool pattern above works for synchronous cases where the Node.js process stays alive during the wait. For longer-running approvals — anything expected to take more than a few minutes — you need to suspend the session state to durable storage and resume it when the approval arrives.

Lemura's `session.getHistory()` method returns the complete turn history. Serialize this to a database row or object store, keyed by session ID and approval ID. When the approval webhook fires, reconstruct the session with `session.loadHistory()` and continue execution.

```typescript
// Suspending and resuming sessions across approval wait
import { SessionManager, OpenAICompatibleAdapter } from 'lemura';

interface SessionCheckpoint {
  history: ReturnType<SessionManager['getHistory']>;
  suspendedAt: string;
  sessionId: string;
}

// Called before releasing the process while awaiting long-lived approval
async function suspendSession(
  session: SessionManager,
  approvalId: string,
  db: Map<string, SessionCheckpoint>,
): Promise<void> {
  const history = session.getHistory();
  db.set(`checkpoint:${approvalId}`, {
    history,
    suspendedAt: new Date().toISOString(),
    sessionId: session.getContext().sessionId ?? '',
  });
}

// Called when the approval webhook fires with a human decision
async function resumeSession(
  approvalId: string,
  approved: boolean,
  db: Map<string, SessionCheckpoint>,
): Promise<string> {
  const checkpoint = db.get(`checkpoint:${approvalId}`);
  if (!checkpoint) {
    throw new Error(`No checkpoint found for approvalId ${approvalId}`);
  }

  const adapter = new OpenAICompatibleAdapter({
    apiKey: process.env.OPENAI_API_KEY ?? '',
    baseURL: 'https://api.openai.com/v1',
  });

  // Rebuild the session from its stored configuration
  const session = new SessionManager({
    adapter,
    model: 'gpt-4o-mini',
    maxTokens: 100_000,
    maxIterations: 50,
    maxCompletionTokens: 4000,
    sessionId: checkpoint.sessionId,
    tools: [requestApprovalTool /* ...add your other tools here */],
  });

  // Restore all turns up to the suspension point
  session.loadHistory(checkpoint.history);

  // Inject the approval decision as the continuation signal
  const continuationMessage = approved
    ? 'Approval granted. Continue with the planned action.'
    : 'Approval denied. Do not proceed. Inform the user and stop.';

  const result = await session.run(continuationMessage);

  // Clean up the checkpoint now that execution has resumed
  db.delete(`checkpoint:${approvalId}`);

  return result.output;
}
```

In a real deployment, replace the in-memory `Map` with a durable database. The checkpoint record should survive process restarts. Include a TTL on checkpoint records so that abandoned checkpoints do not accumulate indefinitely.

#### 27.3.3 Timeout Handling During Human Pause

Timeouts during human pauses must be handled as a first-class concern, not an afterthought. Humans are unavailable, they miss notifications, or they are simply slow. Your agent must have a defined policy for each of these outcomes.

The safe default is always to deny. If a human does not approve a potentially destructive action within the timeout window, the agent should decline to execute it and report the timeout to the user. Defaulting to approval on timeout would mean that human oversight becomes optional — exactly what you were trying to avoid.

Beyond the safe default, you have three additional options: escalate (notify a different human or a supervisor), retry (send a new notification and extend the window once), or abandon the task (terminate with a partial result and a clear explanation of what stopped execution). Document your timeout policy in the system prompt so the agent knows how to explain the situation to the user when it reports a timeout.

For long-lived approvals that have been suspended to durable storage, implement a background job that scans for expired checkpoints. When a checkpoint's timeout has passed, the job calls the resumption path with `approved: false` and cleans up the checkpoint. This ensures that orphaned approvals do not block sessions indefinitely even if the webhook notification was lost.

#### 27.3.4 Async Approval via Webhooks

In a web-native deployment, the full async approval workflow looks like this: the agent calls `request_approval`, your server stores a pending approval record in the database, a notification is dispatched to the human (email, Slack, push notification, or in-app alert), the human opens the approval UI, reviews the action details, and clicks Approve or Deny. Your server receives this action, updates the database record, and calls your webhook endpoint, which triggers the `resolveApproval` function or the session resumption path.

The webhook approach decouples the approval wait from any individual server process. It is more operationally resilient and scales to arbitrarily long approval windows. The tradeoff is complexity: you need durable storage, a notification system, an approval UI, a webhook handler, and a timeout cleanup job. For a production agent that handles sensitive actions, this infrastructure is not optional — it is table stakes.

Secure your webhook endpoint with a shared secret or HMAC signature. An approval webhook that accepts requests from any source is a privilege escalation vulnerability.

### 27.4 Designing Effective Approval Interfaces

A technically correct approval mechanism only helps if the human can make a good decision quickly. Approval UI design directly determines whether your oversight mechanism is genuinely effective or a rubber-stamp exercise that users learn to click through without reading.

#### 27.4.1 What Information the Human Needs

Every approval request must answer five questions clearly: What is the agent about to do? What data will be affected? Why does the agent believe this is the right action? What is the risk if this is wrong? What happens if they deny approval?

Structuring your `request_approval` tool to require an `action_description` forces the agent to produce a plain-language summary of its intent. Supplement this with the specific parameters of the action — file paths, record IDs, API endpoints — the context that led to this decision, and the consequence of approval or denial.

The agent is the best author of this summary because it has the full context of the task. Prompt it explicitly: include in the system prompt an instruction that when calling `request_approval`, the `action_description` field must answer all five questions in plain language, in three sentences or fewer.

#### 27.4.2 Approval UI/UX Principles

Keep the default action safe. The Deny button should be prominent and easy to click. The Approve button should require a deliberate action. Show a countdown timer prominently if a timeout is in effect — a human should never be surprised that their window has expired.

Display the full action context on a single screen. Do not require the human to navigate to another page to understand what they are approving. For complex actions, provide an expandable details panel that shows the raw tool call arguments in formatted JSON. The expandable panel is for power users; the plain-language summary is for everyone.

If the action involves data the human might want to review before approving — a file to be deleted, a database record to be modified, an email draft to be sent — include a preview or a direct link to that data. Approval without the ability to inspect the subject is not meaningful oversight.

#### 27.4.3 Providing Context Without Overwhelming

The opposite failure mode is information overload. If every approval request dumps the full agent conversation history and raw JSON parameters into the reviewer's screen, humans will start approving everything without reading. That eliminates the value of the oversight mechanism entirely.

Focus on signal. Use the agent's own reasoning in the `action_description` field rather than raw technical data. A message reading "Delete 14 customer records from the 2021 cohort as requested in the cleanup task" is more useful than a raw SQL statement.

Reserve the raw data for the expandable details panel. Reviewers who need it can find it; reviewers who trust the summary can approve quickly without being distracted. The right information density at the top level is the single most important factor in approval quality.

### 27.5 Calibrating Autonomy to Risk

Not every action deserves the same level of scrutiny. An effective autonomy system routes actions to the appropriate oversight level based on their risk profile, rather than applying a uniform policy to everything.

#### 27.5.1 Risk Scoring for Actions

Assign every tool call a risk score based on two dimensions: reversibility and impact. Reversibility is binary or graded — a read operation is fully reversible, a write to an append-only log is partially reversible, deleting a record with no backup is irreversible. Impact measures the scope of effect: does this action touch one record, one user, one system, or many?

Multiply the two factors to produce a composite score. High scores trigger approval gates; low scores allow autonomous execution.

```typescript
// Risk scoring for tool calls — drives autonomy routing
type ReversibilityLevel = 'full' | 'partial' | 'none';
type ImpactLevel = 'minimal' | 'moderate' | 'significant' | 'critical';

interface RiskScore {
  score: number;           // 0–100
  requiresApproval: boolean;
  rationale: string;
}

const REVERSIBILITY_WEIGHTS: Record<ReversibilityLevel, number> = {
  full: 0,
  partial: 30,
  none: 60,
};

const IMPACT_WEIGHTS: Record<ImpactLevel, number> = {
  minimal: 0,
  moderate: 15,
  significant: 30,
  critical: 40,
};

const HIGH_RISK_TOOLS = new Set([
  'delete_record',
  'send_email',
  'deploy_to_production',
  'execute_sql',
  'write_file',
]);

const APPROVAL_THRESHOLD = 50;

function scoreToolCall(
  toolName: string,
  reversibility: ReversibilityLevel,
  impact: ImpactLevel,
): RiskScore {
  const baseScore =
    REVERSIBILITY_WEIGHTS[reversibility] + IMPACT_WEIGHTS[impact];
  const namePenalty = HIGH_RISK_TOOLS.has(toolName) ? 10 : 0;
  const score = Math.min(100, baseScore + namePenalty);

  return {
    score,
    requiresApproval: score >= APPROVAL_THRESHOLD,
    rationale:
      `Tool: ${toolName}, reversibility: ${reversibility}, ` +
      `impact: ${impact}, score: ${score}`,
  };
}

// Example: scoring a record deletion
const deletionScore = scoreToolCall(
  'delete_record',
  'none',       // irreversible
  'moderate',   // affects one record
);
// deletionScore.score === 85, requiresApproval === true

// Example: scoring a read operation
const readScore = scoreToolCall(
  'read_file',
  'full',       // fully reversible
  'minimal',    // affects nothing
);
// readScore.score === 0, requiresApproval === false
```

Maintain a registry that maps each tool in your agent's inventory to its default reversibility and impact levels. Review this registry when you add new tools. The defaults you set here determine whether tool calls flow through autonomously or require approval.

#### 27.5.2 Progressive Autonomy: Trust That Builds Over Time

A newly deployed agent at Level 3 might require approval for any write operation. After a hundred successful write operations of a specific type — say, creating calendar events — you have evidence that the agent is reliable at that task. You can reduce or remove the approval gate for that action type.

Implement progressive autonomy by tracking per-action-type success rates in a persistent store. Each successful execution increments a success counter. Each reversal or human correction decrements trust and resets the counter. After crossing a confidence threshold — for example, 50 consecutive successful executions with no reversals — lower the autonomy level for that action type by one notch.

This approach means your agent becomes more capable over time not because the model improves, but because you accumulate justified trust in its behavior on specific tasks. Document the thresholds clearly so operators can understand and audit the autonomy decisions. Never let the system silently move from Level 3 to Level 5 without explicit operator confirmation.

#### 27.5.3 Audit Trails for Autonomous Decisions

Every autonomous decision — every action the agent takes without a human approval step — must be logged with enough context to reconstruct why it happened. The audit trail should include the session ID, the turn index, the tool name, the full parameters, the risk score that justified bypassing approval, the autonomy level at the time, and a timestamp.

This serves two purposes. First, it provides accountability: if an autonomous action causes a problem, you can trace exactly what happened and why the approval gate was bypassed. Second, it feeds your progressive autonomy system: you need the historical record to compute success rates and justify future threshold changes.

Store audit trails in an append-only log. Never allow records to be deleted or modified retroactively. For regulated industries, route them to a compliant audit system and retain them according to your policy requirements.

### 27.6 The Clarification Request Pattern

The clarification request is the human-in-the-loop pattern for ambiguity rather than risk. The agent does not have enough information to proceed confidently, and asking a human is more reliable than guessing.

#### 27.6.1 When the Agent Should Ask a Question

The agent should ask for clarification at the start of a task, not in the middle of it. Discovering mid-execution that you do not have the information you need is a design failure. Before the agent takes its first substantive action, it should review the goal for ambiguities and surface them all at once in a single consolidated request.

The rule is: one round of clarification at the start, then autonomous execution. Users find it extremely frustrating when an agent interrupts execution repeatedly with questions. Consolidate all ambiguities into a single upfront request and proceed only when that round is resolved.

The exception is when genuinely new information emerges during execution that materially changes the nature of the task — a discovered constraint, a conflicting requirement, an unexpected system state that invalidates the original plan. In that case, stopping and asking is correct. But design your agents to minimize these occurrences by doing thorough upfront analysis.

#### 27.6.2 Designing Good Clarification Questions

A good clarification question is specific, provides labeled options, and is answerable in one sentence. "What do you mean by clean up?" is not a good question. "By 'clean up the reports', do you mean: (A) archive them to cold storage, (B) delete them permanently, or (C) compress and summarize them into a digest?" is a good question.

Prompt your agent to generate clarification questions in this format by including explicit instructions in the system prompt. Specify that options should be labeled and mutually exclusive, that the agent should identify the default it will assume if no answer is provided within the timeout, and that each question should reference the specific part of the goal that is ambiguous.

Provide options even when the answer is not a simple choice. Offering a structured set of options reduces the cognitive load on the human, improves the clarity of their response, and makes the agent's downstream behavior more predictable.

#### 27.6.3 Handling Ambiguous Responses

Sometimes the human's clarification response is itself ambiguous. Design a maximum of one follow-up cycle. If the second response is still unclear, the agent should state explicitly: "I understand you want X based on your response. I will proceed on that basis and you can correct me if that is wrong." Then it should proceed.

Endless clarification loops are worse than a reasonable assumption. They erode trust in the agent and often produce no better outcome than a well-reasoned default. Build this policy into the system prompt and document it in the agent's behavior specification. When the agent proceeds on an assumption, it must log the assumption explicitly so that any later review can identify what the agent decided and why.

### 27.7 Building Trust in Autonomous Systems

Trust in an autonomous agent is not granted upfront — it is earned through consistent, verifiable behavior. Building that trust requires both technical practices and organizational commitment.

On the technical side: implement comprehensive audit logging from day one, make your risk scoring logic visible and tunable by operators, provide tools for reviewing and replaying sessions, and never disable oversight mechanisms for convenience. The short-term efficiency gain from removing an approval gate is never worth the long-term cost of an undetected error cascade.

On the organizational side: define clear ownership for the agent's behavior. Someone must be accountable for reviewing audit logs, responding to escalations, and adjusting autonomy thresholds. An agent with no designated human owner is an agent that will eventually cause a problem with no one positioned to catch or correct it. This is an organizational requirement, not a technical one.

The most trusted autonomous agents in production are not the ones with the highest autonomy level. They are the ones with the most legible behavior — systems where, after any execution, you can explain exactly what happened, why, and what would need to change for it to happen differently. Design for legibility from the start, and autonomy will follow naturally as your evidence base grows and your risk models become more precise.

Start every new deployment at Level 2 — approve all — for at least the first week in production. This builds your audit log, surfaces edge cases, and gives you the evidence needed to safely move to Level 3. You cannot skip this step and expect reliable progressive autonomy. The data generated during the fully supervised phase is the foundation on which all future autonomy decisions rest.

> [!TIP]
> Start every new agent deployment at Level 2 (approve all) for the first week in production. This builds your audit log, surfaces edge cases, and gives you the evidence needed to safely move to Level 3. Premature autonomy is the most common mistake in production agent deployments.

> [!WARNING]
> Never allow your timeout-on-approval policy to default to approved. A human who misses a notification should result in a denied action and a retry, not an autonomous execution. Defaulting to approval on timeout defeats the entire purpose of the oversight mechanism.

## Key Takeaways

- Human-in-the-loop is a deliberate design choice that places human judgment exactly where it adds the most value: irreversible actions, ambiguous goals, and high-stakes decisions.

- The autonomy dial has five levels. Most production agents belong at Level 3: auto-execute reads and reversible operations, pause and request approval before executing destructive or irreversible ones.

- The approval tool pattern works by giving the agent a `request_approval` tool that blocks until a human responds. The pending approvals store, keyed by `approvalId`, is the bridge between agent execution and your human-facing UI.

- For approvals that may take minutes or hours, suspend the session state with `session.getHistory()` to durable storage and resume it with `session.loadHistory()` when the approval decision arrives via webhook.

- Always default to denial on timeout. Defaulting to approval removes the protective value of the oversight mechanism.

- Risk-score every tool call on reversibility and impact. Route high-scoring calls to approval gates; auto-execute low-scoring ones. Build progressive autonomy by tracking per-action-type success rates and lowering approval requirements as confidence builds.

- Agents should surface all ambiguities in a single clarification round before they begin executing. Mid-execution clarification requests are a design failure, not a runtime feature.

- Audit trails for autonomous decisions must be append-only, include full context including risk scores, and be reviewed regularly by a named human owner.
