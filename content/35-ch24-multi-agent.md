---
title: "Chapter 24 — Multi-Agent Systems"
part: "Part V — Advanced Patterns"
chapter: 24
page: 35
status: draft
---

*PART V — ADVANCED PATTERNS*

## Chapter 24 — Multi-Agent Systems

> *"One agent hits a wall. A team of agents goes around it."*

> [!NOTE]
> **Chapter Goal:** By the end of this chapter, you will understand the architecture of multi-agent systems, when to use them (and when not to), the communication protocols between agents, and how to implement agent-to-agent tool calls in Lemura.

---

### 24.1 Why Multiple Agents?

A single Lemura session is powerful. It can reason, use tools, track goals, manage its context window, and persist state across turns. For many production tasks, a single agent is exactly what you need.

But some tasks resist the single-agent model. They are too long to fit in one context window even with compression. They require expertise that cannot be expressed in a single system prompt. They have subtasks that can run at the same time and do not need to wait for each other. Or they need to fail safely in parts without losing everything.

Multi-agent systems are the answer to these pressures. You break a problem into pieces, assign each piece to an agent shaped for that piece, and coordinate the results. The architecture is not complex in principle. The challenge is in the details: what each agent knows, how they communicate, and what happens when one of them fails.

#### 24.1.1 Task Decomposition: Divide and Conquer

The most straightforward reason to use multiple agents is that a task is simply too large for one. A single session is bounded by its context window. Even with Lemura's compression strategies reducing token pressure, very long tasks accumulate state, history, and intermediate results that eventually exhaust the available space.

Decomposition solves this by splitting the task into subtasks with clear inputs and outputs. Each subtask runs in its own session with its own context window. When a subtask finishes, it returns a result — usually a concise string — that the parent or next agent can consume. No single session needs to hold the entire problem in memory.

Decomposition requires you to think carefully about the boundaries between subtasks. Good boundaries are ones where the interface is small: a subtask receives a focused input and produces a focused output. Bad boundaries create fat interfaces where one agent passes an enormous blob of state to the next, recreating the context explosion you were trying to avoid.

#### 24.1.2 Specialization: Right Model for the Right Task

A general-purpose system prompt produces a general-purpose agent. For many tasks that is sufficient. For others, you want an agent whose entire identity is oriented toward a specific job.

A code-review agent has a system prompt that focuses on correctness, style, and security. A summarization agent is tuned for concise, accurate distillation. A data-extraction agent knows the target schema and nothing else. Each of these agents performs its specific task better than a generalist would because its system prompt, its tools, and its model selection are optimized for that task.

<!-- Accurate as of 2026-03 — verify before next edition -->
Specialization also lets you use different models for different subtasks. A fast, cheap model handles classification and routing. A more capable model handles complex reasoning. You assign compute where it earns its cost.

#### 24.1.3 Parallelism: Doing Work Concurrently

Sequential agents wait. Parallel agents work. When subtasks do not depend on each other, running them concurrently is straightforward with `Promise.all` or `Promise.allSettled`. A task that takes three minutes sequentially can take one minute when its three independent subtasks run at the same time.

Parallelism in multi-agent systems requires honest dependency analysis. Before fanning out, you must confirm that each parallel agent's input does not depend on another parallel agent's output. If task B requires a result from task A, they must run sequentially. If tasks B and C both require A's result but not each other's, A runs first, then B and C run in parallel.

#### 24.1.4 Isolation: Containing Failures

A single agent that encounters an unrecoverable error ends the session. In a multi-agent system, one agent's failure does not have to propagate. A supervisor can catch the failure, log it, and either retry with a different agent or report partial results.

Isolation also matters for security. An agent that has access to sensitive data should not share that access with agents that do not need it. Each agent's tool set and data access should be scoped to its specific job.

### 24.2 Multi-Agent Topologies

The topology of a multi-agent system describes how agents relate to each other. Choosing the right topology is the first architectural decision you make.

#### 24.2.1 Pipeline: Sequential Handoffs

In a pipeline, agent A produces output that becomes agent B's input. Agent B produces output that becomes agent C's input. Each agent in the chain knows only its own input and produces only its own output. The interface between stages is a plain string or structured object.

Pipelines are simple to reason about. Data flows in one direction. Each stage is independently testable. Failures are easy to locate because you know which stage produced bad output. The cost of a pipeline is latency: you cannot start stage N+1 until stage N finishes.

#### 24.2.2 Supervisor: One Agent Manages Many

