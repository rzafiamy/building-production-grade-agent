---
title: "Chapter 8 — Planning and Goals: Directing the Agent"
part: "Part II — Architecture Fundamentals"
chapter: 8
page: 16
status: draft
---

*PART II — ARCHITECTURE FUNDAMENTALS*

## Chapter 8 — Planning and Goals: Directing the Agent

> *"An agent without a goal is random. An agent with only a goal is naive. The art is in structured intent."*

> [!NOTE]
> **Chapter Goal:** By the end of this chapter, you will understand the difference between goals and plans, how to structure goals that survive multi-turn execution, how plans enable dependency tracking and step sequencing, and how Lemura's `GoalInjector` and `ContinuationPlanner` implement these concepts.

---

### 8.1 The Goal: What the Agent Is Trying to Accomplish

#### 8.1.1 Goals vs. Instructions vs. Prompts

These three terms are often conflated in agent design, and the conflation causes problems.

A **prompt** is what you send to the model. It is the raw string in the user message. "Refactor this code" is a prompt. It is a request, not a specification. The model interprets it, and different models or different context states will interpret it differently.

An **instruction** is a more specific directive with enough context to be actionable: "Refactor the `processPayment` function in `/src/payments.ts` to extract the validation logic into a separate function." Instructions reduce ambiguity but still leave the execution approach underspecified.

A **goal** is a structured intent with success criteria. It includes not just what to do but how the model will know when it is done. "Refactor `processPayment` to extract validation logic. Success criteria: the extracted function is named `validatePaymentInput`, all existing tests pass, and no new code duplicates the extracted logic." A goal survives multi-turn execution because the success criteria give the model a stable reference point throughout.

The distinction matters because the ReAct loop has no natural completion signal beyond "the model stops calling tools." Without explicit success criteria, the model may complete the task and then continue making changes because it cannot tell it is done.

#### 8.1.2 Properties of Good Agent Goals

Good goals are specific, verifiable, and bounded. Specific: the goal leaves no ambiguity about what is being asked. Verifiable: the model can determine whether each success criterion has been met. Bounded: the goal has a defined scope — what is in scope and what is out.

"Improve the codebase" is a bad goal: it is unspecific, unverifiable, and unbounded. "Fix all TypeScript type errors in the `/src/auth` directory" is a good goal: specific (type errors in a specific directory), verifiable (run the TypeScript compiler), bounded (one directory, one error class).

Goals can be decomposed into sub-goals. Lemura's goal interface has a `decomposition` field for exactly this: a list of sub-goals that, when all completed, constitute completion of the main goal. Sub-goals make progress trackable and give the model smaller, more concrete steps to evaluate.

#### 8.1.3 Short-Term Goals, Sub-Goals, and Objectives

In a long session, the main goal may decompose into many sub-goals. The model works through sub-goals in order, marking each complete before moving to the next. The main goal is the invariant that persists throughout; sub-goals are the tactical steps.

Lemura's `setGoal()` accepts a `decomposition` array of sub-goal strings and a `successCriteria` array. The `GoalInjector` formats these into a block that is injected into the context periodically, showing which sub-goals are pending and which are complete. This formatted block is what prevents the model from "forgetting" what it was doing after a long series of tool calls.

### 8.2 Goal Drift: The Silent Killer of Long Agents

#### 8.2.1 Why Models Forget Their Goal

Goal drift is not forgetfulness in the human sense. The model does not "forget" anything — it processes exactly what is in the context window. Goal drift occurs when the goal statement is too far back in the context to receive strong attention, when intermediate tool results are more salient than the original goal, or when the model's interpretation of the goal shifts incrementally over many turns.

A goal stated once in the user message at turn 1 is at the beginning of the conversation history. By turn 30, it is buried under 30 turns of tool calls and responses. The model's attention at turn 30 is dominated by the most recent turns, not the first. The goal is technically present but effectively invisible.

#### 8.2.2 Goal Injection: Keeping the Goal Alive

Goal injection solves this by periodically re-surfacing the goal in the context. Rather than letting the goal drift to the beginning and be forgotten, the `GoalInjector` injects a formatted goal block at a configured position and frequency.

With `injectionPosition: 'pre_turn'`, the goal block is prepended to the context as a system message before each model call. The model sees the goal on every turn, regardless of how long the session has run.

With `injectionFrequency: 'on_compression'`, the goal block is injected whenever a compression event occurs — precisely the moment when historical context is being discarded and the goal needs to be re-established prominently.

