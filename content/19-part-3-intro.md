---
title: "Part III — Lemura Framework Deep Dive"
part: "Part III — Lemura Framework Deep Dive"
page: 19
status: draft
---

# Part III — Lemura Framework Deep Dive

## From Concepts to Code

### What This Part Covers

- Chapter 11: Why Lemura — design philosophy and core decisions
- Chapter 12: Installing and configuring Lemura for your project
- Chapter 13: `SessionManager` — the agent runtime
- Chapter 14: `ContextManager` and the context strategy system
- Chapter 15: Goal injection — keeping the agent on task
- Chapter 16: `ContinuationPlanner` — multi-step execution
- Chapter 17: `ToolResponseProcessor` — compressing tool output
- Chapter 18: MCP integration — connecting to the broader ecosystem
- Chapter 19: The skills system — reusable, token-aware capabilities

### Conventions Used in This Part

All code examples in Part III are TypeScript ESM and target Node.js 18+.
They assume Lemura v1.3+ is installed.

```bash
pnpm add lemura
```

Every example can be run standalone unless noted.

### The Architecture in One Diagram

```text
┌────────────────────────────────────────────────────────────────┐
│                         SessionManager                         │
│                                                                │
│  ┌──────────────┐  ┌───────────────────┐  ┌────────────────┐  │
│  │ GoalInjector │  │ContextManager     │  │SkillInjector   │  │
│  └──────────────┘  │  ├ Sandwich       │  └────────────────┘  │
│  ┌──────────────┐  │  ├ History        │  ┌────────────────┐  │
│  │Continuation  │  │  └ SummaryInject  │  │MCPClient       │  │
│  │Planner       │  └───────────────────┘  │Registry        │  │
│  └──────────────┘                         └────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │             IProviderAdapter (OpenAICompatible...)       │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
```
