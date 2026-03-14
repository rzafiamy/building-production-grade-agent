---
title: "Appendix A — Lemura API Reference"
page: 55
status: draft
---

## Appendix A — Lemura API Reference

*Reference for Lemura v1.3+. See `src/types/` for authoritative TypeScript definitions.*

---

### SessionManager

#### Constructor

#### Methods
- `run(input: string): Promise<AgentResult>`
- `step(input: string): Promise<StepResult>`
- `setGoal(goal: string): void`
- `setPlan(steps: PlanStep[]): void`
- `abort(): void`

---

### SessionConfig

*See Appendix B for full key reference.*

---

### IProviderAdapter

#### Interface
- `complete(request: CompletionRequest): Promise<CompletionResponse>`

---

### OpenAICompatibleAdapter

#### Constructor
#### Configuration Options

---

### ContextManager

#### Constructor
#### Methods
- `addMessage(message: Message): void`
- `getMessages(): Message[]`
- `compress(): Promise<void>`

---

### IContextStrategy

#### Interface
- `priority: number`
- `triggerThreshold: number`
- `compress(context: ContextState, adapter: IProviderAdapter): Promise<ContextState>`

---

### SandwichCompressionStrategy

#### Constructor Parameters
#### Configuration

---

### HistoryCompressionStrategy

#### Constructor Parameters
#### Configuration

---

### SummaryInjectionStrategy

#### Constructor Parameters
#### Configuration

---

### GoalInjector

#### Constructor
#### Methods
- `setGoal(goal: string): void`
- `setSubGoal(subGoal: string): void`
- `completeSubGoal(): void`
- `shouldInjectThisTurn(turn: number): boolean`
- `getFormattedBlock(): string`

---

### ContinuationPlanner

#### Constructor
#### Methods
- `setPlan(steps: PlanStep[]): void`
- `getNextSteps(): PlanStep[]`
- `markComplete(stepId: string, output?: unknown): void`
- `markFailed(stepId: string, error: Error): void`
- `getState(): PlanState`

---

### PlanStep Interface

```typescript
interface PlanStep {
  id: string
  description: string
  dependsOn?: string[]
  condition?: string
  outputKey?: string
  inputMapping?: Record<string, string>
}
```

---

### ToolResponseProcessor

#### Constructor Parameters
#### Methods

---

### MCPClient

#### Constructor
#### Methods
- `connect(): Promise<void>`
- `listTools(): Promise<ToolDefinition[]>`
- `callTool(name: string, args: unknown): Promise<unknown>`
- `disconnect(): Promise<void>`

---

### MCPClientRegistry

#### Methods
- `register(name: string, client: MCPClient): void`
- `getAllTools(): Promise<ToolDefinition[]>`
- `callTool(name: string, args: unknown): Promise<unknown>`