In a supervisor topology, one agent — the supervisor — coordinates the work of multiple worker agents. The supervisor decides what needs to be done, assigns subtasks to workers, collects their results, and synthesizes a final output.

The supervisor does not necessarily do the work itself. Its job is coordination: decomposing the goal, dispatching tasks, tracking progress, handling worker failures, and assembling results. Workers are stateless from the supervisor's perspective: they receive a task and return a result.

This topology scales well because you can add workers without changing the supervisor's logic. It also provides a natural place to implement retry and fallback logic — the supervisor decides whether to retry a failed worker or route to an alternative.

#### 24.2.3 Peer Network: Agents Collaborate as Equals

In a peer network, agents communicate directly without a central coordinator. Each agent can call any other agent as needed. This is the most flexible topology and the hardest to control.

Peer networks work well for small numbers of agents with well-defined collaboration protocols. They break down as agent count grows because the interaction graph becomes difficult to reason about. Circular delegations become possible, and diagnosing failures requires understanding the full conversation history of multiple agents.

Use peer networks when the agents have genuinely symmetric roles and when you can clearly define who initiates what.

#### 24.2.4 Hierarchical: Nested Supervisors

Hierarchical topologies nest supervisors inside supervisors. A top-level supervisor manages domain supervisors. Each domain supervisor manages specialist workers. This mirrors how large organizations work: strategic direction at the top, tactical coordination in the middle, execution at the bottom.

Hierarchies handle very large tasks that would overwhelm a flat supervisor. The cost is coordination overhead at each level and the difficulty of debugging failures that propagate up through multiple layers.

### 24.3 Agent Communication Patterns

How agents talk to each other is as important as how they are arranged.

#### 24.3.1 Tool-as-Agent: Calling an Agent Like a Tool

The cleanest integration point is `IToolDefinition`. Wrapping a `SessionManager` in this interface hides all agent complexity from the parent. From the parent's perspective, it makes a tool call with a string input and receives a string output.

This abstraction is powerful. It means you can replace a static tool implementation with an agent-backed implementation without changing the parent's behavior. The parent continues to call `run_subtask` and receive a result; the fact that the result came from a 15-turn agent conversation is invisible.

#### 24.3.2 Message Passing: Async Communication

For agents that do not need to run synchronously, message passing through a queue or event bus decouples producers from consumers. An agent posts a message to a queue when it completes a step. Another agent picks up that message when it is ready.

Async communication requires external infrastructure — a queue, an event store, or a database with polling. The payoff is resilience: if the consumer agent goes down, the message waits. When it comes back up, it processes the message as if nothing happened.

#### 24.3.3 Shared Memory: Common Context

Agents that need to read and write shared state can do so through a common persistence layer. One agent writes a scratchpad entry. Another agent reads it. This is looser coupling than direct tool calls and more structured than raw message passing.

The risk with shared memory is contention: two agents reading and writing the same key simultaneously can produce inconsistent state. Design shared memory with clear ownership — ideally, only one agent writes a given key, and others only read it.

### 24.4 Implementing Agent-to-Agent Calls in Lemura

The tool-as-agent pattern translates directly into Lemura's `IToolDefinition` API. The implementation is straightforward: a tool's `execute` function creates a `SessionManager`, runs it, and returns the result.

#### 24.4.1 Wrapping a Session as a Tool

Here is a complete implementation of a sub-agent tool. The parent agent calls this tool with a task description. The tool creates a fresh `SessionManager`, runs the sub-agent, and returns its output.

```typescript
// Demonstrates wrapping a Lemura session as an IToolDefinition
import {
  SessionManager,
  OpenAICompatibleAdapter,
  IToolDefinition,
} from 'lemura';

function createSubAgentTool(
  name: string,
  description: string,
  systemPrompt: string,
  tools: IToolDefinition[],
): IToolDefinition {
  return {
    name,
    description,
    parameters: {
      type: 'object',
      properties: {
        task: {
          type: 'string',
          description: 'The task for the sub-agent to complete',
        },
        context: {
          type: 'string',
          description: 'Optional context to pass to the sub-agent',
        },
      },
      required: ['task'],
    },
    async execute(params, executionContext) {
      const adapter = new OpenAICompatibleAdapter({
        apiKey: process.env.OPENAI_API_KEY!,
        baseURL: 'https://api.openai.com/v1',
      });

      const subSession = new SessionManager({
        adapter,
        model: 'gpt-4o-mini',
        maxTokens: 40_000,
        maxIterations: 20,
        maxCompletionTokens: 2000,
        sessionId: `${executionContext.sessionId}-${name}-${Date.now()}`,
        systemPrompt,
        tools,
      });

      const taskInput = params.context
        ? `Context:\n${params.context}\n\nTask:\n${params.task}`
        : params.task;

      const result = await subSession.run(taskInput);
      return {
        output: result.output,
        turns: result.turns,
        tokenUsage: result.tokenUsage,
      };
    },
  };
}

// Usage: create a specialist code-review agent tool
const codeReviewTool = createSubAgentTool(
  'review_code',
  'Review TypeScript code for correctness and style',
  `You are a TypeScript code reviewer. Examine the provided code for:
  - Type safety issues
  - Logic errors
  - Performance problems
  - Style inconsistencies
  Return a structured review with specific line references.`,
  [], // code reviewer needs no external tools
);
```

