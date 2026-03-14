---
title: "Chapter 25 — Agent Orchestration Patterns"
part: "Part V — Advanced Patterns"
chapter: 25
page: 36
status: draft
---

*PART V — ADVANCED PATTERNS*

## Chapter 25 — Agent Orchestration Patterns

> *"Orchestration is not control — it's coordination. The best orchestrators enable agents, they don't micromanage them."*

> [!NOTE]
> **Chapter Goal:** By the end of this chapter, you will understand the key orchestration patterns — router, supervisor, scatter-gather — how to implement them with Lemura, and how to design orchestration systems that are both powerful and debuggable.

---

### 25.1 What Is Orchestration?

Orchestration is the discipline of directing multiple agents toward a shared outcome. An orchestrator decides what work needs to be done, which agent should do it, in what order, and what to do when something goes wrong. Without orchestration, agents in a multi-agent system work at cross-purposes, duplicate effort, or simply wait for coordination that never comes.

The term is borrowed from distributed systems, where an orchestrator is a central coordinator that manages service interactions. In agent systems, the concept maps cleanly: an orchestrating agent or a piece of orchestration code sits above the worker agents and drives the overall workflow.

#### 25.1.1 Orchestration vs. Choreography

Orchestration and choreography are two fundamentally different coordination models, and confusing them leads to systems that are hard to debug.

In orchestration, there is an explicit coordinator. The coordinator knows the full workflow: what steps exist, which agent handles each step, and what the dependencies are. When you need to understand why the system behaved a certain way, you look at the coordinator's decision log. Everything flows through a central point of control.

In choreography, there is no coordinator. Each agent knows its own role and reacts to events from other agents. Agent A finishes its work and publishes an event. Agent B subscribes to that event and starts its work. The workflow emerges from the interactions rather than being declared in a single place.

Choreography is more resilient — there is no single point of failure — but it is dramatically harder to debug. When something goes wrong in a choreographed system, no single agent has a complete view of what happened. You must reconstruct the event sequence from individual agent logs.

For most production agent systems, orchestration is the right default. The debuggability advantage pays for itself quickly when something goes wrong in production. Use choreography only when you need extreme resilience and you are willing to invest in the observability infrastructure required to make it debuggable.

#### 25.1.2 The Orchestrator's Responsibilities

An orchestrator is responsible for four things: decomposing the goal into subtasks, routing subtasks to the right agents, tracking progress and handling failures, and assembling the final result. That is it. The orchestrator is not responsible for doing the actual work — that is the workers' job.

This separation matters. An orchestrator that tries to do work itself becomes complicated to reason about. Keep the orchestrator's logic focused on coordination. If you find your orchestrator making substantive decisions about domain content, factor those decisions out into a worker agent.

### 25.2 The Router Pattern

The router is the simplest orchestration pattern. It classifies an incoming request and dispatches it to the agent best equipped to handle it. No aggregation, no parallelism — just a single routing decision followed by a single agent execution.

#### 25.2.1 Classifying Tasks and Routing to Specialist Agents

A router needs a classification mechanism and a registry of specialist agents. The classification can be rule-based (keyword matching, regex), model-based (a lightweight LLM call to classify intent), or hybrid. The registry maps classification labels to `SessionManager` configurations.

Rule-based routing is fast, cheap, and predictable. It breaks down when input is ambiguous or when classification categories overlap. Model-based routing handles ambiguity but adds latency and cost. In practice, start with rule-based routing and add model-based routing only for the cases rules cannot handle.

#### 25.2.2 Router Implementation Strategies

