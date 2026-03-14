---
title: "Chapter 16 — ContinuationPlanner: Multi-Step Execution"
part: "Part III — Lemura Framework Deep Dive"
chapter: 16
page: 25
status: draft
---

*PART III — LEMURA FRAMEWORK DEEP DIVE*

## Chapter 16 — ContinuationPlanner: Multi-Step Execution

> *"Without a plan tracker, the agent doesn't know if it's on step 2 of 10 or wandering in circles."*

> [!NOTE]
> **Chapter Goal:** By the end of this chapter, you will understand how `ContinuationPlanner` tracks plan execution state, how step dependencies work, how `outputKey` and `inputMapping` wire steps together, and how to design plans for complex multi-step tasks.

---

### 16.1 The Problem: Plans Without State

The ReAct loop has no native concept of "steps completed" versus "steps remaining." The model reasons about what to do next based on the current context, but there is no explicit representation of progress. Without tracked state, the agent can complete step 3, then revisit step 2, then skip step 4 because something in the context made it seem unnecessary. From outside the session, you cannot tell whether the agent is making progress or wandering.

This is the problem `ContinuationPlanner` solves. It imposes structure on the ReAct loop: a set of steps with explicit dependencies, statuses, and data flow between them. The planner does not replace the model's reasoning — the model still decides how to accomplish each step. The planner provides the agenda: what comes next, in what order, given what has happened so far.

### 16.2 What ContinuationPlanner Does

#### 16.2.1 Tracking Step Status

Each `ContinuationStep` has a `status` field: `'pending'`, `'running'`, `'done'`, `'failed'`, or `'skipped'`. The planner transitions steps through these statuses as the session progresses. At any point, you can call `planner.getPlanStatusString()` to get a formatted summary of all step statuses — this is what `SessionManager` injects into the goal block so the model sees the current plan state.

#### 16.2.2 Resolving Dependencies

`ContinuationPlanner.getReadySteps()` returns all steps where every step in `dependsOn` has status `'done'`. These are the steps available for execution on the current turn. `SessionManager` uses this list to inform the model's tool selection — the model is told which steps are ready and which are blocked.

When a step fails, the planner propagates the failure: all steps that have the failed step in their `dependsOn` chain are automatically marked `'skipped'`. This cascade prevents the model from attempting steps that cannot succeed because their prerequisites failed.

#### 16.2.3 Passing Outputs Between Steps

The planner maintains an internal output store keyed by `outputKey` values. When a step completes with an `outputKey`, its result is stored under that key. When a subsequent step has `inputMapping`, the planner resolves the mapping by substituting stored outputs into the step's tool parameters.

This wiring is what makes `ContinuationPlanner` more than a status tracker — it is a data flow manager that ensures downstream steps receive the outputs of upstream steps without relying on the model to remember or re-infer them.

### 16.3 The `PlanStep` Interface

The skeleton for Chapter 16 uses "PlanStep" but the actual Lemura type is `ContinuationStep` (see `src/agent/execution/ContinuationPlanner.ts`). The fields are:

#### 16.3.1 `id`: Step Identity

The `stepId` field uniquely identifies a step within the plan. It is used in `dependsOn` lists and as a reference key when resolving condition checks. Use short, descriptive, snake_case identifiers: `'fetch_data'`, `'analyze_results'`, `'write_report'`.

#### 16.3.2 `description`: What the Agent Reads

The `description` field is shown to the model in the plan status block. Write descriptions as clear, complete sentences: "Fetch the list of open pull requests from the repository." The model reads this to understand what the step is asking it to do.

#### 16.3.3 `dependsOn`: Dependency Declaration

`dependsOn` is an array of `stepId` strings. The step will not be attempted until all listed steps have status `'done'`. An empty array means the step has no prerequisites and can run immediately (or in parallel with other dependency-free steps).

#### 16.3.4 `condition`: Conditional Execution

The optional `condition` field gates a step's execution on the output of a prior step:

```typescript
// A step that only runs if a prior step found security issues
const conditionalStep: ContinuationStep = {
  stepId: "file_bug_report",
  toolName: "create_github_issue",
  description: "File a bug report for discovered security issues",
  dependsOn: ["scan_vulnerabilities"],
  status: "pending",
  condition: {
    step: "scan_vulnerabilities",
    outputContains: "VULNERABILITY",
  },
};
```

