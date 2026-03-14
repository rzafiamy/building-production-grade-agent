---
title: "Chapter 31 — Testing Autonomous Agents"
part: "Part VI — Production Engineering"
chapter: 31
page: 43
status: draft
---

*PART VI — PRODUCTION ENGINEERING*

## Chapter 31 — Testing Autonomous Agents

> *"If you can't test it, you can't trust it. Testing agents is hard, but the alternative — untested agents in production — is worse."*

> [!NOTE]
> **Chapter Goal:** By the end of this chapter, you will have a complete testing strategy for autonomous agents: unit tests for tools, integration tests for the ReAct loop, evaluation frameworks for output quality, and chaos testing for resilience.

---

### 31.1 Why Testing Agents Is Different

Testing an agent is not like testing a REST endpoint or a pure function. The same inputs do not produce identical outputs. The execution path through a multi-turn session is long, branching, and sensitive to subtle changes in model behavior. Success is often a matter of judgment rather than a deterministic comparison. Before you write a single test, you need to understand these properties so you can design around them rather than fight them.

#### 31.1.1 Non-Determinism: The Same Input, Different Output

Every call to a language model carries inherent randomness. Even with `temperature: 0`, providers do not guarantee identical outputs across time — model weights are updated, infrastructure changes, and floating-point non-determinism at scale produces variation. This means your agent tests cannot rely on exact output matching the way unit tests for a sorting function can.

The consequence is practical: if you assert that `result.output === "The capital of France is Paris."` and the model returns "Paris is the capital of France." instead, your test fails for the wrong reason. Your testing strategy must distinguish between correctness (the agent accomplished the task) and exact reproducibility (the agent produced the byte-for-byte same output). Most of your tests will target correctness; only snapshot tests target approximate reproducibility, and even those need tolerance built in.

#### 31.1.2 Long Execution Paths Are Hard to Mock

A single agent session might run for 20 turns, invoking 15 tool calls across 7 different tools, with context compression firing twice along the way. Mocking that entire execution path naively produces tests that are more complex than the code they test. The solution is layering: test each layer in isolation before testing the full path. Tools are tested independently of the ReAct loop. The ReAct loop is tested with a controlled mock model. Only the integration between all layers requires end-to-end execution.

#### 31.1.3 Success Is Often Subjective

When you ask an agent to "summarize this document," is a 3-paragraph summary correct? What about a 1-paragraph summary? What if it misses the third key point but captures the overall tone? These are judgment calls, not binary pass/fail outcomes. Your testing strategy needs to accommodate subjective success criteria at the evaluation layer, while keeping the lower layers of the pyramid as objective as possible.

### 31.2 The Agent Testing Pyramid

The agent testing pyramid organizes tests by determinism, cost, and execution speed. The base is wide and cheap; the top is narrow and expensive.

#### 31.2.1 Level 1: Tool Unit Tests (Deterministic)

Tool unit tests call `execute()` directly, with mocked external dependencies. They are fully deterministic, run in milliseconds, cost nothing in API credits, and should cover every tool in your system. These are the foundation of your testing confidence. A tool that behaves correctly in isolation is a tool you can trust when the agent calls it.

Write tool unit tests for happy paths, error paths, invalid arguments, timeout scenarios, and empty results. You want to know that when the agent passes malformed parameters, the tool throws a well-typed error that the session can handle gracefully.

#### 31.2.2 Level 2: Step Integration Tests (Semi-Deterministic)

Step integration tests run the full ReAct loop with a mock LLM adapter that returns pre-scripted responses in a deterministic sequence. They verify that the session routes tool calls correctly, that the ReAct cycle advances as expected, and that compression strategies fire under the right conditions. Because the model is mocked, these tests are fast and free. They are "semi-deterministic" in the sense that you control the model output precisely, but the rest of the session logic — routing, context management, tool dispatch — is real.

#### 31.2.3 Level 3: Session End-to-End Tests (Probabilistic)

End-to-end tests run a real session against a real provider. They are probabilistic: you assert on the shape of the output, the achievement of the goal, and structural properties (the session completed without error, the tool was called at least once, the output contains the required fields) rather than exact content. These tests are expensive and slow. Run them sparingly — nightly or before releases, not on every pull request.

