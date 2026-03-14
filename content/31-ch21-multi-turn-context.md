---
title: "Chapter 21 — Multi-Turn Context Management"
part: "Part IV — Memory and State"
chapter: 21
page: 31
status: draft
---

*PART IV — MEMORY AND STATE*

## Chapter 21 — Multi-Turn Context Management

> *"Each turn is a conversation. Each conversation is a story. The agent must know where it is in the story at all times."*

> [!NOTE]
> **Chapter Goal:** By the end of this chapter, you will understand how to manage coherent context across dozens or hundreds of turns, how to handle session handoffs, how to inject historical summaries correctly, and how to test multi-turn behavior.

---

### 21.1 The Multi-Turn Challenge
#### 21.1.1 Each Turn Adds, Nothing Removes (by Default)
#### 21.1.2 Coherence Degradation Over Time

### 21.2 Designing for Multi-Turn from the Start
#### 21.2.1 Session Boundaries: When to Start Fresh
#### 21.2.2 Continuity Signals: Telling the Agent It's Continuing
#### 21.2.3 The Session Handoff Protocol

### 21.3 Context Window Budget Allocation
#### 21.3.1 The Budget Equation
#### 21.3.2 Allocating Across: System, Goals, History, Current Input
#### 21.3.3 Dynamic Budget Adjustment

### 21.4 Injecting Prior Session Context
#### 21.4.1 Session Summary Injection
#### 21.4.2 Structured State Injection
#### 21.4.3 Using `SummaryInjectionStrategy`

### 21.5 Multi-Session Agents
#### 21.5.1 Persisting Session State Between Runs
#### 21.5.2 Session Metadata and ID Tracking
#### 21.5.3 Loading Previous Session Context

### 21.6 Testing Multi-Turn Behavior
#### 21.6.1 Simulating Long Sessions in Tests
#### 21.6.2 Detecting Coherence Drift
#### 21.6.3 Regression Testing After Compression Changes

---

## Key Takeaways
