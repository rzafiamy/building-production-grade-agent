---
title: "Chapter 5 — The ReAct Loop: Reasoning and Acting"
part: "Part II — Architecture Fundamentals"
chapter: 5
page: 13
status: draft
---

*PART II — ARCHITECTURE FUNDAMENTALS*

## Chapter 5 — The ReAct Loop: Reasoning and Acting

> *"Think, then act, then observe, then think again. This is the heartbeat of every autonomous agent."*

> [!NOTE]
> **Chapter Goal:** By the end of this chapter, you will understand the ReAct pattern in depth — how it works, why it's the dominant paradigm, its inherent limitations, and how Lemura's `SessionManager` implements it.

---

### 5.1 The Origins of ReAct

#### 5.1.1 From Chain-of-Thought to Action

Before ReAct, the dominant technique for improving reasoning in language models was chain-of-thought (CoT) prompting: instructing the model to write out its reasoning step-by-step before giving an answer. CoT improved accuracy on complex problems by forcing the model to externalize intermediate steps rather than jumping directly to a conclusion.

CoT's limitation was that reasoning remained entirely internal. The model could not check its reasoning against reality — it could not look up a fact, run a calculation, or query a database to verify a claim. If the model reasoned incorrectly about a factual premise, no amount of reasoning-chain length would correct it. The model could only think, not verify.

ReAct (Reasoning + Acting) added the ability to act between reasoning steps. The model produces a thought, then an action that tests or advances that thought against the real world, then an observation of the action's result, then a new thought that incorporates the observation. The loop continues until the model judges the task complete.

#### 5.1.2 The Original Paper and What It Got Right

The ReAct paper (Yao et al., 2022) showed that interleaving reasoning and acting outperformed pure chain-of-thought on tasks requiring factual lookup and multi-step decision-making. The key insight was that grounding reasoning in real observations — rather than the model's internal knowledge — dramatically reduced hallucination rates and improved task completion.

What the paper got right: the fundamental structure (think → act → observe → repeat) is correct, robust, and applicable to a wide range of tasks. The loop is simple enough to implement and debug, yet powerful enough to handle genuine complexity.

What the paper did not address: production reliability, context window management, goal drift, cost, and all the failure modes that emerge when the loop runs in a system with real users, real data, and real side effects. Those are engineering problems that theory does not surface. This chapter addresses the theory; Part II as a whole addresses the engineering.

### 5.2 The Loop in Detail

#### 5.2.1 Thought: The Model Reasons

At the start of each loop iteration, the model receives the current context — system prompt, conversation history, tool definitions — and produces a "thought": its current understanding of where the task stands and what should happen next. In practice, this is not a separate message type; it is the model's reasoning as expressed in its response before it decides whether to call a tool.

Well-structured thoughts are informative. "I need to check whether the config file exists before reading it" is a useful thought. "Proceeding" is not. Better thoughts lead to better actions, and better thoughts come from clearer context and more specific goals. This is why the content of the system prompt and the clarity of the goal matter as much as model capability.

#### 5.2.2 Action: The Model Calls a Tool

If the model's thought concludes that it needs more information or needs to change the world, it calls a tool. A tool call is a structured request: a tool name and a JSON object of arguments. The arguments are derived from the model's reasoning — ideally from information already present in the context, not from inference or fabrication.

The model may call multiple tools in one turn if the provider supports parallel tool calls. Lemura enables this by default: if the model requests multiple tool calls simultaneously, `SessionManager` executes them concurrently, reducing total latency for independent operations.

If the model's thought concludes that the task is complete, it produces a final response instead of a tool call. This terminates the loop naturally — no tool call means no next iteration.

#### 5.2.3 Observation: The Tool Returns a Result

After a tool call, the result is injected back into the context as a tool result message. The model sees the result on the next iteration and incorporates it into the next thought. The observation is the only mechanism by which the agent acquires new ground-truth information — it cannot rely on its training data for current facts, system state, or task-specific context.

The quality of observations determines the quality of subsequent reasoning. An observation that says "file written successfully" gives the model confidence. An observation that says "ok" forces the model to guess. An observation that says "Error: permission denied on /etc/passwd" tells the model exactly what went wrong and why, allowing it to reason correctly about next steps.

Tool result quality is the most underinvested dimension of agent engineering. Most teams spend 80% of their effort on prompting and 20% on tool design. That ratio should be closer to 50/50.

