---
title: "Chapter 16 — ContinuationPlanner: Multi-Step Execution"
part: "Part III — Lemura Framework Deep Dive"
chapter: 16
page: 25
status: draft
---

*PART III — LEMURA FRAMEWORK DEEP DIVE*

## Chapter 16 — ContinuationPlanner: Multi-Step Execution

> *"Without a plan tracker, the agent doesn't know if it's on step 2 of 10 or wandering in circles."*

> [!NOTE]
> **Chapter Goal:** By the end of this chapter, you will understand how `ContinuationPlanner` tracks plan execution state, how step dependencies work, how `outputKey` and `inputMapping` wire steps together, and how to design plans for complex multi-step tasks.

---

### 16.1 The Problem: Plans Without State

### 16.2 What ContinuationPlanner Does
#### 16.2.1 Tracking Step Status
#### 16.2.2 Resolving Dependencies
#### 16.2.3 Passing Outputs Between Steps

### 16.3 The `PlanStep` Interface
#### 16.3.1 `id`: Step Identity
#### 16.3.2 `description`: What the Agent Reads
#### 16.3.3 `dependsOn`: Dependency Declaration
#### 16.3.4 `condition`: Conditional Execution
#### 16.3.5 `outputKey`: Naming the Result
#### 16.3.6 `inputMapping`: Consuming Prior Outputs

### 16.4 Step Status Lifecycle
#### 16.4.1 `pending` → `active` → `complete` / `failed` / `skipped`
#### 16.4.2 How the Planner Decides What's Next
#### 16.4.3 Handling Failures Mid-Plan

### 16.5 Data Flow Between Steps
#### 16.5.1 The Output Store
#### 16.5.2 `inputMapping` in Practice
#### 16.5.3 Complex Data Passing Patterns

### 16.6 Parallel Execution
#### 16.6.1 Steps with No Mutual Dependencies
#### 16.6.2 How Parallelism Is Detected
#### 16.6.3 Limits and Gotchas

### 16.7 Plan Examples
#### 16.7.1 Simple Linear Plan
#### 16.7.2 Fan-Out / Fan-In Plan
#### 16.7.3 Conditional Branching Plan

### 16.8 Integrating ContinuationPlanner with SessionManager

---

## Key Takeaways
