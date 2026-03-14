---
title: "Chapter 23 — State Persistence and Recovery"
part: "Part IV — Memory and State"
chapter: 23
page: 33
status: draft
---

*PART IV — MEMORY AND STATE*

## Chapter 23 — State Persistence and Recovery

> *"In production, processes crash. Networks fail. Users close tabs. Your agent must survive all of this."*

> [!NOTE]
> **Chapter Goal:** By the end of this chapter, you will be able to design agents that persist their state across restarts, recover gracefully from partial failures, implement checkpoint-based resumption, and handle the consistency challenges of distributed execution.

---

### 23.1 Why Statelessness Fails for Agents
#### 23.1.1 The Cost of Restarting from Scratch
#### 23.1.2 Partial Completion and Idempotency

### 23.2 What State Must Be Persisted
#### 23.2.1 The Message History
#### 23.2.2 The Plan and Its Execution State
#### 23.2.3 Tool Results and Artifacts
#### 23.2.4 Goals and Sub-Goals
#### 23.2.5 Compression Summaries

### 23.3 Checkpoint Architecture
#### 23.3.1 After-Turn Checkpointing
#### 23.3.2 Before-Action Checkpointing (for Destructive Tools)
#### 23.3.3 Checkpoint Storage Options

### 23.4 Resumption Strategies
#### 23.4.1 Full Resume: From Last Checkpoint
#### 23.4.2 Partial Resume: Replaying From a Step
#### 23.4.3 Summary Resume: Starting Fresh with Context

### 23.5 Idempotency in Tool Calls
#### 23.5.1 Why Tool Idempotency Matters During Recovery
#### 23.5.2 Idempotency Keys
#### 23.5.3 Checking Before Acting

### 23.6 Implementing Persistence with Lemura
#### 23.6.1 Session Serialization
#### 23.6.2 Restoring a Session from a Checkpoint
#### 23.6.3 Integration with Redis, PostgreSQL, Files

### 23.7 Distributed Agents and Consistency
#### 23.7.1 The Dual-Write Problem
#### 23.7.2 Leader Election for Long-Running Jobs

---

## Key Takeaways