```typescript
// Demonstrates keyword-based routing to specialist session configs
import {
  SessionManager,
  OpenAICompatibleAdapter,
  IToolDefinition,
} from 'lemura';

type AgentConfig = {
  systemPrompt: string;
  tools: IToolDefinition[];
  model: string;
};

const agentRegistry: Record<string, AgentConfig> = {
  code: {
    model: 'gpt-4o',
    systemPrompt:
      'You are a TypeScript expert. Analyze code, find bugs, ' +
      'suggest improvements.',
    tools: [],
  },
  data: {
    model: 'gpt-4o-mini',
    systemPrompt:
      'You are a data analyst. Parse, transform, and summarize ' +
      'structured data.',
    tools: [],
  },
  writing: {
    model: 'gpt-4o-mini',
    systemPrompt:
      'You are a technical writer. Produce clear, concise ' +
      'documentation and summaries.',
    tools: [],
  },
};

function classifyTask(input: string): string {
  const lower = input.toLowerCase();
  if (/\b(code|function|bug|typescript|javascript|error)\b/.test(lower)) {
    return 'code';
  }
  if (/\b(data|csv|json|table|rows|columns|parse)\b/.test(lower)) {
    return 'data';
  }
  if (/\b(write|document|explain|summarize|describe)\b/.test(lower)) {
    return 'writing';
  }
  return 'writing'; // default fallback
}

async function routeTask(
  input: string,
  sessionId: string,
): Promise<string> {
  const category = classifyTask(input);
  const config = agentRegistry[category];

  const adapter = new OpenAICompatibleAdapter({
    apiKey: process.env.OPENAI_API_KEY!,
    baseURL: 'https://api.openai.com/v1',
  });

  const session = new SessionManager({
    adapter,
    model: config.model,
    maxTokens: 40_000,
    maxIterations: 15,
    maxCompletionTokens: 2000,
    sessionId: `${sessionId}-${category}`,
    systemPrompt: config.systemPrompt,
    tools: config.tools,
  });

  const result = await session.run(input);
  return result.output;
}
```

The router creates and runs a session only after the routing decision is made. Each category maps to a different model and system prompt, allowing you to tune cost and capability independently per category.

#### 25.2.3 Fallback Routing

Every router needs a fallback. When classification fails — input is ambiguous, no rules match, or the model cannot decide — route to a general-purpose agent rather than returning an error. The general-purpose agent will do a worse job than a specialist, but a worse job is better than no job.

Log every fallback event. If your fallback rate exceeds five percent of requests, your classification is not good enough and your category definitions need refinement.

### 25.3 The Supervisor Pattern

The supervisor pattern puts a coordinating agent above a pool of worker agents. The supervisor understands the overall goal, assigns work to workers, tracks progress, and handles failures. Workers execute tasks without awareness of the larger plan.

#### 25.3.1 One Agent Manages Many Workers

The supervisor's system prompt defines its coordination role. It knows what workers are available, what each worker does, and how to interpret their outputs. In Lemura, each worker is a tool in the supervisor's tool list. The supervisor makes tool calls to assign work exactly as it would call any other tool.

This means the supervisor is itself a `SessionManager`. It runs an agent loop. At each turn, it decides which worker to dispatch next, calls that worker's tool, receives the result, and updates its internal plan. The workers have no knowledge of the supervisor and no state between invocations.

#### 25.3.2 Task Assignment and Progress Tracking

Use `session.setGoal` on the supervisor session to declare the overall objective and its subgoals. As workers complete tasks, update the subgoal list to mark steps complete. This gives Lemura's compression strategies the information they need to preserve goal state even when the context window is under pressure.

Track worker outputs in the supervisor's scratchpad. After each tool call, write a brief summary of what the worker produced and what remains. This creates a durable record that survives context compression better than raw tool result entries.

#### 25.3.3 Worker Failure and Reassignment

When a worker fails, the supervisor receives a structured error result (as described in Chapter 24). The supervisor's system prompt should include explicit guidance on how to handle worker failures: "If a worker returns an error, log the failure, and either retry the same worker with a clarified prompt or assign the task to an alternative worker."

Limit retries at the supervisor level. If a worker has failed twice with different approaches, do not retry a third time. Mark the subtask as failed, continue with what you have, and include the failure in your final output.

#### 25.3.4 Implementing a Supervisor in Lemura

The supervisor's tools are the workers. Here is the structure of a supervisor that manages two specialist workers:

```typescript
// Demonstrates a Lemura supervisor session with worker tools
import {
  SessionManager,
  OpenAICompatibleAdapter,
  IToolDefinition,
} from 'lemura';

// Worker tool: analysis specialist
const analyzeContentTool: IToolDefinition = {
  name: 'analyze_content',
  description:
    'Analyze text content for themes, sentiment, and key points',
  parameters: {
    type: 'object',
    properties: {
      content: { type: 'string', description: 'Text to analyze' },
    },
    required: ['content'],
  },
  async execute(params, context) {
    const adapter = new OpenAICompatibleAdapter({
      apiKey: process.env.OPENAI_API_KEY!,
      baseURL: 'https://api.openai.com/v1',
    });
    const worker = new SessionManager({
      adapter,
      model: 'gpt-4o-mini',
      maxTokens: 20_000,
      maxIterations: 8,
      maxCompletionTokens: 1000,
      sessionId: `${context.sessionId}-analyze-${Date.now()}`,
      systemPrompt:
        'You are a content analyst. Return structured analysis ' +
        'covering themes, sentiment, and top 3 key points.',
      tools: [],
    });
    const result = await worker.run(params.content);
    return { analysis: result.output };
  },
};

// Worker tool: report generation specialist
const generateReportTool: IToolDefinition = {
  name: 'generate_report',
  description: 'Generate a formatted report from analysis results',
  parameters: {
    type: 'object',
    properties: {
      analysis: {
        type: 'string',
        description: 'Analysis to format as a report',
      },
      title: {
        type: 'string',
        description: 'Report title',
      },
    },
    required: ['analysis', 'title'],
  },
  async execute(params, context) {
    const adapter = new OpenAICompatibleAdapter({
      apiKey: process.env.OPENAI_API_KEY!,
      baseURL: 'https://api.openai.com/v1',
    });
    const worker = new SessionManager({
      adapter,
      model: 'gpt-4o-mini',
      maxTokens: 20_000,
      maxIterations: 8,
      maxCompletionTokens: 1500,
      sessionId: `${context.sessionId}-report-${Date.now()}`,
      systemPrompt:
        'You are a report writer. Format the provided analysis ' +
        'into a professional markdown report with sections and ' +
        'bullet points.',
      tools: [],
    });
    const result = await worker.run(
      `Title: ${params.title}\n\nAnalysis:\n${params.analysis}`,
    );
    return { report: result.output };
  },
};

// Supervisor session
async function runSupervisor(content: string): Promise<string> {
  const adapter = new OpenAICompatibleAdapter({
    apiKey: process.env.OPENAI_API_KEY!,
    baseURL: 'https://api.openai.com/v1',
  });

  const supervisor = new SessionManager({
    adapter,
    model: 'gpt-4o',
    maxTokens: 60_000,
    maxIterations: 20,
    maxCompletionTokens: 2000,
    sessionId: 'supervisor-session',
    systemPrompt: `You are a supervisor coordinating a content
    processing pipeline. Use analyze_content to analyze the input,
    then use generate_report to create a final report from the
    analysis. Always complete both steps.`,
    tools: [analyzeContentTool, generateReportTool],
  });

  supervisor.setGoal('Process content into a final report', [
    { id: 'sg1', description: 'Analyze content', completed: false },
    { id: 'sg2', description: 'Generate report', completed: false },
  ]);

  const result = await supervisor.run(content);
  return result.output;
}
```

### 25.4 The Scatter-Gather Pattern

Scatter-gather fans out the same task — or variations of a task — to multiple agents simultaneously and then combines the results into a single output. It is the right pattern when you need parallel work that converges into one answer.

#### 25.4.1 Fanning Out to Multiple Agents in Parallel

The scatter phase creates multiple sessions and runs them concurrently. Each session receives the same or a similar input but may have a different system prompt, a different model, or a different slice of the problem.

`Promise.allSettled` is preferable to `Promise.all` for scatter-gather. `Promise.all` fails the entire operation if any single agent fails. `Promise.allSettled` returns results for all agents, including those that failed, and lets your gather phase decide how to handle partial results.

#### 25.4.2 Aggregating Results

The gather phase receives an array of results, some of which may be failures. Your aggregation strategy depends on your use case. For opinion aggregation, merge the successful results and note the count of failures. For tasks where all results are required, check that no critical agents failed before proceeding. For competitive generation, pick the best result using a scoring function or a separate judge agent.

#### 25.4.3 Partial Results and Timeouts