If the condition is not met (the referenced step's output does not contain the substring), the step is automatically marked `'skipped'` without the model ever attempting it.

#### 16.3.5 `outputKey`: Naming the Result

When a step has `outputKey`, the tool's result is stored in the planner's output store under that key. Choose key names that are meaningful to downstream steps: `'pr_list'`, `'vulnerability_report'`, `'config_content'`.

#### 16.3.6 `inputMapping`: Consuming Prior Outputs

`inputMapping` is a `Record<string, string>` where each key is a tool parameter name and each value is an `outputKey` from a prior step:

```typescript
// inputMapping connects prior step outputs to this step's tool parameters
const analyzeStep: ContinuationStep = {
  stepId: "analyze_prs",
  toolName: "analyze_pull_requests",
  description: "Analyze the fetched pull requests for merge readiness",
  dependsOn: ["fetch_prs"],
  status: "pending",
  inputMapping: { prs: "pr_list" },
  // The 'prs' parameter of analyze_pull_requests
  // receives the value stored under 'pr_list'
};
```

The planner resolves `inputMapping` via `resolveInputs()` when a step becomes ready, injecting the stored output value as a literal argument to the tool call.

### 16.4 Step Status Lifecycle

#### 16.4.1 `pending` → `active` → `complete` / `failed` / `skipped`

Steps start as `'pending'`. When `SessionManager` dispatches a tool call for a step, the step transitions to `'running'`. When the tool completes successfully, it transitions to `'done'`. When the tool call throws or returns an error result, it transitions to `'failed'`. When a dependency fails or a condition is not met, it transitions to `'skipped'` without executing.

The status lifecycle is unidirectional. A step cannot move from `'done'` back to `'pending'`. If you need to retry a failed step, create a new plan with the failed step reset to `'pending'` via `session.setPlan()`.

#### 16.4.2 How the Planner Decides What's Next

On each turn, `SessionManager` calls `planner.getReadySteps()` and injects the result into the model's context. The model is told: "The following steps are available to execute: [step descriptions]." The model then selects which tool to call based on that information.

This guidance is advisory, not mandatory. The model can choose to call a tool that is not in the ready list. `SessionManager` honors the tool call regardless. The planner then updates step statuses based on which tools were actually called, not which tools were suggested.

#### 16.4.3 Handling Failures Mid-Plan

When a step fails, the planner marks all downstream dependents as `'skipped'`. The session continues — the model is free to address the failure (retry the tool, take an alternative approach, or produce a partial result). The planner's status propagation gives the model a clear signal: "step X failed; steps Y and Z that depended on it are now skipped."

### 16.5 Data Flow Between Steps

#### 16.5.1 The Output Store

The output store is an internal `Map<string, string>` inside `ContinuationPlanner`. When a step completes with an `outputKey`, `planner.markStepDone(stepId, output)` stores the output under that key. `planner.getOutput(key)` retrieves it.

Outputs are stored as strings. If your tool returns a structured object, serialize it to JSON before storing. `resolveInputs()` passes the string as-is to the tool parameter — the tool's `execute()` method is responsible for parsing it if needed.

#### 16.5.2 `inputMapping` in Practice

```typescript
// A three-step plan with data flowing through outputKey and inputMapping
import { ContinuationStep } from "lemura";

const auditPlan: ContinuationStep[] = [
  {
    stepId: "list_files",
    toolName: "list_directory",
    description: "List all .ts files in /src",
    dependsOn: [],
    status: "pending",
    outputKey: "file_list",
  },
  {
    stepId: "grep_patterns",
    toolName: "grep_files",
    description: "Search listed files for SQL string concatenation",
    dependsOn: ["list_files"],
    status: "pending",
    outputKey: "findings",
    inputMapping: { files: "file_list" },
  },
  {
    stepId: "write_report",
    toolName: "write_file",
    description: "Write the security audit report",
    dependsOn: ["grep_patterns"],
    status: "pending",
    inputMapping: { content: "findings" },
    condition: { step: "grep_patterns", outputContains: "MATCH" },
  },
];

session.setPlan(auditPlan, "sequential");
```

#### 16.5.3 Complex Data Passing Patterns

For steps where a single `outputKey` is not sufficient — for example, when a step produces multiple distinct outputs that different downstream steps need — use a JSON object as the output value and parse the relevant fields in each tool's `execute()` method.

Alternatively, use separate steps with separate `outputKey` values to decompose a complex output into named components. The planner has no limit on the number of stored output keys.

### 16.6 Parallel Execution

#### 16.6.1 Steps with No Mutual Dependencies

Steps that have no shared dependencies and no mutual dependencies can execute concurrently. With `continuationStrategy: 'parallel'` in `SessionConfig` and `parallelToolCalls: true`, `SessionManager` will dispatch all ready steps simultaneously via `ToolRegistry.executeParallel()`.

```typescript
// A fan-out plan: multiple independent research steps in parallel
const researchPlan: ContinuationStep[] = [
  {
    stepId: "fetch_docs",
    toolName: "fetch_url",
    description: "Fetch the API documentation",
    dependsOn: [],
    status: "pending",
    outputKey: "docs",
  },
  {
    stepId: "fetch_examples",
    toolName: "search_github",
    description: "Find code examples using this API",
    dependsOn: [],
    status: "pending",
    outputKey: "examples",
  },
  {
    stepId: "synthesize",
    toolName: "write_summary",
    description: "Synthesize docs and examples into a guide",
    dependsOn: ["fetch_docs", "fetch_examples"],
    status: "pending",
    inputMapping: { docs: "docs", examples: "examples" },
  },
];

session.setPlan(researchPlan, "parallel");
```

`fetch_docs` and `fetch_examples` run concurrently. `synthesize` waits for both.

#### 16.6.2 How Parallelism Is Detected

`getReadySteps()` returns all steps whose dependencies are fully satisfied. If multiple steps have empty `dependsOn` arrays or all their dependencies are done, they are all returned. `SessionManager` dispatches them in a single parallel execution batch when `parallelToolCalls` is enabled.

#### 16.6.3 Limits and Gotchas

Parallel execution requires all parallel tools to be idempotent or at least non-conflicting. Two tools writing to the same file simultaneously will produce unpredictable results. Use parallel execution for read-heavy steps (fetching, searching, analyzing) and sequential execution for write-heavy steps (creating, updating, deleting).

### 16.7 Plan Examples

#### 16.7.1 Simple Linear Plan

A linear plan where each step depends on the previous: fetch → analyze → report.

#### 16.7.2 Fan-Out / Fan-In Plan

A fan-out plan with parallel independent steps merging into a single synthesis step, as shown in section 16.6.1 above.

#### 16.7.3 Conditional Branching Plan

A plan where a step only executes if the previous step's output meets a condition, as shown in section 16.3.4 above. Use this for steps that are contingent on whether an earlier step found relevant results.

### 16.8 Integrating ContinuationPlanner with SessionManager

`ContinuationPlanner` is created automatically when `session.setPlan()` is called. You do not instantiate it directly. `SessionManager` accesses the planner's formatted status string and injects it into the goal block alongside the `GoalInjector` output.

The planner's status string shows every step with its current status icon:

```text
[EXECUTION PLAN]
✓ list_files — List all .ts files in /src
→ grep_patterns — Search listed files for SQL patterns (ready)
  write_report — Write audit report (waiting on grep_patterns)
```

This visibility gives the model an accurate picture of where it is in the plan at the start of every turn that triggers goal injection.

> [!WARNING]
> Do not set `dependsOn` to reference a `stepId` that does not exist in the plan. The planner will not error at construction time — it will simply never mark that step as ready, and the dependent step will remain `'pending'` for the entire session. Validate all `dependsOn` references before calling `session.setPlan()`.

---

## Key Takeaways

- `ContinuationPlanner` tracks step statuses, resolves dependencies, and manages data flow between steps — it imposes structure on the ReAct loop without replacing the model's reasoning.
- Step dependencies are declared via `dependsOn`; when a dependency fails, all downstream steps are automatically marked `'skipped'` and the model is informed.
- `outputKey` stores a step's result; `inputMapping` injects stored results as tool parameters for downstream steps — together they prevent argument hallucination across dependent steps.
- Parallel execution requires `continuationStrategy: 'parallel'` and `parallelToolCalls: true`; use it for independent read steps and avoid it when steps write to shared state.
- The plan status string is injected into the goal block — the model always knows which steps are ready, which are done, and which are blocked.