#### 31.2.4 Level 4: Evaluation (Human or Model-Graded)

Evaluation is the top of the pyramid. It answers the question "is this agent actually good?" rather than "does this agent behave as programmed?" Evaluation uses a separate model or human raters to judge output quality on dimensions like accuracy, completeness, and helpfulness. Run evaluation suites on a weekly cadence or whenever you ship a significant change to the system prompt or model version.

### 31.3 Testing Tools

Tools are the most testable part of your agent system. They are ordinary functions with a defined interface. Test them thoroughly.

#### 31.3.1 Unit Testing Each Tool in Isolation

Call `tool.execute(params, context)` directly in your test suite. Do not instantiate a `SessionManager` for tool unit tests. The tool's `execute()` method is a plain async function — treat it that way.

```typescript
// Unit test for a search tool using Jest
import { searchTool } from '../tools/search';
import { mockSearchClient } from './__mocks__/searchClient';

describe('searchTool', () => {
  it('returns results for a valid query', async () => {
    mockSearchClient.search.mockResolvedValue([
      { title: 'Result A', url: 'https://example.com/a' },
    ]);

    const result = await searchTool.execute(
      { q: 'TypeScript generics' },
      { sessionId: 'test-session', turnIndex: 0 }
    );

    expect(result.results).toHaveLength(1);
    expect(result.results[0].title).toBe('Result A');
  });

  it('throws ToolError when query is empty', async () => {
    await expect(
      searchTool.execute(
        { q: '' },
        { sessionId: 'test-session', turnIndex: 0 }
      )
    ).rejects.toThrow('Query must not be empty');
  });

  it('returns empty array when no results found', async () => {
    mockSearchClient.search.mockResolvedValue([]);
    const result = await searchTool.execute(
      { q: 'xyzzy obscure query' },
      { sessionId: 'test-session', turnIndex: 0 }
    );
    expect(result.results).toEqual([]);
  });
});
```

#### 31.3.2 Edge Cases: Invalid Args, Timeouts, Empty Results

For each tool, write tests for at least four edge cases: missing required parameters, parameters of the wrong type, external service returning empty results, and external service throwing or timing out. These edge cases are exactly what your agent will encounter in production when a user provides an unusual task or when a downstream service degrades.

The empty-results case is particularly important. Many tools return arrays. When the array is empty, does the agent interpret that as "no results found" or does it crash because it tried to access `results[0].url` unconditionally? Your tool test is where you catch this.

#### 31.3.3 Mock vs. Real Dependencies

Use mocks for external dependencies (HTTP APIs, databases, file systems) in unit tests. Use real dependencies only in integration tests that specifically test the connection to that external system. Never call a real external API in a test that runs on every pull request — external services are unreliable, rate-limited, and potentially costly. Wrap your external clients in a thin interface that is trivial to mock.

### 31.4 Integration Testing the ReAct Loop

Integration tests for the ReAct loop require a controllable model. You achieve this with a mock adapter.

#### 31.4.1 Using a Deterministic Mock LLM

A mock LLM adapter takes a pre-scripted list of responses and returns them in order, one per call. This gives you complete control over what the model says at each turn, allowing you to test specific execution paths without any API calls.

