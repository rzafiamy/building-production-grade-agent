---
title: "Part II — Architecture Fundamentals"
part: "Part II — Architecture Fundamentals"
page: 12
status: draft
---

# Part II — Architecture Fundamentals

## Building on Solid Ground

Part I gave you the why: why agents are viable now, what properties define them, what failure modes to watch for, and how the current model and API landscape is structured. Part II gives you the how — not the how of any specific framework, but the how of building agent systems at all.

Every production agent, regardless of the framework that implements it, is built from the same set of architectural components. Understanding those components — what they do, why they are shaped the way they are, and how they interact — is the prerequisite for using any framework intelligently. A developer who understands the ReAct loop will use `SessionManager` better than one who only knows the `session.run()` API. A developer who understands context growth will configure compression strategies correctly the first time rather than after the first production incident.

Part II is deliberately framework-agnostic for the first five sections. The concepts are presented in terms of the problems they solve, with concrete implementations in Lemura as the reference. The goal is that after reading this part, you could implement a minimal agent runtime yourself — and therefore understand exactly what Lemura is doing and why.

### What This Part Covers

- Chapter 5: The ReAct Loop — the engine of every agent
- Chapter 6: Tools — the interface between the agent and the world
- Chapter 7: Context — the agent's working memory and its limits
- Chapter 8: Planning and Goals — directing agents toward outcomes
- Chapter 9: Compression — surviving the context window
- Chapter 10: Provider Adapters — staying model-agnostic

### Why Architecture Comes Before Framework

Frameworks are opinions encoded in code. When you understand the architecture they implement, you can evaluate whether their opinions match your requirements, extend them in the right places, and debug them when they do not behave as expected.

Without architectural understanding, framework usage becomes cargo-cult engineering: you copy the example, it works until it does not, and you have no model for diagnosing the failure. The first time your agent hits a context window exhaustion bug, you need to understand what a context window is and how it fills — not just which configuration parameter controls the compression threshold.

There is also a practical benefit: the architectural patterns in this part transfer across frameworks. If you understand the ReAct loop, you can read LangGraph code, AutoGen code, and Lemura code and recognize what each component does. The concepts are more durable than any specific API.

### The Mental Model That Ties It All Together

Every agent session is a loop operating on shared state. The state is the context window. The loop is the ReAct cycle. The inputs to the loop come from tools. The outputs of the loop are tool calls and, eventually, a final response.

```text
┌─────────────────────────────────────────────────────┐
│                   AGENT SESSION                     │
│                                                     │
│  ┌─────────┐   reason   ┌──────────┐               │
│  │  Goal   │──────────▶ │   LLM    │               │
│  └─────────┘            └──────────┘               │
│       ▲                      │ tool call            │
│       │                      ▼                     │
│  ┌─────────┐   result  ┌──────────┐               │
│  │ Context │◀────────── │  Tools  │               │
│  └─────────┘            └──────────┘               │
│       │                                             │
│  ┌─────────┐                                        │
│  │Compress │  (when context grows too large)        │
│  └─────────┘                                        │
└─────────────────────────────────────────────────────┘
```

Each chapter in this part addresses one component of this diagram. Chapter 5 covers the loop itself. Chapter 6 covers the tools. Chapter 7 covers the context. Chapter 8 covers the goal. Chapter 9 covers compression. Chapter 10 covers the provider sitting behind the LLM box. By the end of Part II, every box and every arrow in this diagram will have a concrete engineering implementation behind it.
