---
title: "Chapter 14 — ContextManager and Context Strategies"
part: "Part III — Lemura Framework Deep Dive"
chapter: 14
page: 23
status: draft
---

*PART III — LEMURA FRAMEWORK DEEP DIVE*

## Chapter 14 — ContextManager and Context Strategies

> *"Context management is the difference between an agent that runs for five turns and one that runs for five hundred."*

> [!NOTE]
> **Chapter Goal:** By the end of this chapter, you will understand Lemura's `ContextManager`, how to compose multiple strategies, how the priority and trigger system works, and how to choose the right strategy for your use case.

---

### 14.1 The ContextManager's Job
#### 14.1.1 Building the Message Array for Each Turn
#### 14.1.2 Deciding When and How to Compress

### 14.2 The `IContextStrategy` Interface
#### 14.2.1 `priority`: Execution Order
#### 14.2.2 `triggerThreshold`: When to Fire
#### 14.2.3 `compress()`: The Core Method
#### 14.2.4 Returning a Compressed Result

### 14.3 Strategy Composition
#### 14.3.1 Running Multiple Strategies
#### 14.3.2 How Priority Determines Order
#### 14.3.3 Chaining vs. Fallback

### 14.4 `SandwichCompressionStrategy` In Depth
#### 14.4.1 The Sandwich Explained
#### 14.4.2 Configuration Options
#### 14.4.3 When to Use It

### 14.5 `HistoryCompressionStrategy` In Depth
#### 14.5.1 Rolling Window Summarization
#### 14.5.2 Summary Quality and Length
#### 14.5.3 When to Use It

### 14.6 `SummaryInjectionStrategy` In Depth
#### 14.6.1 Re-injecting Compressed Summaries
#### 14.6.2 Keeping the Summary Fresh
#### 14.6.3 When to Use It

### 14.7 Building a Custom Strategy
#### 14.7.1 Implementing `IContextStrategy`
#### 14.7.2 Testing Your Strategy

### 14.8 Strategy Selection Guide

| Scenario | Recommended Strategy |
|---|---|
| Short tasks (< 20 turns) | None needed |
| Long research tasks | `HistoryCompressionStrategy` |
| Tasks with large tool outputs | `SandwichCompressionStrategy` |
| Both | Compose both |
| Returning to a previous session | `SummaryInjectionStrategy` |

---

## Key Takeaways
