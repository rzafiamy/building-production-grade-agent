---
title: "Chapter 17 — ToolResponseProcessor: Compressing Tool Output"
part: "Part III — Lemura Framework Deep Dive"
chapter: 17
page: 26
status: draft
---

*PART III — LEMURA FRAMEWORK DEEP DIVE*

## Chapter 17 — ToolResponseProcessor: Compressing Tool Output

> *"A tool that returns 50,000 tokens of JSON will eat your context window in two calls. The ToolResponseProcessor is the gatekeeper."*

> [!NOTE]
> **Chapter Goal:** By the end of this chapter, you will understand how `ToolResponseProcessor` intercepts and compresses large tool results, how to configure its budget and thresholds, and how to write custom response processors for domain-specific compression.

---

### 17.1 The Tool Result Explosion Problem
#### 17.1.1 How Tool Results Grow Without Bound
#### 17.1.2 Why This Breaks Agents Silently

### 17.2 What ToolResponseProcessor Does
#### 17.2.1 Interception: Seeing the Result Before the Context Does
#### 17.2.2 Budget Enforcement: Token Limits per Result
#### 17.2.3 Compression: Summarizing Large Results

### 17.3 Configuration
#### 17.3.1 `budgetPercent`: Fraction of Context for Tool Results
#### 17.3.2 Thresholds: When to Compress vs. Pass Through
#### 17.3.3 Per-Tool Configuration

### 17.4 Compression Strategies for Tool Output
#### 17.4.1 Truncation: Fast and Lossy
#### 17.4.2 Summarization: Slower but Semantic
#### 17.4.3 Structured Extraction: Best for JSON/Data

### 17.5 Preserving Key Information
#### 17.5.1 What Must Survive Compression
#### 17.5.2 Anchors: Fields That Are Always Kept

### 17.6 Custom Response Processors

### 17.7 Debugging Tool Response Compression
#### 17.7.1 Logging Before and After
#### 17.7.2 Detecting When Compression Causes Errors

---

## Key Takeaways
