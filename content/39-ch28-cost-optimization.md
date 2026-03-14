---
title: "Chapter 28 — Cost Optimization"
part: "Part V — Advanced Patterns"
chapter: 28
page: 39
status: draft
---

*PART V — ADVANCED PATTERNS*

## Chapter 28 — Cost Optimization

> *"An agent that solves your problem but costs $50 per run is a prototype, not a product."*

> [!NOTE]
> **Chapter Goal:** By the end of this chapter, you will be able to profile agent token usage, identify the largest cost drivers, apply optimization techniques across the full stack, and set budget controls that prevent cost runaway.

---

### 28.1 The Token Economy
#### 28.1.1 Input vs. Output Token Pricing
#### 28.1.2 Where Tokens Come From in an Agent
#### 28.1.3 The Compounding Cost of Long Sessions

### 28.2 Profiling Token Usage
#### 28.2.1 Per-Turn Token Accounting
#### 28.2.2 Identifying the Biggest Token Consumers
#### 28.2.3 Cost Projection for Long Tasks

### 28.3 System Prompt Optimization
#### 28.3.1 Measuring System Prompt Token Cost
#### 28.3.2 Trimming Without Losing Instruction Quality
#### 28.3.3 Caching System Prompts (Provider-Specific)

### 28.4 Context Compression as Cost Control
#### 28.4.1 Compression ROI: When Is It Worth the Extra Call?
#### 28.4.2 Tool Result Compression as Priority #1
#### 28.4.3 History Compression Schedules

### 28.5 Model Routing for Cost
#### 28.5.1 Cheap Models for Simple Steps
#### 28.5.2 Expensive Models Only When Needed
#### 28.5.3 Implementing Model Routing in Lemura

### 28.6 Caching Strategies
#### 28.6.1 Tool Result Caching
#### 28.6.2 Prompt Caching (Provider-Level)
#### 28.6.3 Semantic Deduplication

### 28.7 Budget Controls and Hard Limits
#### 28.7.1 Session-Level Token Budgets
#### 28.7.2 Per-Tool Cost Limits
#### 28.7.3 `maxCompletionTokens` in Lemura
#### 28.7.4 Circuit Breakers for Cost

### 28.8 Cost Benchmarking and Reporting

---

## Key Takeaways
