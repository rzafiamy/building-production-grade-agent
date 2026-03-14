---
title: "Appendix A — Lemura API Reference"
page: 55
status: draft
---

## Appendix A — Lemura API Reference

*Reference for the Lemura framework. See `src/types/` for authoritative TypeScript definitions.*

*All classes and interfaces are exported from the `lemura` package root unless otherwise noted.*

---

### SessionManager

The central class that implements the ReAct loop and coordinates all agent components.
See `src/agent/SessionManager.ts`.

#### Constructor

```typescript
new SessionManager(config: SessionConfig)
```

#### Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `run` | `(userMessage: string, initialContext?: string) => Promise<string>` | Run the agent to completion and return the final response string |
| `stream` | `(userMessage: string) => AsyncIterable<string>` | Stream agent output token by token |
| `reset` | `() => void` | Reset session state, clearing history and context |
| `close` | `() => Promise<void>` | Gracefully close all connections (MCP, adapters) |
| `getContext` | `() => ContextWindow` | Return the current context window state |
| `getHistory` | `() => Turn[]` | Return the full turn history |
| `loadHistory` | `(history: Array<{ role, content, toolCalls?, toolResults? }>) => void` | Pre-load turn history before running |
| `setPlan` | `(steps: ContinuationStep[], strategy?: 'sequential'\|'parallel'\|'conditional') => void` | Set a multi-step execution plan |
| `setGoal` | `(goal: Omit<Goal, 'id'\|'injectionFrequency'\|'injectionPosition'>) => void` | Set the agent's current goal |

#### Properties

| Property | Type | Description |
|----------|------|-------------|
| `tools` | `ToolRegistry` | Access the tool registry to register or inspect tools |
| `skills` | `SkillInjector` | Access the skill injector to manage skills |

---

### SessionConfig

The configuration object passed to `SessionManager`. See `src/types/agent.ts`.

#### Required Fields

| Key | Type | Description |
|-----|------|-------------|
| `adapter` | `IProviderAdapter` | The LLM provider adapter |
| `model` | `string` | Model identifier string passed to the provider |
| `maxTokens` | `number` | Hard limit on context window tokens |

#### Context and Compression

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `compressionStrategies` | `IContextStrategy[]` | `[]` | Ordered list of compression strategies |

#### Goal and Plan

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `enableGoalPlanning` | `boolean` | `false` | Enable goal injection via `GoalInjector` |
| `goalInjectionFrequency` | `'always'\|'every_N_turns'\|'on_compression'` | `'always'` | When to re-inject the goal |
| `goalInjectionPosition` | `'system_prompt'\|'pre_turn'` | `'system_prompt'` | Where to inject the goal reminder |
| `goalInjectionN` | `number` | `1` | Inject goal every N turns (used with `'every_N_turns'`) |
| `enableContinuationPlanning` | `boolean` | `false` | Enable multi-step plan tracking |
| `continuationStrategy` | `'sequential'\|'parallel'\|'conditional'` | `'sequential'` | Plan execution strategy |

#### Tools

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `tools` | `IToolDefinition[]` | `[]` | Available tools for the agent |
| `toolResponseProcessor` | `IToolResponseProcessor` | `undefined` | Processor for evaluating and compressing tool results |
| `toolResponseTokenBudget` | `number` | `undefined` | Max tokens for any single tool response |
| `maxTokensPerTool` | `number` | `undefined` | Per-tool token cap on responses |
| `parallelToolCalls` | `boolean` | `false` | Execute multiple tool calls in parallel |
| `toolRegistryTimeoutMs` | `number` | `30000` | Default timeout for tool execution |
| `toolExecutionBudget` | `ToolExecutionBudget` | `undefined` | Per-tool call count limits |
| `toolFirewall` | `ToolFirewallConfig` | `undefined` | Tool access control configuration |

#### Skills

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `skills` | `ISkill[]` | `[]` | Skills to register at session start |
| `activeDynamicSkills` | `string[]` | `[]` | Dynamic skill names to activate |
| `activeDynamicTags` | `string[]` | `[]` | Dynamic skill tags to activate |
| `skillTokenBudget` | `number` | `undefined` | Max tokens for all skills combined |

#### Execution Control

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `maxIterations` | `number` | `50` | Max ReAct loop iterations before raising `LemuraMaxIterationsError` |
| `maxSteps` | `number` | `undefined` | Max plan steps to execute |
| `maxCompletionTokens` | `number` | `undefined` | Max tokens for each completion response |
| `systemPrompt` | `string` | `undefined` | Base system prompt |
| `sessionId` | `string` | auto-generated | Session identifier for logging and tracing |

