---
title: "Chapter 28 — Cost Optimization"
part: "Part V — Advanced Patterns"
chapter: 28
page: 39
status: draft
---

*PART V — ADVANCED PATTERNS*

## Chapter 28 — Cost Optimization

> *"An agent that solves your problem but costs $50 per run is a prototype, not a product."*

> [!NOTE]
> **Chapter Goal:** By the end of this chapter, you will be able to profile agent token usage, identify the largest cost drivers, apply optimization techniques across the full stack, and set budget controls that prevent cost runaway.

Token cost is not a detail you optimize after launch. It is an architectural concern that shapes model selection, context management, tool design, and session lifecycle from the beginning. An agent that processes large tool results across many turns compounds costs rapidly. This chapter shows you where the tokens come from, how to measure them, and how to reduce them without sacrificing capability.

### 28.1 The Token Economy

Understanding how tokens translate to cost is the foundation of every optimization decision. Get the economics wrong and you will optimize the wrong things.

#### 28.1.1 Input vs. Output Token Pricing

Every major provider prices input tokens and output tokens differently. <!-- Accurate as of 2026-03 — verify before next edition --> At current rates, input tokens are typically four to ten times cheaper than output tokens. This asymmetry matters enormously for agent design: the output the model generates on each turn is your most expensive token category, not the context you send in.

This creates a specific optimization target: reduce unnecessary output verbosity while keeping context manageable. `maxCompletionTokens` in Lemura's `SessionManager` config directly caps output token spend per turn. Use it.

The asymmetry also means that strategies like prompt caching and context compression, which reduce input tokens, have a lower ROI ceiling than strategies that reduce output tokens. Both matter, but track them separately in your profiling.

#### 28.1.2 Where Tokens Come From in an Agent

In a typical agent turn, the input to the model is the sum of: the system prompt, the full conversation history (all prior turns), any tool definitions you have registered, and the current user message or tool results. The output is the model's response, which may include reasoning, a tool call, or a final answer.

Of these, the conversation history is the fastest-growing component. Every turn appends new content to history. Tool results in particular can be enormous — a web search result, a file read, or a database query can return thousands of tokens in a single tool result, and that content persists in the context window for every subsequent turn until compression removes it.

The practical implication: a 30-turn session with large tool results can cost ten times more than a 30-turn session with small tool results, even with identical model selection and system prompt length.

#### 28.1.3 The Compounding Cost of Long Sessions

Cost in an agent session compounds. Turn 1 sends 1,000 tokens. Turn 2 sends 1,000 tokens plus the history of turn 1. Turn 3 sends 1,000 tokens plus the history of turns 1 and 2. By turn 20, you are sending the accumulated weight of 19 prior turns on every single model call.

This is not a linear cost curve — it is quadratic if you allow history to grow unconstrained. A session that costs $0.01 on turn 1 may cost $0.20 on turn 20, not because the model pricing changed but because the input size grew by 20x.

Context compression breaks this compounding. By periodically replacing detailed history with dense summaries, you keep the input size bounded. The cost of compression is one extra model call per compression event; the benefit is that all subsequent turns are cheaper. For sessions running more than 10 turns, compression nearly always has positive ROI.

### 28.2 Profiling Token Usage

You cannot optimize what you have not measured. Build per-turn token accounting into every agent from the start.

#### 28.2.1 Per-Turn Token Accounting

Lemura's `onTrace` callback fires on every significant event in the agent's execution. The `turn_end` event carries token usage data. Use this to build a running ledger of token spend.