```typescript
// Deterministic mock adapter for ReAct loop integration tests
import type { IAdapter, AdapterRequest, AdapterResponse } from 'lemura';

export class MockSequenceAdapter implements IAdapter {
  // Queue of responses to return in order
  private responses: AdapterResponse[];
  private index = 0;

  constructor(responses: AdapterResponse[]) {
    this.responses = responses;
  }

  async complete(_request: AdapterRequest): Promise<AdapterResponse> {
    if (this.index >= this.responses.length) {
      throw new Error(
        `MockSequenceAdapter exhausted after ${this.responses.length} calls`
      );
    }
    return this.responses[this.index++];
  }

  getCallCount(): number {
    return this.index;
  }

  reset(): void {
    this.index = 0;
  }
}

// Usage in a test
const adapter = new MockSequenceAdapter([
  {
    // Turn 1: model decides to call search_web
    content: null,
    toolCalls: [{
      id: 'call_1',
      name: 'search_web',
      arguments: { q: 'TypeScript 5.4 new features' },
    }],
    usage: { inputTokens: 200, outputTokens: 30 },
  },
  {
    // Turn 2: model synthesizes tool result into final answer
    content: 'TypeScript 5.4 introduced NoInfer...',
    toolCalls: [],
    usage: { inputTokens: 450, outputTokens: 120 },
  },
]);

const session = new SessionManager({
  adapter,
  model: 'mock',
  tools: [searchTool],
});

const result = await session.run('What is new in TypeScript 5.4?');
expect(result.output).toContain('NoInfer');
expect(adapter.getCallCount()).toBe(2);
```

#### 31.4.2 Recording and Replaying Model Responses

For complex sessions that are difficult to script by hand, record a real execution first, then replay it in tests. A recording adapter wraps a real adapter, captures every request and response pair to a JSON fixture file, and saves it to disk. A replay adapter reads that fixture file and returns responses in order. The technique lets you test complex, realistic session flows without ongoing API costs.

When a recorded session becomes stale (because you changed the system prompt or added tools), re-record it. Treat fixture files like test fixtures for any other I/O-dependent code: regenerate them when the contract changes, and commit them to version control so diffs are visible in code review.

#### 31.4.3 Testing Specific Turn Sequences

The mock adapter lets you test sequences that would be difficult to reproduce reliably with a real model. Test the sequence where the model calls a tool that returns an error, then calls a different tool as a fallback. Test the sequence where the model calls the same tool twice with different arguments. Test the sequence where context compression fires mid-session and the model continues correctly after summarization. Each of these is a specific scenario you can script with the mock adapter and assert on with precision.

### 31.5 End-to-End Agent Tests

End-to-end tests use a real provider and validate real behavior. Use them selectively.

#### 31.5.1 Running Against a Real Provider (When Necessary)

Some behaviors can only be tested against a real model: the agent's response to genuinely ambiguous instructions, its use of reasoning over retrieved content, its behavior when the context window approaches capacity under real token counts. For these tests, use a fast, cheap model. `gpt-4o-mini` or an equivalent small model runs E2E tests at a fraction of the cost of a frontier model. <!-- Accurate as of 2026-03 — verify before next edition -->

Tag your E2E tests so your CI pipeline can include or exclude them by tag. Mark them as slow, and set a per-test budget limit so a runaway session does not consume unexpected credits.

#### 31.5.2 Snapshot Testing for Agent Behavior

Snapshot tests run the agent on a fixed task, capture key properties of the output, and alert when those properties change significantly. You are not asserting exact output equality — you are asserting structural and semantic stability. A snapshot for a summarization agent might assert that the output is between 100 and 300 words, contains at least three of the five key topics from the source document, and does not contain the phrase "I cannot help with that."

When a snapshot test fails, it tells you that the agent's behavior changed. That change might be an improvement (a prompt refinement made the output more concise) or a regression (a model update changed the tone in an unintended way). In either case, the test gives you a signal to review. Update snapshots deliberately, in code review, not automatically.

#### 31.5.3 Cost-Aware E2E Tests

Track token usage for every E2E test and fail the test if usage exceeds a threshold. Unexpected token spikes in E2E tests are an early warning of runaway sessions — a sign that your agent is not converging on a solution and is instead looping or generating excessive output. Set the threshold at 150% of the baseline you measured when you first wrote the test.

### 31.6 Evaluation Frameworks

Evaluation answers questions that tests cannot: is the output good? Is the agent actually useful?

#### 31.6.1 What Is "Correct" for an Agent?

For many agent tasks, correctness has multiple dimensions. A research agent might be correct on factual accuracy but weak on completeness. A code-generation agent might produce code that runs but uses deprecated patterns. A customer support agent might resolve the immediate issue but communicate in a tone that frustrates users. No single metric captures all of this. Your evaluation framework should measure the dimensions that matter for your specific use case and report them separately.

