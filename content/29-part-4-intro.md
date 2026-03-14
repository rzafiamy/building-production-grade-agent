---
title: "Part IV — Memory and State"
part: "Part IV — Memory and State"
page: 29
status: draft
---

# Part IV — Memory and State

## What the Agent Remembers

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