```typescript
// Demonstrates scatter-gather with Promise.allSettled and timeout
import {
  SessionManager,
  OpenAICompatibleAdapter,
} from 'lemura';

type ScatterConfig = {
  sessionId: string;
  systemPrompt: string;
  model: string;
};

async function withTimeout<T>(
  promise: Promise<T>,
  ms: number,
  label: string,
): Promise<T> {
  return Promise.race([
    promise,
    new Promise<T>((_, reject) =>
      setTimeout(
        () => reject(new Error(`Timeout: ${label} exceeded ${ms}ms`)),
        ms,
      ),
    ),
  ]);
}

async function scatterGather(
  input: string,
  configs: ScatterConfig[],
  timeoutMs = 30_000,
): Promise<{ results: string[]; failures: string[] }> {
  const adapter = new OpenAICompatibleAdapter({
    apiKey: process.env.OPENAI_API_KEY!,
    baseURL: 'https://api.openai.com/v1',
  });

  // Scatter: fan out to all agents in parallel
  const promises = configs.map((config) => {
    const session = new SessionManager({
      adapter,
      model: config.model,
      maxTokens: 30_000,
      maxIterations: 10,
      maxCompletionTokens: 1500,
      sessionId: config.sessionId,
      systemPrompt: config.systemPrompt,
      tools: [],
    });

    return withTimeout(
      session.run(input).then((r) => r.output),
      timeoutMs,
      config.sessionId,
    );
  });

  // Gather: collect all results, including failures
  const settled = await Promise.allSettled(promises);

  const results: string[] = [];
  const failures: string[] = [];

  settled.forEach((outcome, i) => {
    if (outcome.status === 'fulfilled') {
      results.push(outcome.value);
    } else {
      failures.push(
        `Agent ${configs[i].sessionId}: ${outcome.reason?.message ?? 'unknown error'}`,
      );
    }
  });

  return { results, failures };
}

// Example: gather three perspective agents in parallel
async function gatherPerspectives(topic: string) {
  const { results, failures } = await scatterGather(topic, [
    {
      sessionId: 'perspective-technical',
      model: 'gpt-4o-mini',
      systemPrompt:
        'Analyze the topic from a technical implementation ' +
        'perspective. Be specific and concrete.',
    },
    {
      sessionId: 'perspective-business',
      model: 'gpt-4o-mini',
      systemPrompt:
        'Analyze the topic from a business value perspective. ' +
        'Focus on ROI and risk.',
    },
    {
      sessionId: 'perspective-user',
      model: 'gpt-4o-mini',
      systemPrompt:
        'Analyze the topic from an end-user experience ' +
        'perspective. Focus on usability.',
    },
  ]);

  if (results.length === 0) {
    throw new Error('All agents failed: ' + failures.join('; '));
  }

  const combined = results
    .map((r, i) => `Perspective ${i + 1}:\n${r}`)
    .join('\n\n');

  if (failures.length > 0) {
    console.warn(`Partial results: ${failures.length} agents failed`);
  }

  return combined;
}
```

The timeout wrapper prevents a single slow agent from blocking the gather phase indefinitely. Treat any agent that exceeds the timeout as a failure, include it in the failures list, and proceed with the results you have.

### 25.5 The Critic Pattern

The critic pattern separates generation from evaluation. One agent produces output. A second agent — the critic — reviews that output and provides structured feedback. The writer incorporates the feedback and produces a revised draft. The loop continues until the output meets quality criteria or a maximum iteration count is reached.

#### 25.5.1 Using a Separate Agent to Review Output

A critic agent has a fundamentally different job than a writer agent. The writer's goal is to produce the most useful, complete, or creative output it can. The critic's goal is to find what is wrong with it: factual errors, logical inconsistencies, missing information, unclear phrasing, violations of constraints.

Using a separate session for the critic matters for two reasons. First, a fresh context window without the writer's reasoning history produces a more objective review. Second, a critic-specific system prompt sharpens the evaluation against explicit criteria rather than the writer's implicit assumptions.

#### 25.5.2 Critic Prompt Design

A critic prompt should enumerate specific evaluation criteria. Vague criticism ("improve this") is not useful. Specific criticism ("check that all numbered claims have supporting evidence, verify that the conclusion follows from the premises, and flag any section that exceeds 200 words") produces actionable feedback.

