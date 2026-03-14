---
title: "Part IV — Memory and State"
part: "Part IV — Memory and State"
page: 29
status: draft
---

# Part IV — Memory and State

## What the Agent Remembers

An agent that cannot remember is an agent that cannot learn. Every tool result it collected, every decision it made, every sub-goal it completed — if none of this persists beyond the current context window, each turn is effectively the agent starting over with slightly more context. For short sessions this is acceptable. For the agents that matter most in production — the ones running long research tasks, managing complex multi-step workflows, or sustaining coherence across days of work — memory architecture is not an implementation detail. It is the core engineering problem.

Part III showed you how Lemura's subsystems work within a single session. Part IV shows you how to extend coherence beyond a single session: how to architect memory systems that scale, how to manage context across hundreds of turns, how to compress without losing what matters, and how to make sessions survivable across crashes and restarts.

### What This Part Covers

- Chapter 20: Memory architecture — the types of memory an agent can have
- Chapter 21: Multi-turn context management — sustaining coherence over time
- Chapter 22: Compression strategies in depth — the full playbook
- Chapter 23: State persistence and recovery — surviving crashes and restarts

### The Memory Hierarchy

```text
┌──────────────────────────────────────┐
│          IN-CONTEXT MEMORY           │  ← fast, limited, expensive
│  (system prompt, recent turns,       │
│   tool results, injected goals)      │
└──────────────────────────────────────┘
           ↕ compression / retrieval
┌──────────────────────────────────────┐
│         SUMMARY MEMORY               │  ← medium speed, lossy
│  (compressed history, rolling        │
│   summaries of past turns)           │
└──────────────────────────────────────┘
           ↕ storage / retrieval
┌──────────────────────────────────────┐
│         EXTERNAL MEMORY              │  ← slow, lossless, unlimited
│  (vector stores, databases,          │
│   file systems, session logs)        │
└──────────────────────────────────────┘
```

### Why Memory Is the Hardest Problem in Agents

Memory is hard because it is cross-cutting. A bad tool design produces a bad tool. A bad compression configuration produces a compressible but lossy context. A bad memory architecture produces failures that are distributed across every part of the system and often show up only under the specific conditions of long sessions, edge-case inputs, or high concurrent load.

The four chapters in this part give you the complete playbook for each layer of the hierarchy. Read them in order the first time — the memory architecture (Chapter 20) provides the mental model that the subsequent chapters build on.