#### 31.6.2 Model-Graded Evaluation (LLM-as-Judge)

LLM-as-judge evaluation runs a separate model — not the one doing the task — to grade the output on defined criteria. You provide the judge model with the original task, the agent's output, and a rubric that specifies what a good output looks like. The judge returns a score (typically 1–5 per criterion) and a brief explanation.

This approach scales better than human evaluation and is reproducible. Its weakness is that the judge model has its own biases and failure modes. To mitigate this, use a more capable model as the judge than the one you used for the task, and calibrate the rubric against a set of human-rated examples before you rely on the scores.

```typescript
// LLM-as-judge evaluation runner using a separate session
import { SessionManager, OpenAICompatibleAdapter } from 'lemura';

interface EvalCriteria {
  name: string;
  description: string;
}

interface EvalResult {
  criterion: string;
  score: number; // 1-5
  explanation: string;
}

async function evaluateOutput(
  task: string,
  agentOutput: string,
  criteria: EvalCriteria[],
  judgeAdapter: OpenAICompatibleAdapter
): Promise<EvalResult[]> {
  // Build a structured rubric prompt for the judge session
  const rubric = criteria
    .map((c) => `- ${c.name}: ${c.description}`)
    .join('\n');

  const judgePrompt = `
You are an objective evaluator. Score the following agent output on each
criterion from 1 (poor) to 5 (excellent). Respond with JSON only.

TASK: ${task}
OUTPUT: ${agentOutput}
CRITERIA:
${rubric}

Respond with: { "scores": [{ "criterion": string, "score": number, "explanation": string }] }
  `.trim();

  const judgeSession = new SessionManager({
    adapter: judgeAdapter,
    model: 'gpt-4o-2024-08-06',
    systemPrompt: 'You are a precise, consistent output evaluator.',
  });

  const result = await judgeSession.run(judgePrompt);
  const parsed = JSON.parse(result.output);
  return parsed.scores as EvalResult[];
}
```

#### 31.6.3 Task-Specific Metrics

Beyond general quality, define metrics specific to your task. For a code-generation agent: does the code compile? Do the tests pass? For a data-extraction agent: precision and recall against a labeled dataset. For a scheduling agent: are all constraints satisfied in the output? Task-specific metrics are deterministic and cheap to compute. Combine them with LLM-as-judge scores for a complete picture.

#### 31.6.4 Regression Suites for Agent Quality

A regression suite is a fixed set of tasks with known-good outputs or quality thresholds. Run it before and after any significant change — a new model version, a system prompt update, a new tool added. If the average quality score across the suite drops by more than your threshold (commonly 5%), treat the change as a regression and investigate before deploying.

Maintain the regression suite as a first-class asset. Add a new task every time you fix a quality bug in production — this prevents the same failure from recurring silently.

### 31.7 Chaos and Resilience Testing

Your agent will encounter tool failures, timeouts, and resource exhaustion in production. Test for these conditions deliberately.

#### 31.7.1 Tool Failure Injection

A fault injection wrapper intercepts calls to a tool's `execute()` method and randomly introduces failures: exceptions, slow responses, malformed return values, or partial results. Wrap your tools with this injector in chaos tests and run the session to completion. What you want to verify is that the session handles tool failures gracefully — retrying where appropriate, reporting errors clearly, and not looping indefinitely.

```typescript
// Fault injection wrapper for chaos testing tool resilience
import type { IToolDefinition, ToolContext } from 'lemura';

interface FaultConfig {
  errorRate: number;    // 0.0 to 1.0 — probability of injecting a fault
  errorMessage: string; // Error message to throw when fault fires
  delayMs?: number;     // Optional latency injection in milliseconds
}

export function withFaultInjection(
  tool: IToolDefinition,
  config: FaultConfig
): IToolDefinition {
  return {
    ...tool,
    async execute(
      params: Record<string, unknown>,
      context: ToolContext
    ) {
      // Optionally inject latency before processing
      if (config.delayMs) {
        await new Promise((r) => setTimeout(r, config.delayMs));
      }

      // Randomly inject an error based on configured error rate
      if (Math.random() < config.errorRate) {
        throw new Error(
          `[FaultInjector] ${config.errorMessage} (tool: ${tool.name})`
        );
      }

      return tool.execute(params, context);
    },
  };
}

// Wrap tools at 30% error rate for chaos tests
const chaosSearchTool = withFaultInjection(searchTool, {
  errorRate: 0.3,
  errorMessage: 'Simulated search service failure',
  delayMs: 500,
});
```

