---
title: "Appendix B — SessionConfig Key Reference"
page: 56
status: draft
---

## Appendix B — SessionConfig Key Reference

*Complete reference for all keys in the `SessionConfig` interface.*
*Source of truth: `src/types/agent.ts`*

---

### Model and Provider

| Key | Type | Default | Description |
|---|---|---|---|
| `adapter` | `IProviderAdapter` | required | The LLM provider adapter |
| `model` | `string` | required | Model identifier string |
| `maxCompletionTokens` | `number` | `2000` | Max tokens for each completion |

---

### Context and Compression

| Key | Type | Default | Description |
|---|---|---|---|
| `contextStrategies` | `IContextStrategy[]` | `[]` | Ordered list of compression strategies |
| `maxContextTokens` | `number` | provider limit | Hard context window limit |

---

### Goal and Plan

| Key | Type | Default | Description |
|---|---|---|---|
| `goal` | `string` | `undefined` | Initial agent goal |
| `plan` | `PlanStep[]` | `undefined` | Initial plan steps |
| `goalInjectionPosition` | `'pre_system' \| 'post_system' \| 'pre_turn'` | `'post_system'` | Where to inject goal reminder |
| `goalInjectionN` | `number` | `1` | Inject goal every N turns |

---

### Tools

| Key | Type | Default | Description |
|---|---|---|---|
| `tools` | `ToolDefinition[]` | `[]` | Available tools for the agent |
| `toolResponseProcessor` | `ToolResponseProcessor` | `undefined` | Processor for tool results |

---

### Skills

| Key | Type | Default | Description |
|---|---|---|---|
| `skills` | `Skill[]` | `[]` | Skills to inject into context |
| `skillTokenBudget` | `number` | `undefined` | Max tokens for all skills combined |

---

### Execution Control

| Key | Type | Default | Description |
|---|---|---|---|
| `maxIterations` | `number` | `50` | Max ReAct loop iterations |
| `systemPrompt` | `string` | `undefined` | Base system prompt |

---

### Callbacks and Hooks

| Key | Type | Description |
|---|---|---|
| `onTurnStart` | `(turn: number) => void` | Called before each turn |
| `onTurnEnd` | `(turn: number, result: StepResult) => void` | Called after each turn |
| `onToolCall` | `(call: ToolCall) => void` | Called before tool execution |
| `onToolResult` | `(result: ToolResult) => void` | Called after tool execution |
| `onContextCompressed` | `(event: CompressionEvent) => void` | Called when compression fires |
| `onComplete` | `(result: AgentResult) => void` | Called on session completion |
| `onError` | `(error: Error) => void` | Called on unrecoverable error |