Add `codeReviewTool` to the parent's `tools` list. Call `review_code` like a normal tool; the `execute` function handles the entire sub-agent lifecycle.

#### 24.4.2 Passing Context Between Sessions

The sub-agent needs enough context to do its job, but not more. Passing the parent's full history to a sub-agent defeats the purpose of decomposition. Instead, extract only what is relevant.

The `context` parameter in the tool above is the primary mechanism. The parent agent is responsible for summarizing what the sub-agent needs. You can also pass structured data: a JSON string with specific fields, a code snippet, a file path. The sub-agent's system prompt tells it how to interpret what it receives.

For cases where the sub-agent needs to write back persistent information — not just return a value — use a shared `IScratchpadAdapter` keyed by a well-known name. The parent reads that key after the tool call returns.

#### 24.4.3 Handling Agent Failures from a Parent

Sub-agent tool calls can fail. The sub-agent might exhaust its `maxIterations`, encounter a tool error it cannot recover from, or return output that does not match what the parent expected.

Wrap sub-agent tool calls in try-catch at the parent level. When a sub-agent fails, the parent receives the error in its tool result and can decide: retry the same sub-agent, try an alternative, or report partial failure and continue with what it has.

```typescript
// Demonstrates parent-side error handling for sub-agent tool calls
import { IToolDefinition, SessionManager } from 'lemura';

function createResilientSubAgentTool(
  innerTool: IToolDefinition,
  maxRetries = 2,
): IToolDefinition {
  return {
    ...innerTool,
    async execute(params, context) {
      let lastError: unknown;
      for (let attempt = 0; attempt <= maxRetries; attempt++) {
        try {
          return await innerTool.execute(params, context);
        } catch (err) {
          lastError = err;
          if (attempt < maxRetries) {
            // Add retry context on subsequent attempts
            params = {
              ...params,
              context: `${params.context ?? ''}\n\nPrevious attempt failed: ${
                err instanceof Error ? err.message : String(err)
              }. Please try a different approach.`,
            };
          }
        }
      }
      // Return a structured failure instead of throwing,
      // so the parent agent can decide what to do
      return {
        error: true,
        message: `Sub-agent failed after ${maxRetries + 1} attempts`,
        lastError:
          lastError instanceof Error
            ? lastError.message
            : String(lastError),
      };
    },
  };
}
```

Returning a structured failure object rather than throwing gives the parent agent a tool result it can reason about. It sees `{ error: true, message: '...' }` and can decide to route the task differently rather than crashing the session.

### 24.5 State and Context in Multi-Agent Systems

State management is where multi-agent systems most often go wrong. Agents that know too much are inefficient. Agents that know too little produce bad output. Finding the right boundary takes deliberate design.

#### 24.5.1 What Each Agent Knows

Each agent should receive exactly the context it needs to do its job. No more, no less. A worker agent doing file analysis needs the file content and perhaps a schema for the expected output. It does not need the full conversation history of the supervisor session, the output of unrelated parallel agents, or implementation details of the orchestration layer.

Define a context contract for each agent type: what it receives as input, what it produces as output, and what it can read from shared storage. Treat this contract as an interface that the agent's system prompt and tool definitions must satisfy.

#### 24.5.2 Shared Goals vs. Local Goals

In a multi-agent system, there is a top-level goal (what the entire system is trying to achieve) and local goals (what each individual agent is trying to achieve). These must be consistent but they need not be identical.

The supervisor carries the top-level goal. Workers carry local goals derived from the supervisor's task assignment. The supervisor uses Lemura's `session.setGoal` to track overall progress. Workers use their own `setGoal` to track their subtask. When a worker finishes, the supervisor updates its goal state to mark that subtask complete.