```typescript
// Per-turn token accounting with onTrace
import { SessionManager, TraceEvent } from 'lemura';

interface TurnRecord {
  turnIndex: number;
  inputTokens: number;
  outputTokens: number;
  totalTokens: number;
  estimatedCostUsd: number;
}

// Approximate pricing — verify current rates before using in production
// Accurate as of 2026-03 — verify before next edition
const INPUT_COST_PER_TOKEN = 0.00000015;   // e.g., gpt-4o-mini input
const OUTPUT_COST_PER_TOKEN = 0.0000006;   // e.g., gpt-4o-mini output

function buildAccountingTracer(records: TurnRecord[]) {
  let turnIndex = 0;

  return (event: TraceEvent) => {
    if (event.type !== 'turn_end') return;

    const usage = event.metadata?.tokenUsage;
    if (!usage) return;

    const inputTokens: number = usage.inputTokens ?? 0;
    const outputTokens: number = usage.outputTokens ?? 0;
    const totalTokens = inputTokens + outputTokens;
    const estimatedCostUsd =
      inputTokens * INPUT_COST_PER_TOKEN +
      outputTokens * OUTPUT_COST_PER_TOKEN;

    records.push({
      turnIndex: turnIndex++,
      inputTokens,
      outputTokens,
      totalTokens,
      estimatedCostUsd,
    });

    console.log(
      `[TURN ${turnIndex}] in=${inputTokens} out=${outputTokens} ` +
      `total=${totalTokens} ~$${estimatedCostUsd.toFixed(6)}`,
    );
  };
}

// Wire it up in SessionManager config
const turnRecords: TurnRecord[] = [];

const session = new SessionManager({
  adapter: myAdapter,
  model: 'gpt-4o-mini',
  maxTokens: 100_000,
  maxIterations: 50,
  maxCompletionTokens: 4000,
  onTrace: buildAccountingTracer(turnRecords),
});

await session.run('Complete the analysis task');

const totalCost = turnRecords.reduce(
  (sum, r) => sum + r.estimatedCostUsd, 0
);
console.log(
  `Session complete: ${turnRecords.length} turns, ` +
  `~$${totalCost.toFixed(4)} total`,
);
```

#### 28.2.2 Identifying the Biggest Token Consumers

Once you have per-turn records, identify the largest contributors to input token growth. The common culprits are large tool results that persist in history, a verbose system prompt, tool definitions with long descriptions, and turns that repeat context unnecessarily.

To identify tool result inflation specifically, log the character count of each tool result alongside its tool name. Tool results that consistently return more than 5,000 tokens are your highest-priority optimization targets. Even a 50% reduction in a single high-volume tool result can reduce session cost by 20–40% across all subsequent turns.

#### 28.2.3 Cost Projection for Long Tasks

For tasks with a predictable turn structure, project cost before running. Multiply the expected average input tokens per turn by the number of turns, then apply your pricing. Add a 30% buffer for variance.

If your projection exceeds your per-task budget, redesign the session structure before running. Add compression earlier, reduce tool result size, or decompose the task into multiple shorter sessions rather than one long one.

### 28.3 System Prompt Optimization

The system prompt is sent on every single model call. Even a system prompt that is 200 tokens over optimal costs 200 extra tokens on every turn across every session. At scale, this adds up quickly.

#### 28.3.1 Measuring System Prompt Token Cost

Tokenize your system prompt using the provider's tokenizer and record the count. This is your fixed overhead per turn. For a 50-turn session with a 2,000-token system prompt, you are spending 100,000 tokens just on the system prompt — before any history or tool results are included.

Track system prompt token count as a first-class metric alongside model selection and tool result sizes.

#### 28.3.2 Trimming Without Losing Instruction Quality

Review your system prompt for these common token wastes: redundant restatements of the same rule in different words, verbose examples where compact examples would work equally well, filler phrases that do not carry instruction content ("You are a helpful assistant that..."), and role-playing boilerplate that the model does not actually need to perform well.

Cut aggressively. Test after each significant cut by running your standard evaluation suite. The goal is the smallest system prompt that passes your quality bar — not the most comprehensive one you can write.

#### 28.3.3 Caching System Prompts (Provider-Specific)

<!-- Accurate as of 2026-03 — verify before next edition -->
Several providers offer prompt caching: if the prefix of a request matches a recently sent prefix, the cached portion is priced at a significant discount — typically 50–90% of normal input token pricing. Since your system prompt is always at the top of the request, it is an ideal candidate for caching.

