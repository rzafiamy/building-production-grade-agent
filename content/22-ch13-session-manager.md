---
title: "Chapter 13 — SessionManager: The Agent Runtime"
part: "Part III — Lemura Framework Deep Dive"
chapter: 13
page: 22
status: draft
---

*PART III — LEMURA FRAMEWORK DEEP DIVE*

## Chapter 13 — SessionManager: The Agent Runtime

> *"The `SessionManager` is where intent meets execution. Everything else is preparation."*

> [!NOTE]
> **Chapter Goal:** By the end of this chapter, you will understand how `SessionManager` orchestrates the ReAct loop, how to control session lifecycle, how to configure all aspects of execution, and what happens internally during each turn.

---

### 13.1 The SessionManager's Role
#### 13.1.1 What It Owns
#### 13.1.2 What It Delegates

### 13.2 Creating a Session
#### 13.2.1 Constructor and Configuration
#### 13.2.2 Initialization and Warmup

### 13.3 Running the Agent
#### 13.3.1 `session.run()`: Fire and Forget
#### 13.3.2 `session.step()`: One Turn at a Time
#### 13.3.3 Async Iteration with `session.stream()`

### 13.4 Setting Goals and Plans
#### 13.4.1 `session.setGoal(goal: string)`
#### 13.4.2 `session.setPlan(steps: PlanStep[])`
#### 13.4.3 Updating Goals Mid-Session

### 13.5 Session Lifecycle Events
#### 13.5.1 `onTurnStart` / `onTurnEnd`
#### 13.5.2 `onToolCall` / `onToolResult`
#### 13.5.3 `onContextCompressed`
#### 13.5.4 `onComplete` / `onError`

### 13.6 What Happens Inside a Turn
#### 13.6.1 Pre-Turn: Goal and Plan Injection
#### 13.6.2 Context Assembly
#### 13.6.3 LLM Call via Adapter
#### 13.6.4 Tool Call Dispatch and Result Collection
#### 13.6.5 Post-Turn: State Update and Compression Check

### 13.7 Controlling Execution
#### 13.7.1 Max Iterations
#### 13.7.2 Abort and Pause
#### 13.7.3 Resuming a Session

### 13.8 Session State and Introspection

---

## Key Takeaways