Structure the critic's output so the writer agent can parse and act on it. A list of numbered issues with severity levels is more useful than a paragraph of prose criticism. Include a pass/fail signal so your orchestration code can decide whether another iteration is needed.

#### 25.5.3 Iterative Refinement Loops

```typescript
// Demonstrates a writer-critic refinement loop with iteration limit
import {
  SessionManager,
  OpenAICompatibleAdapter,
} from 'lemura';

interface CriticFeedback {
  approved: boolean;
  issues: string[];
  revisedGuidance: string;
}

async function criticRefinementLoop(
  initialTask: string,
  maxIterations = 3,
): Promise<string> {
  const adapter = new OpenAICompatibleAdapter({
    apiKey: process.env.OPENAI_API_KEY!,
    baseURL: 'https://api.openai.com/v1',
  });

  let currentDraft = '';
  let approved = false;

  for (let iteration = 0; iteration < maxIterations; iteration++) {
    // Writer phase
    const writerSession = new SessionManager({
      adapter,
      model: 'gpt-4o',
      maxTokens: 40_000,
      maxIterations: 10,
      maxCompletionTokens: 2000,
      sessionId: `writer-iter-${iteration}`,
      systemPrompt:
        'You are a technical writer producing precise, ' +
        'well-structured documentation. If given previous ' +
        'feedback, address every issue explicitly.',
      tools: [],
    });

    const writerInput =
      iteration === 0
        ? initialTask
        : `Original task: ${initialTask}\n\n` +
          `Previous draft:\n${currentDraft}\n\n` +
          `Critic feedback:\nPlease revise to address these issues.`;

    const writerResult = await writerSession.run(writerInput);
    currentDraft = writerResult.output;

    // Critic phase
    const criticSession = new SessionManager({
      adapter,
      model: 'gpt-4o-mini',
      maxTokens: 20_000,
      maxIterations: 5,
      maxCompletionTokens: 1000,
      sessionId: `critic-iter-${iteration}`,
      systemPrompt: `You are a strict technical editor.
      Evaluate the draft against these criteria:
      1. All claims are specific and verifiable
      2. No unsupported generalities
      3. Code examples (if any) are syntactically correct
      4. Each section has a clear purpose

      Respond with JSON matching this schema:
      { "approved": boolean, "issues": string[],
        "revisedGuidance": string }

      Set approved=true only if there are zero issues.`,
      tools: [],
    });

    const criticResult = await criticSession.run(
      `Review this draft:\n\n${currentDraft}`,
    );

    let feedback: CriticFeedback;
    try {
      feedback = JSON.parse(criticResult.output) as CriticFeedback;
    } catch {
      // If the critic response is not valid JSON, treat as approved
      // to avoid getting stuck on a parsing failure
      feedback = { approved: true, issues: [], revisedGuidance: '' };
    }

    if (feedback.approved) {
      approved = true;
      break;
    }

    // Inject critic feedback for next iteration
    if (iteration < maxIterations - 1) {
      initialTask =
        initialTask +
        `\n\nCritic issues from iteration ${iteration + 1}:\n` +
        feedback.issues.map((issue, i) => `${i + 1}. ${issue}`).join('\n');
    }
  }

  if (!approved) {
    console.warn(
      `Critic loop ended without approval after ${maxIterations} iterations`,
    );
  }

  return currentDraft;
}
```

Cap the refinement loop. Three iterations is usually sufficient. Beyond three, the marginal improvement from additional critic passes diminishes and costs compound. If the critic has not approved after three passes, return the best draft you have and log the remaining issues for human review.

> [!TIP]
> The critic pattern is most valuable when the output has objective quality criteria — correctness, adherence to a schema, coverage of required topics. It is less valuable for subjective qualities like tone or style, where the critic's judgments may conflict with the writer's intent without a clear resolution path.

### 25.6 Dynamic Orchestration

Static orchestration follows a fixed workflow: step 1, step 2, step 3. Dynamic orchestration builds the workflow at runtime based on what each step discovers.

#### 25.6.1 Plans That Spawn Sub-Plans