Enable prompt caching in your adapter configuration if your provider supports it. This is one of the highest-ROI optimizations available because it requires no changes to agent logic and no quality tradeoff. For agents with large system prompts running many sessions, caching alone can reduce input token cost by 30–50%.

### 28.4 Context Compression as Cost Control

Context compression, covered in depth in Chapter 22, is also your most powerful cost control lever. This section focuses specifically on the cost economics of compression decisions.

#### 28.4.1 Compression ROI: When Is It Worth the Extra Call?

Every compression event costs one model call. For a compression strategy that replaces 10,000 tokens of history with a 500-token summary, the break-even point is the number of subsequent turns at which the savings exceed the cost of the compression call.

If the compression call itself costs 10,000 tokens in input and generates 500 tokens in output, and each subsequent turn saves 9,500 tokens of input (the difference between original and compressed history), the compression pays for itself after just one additional turn. For sessions running five or more turns after the compression point, the ROI is strongly positive.

Trigger compression before the context window reaches 50% capacity. Waiting until you are near the limit forces you into a more expensive compression call and gives you fewer subsequent turns to recoup the cost.

#### 28.4.2 Tool Result Compression as Priority #1

The single highest-ROI compression target is large tool results. When a web search, file read, or database query returns thousands of tokens, and that result will remain in history for dozens of subsequent turns, compressing it to a few hundred tokens immediately after receipt saves an enormous amount across the session lifetime.

Use `ToolResponseProcessor` in Lemura to apply size budgets to tool results automatically. Configure `smallMaxTokens`, `mediumMaxTokens`, and `largeMaxTokens` thresholds. Results over the large threshold should be summarized before entering history.

The ROI math: a 10,000-token search result compressed to 500 tokens saves 9,500 tokens on every subsequent turn. In a 20-turn session, that is 190,000 tokens saved from a single compression call.

#### 28.4.3 History Compression Schedules

For history compression (compressing the full conversation history rather than individual tool results), choose a schedule that triggers compression before compounding costs accelerate. Two effective schedules:

**Turn-based:** trigger compression every N turns (for example, every 10 turns). Simple to implement and predictable.

**Token-threshold:** trigger compression when `session.getContext().tokenCount` exceeds a threshold (for example, 60% of `maxTokens`). More adaptive because it responds to actual usage rather than a fixed interval.

Use `SandwichCompressionStrategy` in Lemura for history compression. Configure `preserveFirst` to keep the goal-establishing turns and `preserveLast` to keep recent context for coherence, while compressing the middle of the history.

### 28.5 Model Routing for Cost

You do not need your most capable (and expensive) model for every step of an agent's workflow. Model routing — using different models for different task types — is one of the most impactful cost levers you have.

#### 28.5.1 Cheap Models for Simple Steps

<!-- Accurate as of 2026-03 — verify before next edition -->
Small models such as `gpt-4o-mini` and Claude Haiku perform excellently at tasks that do not require deep reasoning: summarizing a tool result, formatting data into a specific structure, classifying content into a predefined category, or extracting named entities from a document. These tasks are well within their capability, and using a larger model for them wastes money.

Route all tool result summarization, compression calls, and single-step extraction tasks to your cheapest capable model. The quality difference on these tasks is negligible; the cost difference is 5–20x.

#### 28.5.2 Expensive Models Only When Needed

Reserve your most capable model for steps that genuinely require it: multi-step planning, complex reasoning chains, tasks where the output will directly influence many downstream steps, and cases where quality has been demonstrated to degrade on smaller models.

Define a model tier for each tool call type in your agent's workflow. Audit this assignment periodically as model capabilities change. A step that required your most capable model six months ago may now be well within a cheaper model's capability.

#### 28.5.3 Implementing Model Routing in Lemura

