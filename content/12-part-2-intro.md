---
title: "Part II — Architecture Fundamentals"
part: "Part II — Architecture Fundamentals"
page: 12
status: draft
---

# Part II — Architecture Fundamentals

## Building on Solid Ground

### What This Part Covers

- Chapter 5: The ReAct Loop — the engine of every agent
- Chapter 6: Tools — the interface between the agent and the world
- Chapter 7: Context — the agent's working memory and its limits
- Chapter 8: Planning and Goals — directing agents toward outcomes
- Chapter 9: Compression — surviving the context window
- Chapter 10: Provider Adapters — staying model-agnostic

### Why Architecture Comes Before Framework

### The Mental Model That Ties It All Together

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
