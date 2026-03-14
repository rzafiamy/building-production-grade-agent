---
title: "Chapter 12 — Installing and Configuring Lemura"
part: "Part III — Lemura Framework Deep Dive"
chapter: 12
page: 21
status: draft
---

*PART III — LEMURA FRAMEWORK DEEP DIVE*

## Chapter 12 — Installing and Configuring Lemura

> [!NOTE]
> **Chapter Goal:** By the end of this chapter, you will have a working Lemura installation, understand all major configuration options via `SessionConfig`, and have run your first agent session end-to-end.

---

### 12.1 Prerequisites

#### 12.1.1 Node.js 18+ and ESM

Lemura is a native ESM package. It uses `export` and `import` syntax throughout and does not ship CommonJS bundles. Your project must be configured for ESM: set `"type": "module"` in `package.json` and use `.js` extensions on local imports in TypeScript output.

Node.js 18 is the minimum supported version. Node.js 20 LTS is recommended for production. Node.js 18 and later include native `fetch` and the `ReadableStream` APIs that Lemura's streaming support depends on without polyfills.

#### 12.1.2 TypeScript Setup

Lemura is written in strict TypeScript and ships type declarations with the package. You do not need a separate `@types/lemura` package. The minimum TypeScript version is 5.0.

Set `"moduleResolution": "bundler"` or `"node16"` in your `tsconfig.json`. The default `"node"` resolution does not handle ESM package exports correctly. A minimal working `tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "strict": true,
    "outDir": "dist"
  }
}
```

#### 12.1.3 API Keys and Provider Access

Lemura needs credentials for whichever provider you use. `OpenAICompatibleAdapter` reads from these environment variables by default:

- `LEMURA_API_KEY` — API key for the provider
- `LEMURA_BASE_URL` — Base URL (e.g. `https://api.openai.com/v1`)
- `LEMURA_MODEL` — Default model name

You can also pass these values directly to the adapter constructor. Environment variables are the recommended pattern for production to avoid hardcoding credentials.

### 12.2 Installation

```bash
# Install Lemura with pnpm (recommended)
pnpm add lemura

# Or with npm
npm install lemura
```

Lemura has no required peer dependencies beyond the Node.js runtime. Optional features — MCP transport, audio, vision — activate only when their transports are configured.

### 12.3 Project Structure Recommendations

A production Lemura project benefits from a consistent layout:

```text
src/
  agent/
    tools/          ← IToolDefinition implementations
    skills/         ← ISkill definitions
    session.ts      ← SessionManager factory / session builder
  adapters/         ← custom IProviderAdapter implementations (if any)
  index.ts          ← entry point
```

Keep tool definitions in their own files. A tool that reads a file, queries a database, or calls an external API is a non-trivial piece of logic — it deserves its own module with its own tests.

Keep session construction in a factory function. `SessionConfig` grows as the project does. Centralizing session construction means compression strategies, tool sets, and skill configurations are defined in one place and reused across different session types.

### 12.4 Your First Agent Session

#### 12.4.1 The Minimal Example

A minimal Lemura session requires three things: an adapter with a model, a `maxTokens` budget, and a goal string.

```typescript
// Minimal Lemura session — runs a ReAct loop and returns the result
import { SessionManager, OpenAICompatibleAdapter } from "lemura";

const adapter = new OpenAICompatibleAdapter({
  baseUrl: process.env.LEMURA_BASE_URL!,
  apiKey: process.env.LEMURA_API_KEY!,
  defaultModel: process.env.LEMURA_MODEL ?? "gpt-4o-mini",
});

const session = new SessionManager({
  adapter,
  model: "gpt-4o-mini",
  maxTokens: 50_000,
});

const result = await session.run(
  "What is 2 + 2? Show your reasoning."
);

console.log(result);
// Output: "2 + 2 = 4. ..."
```

#### 12.4.2 Running It