Lemura's `SessionManager` takes a `model` config at construction time. To implement model routing, create separate `SessionManager` instances configured with different models for different subtasks, or build a routing wrapper that selects a model based on the task type before dispatching to Lemura.

```typescript
// Model routing wrapper for cost-aware dispatch
import {
  SessionManager,
  OpenAICompatibleAdapter,
} from 'lemura';

type TaskComplexity = 'simple' | 'standard' | 'complex';

const MODEL_ROUTING: Record<TaskComplexity, string> = {
  simple: 'gpt-4o-mini',      // cheap, fast, good enough for simple tasks
  standard: 'gpt-4o-mini',    // still cheap for most production tasks
  complex: 'gpt-4o',          // reserved for genuine complex reasoning
};

function classifyTask(prompt: string): TaskComplexity {
  const lower = prompt.toLowerCase();

  // Complex tasks: multi-step planning, synthesis, code generation
  if (
    lower.includes('plan') ||
    lower.includes('architect') ||
    lower.includes('design') ||
    lower.includes('analyze and recommend')
  ) {
    return 'complex';
  }

  // Simple tasks: summarize, extract, format, classify
  if (
    lower.includes('summarize') ||
    lower.includes('extract') ||
    lower.includes('format') ||
    lower.includes('list')
  ) {
    return 'simple';
  }

  return 'standard';
}

async function routedRun(
  prompt: string,
  tools: unknown[],
): Promise<string> {
  const complexity = classifyTask(prompt);
  const model = MODEL_ROUTING[complexity];

  const adapter = new OpenAICompatibleAdapter({
    apiKey: process.env.OPENAI_API_KEY ?? '',
    baseURL: 'https://api.openai.com/v1',
  });

  const session = new SessionManager({
    adapter,
    model,
    maxTokens: 100_000,
    maxIterations: 50,
    maxCompletionTokens: complexity === 'simple' ? 1000 : 4000,
    tools: tools as never,
  });

  console.log(`[ROUTING] complexity=${complexity} model=${model}`);
  const result = await session.run(prompt);
  return result.output;
}
```

### 28.6 Caching Strategies

Caching prevents spending tokens on work the agent has already done. Even modest hit rates produce meaningful cost reductions in high-volume deployments.

#### 28.6.1 Tool Result Caching

Many tool calls produce stable results for a given input. A `get_weather` call for the same city within a five-minute window, a `search_database` query for a record that has not changed, or a `read_file` call for a file that is stable — these can all be cached.

Implement a cache wrapper around your tools that keys on the tool name plus a hash of the parameters. Before executing, check the cache. If a valid entry exists (not expired), return it directly without calling the tool. On a cache miss, execute normally and store the result with a TTL.

```typescript
// Tool result cache wrapper
import { IToolDefinition } from 'lemura';
import { createHash } from 'crypto';

interface CacheEntry {
  result: unknown;
  expiresAt: number;
}

const toolResultCache = new Map<string, CacheEntry>();

function hashParams(params: Record<string, unknown>): string {
  return createHash('sha256')
    .update(JSON.stringify(params))
    .digest('hex')
    .slice(0, 16);
}

function withCache(
  tool: IToolDefinition,
  ttlSeconds: number,
): IToolDefinition {
  return {
    ...tool,
    async execute(params, context) {
      const cacheKey = `${tool.name}:${hashParams(params)}`;
      const cached = toolResultCache.get(cacheKey);

      if (cached && cached.expiresAt > Date.now()) {
        console.log(`[CACHE HIT] ${tool.name}`);
        return cached.result;
      }

      console.log(`[CACHE MISS] ${tool.name}`);
      const result = await tool.execute(params, context);

      toolResultCache.set(cacheKey, {
        result,
        expiresAt: Date.now() + ttlSeconds * 1000,
      });

      return result;
    },
  };
}

// Usage: wrap any stable tool with a TTL
const cachedSearchTool = withCache(searchDatabaseTool, 300); // 5 min TTL
const cachedFileTool = withCache(readFileTool, 60);           // 1 min TTL
```