#### 5.2.4 Repeat Until Done (or Stuck)

The loop continues until one of four things happens: the model produces a response without a tool call (natural completion), `maxIterations` is reached (hard stop), an error terminates the session, or a human interrupts. The first case is the desired one. The others are safety nets and failure modes, covered in section 5.4.

Each iteration adds to the context window. The cost of running the loop grows with each turn — both in tokens billed and in the latency of each model call as the context lengthens. This is the structural reason context management is not optional: the loop's cost structure makes it expensive to run naively.

### 5.3 The Loop as a State Machine

```text
┌─────────┐
│  START  │
└────┬────┘
     │
     ▼
┌─────────────┐       no tool call      ┌─────────────┐
│   THINKING  │ ─────────────────────▶  │    DONE     │
└─────────────┘                         └─────────────┘
     │ tool call
     ▼
┌─────────────┐
│   ACTING    │
└─────────────┘
     │ result
     ▼
┌─────────────┐
│  OBSERVING  │ ─────────────────────▶  (back to THINKING)
└─────────────┘
```

The state machine representation makes the loop's behavior explicit. The agent is always in one of four states: starting, thinking, acting, or done. The transition from THINKING to DONE happens when the model produces a text response without a tool call. The transition from THINKING to ACTING happens when the model produces a tool call. The transition from OBSERVING back to THINKING is automatic — the tool result is added to context and the next model call begins.

The state machine also shows where the failure modes live. Infinite loops are a cycle between ACTING and OBSERVING that never reaches THINKING → DONE. Stuck states are THINKING that produces no tool call but no satisfying final response either. Hard limits (`maxIterations`) add a forced transition from any state to DONE after a specified number of THINKING → ACTING cycles.

### 5.4 Termination Conditions

#### 5.4.1 Natural Completion

Natural completion is the desired termination: the model finishes reasoning, determines the task is done, and produces a final response without calling any tools. The session terminates cleanly. The response is the output.

For natural completion to be reliable, the model needs a clear success criterion — how does it know when the task is done? Vague goals ("help me with this codebase") have no natural completion point. Specific goals ("find all files that import `deprecated-module` and list their paths") have an obvious one.

#### 5.4.2 Max Iterations

`maxIterations` is a hard ceiling on the number of ReAct cycles. When the limit is reached, `SessionManager` terminates the session and returns the last response the model produced, along with a flag indicating the session was cut short. The caller must handle this case.

Setting `maxIterations` requires understanding the expected task depth. A simple lookup task might complete in 3–5 iterations. A multi-file code audit might require 15–25. Set the limit generously for the task's expected length, but not so generously that a looping session runs for 200 turns before terminating.

#### 5.4.3 Error Termination

Unhandled errors — tool execution failures that propagate as exceptions, provider API errors, network failures — can terminate the session abruptly. How `SessionManager` handles these depends on configuration: some errors are retryable, others should terminate immediately.

The key engineering requirement is that error termination is never silent. The session should log the error, emit a trace event, and return an error response that distinguishes "task complete but imperfect" from "session terminated due to error." Callers need this distinction to handle the two cases correctly.

#### 5.4.4 Human Interrupt

For long-running or user-facing agents, the ability to interrupt a running session is a requirement. Lemura supports this through session lifecycle management. A running session can be paused, its current state inspected, and a human judgment injected before resuming.

Human interrupt is the foundation of human-in-the-loop patterns, covered in **Chapter 27 — Human-in-the-Loop**. For now, the design principle is that every agent session that may run for more than a minute in user-facing context should have an interrupt mechanism.

### 5.5 The ReAct Loop in Lemura: SessionManager

`SessionManager` is Lemura's implementation of the ReAct loop. It manages the full lifecycle: receiving a goal, running the loop, calling tools, managing context, and returning the final result.

```typescript
// Running a basic ReAct session with SessionManager
import { SessionManager, OpenAICompatibleAdapter } from "lemura";

const adapter = new OpenAICompatibleAdapter({
  baseUrl: process.env.LEMURA_BASE_URL!,
  apiKey: process.env.LEMURA_API_KEY!,
  defaultModel: "claude-sonnet-4-6",
});

const session = new SessionManager({
  adapter,
  model: "claude-sonnet-4-6",
  maxTokens: 100_000,
  maxIterations: 20,
  systemPrompt: "You are a code audit assistant. Be precise and methodical.",
  tools: [readFileTool, listDirTool, searchTool],
});

// session.run() starts the ReAct loop and returns when the model produces
// a final response (no tool call) or maxIterations is reached
const result = await session.run(
  "Find all TypeScript files that use the `eval()` function and list them with line numbers."
);

console.log(result); // Output: the model's final audit report
```