#### 31.7.2 Context Overflow Testing

Construct a synthetic session history that fills the context window to near capacity, then run the agent on a new task. Verify that compression fires before the session would otherwise fail, that the output after compression is coherent, and that token counts remain within the configured `maxTokens` limit. Use `session.loadHistory(syntheticTurns)` to inject the pre-built history before calling `session.run()`.

This test is important because context overflow is a silent failure mode in production. An agent that runs long tasks gradually fills its context window. Without testing the compression path, you do not know whether your `compressionStrategies` configuration actually works until a real session hits the ceiling.

#### 31.7.3 Network Timeout Simulation

Test what happens when the model API takes 30 seconds to respond, then times out. Use a mock adapter that inserts a configurable delay before throwing a network timeout error. Verify that your session configuration has a reasonable timeout, that the session surfaces a clear error to the caller rather than hanging indefinitely, and that any partial state is cleanly handled. Do not let the session block indefinitely — set explicit timeout values on all external calls.

### 31.8 CI/CD for Agent Systems

Your CI/CD pipeline determines how quickly you can ship changes and how much confidence you have in each deployment. Structure it around the testing pyramid.

#### 31.8.1 What Runs on Every PR

Every pull request should trigger: all tool unit tests, all step integration tests with the mock LLM adapter, and any evaluation tests that use mocked or recorded responses. This suite should complete in under five minutes and cost zero API credits. If it takes longer, investigate which tests are slow and either parallelize them or move them to a slower pipeline stage.

The goal of the per-PR suite is fast feedback. A developer pushing a tool change should know within five minutes whether they broke an existing behavior. If your per-PR suite hits a real API, that goal is unachievable — provider latency and rate limits will make it slow and flaky.

#### 31.8.2 What Runs Nightly

The nightly pipeline runs everything the PR pipeline runs, plus: E2E tests against a real provider (using cheap models), the full regression evaluation suite (using LLM-as-judge), and any chaos tests that are too slow for per-PR runs. The nightly pipeline can run for 30–60 minutes and can consume API credits because it runs once per day, not dozens of times per day.

When the nightly pipeline fails, the on-call engineer investigates before the next morning's standup. Configure nightly failures to notify a Slack channel or PagerDuty rotation, not just appear silently in a CI dashboard that nobody checks.

#### 31.8.3 Cost Management in CI

Track cumulative API spend in your CI pipeline. Set a per-run budget limit and fail the run if it is exceeded — this catches runaway sessions in tests before they drain your quota. Use the cheapest model that can serve the test's purpose. Reserve frontier models for the evaluation suite where output quality actually matters. Cache recorded session fixtures aggressively, and do not re-record them unless the contract has changed.

---

## Key Takeaways

- Test at four levels: deterministic tool unit tests, semi-deterministic mock-LLM integration tests, probabilistic E2E tests, and subjective evaluation. Each level has a different cost, speed, and confidence profile.
- Tools are testable in isolation — call `execute()` directly, mock external dependencies, and cover every edge case you can think of.
- A mock LLM adapter that returns scripted responses in sequence lets you test the full ReAct loop without any API calls. Use it for all per-PR integration tests.
- Snapshot tests track behavioral stability across deployments. Fail on significant change, not on exact output equality.
- LLM-as-judge evaluation scales quality assessment. Use a more capable model as the judge than the model under test, and calibrate the rubric against human-rated examples.
- Fault injection and context overflow tests expose failure modes that only surface under production conditions. Run them before every release.
- Structure your CI pipeline around the pyramid: fast and free tests on every PR, slow and thorough tests nightly. Track API spend in CI and enforce per-run budget limits.
