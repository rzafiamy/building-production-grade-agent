---
title: "Chapter 20 — Memory Architecture for Long-Running Agents"
part: "Part IV — Memory and State"
chapter: 20
page: 30
status: draft
---

*PART IV — MEMORY AND STATE*

## Chapter 20 — Memory Architecture for Long-Running Agents

> *"The context window is RAM. Summary memory is a cache. External storage is disk. Use them at the right layer."*

> [!NOTE]
> **Chapter Goal:** By the end of this chapter, you will understand the three tiers of agent memory, how to architect memory systems for agents that run for hours or days, and how to integrate external memory stores with Lemura sessions.

---

### 20.1 Why Single-Context Memory Fails for Long Tasks
#### 20.1.1 The Physical Limit
#### 20.1.2 The Degradation Problem
#### 20.1.3 The Cost Problem

### 20.2 The Three-Tier Memory Architecture
#### 20.2.1 Tier 1: In-Context Memory (Working Memory)
#### 20.2.2 Tier 2: Summary Memory (Compressed Cache)
#### 20.2.3 Tier 3: External Memory (Persistent Store)

### 20.3 What Goes in Each Tier
#### 20.3.1 In-Context: Goals, Recent History, Active Tool Results
#### 20.3.2 Summary: Compressed History, Completed Step Summaries
#### 20.3.3 External: All History, Artifacts, Structured Data

### 20.4 External Memory Integration
#### 20.4.1 Vector Stores for Semantic Retrieval
#### 20.4.2 Key-Value Stores for Structured State
#### 20.4.3 File Systems for Artifacts

### 20.5 Memory Retrieval Strategies
#### 20.5.1 Recency-Based Retrieval
#### 20.5.2 Relevance-Based Retrieval (RAG)
#### 20.5.3 Entity-Based Retrieval

### 20.6 Memory Consistency
#### 20.6.1 The Write-After-Read Problem
#### 20.6.2 Keeping Tiers in Sync
#### 20.6.3 Memory Invalidation

### 20.7 Implementing a Memory Tool in Lemura
#### 20.7.1 `remember()` and `recall()` Tool Pattern
#### 20.7.2 Integrating with ContextManager

---

## Key Takeaways