#### Callbacks and Observability

| Key | Type | Description |
|-----|------|-------------|
| `onTurn` | `(turn: any) => void` | Called after each completed turn |
| `onTrace` | `(event: TraceEvent) => void` | Called for every trace event (tool calls, compression, errors) |

#### Storage and Memory

| Key | Type | Description |
|-----|------|-------------|
| `stmRegistry` | `ShortTermMemoryRegistry` | Short-term memory registry for large content storage |
| `scratchpadAdapter` | `IScratchpadAdapter` | Persistent scratchpad for agent working notes |
| `ragAdapter` | `IRAGAdapter` | RAG adapter for semantic retrieval |

#### MCP

| Key | Type | Description |
|-----|------|-------------|
| `mcpServers` | `MCPServerConfig[]` | MCP servers to connect at session start |

---

### IContextStrategy

Interface for implementing custom compression strategies. See `src/types/context.ts`.

```typescript
interface IContextStrategy {
  name: string
  priority: number  // Lower number = applied first
  shouldApply(ctx: ContextWindow): boolean
  apply(ctx: ContextWindow): Promise<ContextWindow>
}
```

---

### SandwichCompressionStrategy

Preserves the first N and last N turns, compressing the middle. See `src/context/SandwichCompressionStrategy.ts`.

#### Constructor

```typescript
new SandwichCompressionStrategy(adapter: IProviderAdapter, config: SandwichCompressionConfig)
```

#### SandwichCompressionConfig

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `preserveFirst` | `number` | required | Number of turns to preserve from the start |
| `preserveLast` | `number` | required | Number of turns to preserve from the end |
| `triggerThreshold` | `number` | `0.80` | Fire when context reaches this fraction of `maxTokens` |
| `summaryMaxTokens` | `number` | `undefined` | Max tokens for the generated summary of the middle |
| `priority` | `number` | `20` | Strategy priority (lower = runs first) |

---

### HistoryCompressionStrategy

Compresses older turns using a rolling window. See `src/context/HistoryCompressionStrategy.ts`.

#### Constructor

```typescript
new HistoryCompressionStrategy(adapter: IProviderAdapter, config: HistoryCompressionConfig)
```

#### HistoryCompressionConfig

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `windowSize` | `number` | required | Number of recent turns to keep uncompressed |
| `triggerAtPercent` | `number` | required | Fire when context reaches this percent of max |
| `priority` | `number` | `30` | Strategy priority |

---

### SummaryInjectionStrategy

Injects a previously generated summary back into the context after compression. See `src/context/SummaryInjectionStrategy.ts`.

#### Constructor

```typescript
new SummaryInjectionStrategy(config?: SummaryInjectionConfig)
```

#### SummaryInjectionConfig

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `priority` | `number` | `1` | Strategy priority (runs early, before compression) |
| `label` | `string` | `'Earlier conversation summary'` | Label prepended to the injected summary |

---

### GoalInjector

Manages goal state and injects goal reminders into context. See `src/agent/execution/GoalInjector.ts`.

Used internally by `SessionManager` when `enableGoalPlanning: true`. Access via `session.setGoal()`.

#### Goal Interface

```typescript
interface Goal {
  id: string
  statement: string              // The primary goal statement
  decomposition: string[]        // Sub-goals or task breakdown
  successCriteria: string[]      // How to know when done
  injectionFrequency: 'always' | 'every_N_turns' | 'on_compression'
  injectionPosition: 'system_prompt' | 'pre_turn'
  completedSubGoals?: string[]   // Tracks completed sub-goals
}
```

#### Methods (on GoalInjector instance)

| Method | Signature | Description |
|--------|-----------|-------------|
| `getFormattedBlock` | `() => string` | Get the formatted goal block for injection |
| `injectInto` | `(prompt: string) => string` | Inject goal into a prompt string |
| `shouldInjectThisTurn` | `(turnIndex: number, compressionOccurred?: boolean, injectionN?: number) => boolean` | Whether to inject on this turn |
| `updateDecomposition` | `(decomposition: string[], successCriteria?: string[]) => void` | Update the goal's sub-goal list |
| `markSubGoalDone` | `(subGoal: string) => void` | Mark a sub-goal as completed |
| `getGoal` | `() => Goal` | Get the current goal state |
| `incrementTurn` | `() => void` | Advance the turn counter (called automatically by `SessionManager`) |

---

### ContinuationPlanner

Tracks multi-step plan execution with dependency resolution. See `src/agent/execution/ContinuationPlanner.ts`.

