---
title: "Chapter 22 — Compression Strategies in Depth"
part: "Part IV — Memory and State"
chapter: 22
page: 32
status: draft
---

*PART IV — MEMORY AND STATE*

## Chapter 22 — Compression Strategies in Depth

> *"Compression is a lossy transform. The goal is to lose the right information — not randomly, but strategically."*

> [!NOTE]
> **Chapter Goal:** By the end of this chapter, you will have a complete playbook for context compression: when to use each strategy, how to configure them, how to compose them, and how to measure their effectiveness.

---

### 22.1 A Complete Taxonomy of Compression Approaches

| Strategy | Lossiness | Speed | Cost | Best For |
|---|---|---|---|---|
| Truncation | High (blind) | Instant | Free | Emergency only |
| Rolling Summary | Medium | Slow | LLM call | Long research tasks |
| Sandwich | Low | Medium | LLM call | Mixed tool/conversation |
| Summary Injection | None (re-use) | Fast | Free | Resuming sessions |
| External RAG | Zero | Slow | DB query | Archive retrieval |

### 22.2 Truncation: When You Have No Choice
#### 22.2.1 Safe Truncation Points
#### 22.2.2 What Must Never Be Truncated
#### 22.2.3 Implementing Graceful Truncation

### 22.3 Rolling History Summarization
#### 22.3.1 Summarization Prompt Design
#### 22.3.2 Summary Chaining: Summaries of Summaries
#### 22.3.3 Information Preservation Quality

### 22.4 The Sandwich Strategy Fully Explained
#### 22.4.1 The Three Zones: Header, Body, Footer
#### 22.4.2 Window Size Configuration
#### 22.4.3 Triggering and Re-Triggering
#### 22.4.4 Adapter Requirement (Why It Needs an LLM)

### 22.5 Summary Injection: Continuity Without Redundancy
#### 22.5.1 Where the Summary Comes From
#### 22.5.2 Where It Gets Injected
#### 22.5.3 Keeping the Summary Current

### 22.6 Composition Patterns
#### 22.6.1 Sandwich + Summary Injection
#### 22.6.2 History + Summary Injection
#### 22.6.3 Three-Layer Compression for Very Long Tasks

### 22.7 Measuring Compression Effectiveness
#### 22.7.1 Token Reduction Ratio
#### 22.7.2 Task Completion Rate Before/After
#### 22.7.3 Goal Retention Score

---

## Key Takeaways
