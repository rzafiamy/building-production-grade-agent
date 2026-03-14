---
title: "Part III — Lemura Framework Deep Dive"
part: "Part III — Lemura Framework Deep Dive"
page: 19
status: draft
---

# Part III — Lemura Framework Deep Dive

## From Concepts to Code

Parts I and II gave you the architecture. Part III gives you the implementation. Every concept introduced in the first two parts has a concrete counterpart in Lemura — a class that owns it, a configuration option that controls it, a method that activates it. This part maps those concepts to code with enough depth that you can use each component confidently in production.

Part III is not a tutorial. It is a reference with explanation. The chapters follow the natural ordering of a session: first you understand why Lemura exists and what it was designed to solve (Chapter 11), then you install it and configure your first session (Chapter 12), then you learn the runtime that drives everything (Chapter 13), and then you go deeper into each subsystem. By the end of this part, you will have used every major API in the framework.

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
They assume Lemura v1.4+ is installed.

```bash
# Install Lemura
pnpm add lemura
```

Every example can be run standalone unless noted. Examples that require an API key read from environment variables rather than hardcoding credentials. Set `LEMURA_API_KEY`, `LEMURA_BASE_URL`, and `LEMURA_MODEL` before running.

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

Each box in this diagram is a chapter in Part III. `SessionManager` is the outermost shell — it wires everything together and exposes the single `run()` method callers interact with. The inner boxes are the subsystems that `SessionManager` orchestrates. Understanding each one individually is the goal of this part.