Used internally by `SessionManager` when `enableContinuationPlanning: true`. Set plans via `session.setPlan()`.

#### ContinuationStep Interface

```typescript
interface ContinuationStep {
  stepId: string                   // Unique step identifier
  toolName: string                 // Tool to call for this step
  description: string              // Human-readable description
  dependsOn: string[]              // stepIds that must complete before this step
  status: 'pending' | 'running' | 'done' | 'failed' | 'skipped'
  outputKey?: string               // Store this step's output under this key
  inputMapping?: Record<string, string>  // Map prior step outputs to this step's inputs
  condition?: StepCondition        // Skip unless condition is met
}

interface StepCondition {
  step: string       // stepId whose output to check
  outputContains: string  // String that must be present in that step's output
}
```

#### ContinuationPlan Interface

```typescript
interface ContinuationPlan {
  steps: ContinuationStep[]
  currentStepIndex: number
  strategy: 'sequential' | 'parallel' | 'conditional'
}
```

#### Methods (on ContinuationPlanner instance)

| Method | Signature | Description |
|--------|-----------|-------------|
| `getPlan` | `() => ContinuationPlan` | Get the full plan state |
| `getPlanStatusString` | `() => string` | Get a human-readable status summary |
| `getReadySteps` | `() => ContinuationStep[]` | Get steps whose dependencies are satisfied |
| `isComplete` | `() => boolean` | Whether all steps are done or skipped |
| `markStepRunning` | `(stepId: string) => void` | Mark a step as running |
| `markStepDone` | `(stepId: string, output?: string) => void` | Mark a step as done with optional output |
| `markStepFailed` | `(stepId: string) => void` | Mark a step as failed |
| `markStepSkipped` | `(stepId: string) => void` | Mark a step as skipped (condition not met) |
| `getOutput` | `(key: string) => string \| undefined` | Get a stored step output by key |
| `resolveInputs` | `(step: ContinuationStep, baseArgs?: Record<string, unknown>) => Record<string, unknown>` | Resolve input mappings for a step |

---

### ToolResponseProcessor

Evaluates and compresses tool call results before they enter context. See `src/agent/execution/ToolResponseProcessor.ts`.

#### Constructor

```typescript
new ToolResponseProcessor(config?: ToolResponseProcessorConfig)
```

#### ToolResponseProcessorConfig

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `smallMaxTokens` | `number` | `200` | Token cap for small tool responses |
| `mediumMaxTokens` | `number` | `800` | Token cap for medium tool responses |
| `largeMaxTokens` | `number` | `2000` | Token cap for large tool responses |
| `budgetPercent` | `number` | `undefined` | Alternatively, set max tokens as a percent of context |

#### Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `evaluate` | `(response: string, tool: IToolDefinition, context: unknown) => ToolResponseEvaluation` | Classify and evaluate a tool response |
| `compress` | `(response: string, evaluation: ToolResponseEvaluation) => string` | Compress a response based on its evaluation |

#### ToolResponseEvaluation

```typescript
interface ToolResponseEvaluation {
  relevanceScore: number
  sizeClass: 'small' | 'medium' | 'large' | 'oversized'
  shouldCompress: boolean
  suggestedMaxTokens: number
  answered: boolean
  answeredPartially: boolean
  errorDetected: boolean
  suggestedAction: 'continue' | 'retry' | 'retry_with_params' | 'skip' | 'escalate'
}
```

---

### IToolDefinition

Interface for defining tools available to the agent. See `src/types/tools.ts`.

```typescript
interface IToolDefinition {
  name: string
  description: string
  parameters: Record<string, unknown>  // JSON Schema object
  execute(params: unknown, context: ToolContext): Promise<unknown>
  timeoutMs?: number  // Per-tool timeout override (ms)
}
```

#### ToolContext

Passed to every tool's `execute()` call:

```typescript
interface ToolContext {
  sessionId: string
  turnIndex: number
  logger: ILogger
  adapter?: IProviderAdapter
  ragAdapter?: IRAGAdapter
  stmRegistry?: ShortTermMemoryRegistry
  scratchpad?: string
  scratchpadAdapter?: IScratchpadAdapter
}
```

---

### ToolRegistry

Manages tool registration and execution. Accessed via `session.tools`. See `src/tools/ToolRegistry.ts`.

#### Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `register` | `(tool: IToolDefinition) => void` | Register a tool |
| `unregister` | `(name: string) => boolean` | Remove a tool by name |
| `get` | `(name: string) => IToolDefinition \| undefined` | Get a tool by name |
| `getAll` | `() => IToolDefinition[]` | Get all registered tools |
| `execute` | `(name: string, params: unknown, context: ToolContext) => Promise<unknown>` | Execute a tool call |
| `executeParallel` | `(calls: Array<{ id, name, params }>, context: ToolContext) => Promise<Array<{ id, result?, error? }>>` | Execute multiple tool calls in parallel |