```typescript
// Setting a structured goal with sub-goals and success criteria
import { SessionManager, OpenAICompatibleAdapter } from "lemura";

const session = new SessionManager({
  adapter,
  model: "gpt-4o-mini",
  maxTokens: 100_000,
  maxIterations: 30,
  enableGoalPlanning: true,           // run a planning step before the loop
  goalInjectionFrequency: "always",   // inject the goal on every turn
  goalInjectionPosition: "pre_turn",  // inject before the user message
  tools: [readFileTool, writeFileTool, runTestsTool],
});

session.setGoal({
  statement: "Refactor processPayment to extract validation logic.",
  decomposition: [
    "Read the current processPayment implementation",
    "Identify the validation logic to extract",
    "Create the validatePaymentInput function",
    "Update processPayment to call the new function",
    "Run the test suite to confirm all tests pass",
  ],
  successCriteria: [
    "validatePaymentInput function exists and contains the extracted logic",
    "processPayment delegates to validatePaymentInput",
    "All existing tests pass with no modifications",
  ],
});

const result = await session.run(
  "Refactor processPayment in /src/payments.ts to extract validation logic."
);
```

### 8.3 Plans: Structured Sequences of Intent

#### 8.3.1 What Is a Plan?

A plan is an explicit sequence of steps the agent should execute. Where a goal describes the desired outcome, a plan describes the approach. A plan says "first do A, then do B, then do C" — an explicit structure that the agent follows rather than discovers.

Plans are valuable when the execution sequence is known in advance and when tool dependencies are predictable. If you know that step C requires the output of step B, encoding that dependency in the plan ensures the agent does not attempt step C before step B is complete.

#### 8.3.2 Plan vs. Script: The Key Difference

A script is a rigid program: if step B fails, the script fails. A plan is a structured intent with flexibility: if step B fails, the agent can decide what to do — retry, skip, or take an alternative path.

Plans in Lemura are implemented as `ContinuationStep` arrays. Each step has a status (`pending`, `running`, `done`, `failed`, `skipped`). The `ContinuationPlanner` tracks status transitions and determines which steps are ready to run based on their `dependsOn` list. The ReAct loop uses the plan to inform tool selection — the model is aware of which steps are pending and can focus its actions accordingly.

#### 8.3.3 Step Dependencies and Execution Order

Dependencies are specified per step in the `dependsOn` array. A step with no dependencies can run immediately. A step that depends on another step will not be attempted until the dependency has status `done`. If a dependency fails, all steps that depend on it are automatically marked `skipped`.

This dependency tracking eliminates a common class of agent failure: calling a tool that requires output from a previous tool before that tool has run. Without explicit dependencies, the agent may hallucinate the required input. With them, the framework prevents premature execution.

#### 8.3.4 Conditional Steps and Branching

`ContinuationStep` supports an optional `condition` field that gates a step on the output of a prior step. The condition specifies a step ID and a substring that must be present in that step's output. If the substring is absent, the step is automatically skipped.

This enables simple branching: "run step C only if step B's output contains 'tests passed'." It is not a full workflow engine — for complex conditional logic, a more structured orchestration approach is appropriate — but it covers the most common case: skipping steps that are contingent on a specific prior outcome.

### 8.4 Plan Design Patterns

#### 8.4.1 Linear Plans

A linear plan is the simplest: steps execute in sequence, each depending on the previous. No parallelism, no branching. Appropriate for tasks where the sequence is strict and each step requires the previous step's output.

```typescript
// A linear plan: each step depends on the previous
import { ContinuationStep } from "lemura";

const auditPlan: ContinuationStep[] = [
  {
    stepId: "list_files",
    toolName: "list_directory",
    description: "List all TypeScript files in /src",
    dependsOn: [],
    status: "pending",
    outputKey: "fileList",
  },
  {
    stepId: "scan_imports",
    toolName: "grep_files",
    description: "Search listed files for deprecated imports",
    dependsOn: ["list_files"],        // waits for list_files to complete
    status: "pending",
    outputKey: "deprecatedImports",
    inputMapping: { files: "fileList" }, // uses list_files output
  },
  {
    stepId: "write_report",
    toolName: "write_file",
    description: "Write the audit report",
    dependsOn: ["scan_imports"],
    status: "pending",
    inputMapping: { content: "deprecatedImports" },
  },
];

session.setPlan(auditPlan, "sequential");
```

#### 8.4.2 Parallel Steps

Steps with the same `dependsOn` list (including empty lists) can be executed concurrently when the strategy is `parallel`. This is valuable when independent information needs to be gathered before a synthesis step.

A research agent that must retrieve information from multiple sources before synthesizing a report can collect from all sources in parallel, then run the synthesis step only after all retrievals are complete. The parallel step execution reduces total latency proportionally to the number of independent steps.

#### 8.4.3 Dependent Chains with `inputMapping`

`inputMapping` connects the output of one step to the input parameters of a later step. The key is the target tool parameter name; the value is the `outputKey` from a prior step. The `ContinuationPlanner` resolves these mappings when a step becomes ready, injecting the prior step's stored output as an argument.