In a production deployment, replace the in-memory map with a distributed cache (Redis, Memcached) so that cache benefits apply across multiple agent instances and process restarts.

#### 28.6.2 Prompt Caching (Provider-Level)

<!-- Accurate as of 2026-03 — verify before next edition -->
As noted in section 28.3.3, provider-level prompt caching applies to the prefix of your request. Beyond the system prompt, any stable content that appears consistently at the start of requests — a standard tool definitions block, a fixed knowledge base injection — can benefit from caching if your provider supports it.

Structure your requests to maximize cacheable prefix length. Place static content first, dynamic content (the current conversation history and latest user message) last.

#### 28.6.3 Semantic Deduplication

For agents that perform research or retrieval tasks, semantic deduplication prevents the same information from appearing multiple times in the context. Before adding a new tool result to history, compute its embedding and check for high similarity against existing history entries. If similarity exceeds a threshold (for example, 0.95 cosine similarity), skip the new result or replace the existing one rather than appending.

This optimization is most valuable for research agents that search multiple sources, web browsing agents that visit similar pages, and agents that call the same tool multiple times with slightly different parameters.

### 28.7 Budget Controls and Hard Limits

Optimization reduces average cost. Budget controls prevent worst-case cost. Both are required for production deployments.

#### 28.7.1 Session-Level Token Budgets

Set a maximum token spend for each session at construction time. Track cumulative spend using the `onTrace` callback. When cumulative spend reaches the budget limit, stop the session, return a partial result, and inform the user that the budget was exhausted.

Express the budget in tokens rather than dollars so that it integrates cleanly with Lemura's token accounting. Convert from a dollar budget to a token budget using your current pricing at deployment time.

#### 28.7.2 Per-Tool Cost Limits

Some tools are inherently expensive — a tool that makes an external API call charging per request, or a tool that reads large files. Set a per-tool invocation limit within a session. After a tool has been called N times, subsequent calls return an error message instructing the agent to work with what it already has.

This prevents a class of failure where the agent enters a retrieval loop, calling the same expensive tool repeatedly trying to find information it is not going to find.

#### 28.7.3 `maxCompletionTokens` in Lemura

Lemura's `SessionManager` config accepts `maxCompletionTokens`, which limits the number of output tokens the model can generate on each turn. This is your primary lever for controlling output token spend — the most expensive token category.

Set `maxCompletionTokens` to the minimum value that does not degrade task quality. For most tasks, 2,000–4,000 tokens per turn is sufficient. Reasoning-heavy tasks may need more; simple extraction tasks can often work well with 500–1,000 tokens.

Calibrate this value empirically. Run your standard task suite with progressively lower values and identify the threshold at which quality begins to drop. Set your production value slightly above that threshold.

#### 28.7.4 Circuit Breakers for Cost

A circuit breaker stops execution when a running metric crosses a threshold. For cost, the relevant circuit breaker fires when cumulative token spend for the session exceeds a budget, stopping further turns before additional cost is incurred.