---

### MCPClient

Client for connecting to a single MCP server. See `src/mcp/MCPClient.ts`.

#### Constructor

```typescript
new MCPClient(name: string, config: MCPServerConfig, logger: ILogger)
```

#### MCPServerConfig

```typescript
interface MCPServerConfig {
  name: string
  transport: 'stdio' | 'http' | 'sse'
  command?: string         // For stdio transport: executable to run
  args?: string[]          // For stdio transport: command arguments
  url?: string             // For http/sse transport: server URL
  env?: Record<string, string>  // Environment variables for stdio process
  timeoutMs?: number       // Default: 30000
}
```

#### Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `connect` | `() => Promise<void>` | Connect to the MCP server |
| `callTool` | `(toolName: string, args: Record<string, unknown>) => Promise<unknown>` | Call a tool on this server |
| `disconnect` | `() => Promise<void>` | Disconnect and clean up |

#### Properties

| Property | Type | Description |
|----------|------|-------------|
| `serverName` | `string` | The registered name of this server |
| `tools` | `MCPToolDefinition[]` | Tool definitions discovered from this server |
| `isConnected` | `boolean` | Whether the connection is currently active |

---

### MCPClientRegistry

Manages connections to multiple MCP servers. See `src/mcp/MCPClientRegistry.ts`.

#### Constructor

```typescript
new MCPClientRegistry(logger: ILogger)
```

#### Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `register` | `(name: string, config: MCPServerConfig) => Promise<void>` | Connect and register an MCP server |
| `discoverTools` | `() => Promise<IToolDefinition[]>` | Discover all tools from all registered servers |
| `callTool` | `(toolName: string, args: Record<string, unknown>) => Promise<unknown>` | Call a tool on any registered server |
| `disconnectAll` | `() => Promise<void>` | Disconnect all servers |
| `getRegisteredServers` | `() => string[]` | List all registered server names |

---

### SkillInjector

Manages skill registration and injection into context. Accessed via `session.skills`. See `src/skills/SkillInjector.ts`.

#### ISkill Interface

```typescript
interface ISkill {
  name: string
  version: string
  description: string
  inject: 'system_prompt' | 'pre_turn' | 'post_history'
  priority: number
  tier?: 'nano' | 'micro' | 'standard' | 'extended'
  nano?: string       // ~50 token version
  micro?: string      // ~150 token version
  standard?: string   // ~400 token version
  extended?: string   // ~1000 token version
  content?: string    // Fallback content
  strategy?: 'fixed' | 'dynamic'
  requiredTools?: string[]
  tags?: string[]
  enabled?: boolean
}
```

#### Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `register` | `(skill: ISkill) => void` | Register a skill |
| `enableSkill` | `(name: string) => void` | Enable a skill by name |
| `disableSkill` | `(name: string) => void` | Disable a skill by name |
| `enableByTags` | `(tags: string[]) => void` | Enable all skills matching any of the given tags |
| `disableByTags` | `(tags: string[]) => void` | Disable all skills matching any of the given tags |
| `getAll` | `() => ISkill[]` | Get all registered skills |
| `getActiveSkills` | `() => ISkill[]` | Get currently enabled skills |
| `getSkillsForInjection` | `(position: ISkill['inject']) => ISkill[]` | Get active skills for a given injection position |
| `getRequiredTools` | `() => string[]` | Aggregate required tool names from all active skills |
| `buildInjectionBlock` | `(position: ISkill['inject'], tokenBudget?: number) => string` | Build the formatted injection block for a position |

---

### ShortTermMemoryRegistry

Manages large content items that exceed context window limits. See `src/context/ShortTermMemoryRegistry.ts`.

#### Constructor

```typescript
new ShortTermMemoryRegistry(config: STMRegistryConfig)

interface STMRegistryConfig {
  storage: IStorageAdapter
  maxTextTokens?: number  // Default: 100000
}
```

#### Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `register` | `(content: any, type: 'text'\|'blob', metadata?: Record<string, unknown>, estimateTokens?: (text: string) => number) => Promise<string>` | Store content and return an STM reference ID |
| `update` | `(id: string, updates: { content?: any; metadata?: Record<string, unknown> }) => Promise<void>` | Update stored content |
| `getByRef` | `(ref: string) => Promise<STMItem \| undefined>` | Retrieve content by reference ID |
| `delete` | `(id: string) => Promise<void>` | Delete stored content |