An agent executing a plan step may discover that the step requires more work than anticipated. Rather than failing, it spawns a sub-plan: a new set of steps that decompose the original step further. The parent plan adds the sub-plan's steps as dependencies and waits for them to complete before continuing.

In Lemura, you implement this through `session.setPlan`. The plan is a list of steps with dependencies. After each tool call, the agent can update the plan to add new steps. Lemura's goal injection mechanism will include the updated plan in subsequent turns.

#### 25.6.2 Self-Organizing Agent Networks

In a self-organizing network, agents negotiate responsibilities at runtime. An orchestrating agent posts a task and any available worker agent can claim it. Workers advertise their capabilities through a shared registry. The orchestrator selects the best available worker for each task.

This pattern provides maximum flexibility but requires substantial infrastructure: a capability registry, a task queue, worker availability tracking, and conflict resolution when multiple workers claim the same task. It is appropriate for complex, long-running workflows where the set of available workers changes over time.

#### 25.6.3 When Dynamic Orchestration Goes Wrong

Dynamic orchestration fails in predictable ways. Plans grow without bound when agents are too conservative about scope, adding sub-steps for every uncertainty instead of making reasonable assumptions. Agents spawn duplicate work when they discover the same sub-task independently. Coordination overhead exceeds the value of the work when each new step requires multiple round-trips through the orchestrator.

Set hard limits on plan size and spawning depth. A plan that exceeds 50 steps is a sign that decomposition has gone wrong. A spawning depth beyond three levels is a sign that the top-level goal was underspecified.

### 25.7 Orchestration Observability

An orchestration system you cannot debug is a liability.

#### 25.7.1 Tracking What Each Agent Did

Every agent session in your orchestration system should emit trace events through `onTrace`. Collect these events centrally, keyed by the session's parent ID. When you investigate a failure, you can reconstruct the full causal chain: the orchestrator dispatched task X to session Y, session Y made these tool calls, and tool call N failed.

The `onTurn` callback is equally valuable. Log the turn index, the model's response summary, and the tool calls made at each turn. This gives you a turn-by-turn narrative of the agent's reasoning without requiring you to re-read the full conversation history.

#### 25.7.2 Attribution in Multi-Agent Traces

In a multi-agent system, a trace event from a worker session tells you what the worker did, but not why the worker was invoked. Preserve attribution by including the parent session's ID in each child session's ID or scratchpad.

A practical convention: name sessions with a path that reflects their lineage. `orchestrator/supervisor-A/worker-1/subtask-3` tells you immediately where in the hierarchy an event originated. This naming scheme makes filtering and grouping traces trivial.

#### 25.7.3 Debugging Orchestration Failures

When an orchestration failure occurs, start with the orchestrator's trace. Find the last successful turn before the failure. Identify which worker was dispatched and when. If the worker has its own trace, examine the worker's last successful turn. Follow the chain until you find the root cause.

The most common orchestration failures are: a worker returned a result in an unexpected format that the orchestrator could not parse; a worker failed silently and returned a plausible-looking result that was actually wrong; or the orchestrator made a routing decision based on incorrect classification of the input.

Instrument your format parsing with explicit error logging. When an orchestrator parses a worker's output, log both the raw output and the parsed result. When they diverge, you have found your bug.

---

## Key Takeaways

- Orchestration is explicit coordination through a central controller. Choreography is implicit coordination through events. Orchestration is almost always more debuggable.
- The router pattern classifies and dispatches. Use rule-based classification first and add model-based routing only where rules fail.
- The supervisor pattern gives one agent responsibility for coordinating many workers. Workers are tools in the supervisor's tool list; they have no awareness of the broader plan.
- The scatter-gather pattern fans out work in parallel and aggregates results. Use `Promise.allSettled` to handle partial failures gracefully, and wrap each agent with a timeout.
- The critic pattern separates generation from evaluation. Cap refinement at three iterations; beyond that, marginal quality gains rarely justify the cost.
- Dynamic orchestration is powerful but fragile. Limit plan size and spawning depth to prevent runaway complexity.
- Observability is not optional. Name sessions with lineage-reflecting IDs, collect traces centrally, and log both raw and parsed worker outputs.