```bash
# Set environment variables then run
LEMURA_API_KEY=sk-... LEMURA_BASE_URL=https://api.openai.com/v1 npx tsx src/index.ts
```

For a session with no tools, the model answers directly and the loop terminates after one turn. The real value of the session appears when you add tools and the model starts making tool calls.

#### 12.4.3 Reading the Output

`session.run()` returns the final assistant response as a plain string. If the session calls tools, you do not see those tool calls in the return value — only the model's final text response after all tool calls are complete. Use the `onTrace` callback to observe intermediate steps.

To observe every turn in real time without a full observability setup:

```typescript
// Tracing all session events to stdout during development
import { SessionManager, OpenAICompatibleAdapter } from "lemura";

const session = new SessionManager({
  adapter,
  model: "gpt-4o-mini",
  maxTokens: 50_000,
  onTrace: (event) => {
    console.log(`[${event.type}] ${event.name}`, event.status ?? "");
  },
});
```

### 12.5 The `SessionConfig` Interface

`SessionConfig` is the complete configuration object for a `SessionManager`. All fields except `adapter`, `model`, and `maxTokens` are optional.

#### 12.5.1 Required Fields

| Field | Type | Purpose |
|-------|------|---------|
| `adapter` | `IProviderAdapter` | The provider adapter for model calls |
| `model` | `string` | Model name passed to the adapter |
| `maxTokens` | `number` | Maximum context window size |

These three fields are the minimum. Any session without them will not compile.

#### 12.5.2 Model and Provider Configuration

```typescript
// Session config — model and provider fields
{
  adapter: IProviderAdapter;   // required
  model: string;               // required
  maxTokens: number;           // required
  maxCompletionTokens?: number; // default: 2000 — max tokens per LLM response
  parallelToolCalls?: boolean;  // default: false — run tools concurrently
  toolRegistryTimeoutMs?: number; // default: 30000 — per-tool timeout
}
```

`maxCompletionTokens` limits the length of each model response. Set it based on the maximum expected response length. For agents that write long code outputs, increase this; for agents that return short summaries, reduce it.

#### 12.5.3 Context and Compression Configuration

```typescript
// Session config — context and compression fields
{
  systemPrompt?: string;
  compressionStrategies?: IContextStrategy[];
}
```

`systemPrompt` is the durable instruction set for the session — the agent's constitution. All compression strategies receive it in `SessionConfig.compressionStrategies` as an array of `IContextStrategy` implementations. They execute in priority order before each model call.

#### 12.5.4 Goal and Plan Configuration

```typescript
// Session config — goal and plan fields
{
  enableGoalPlanning?: boolean;  // auto-decompose goals into sub-goals
  goalInjectionFrequency?: 'always' | 'every_N_turns' | 'on_compression';
  goalInjectionPosition?: 'system_prompt' | 'pre_turn';
  goalInjectionN?: number;       // used with 'every_N_turns', default: 3
  enableContinuationPlanning?: boolean;
  continuationStrategy?: 'sequential' | 'parallel' | 'conditional';
}
```

When `enableGoalPlanning` is true, `SessionManager` runs a planning step before the first ReAct turn to decompose the user's goal into sub-goals and success criteria. When `enableContinuationPlanning` is true, `ContinuationPlanner` tracks step-by-step execution state.

#### 12.5.5 Tool Configuration

```typescript
// Session config — tool fields
{
  tools?: IToolDefinition[];
  toolFirewall?: ToolFirewallConfig;
  toolExecutionBudget?: ToolExecutionBudget;
  toolResponseProcessor?: IToolResponseProcessor;
  toolResponseTokenBudget?: number;
  maxTokensPerTool?: number;
}
```

`tools` is the initial tool set. Add tools dynamically after construction via `session.tools.register()`. `toolFirewall` implements an ask/accept/deny policy for tool execution. `toolExecutionBudget` caps the number of tool calls per session or per tool name.

#### 12.5.6 Token Budgets and Limits