This is the mechanism that prevents the model from hallucinating arguments for steps that depend on prior outputs. Without `inputMapping`, the model must remember or re-infer the output of a prior step from the context. With it, the framework handles the handoff.

#### 8.4.4 Fallback and Retry Steps

A practical extension of linear plans is the fallback step: a step that depends on an earlier step's failure. This is implemented via `condition` — a step that is skipped if the prior step succeeds, but runs if it fails.

Retry logic at the plan level is simpler than retry logic at the tool level for multi-step recovery: if a primary approach fails, activate a fallback step that uses a different tool or a different approach. The ReAct loop handles the execution; the plan tracks the state.

### 8.5 Dynamic Planning: When the Plan Changes Mid-Execution

#### 8.5.1 When to Revise the Plan

Not all tasks are fully plannable in advance. When a step produces an unexpected result — a file contains far more complexity than anticipated, a search returns no results, an API returns an unexpected schema — the original plan may no longer be viable.

Dynamic plan revision means updating the active plan in response to observations. In Lemura, this can be done by calling `session.setPlan()` with a revised step list mid-session. The `ContinuationPlanner` accepts the new plan and continues from the current state.

When to do this: when a step fails in a way that requires a fundamentally different approach, not just a retry. When a step produces output that makes downstream steps redundant. When new information changes the cost-benefit of remaining steps.

#### 8.5.2 Keeping the Agent Informed of Plan Changes

When the plan changes, the model needs to know. If the plan is injected into the context via the goal block, updating the plan via `session.setPlan()` causes the next goal injection to reflect the new plan. The model sees the updated step list and can orient its reasoning accordingly.

Without explicit notification, the model may continue reasoning based on the old plan even if the step list has changed. The goal injection mechanism — specifically setting `goalInjectionFrequency: 'always'` during dynamic planning sessions — ensures the model is always working from the current plan state.

### 8.6 Planning in Lemura

#### 8.6.1 `session.setGoal()` and `session.setPlan()`

`session.setGoal()` accepts an object with `statement`, `decomposition`, and `successCriteria`. It creates a `GoalInjector` that will format and inject the goal block according to the session's `goalInjectionFrequency` and `goalInjectionPosition` configuration.

`session.setPlan()` accepts a `ContinuationStep[]` array and an optional strategy (`'sequential'`, `'parallel'`, or `'conditional'`). It creates or replaces the active `ContinuationPlan`. Both methods can be called before `session.run()` to initialize the session with a pre-defined goal and plan, or mid-session to update them dynamically.

#### 8.6.2 The PlanStep Interface

The `ContinuationStep` interface in full:

- `stepId`: unique identifier for the step, used in `dependsOn` references
- `toolName`: the name of the tool this step should call
- `description`: human-readable description of what this step does
- `dependsOn`: array of step IDs that must be `done` before this step runs
- `status`: current status — `'pending'` on creation, updated by the planner
- `outputKey`: optional key under which to store this step's output for later steps
- `inputMapping`: optional mapping from output keys to tool parameter names
- `condition`: optional `{ step, outputContains }` to gate execution on a prior step's output

#### 8.6.3 `ContinuationPlanner` Overview

`ContinuationPlanner` is the internal component that manages plan execution state. It tracks step statuses, determines which steps are ready to run (all dependencies done), propagates failures to dependent steps, resolves input mappings, and stores step outputs.

During the ReAct loop, `SessionManager` consults the `ContinuationPlanner` at each iteration to determine whether there are ready steps and what tool calls to make. This integration means the plan drives the agent's action selection without replacing the model's reasoning — the model can still deviate from the plan if the context requires it, but the planner provides the default agenda.

> [!TIP]
> For most task-completion agents, start with a goal (via `setGoal()`) without a plan. Add an explicit plan (via `setPlan()`) only when you have observed that the agent reliably gets the execution order wrong or wastes turns on redundant steps. Plans add structure but also add the overhead of maintaining step state. Earn the complexity.

---

## Key Takeaways

- A goal is a structured intent with success criteria; a plan is a sequence of steps the agent should follow — both are distinct from a prompt, which is just the raw input string.
- Goal drift occurs when the original goal loses salience in a long context; goal injection (re-surfacing the goal at configured intervals) is the primary prevention mechanism.
- `session.setGoal()` creates a `GoalInjector`; setting `goalInjectionFrequency: 'always'` and `goalInjectionPosition: 'pre_turn'` keeps the goal visible on every turn.
- `session.setPlan()` provides a `ContinuationStep[]` array that the `ContinuationPlanner` executes in dependency order; `dependsOn` prevents premature execution, and `inputMapping` prevents argument hallucination.
- Start agents with goals only; add explicit plans when you observe the agent reliably getting execution order wrong — plans add structure but earn the complexity cost only when needed.