This separation keeps each agent's context focused. A worker does not need to know that it is part of a larger plan. It needs to know its task and its success criteria.

#### 24.5.3 Avoiding Context Explosion

Context explosion happens when agents accumulate too much state. The most common cause is passing large intermediate results between agents. A sub-agent that produces a 10,000-word report should not pass that report verbatim to the next agent. Instead, it should summarize it to the size the next agent actually needs.

Establish maximum sizes for inter-agent messages. If an agent's output exceeds the limit, the agent must summarize before returning. This is a constraint you build into the sub-agent's system prompt: "Your output must be no longer than 1,000 words. If your findings exceed this, prioritize the most important and summarize the rest."

### 24.6 Multi-Agent Anti-Patterns

Understanding what to avoid is as important as understanding what to build.

#### 24.6.1 Too Many Agents for a Simple Task

More agents mean more coordination overhead, more latency, more token spend, and more failure points. A task that a single agent can complete in five turns should not be routed through three specialized agents.

The test is simple: if the total cost and latency of the multi-agent system exceeds what a capable single agent would require, and the quality improvement is marginal, you have added unnecessary complexity. Start with a single agent. Add agents only when the single agent demonstrably fails at the task.

#### 24.6.2 Agents That Talk to Each Other in Loops

The most dangerous anti-pattern in multi-agent systems is circular delegation. Agent A calls Agent B as a tool. Agent B decides it needs Agent A's help and calls Agent A. You now have infinite recursion that exhausts resources and produces nothing useful.

Circular loops usually arise when agent roles are not clearly separated. If Agent A and Agent B have overlapping responsibilities, each will try to delegate the overlapping work to the other. The fix is clear ownership: each agent has responsibilities that do not overlap with any other agent it can call.

> [!WARNING]
> Circular agent delegation can exhaust your token budget rapidly. Before deploying a multi-agent system, explicitly map the call graph. If any cycle is possible, enforce a maximum call depth or use a supervisor topology where workers cannot call other workers.

#### 24.6.3 No Clear Ownership of State

When multiple agents can write the same piece of state, you will eventually encounter a conflict: two agents write different values to the same key, or one agent reads stale state written by another. These bugs are difficult to reproduce and diagnose.

Assign clear ownership to every piece of shared state. Only the owner writes it. Others may read it. Document ownership in the system prompt of each agent so the agent itself knows what it is and is not allowed to modify.

### 24.7 When NOT to Use Multiple Agents

Multi-agent systems are not always the answer. A single agent with good tools and a well-structured system prompt is almost always simpler to build, debug, and maintain than a network of agents.

Do not use multiple agents when the task has a single, coherent thread of reasoning that would be disrupted by handoffs. Code generation, for example, often benefits from a single agent that holds the entire codebase context, because splitting generation across agents introduces consistency problems at the boundaries.

Do not use multiple agents when the coordination overhead exceeds the value of parallelism. If your three parallel subtasks each take 10 seconds but the supervisor adds 15 seconds of overhead, you have saved nothing.

Do not use multiple agents when the failure modes of the architecture are harder to reason about than the original problem. If you cannot clearly answer "what happens when agent 3 fails at step 5?", the architecture is not yet ready for production.

> [!TIP]
> When evaluating whether to add a second agent, ask: does the handoff between these agents have a clean, well-defined interface? If you cannot write a one-sentence description of what the first agent produces and what the second agent consumes, the boundary is not clear enough to be useful.

Start with one agent. Add a second only when the first demonstrably cannot do the job. Add a third only when two demonstrably cannot. Multi-agent complexity should be earned, not anticipated.

---

## Key Takeaways

- Use multiple agents when a task benefits from decomposition, specialization, parallelism, or fault isolation — not by default.
- The four main topologies are pipeline, supervisor, peer network, and hierarchical. Choose based on whether your data flows sequentially, needs central coordination, is symmetric, or scales beyond a single supervisor.
- The cleanest agent-to-agent communication in Lemura is the tool-as-agent pattern: wrap a `SessionManager` inside an `IToolDefinition` and the parent agent calls it like any other tool.
- Pass only what each agent needs. Context explosion happens when agents accumulate or forward more state than their task requires.
- Each agent should have a clearly defined context contract: what it receives, what it produces, and what shared state it owns.
- Circular delegation is the most dangerous anti-pattern. Map your agent call graph before deployment and ensure no cycles exist.
- A single well-designed agent with good tools beats a poorly designed multi-agent system every time. Add agents only when the single-agent approach has a clear, demonstrated limitation.
