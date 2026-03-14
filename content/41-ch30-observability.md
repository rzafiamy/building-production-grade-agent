---
title: "Chapter 30 — Observability and Debugging"
part: "Part V — Advanced Patterns"
chapter: 30
page: 41
status: draft
---

*PART V — ADVANCED PATTERNS*

## Chapter 30 — Observability and Debugging

> *"You can't debug what you can't see. Agents that run in the dark fail in the dark."*

> [!NOTE]
> **Chapter Goal:** By the end of this chapter, you will be able to instrument agents for full observability, build effective debugging workflows, trace agent failures to their root cause, and set up alerting for production issues.

---

### 30.1 Why Agent Observability Is Hard
#### 30.1.1 Non-Determinism Makes Reproduction Difficult
#### 30.1.2 Many Steps, Many Failure Points
#### 30.1.3 Context Is Both Evidence and Evidence Destroyer

### 30.2 The Three Pillars of Agent Observability
#### 30.2.1 Logs: The Full Execution Record
#### 30.2.2 Traces: The Causal Chain
#### 30.2.3 Metrics: The Aggregated View

### 30.3 What to Log
#### 30.3.1 Every Turn: Input, Output, Token Count
#### 30.3.2 Every Tool Call: Name, Args, Result, Latency
#### 30.3.3 Every Compression Event
#### 30.3.4 Goal State at Each Turn
#### 30.3.5 Errors and Recovery Actions

### 30.4 Distributed Tracing for Multi-Agent Systems
#### 30.4.1 Trace IDs Across Agent Boundaries
#### 30.4.2 Parent-Child Spans for Tool Calls
#### 30.4.3 OpenTelemetry Integration

### 30.5 Key Metrics to Track
#### 30.5.1 Turns per Session
#### 30.5.2 Token Usage per Turn and Total
#### 30.5.3 Tool Call Success Rate
#### 30.5.4 Compression Trigger Frequency
#### 30.5.5 Goal Completion Rate

### 30.6 Debugging Agent Failures
#### 30.6.1 Reconstructing the Session from Logs
#### 30.6.2 Identifying the First Wrong Turn
#### 30.6.3 The "Turn Replay" Technique
#### 30.6.4 Prompting the Agent to Explain Its Reasoning

### 30.7 Session Replay and Post-Mortems

### 30.8 Alerting and SLOs for Agents

---

## Key Takeaways
