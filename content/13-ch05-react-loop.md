---
title: "Chapter 5 — The ReAct Loop: Reasoning and Acting"
part: "Part II — Architecture Fundamentals"
chapter: 5
page: 13
status: draft
---

*PART II — ARCHITECTURE FUNDAMENTALS*

## Chapter 5 — The ReAct Loop: Reasoning and Acting

> *"Think, then act, then observe, then think again. This is the heartbeat of every autonomous agent."*

> [!NOTE]
> **Chapter Goal:** By the end of this chapter, you will understand the ReAct pattern in depth — how it works, why it's the dominant paradigm, its inherent limitations, and how Lemura's `SessionManager` implements it.

---

### 5.1 The Origins of ReAct
#### 5.1.1 From Chain-of-Thought to Action
#### 5.1.2 The Original Paper and What It Got Right

### 5.2 The Loop in Detail
#### 5.2.1 Thought: The Model Reasons
#### 5.2.2 Action: The Model Calls a Tool
#### 5.2.3 Observation: The Tool Returns a Result
#### 5.2.4 Repeat Until Done (or Stuck)

### 5.3 The Loop as a State Machine

```text
┌─────────┐
│  START  │
└────┬────┘
     │
     ▼
┌─────────────┐       no tool call      ┌─────────────┐
│   THINKING  │ ─────────────────────▶  │    DONE     │
└─────────────┘                         └─────────────┘
     │ tool call
     ▼
┌─────────────┐
│   ACTING    │
└─────────────┘
     │ result
     ▼
┌─────────────┐
│  OBSERVING  │ ─────────────────────▶  (back to THINKING)
└─────────────┘
```

### 5.4 Termination Conditions
#### 5.4.1 Natural Completion
#### 5.4.2 Max Iterations
#### 5.4.3 Error Termination
#### 5.4.4 Human Interrupt

### 5.5 The ReAct Loop in Lemura: SessionManager

### 5.6 What ReAct Gets Wrong (and How to Work Around It)
#### 5.6.1 Shallow Reasoning
#### 5.6.2 Context Accumulation
#### 5.6.3 No Native Plan Tracking

### 5.7 Beyond Vanilla ReAct: Extensions and Variants

---

## Key Takeaways