---

### IProviderAdapter

Interface for LLM provider adapters. See `src/types/adapters.ts`.

```typescript
interface IProviderAdapter {
  readonly name: string
  readonly version: string

  complete(request: CompletionRequest): Promise<CompletionResponse>
  stream(request: CompletionRequest): AsyncIterable<CompletionChunk>
  estimateTokens(text: string): number
  getModelInfo(): ModelInfo
  healthCheck(): Promise<boolean>
}
```

#### CompletionRequest

```typescript
interface CompletionRequest {
  model: string
  messages: NormalizedMessage[]
  tools?: IToolDefinition[]
  maxTokens?: number
  temperature?: number
  stopSequences?: string[]
  stream?: boolean
}
```

#### CompletionResponse

```typescript
interface CompletionResponse {
  content: string
  toolCalls?: ToolCall[]
  finishReason: 'stop' | 'tool_call' | 'max_tokens' | 'error'
  usage: TokenUsage
  rawResponse?: unknown
}
```

---

### Error Classes

All errors extend `LemuraError`. See `src/types/errors.ts`.

| Class | When thrown |
|-------|-------------|
| `LemuraContextOverflowError` | Context exceeds `maxTokens` and no strategy can compress it further |
| `LemuraToolNotFoundError` | Agent called a tool not in the registry |
| `LemuraAdapterError` | Provider adapter API call failed |
| `LemuraMaxIterationsError` | ReAct loop reached `maxIterations` without completing |
| `LemuraToolValidationError` | Tool arguments failed JSON Schema validation |
| `LemuraToolTimeoutError` | Tool `execute()` exceeded its timeout |
| `LemuraMCPConnectionError` | Could not connect to an MCP server |
| `LemuraMCPTimeoutError` | MCP tool call timed out |
| `LemuraSkillInjectionError` | Skill parsing or injection failed |

---

### TraceEvent

Emitted via `onTrace` for every significant event in the session. See `src/types/agent.ts`.

```typescript
interface TraceEvent {
  sessionId?: string
  type: 'planning' | 'budget' | 'tool_call' | 'tool_result' | 'thinking' |
        'system' | 'compression' | 'error' | 'skill'
  name: string
  input?: any
  output?: any
  durationMs?: number
  startedAt?: number
  status?: 'running' | 'done' | 'error'
  metadata?: Record<string, any>
}
```

Use `type === 'tool_call'` and `type === 'tool_result'` to observe all tool interactions. Use `type === 'compression'` to detect when context compression fires.

---

### Context Types

#### ContextWindow

```typescript
interface ContextWindow {
  systemPrompt: string
  scratchpad: string
  turns: Turn[]
  tokenCount: number
  maxTokens: number
  compressionSummary?: string
  metadata: Record<string, unknown>
}
```

#### Turn

```typescript
interface Turn {
  role: 'user' | 'assistant' | 'tool' | 'system'
  content: string | ContentBlock[]
  tokenCount: number
  turnIndex: number
  compressed: boolean
  toolCalls?: ToolCall[]
  toolResults?: ToolResult[]
}
```

#### ToolCall / ToolResult

```typescript
interface ToolCall {
  id: string
  name: string
  arguments: string  // JSON-encoded string
}

interface ToolResult {
  toolCallId: string
  content: string
}
```

---

### IRAGAdapter

Interface for retrieval-augmented generation integration. See `src/types/rag.ts`.

```typescript
interface IRAGAdapter {
  ingest(request: RAGIngestRequest): Promise<RAGIngestResponse>
  query(request: RAGQueryRequest): Promise<RAGQueryResponse>
  delete?(ids: string[]): Promise<void>
  healthCheck?(): Promise<boolean>
}

interface RAGQueryRequest {
  query: string
  topK?: number
  collectionId?: string
  filter?: Record<string, unknown>
  minScore?: number
}
```

---

### ILogger

Interface for plugging in a custom logger. See `src/types/logger.ts`.

```typescript
// LogLevel enum and ILogger interface for custom logging integrations
enum LogLevel { DEBUG = 0, INFO = 1, WARN = 2, ERROR = 3, FATAL = 4 }

interface ILogger {
  debug(message: string, metadata?: Record<string, unknown>): void
  info(message: string, metadata?: Record<string, unknown>): void
  warn(message: string, metadata?: Record<string, unknown>): void
  error(message: string, metadata?: Record<string, unknown>): void
  fatal(message: string, metadata?: Record<string, unknown>): void
  setLevel(level: LogLevel): void
}
```