```typescript
// Session budget circuit breaker using onTurn callback
import { SessionManager, TraceEvent } from 'lemura';

interface BudgetState {
  cumulativeTokens: number;
  budgetTokens: number;
  tripped: boolean;
}

function buildBudgetCircuitBreaker(
  budgetTokens: number,
): {
  state: BudgetState;
  onTrace: (event: TraceEvent) => void;
  onTurn: (turn: unknown) => void;
} {
  const state: BudgetState = {
    cumulativeTokens: 0,
    budgetTokens,
    tripped: false,
  };

  const onTrace = (event: TraceEvent) => {
    if (event.type !== 'turn_end') return;

    const usage = event.metadata?.tokenUsage;
    if (!usage) return;

    const turnTokens =
      (usage.inputTokens ?? 0) + (usage.outputTokens ?? 0);
    state.cumulativeTokens += turnTokens;

    if (state.cumulativeTokens >= budgetTokens && !state.tripped) {
      state.tripped = true;
      console.warn(
        `[BUDGET CIRCUIT BREAKER] Budget of ${budgetTokens} tokens ` +
        `exceeded at ${state.cumulativeTokens} tokens. ` +
        `Stopping session.`,
      );
    }
  };

  // onTurn fires after each turn — check circuit breaker state
  const onTurn = (_turn: unknown) => {
    if (state.tripped) {
      throw new Error(
        `Session budget of ${budgetTokens} tokens exceeded. ` +
        `Partial result returned.`,
      );
    }
  };

  return { state, onTrace, onTurn };
}

// Wire circuit breaker into session
const BUDGET_TOKENS = 50_000; // adjust to your per-session budget
const breaker = buildBudgetCircuitBreaker(BUDGET_TOKENS);

const session = new SessionManager({
  adapter: myAdapter,
  model: 'gpt-4o-mini',
  maxTokens: 100_000,
  maxIterations: 50,
  maxCompletionTokens: 4000,
  onTrace: breaker.onTrace,
  onTurn: breaker.onTurn,
});
```

When the circuit breaker trips, the error propagates up to your session runner. Catch it, log the budget event, and return the last available partial result to the user with an explanation that the session was stopped due to budget limits.

### 28.8 Cost Benchmarking and Reporting

Optimization without measurement is guesswork. Build a structured benchmarking process for cost.

Define a benchmark suite of 50 representative tasks covering your agent's typical workload. Run the full suite before and after each optimization. Measure total token spend, cost per task, and P95 cost per task for each run. The P95 matters because your budget controls need to handle tail cases, not just the average.

Track cost metrics in your observability stack. Set up dashboards showing cost per session, cost per task type, and cost per tool call. Alert when any metric spikes more than 2x above its rolling average — this almost always indicates a tool returning unexpectedly large results, a loop condition, or a prompt regression.

Report cost per task alongside quality metrics in your evaluation pipeline. An optimization that reduces cost 30% with no quality degradation is always worth shipping. An optimization that reduces cost 30% with a 5% quality degradation requires a business decision. Make that tradeoff visible.

> [!TIP]
> The highest single ROI optimization in almost every production agent is compressing large tool results immediately after receipt. Before tuning models, system prompts, or caching strategies, measure your tool result sizes and apply `ToolResponseProcessor` budgets. The savings compound on every subsequent turn.

> [!WARNING]
> Do not set `maxCompletionTokens` so low that the agent starts truncating mid-response or mid-reasoning-chain. A truncated tool call argument is worse than a slightly over-budget response — it creates agent errors that require extra turns to recover from, ultimately costing more than the tokens you saved.

## Key Takeaways

- Output tokens are significantly more expensive than input tokens. Use `maxCompletionTokens` to cap output size. Track both separately in your profiling.

- Token cost compounds across turns because history grows. Context compression is not optional for sessions longer than 10 turns — it is the mechanism that keeps compounding costs bounded.

- Tool result compression has the highest ROI of any single optimization. A large tool result compressed immediately after receipt saves those tokens on every subsequent turn. Use `ToolResponseProcessor` in Lemura to apply size budgets automatically.

- Model routing — using cheap models for summarization, extraction, and formatting while reserving expensive models for complex reasoning — can reduce per-session cost by 5–20x on mixed workloads.

- Tool result caching prevents repeated execution of stable lookups. Cache by `tool_name + hash(params)` with a TTL appropriate to the data's staleness characteristics.

- The `maxCompletionTokens` setting in `SessionManager` config is your primary lever for output token spend. Calibrate it empirically to the minimum value that does not degrade task quality.

- Circuit breakers for cost fire when cumulative session token spend exceeds a budget. Use the `onTurn` callback to check breaker state and throw before incurring the next turn's cost.

- Build a benchmark suite of representative tasks. Run it before and after every optimization to measure actual cost reduction and confirm no quality regression.