`SessionManager` handles everything inside the loop: context management, tool dispatch, parallel tool execution, tracing, and compression. From the outside, it looks like a single async function call. From the inside, it may have run 15 model calls and 30 tool executions to produce that result.

The `run()` method accepts a string goal. That goal is added to the conversation as a user message and the loop begins immediately. Every tool call, every model response, and every context compression event is recorded in the session trace, queryable after completion.

### 5.6 What ReAct Gets Wrong (and How to Work Around It)

#### 5.6.1 Shallow Reasoning

The ReAct loop produces a thought before each action, but that thought is only one model call deep. For tasks that require multi-step planning upfront — "figure out the entire approach before starting" — a single thought step is insufficient. The model begins executing before the plan is fully formed.

The workaround is explicit planning before the ReAct loop: run a planning call that produces a structured plan, then feed that plan to the ReAct loop as a constraint. Lemura's `ContinuationPlanner` implements this pattern. When `enableContinuationPlanning: true` is set in the session config, the session runs a planning step before the first ReAct cycle and tracks progress through the plan as tools are called.

#### 5.6.2 Context Accumulation

Every ReAct iteration adds tool results and model reasoning to the context window. The loop's context grows monotonically unless compression is applied. Without compression, long sessions hit the context limit and fail. With naive truncation, the model loses history and produces inconsistent results.

The workaround is active context management via compression strategies, configured on the `SessionManager`. **Chapter 9 — Compression: The Hidden Challenge** covers the mechanics. The key integration point is the `compressionStrategies` configuration option, which is where you attach `SandwichCompressionStrategy`, `HistoryCompressionStrategy`, or other strategies to the session.

#### 5.6.3 No Native Plan Tracking

The vanilla ReAct loop has no concept of a plan. The model reasons about what to do next based on the current context, but there is no explicit representation of "steps completed" vs "steps remaining." Goal drift is a direct consequence: without a tracked plan, the model may complete sub-tasks in the wrong order, skip steps, or pursue tangents.

The workarounds are goal injection (surfacing the original goal regularly via `session.setGoal()`) and explicit plan tracking (providing a `ContinuationPlan` that records step status). Both are covered in **Chapter 8 — Planning and Goals: Directing the Agent**.

### 5.7 Beyond Vanilla ReAct: Extensions and Variants

The ReAct loop is a starting point, not an endpoint. Several extensions address its limitations.

**Reflexion** adds a self-evaluation step after each tool observation: the model explicitly rates the quality of its last action and adjusts its strategy. This improves multi-attempt tasks like coding, where the model can observe test failures and iterate.

**Tree-of-Thought** replaces the linear chain of thoughts with a tree: the model generates multiple possible next actions, evaluates them, and selects the most promising. This is expensive but useful for tasks where the first approach is frequently wrong.

**Plan-and-Execute** separates planning from execution entirely: a planning model produces a structured plan, and one or more execution models carry out the steps. This reduces goal drift and improves parallelism at the cost of added complexity.

Lemura's `ContinuationPlanner` implements a practical version of plan-and-execute within the session lifecycle, without requiring separate planning and execution models. For most production use cases, it is sufficient. The more complex variants are worth understanding but are engineering infrastructure investments, not day-one choices.

---

## Key Takeaways

- The ReAct loop interleaves reasoning (thought) and action (tool call + observation) in a cycle, grounding the model's reasoning in real-world observations rather than internal knowledge alone.
- The loop terminates naturally when the model produces a response without a tool call; `maxIterations` provides a hard safety limit — set it on every session.
- `SessionManager` is Lemura's ReAct implementation; `session.run(goal)` runs the full loop internally and returns the model's final response.
- ReAct's three inherent limitations are shallow reasoning, monotonic context accumulation, and the absence of native plan tracking — each has a specific mitigation in Lemura.
- Tool result quality is the most underinvested dimension of ReAct systems; clear, informative tool outputs drive better reasoning more reliably than prompt engineering alone.