```typescript
// Session config — execution limits
{
  maxIterations?: number;  // default: 10 — max ReAct turns
  maxSteps?: number;       // default: 20 — max tool calls total
}
```

Set both on every production session. `maxIterations` bounds the number of ReAct cycles. `maxSteps` bounds the total number of tool executions. Either limit terminating the session produces a log entry and returns the last model response.

#### 12.5.7 Callbacks and Hooks

```typescript
// Session config — callbacks
{
  onTurn?: (turn: Turn) => void;
  onTrace?: (event: TraceEvent) => void;
  logger?: ILogger;
}
```

`onTurn` fires after each conversation turn. `onTrace` fires for every granular event: planning, tool calls, tool results, compression, errors. `logger` receives structured log messages at configurable verbosity levels. For production, wire `onTrace` into your observability stack (OpenTelemetry spans, Datadog traces, or a custom log aggregator).

### 12.6 Environment Variables vs. Config Objects

Both approaches work. The choice is a matter of deployment context.

Environment variables (`LEMURA_API_KEY`, `LEMURA_BASE_URL`, `LEMURA_MODEL`) are convenient for local development, Docker containers, and cloud deployments where secrets are injected as environment variables. `OpenAICompatibleAdapter` reads them automatically when constructor options are omitted.

Config objects are better for applications that manage multiple sessions with different providers, or that construct session configurations dynamically based on request parameters. The adapter constructor accepts the same fields as the environment variables, so switching is mechanical.

```typescript
// Preferring explicit config objects in multi-provider applications
const groqAdapter = new OpenAICompatibleAdapter({
  baseUrl: "https://api.groq.com/openai/v1",
  apiKey: config.groqApiKey,
  defaultModel: "llama-3.3-70b-versatile",
});
```

### 12.7 TypeScript Strict Mode and Type Safety

Run Lemura projects with `strict: true` in `tsconfig.json`. All `SessionConfig` fields are typed with precise types. With strict mode on, the TypeScript compiler catches:

- Missing required fields (`adapter`, `model`, `maxTokens`)
- Wrong types in compression strategy arrays
- Invalid values for enum fields like `goalInjectionPosition`
- Passing an `IToolDefinition` where an `IContextStrategy` is expected

Without strict mode, these errors appear at runtime. In a session that runs for 20 turns, a misconfiguration caught at turn 15 is a much more expensive debugging experience than a compile-time error.

### 12.8 Common Setup Errors and How to Fix Them

**`Cannot find module 'lemura'`** — The package is installed but ESM module resolution is not configured. Set `"moduleResolution": "bundler"` or `"node16"` in `tsconfig.json`.

**`Error: LEMURA_API_KEY is not set`** — The adapter is reading from environment variables but the variable is not set in the current shell. Either set the variable or pass `apiKey` directly to the adapter constructor.

**`LemuraAdapterError: 401 Unauthorized`** — The API key is set but invalid. Verify the key is correct and that it has access to the model you specified in `model`.

**`LemuraToolValidationError: Unknown tool "X"`** — The model called a tool that is not registered in the session. Check the tool names in your `IToolDefinition` array match exactly what the model would generate. Tool names are case-sensitive.

> [!WARNING]
> Never commit API keys to version control. Use environment variables, `.env` files excluded by `.gitignore`, or a secrets manager. A leaked API key can result in significant unexpected charges before you notice.

---

## Key Takeaways

- Lemura requires Node.js 18+, TypeScript 5+, and ESM module configuration (`"moduleResolution": "bundler"` or `"node16"`).
- Three fields are required in `SessionConfig`: `adapter`, `model`, and `maxTokens` — everything else is optional and additive.
- Set `maxIterations` and `maxSteps` on every production session; without them, a looping agent will run until the context fills or the provider's rate limit is hit.
- Use `onTrace` to observe all session events; it is the integration point for connecting Lemura to your observability stack.
- Run with TypeScript strict mode — it catches misconfiguration at compile time rather than at runtime inside a multi-turn session.
