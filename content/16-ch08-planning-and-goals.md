---
title: "Chapter 8 — Planning and Goals: Directing the Agent"
part: "Part II — Architecture Fundamentals"
chapter: 8
page: 16
status: draft
---

*PART II — ARCHITECTURE FUNDAMENTALS*

## Chapter 8 — Planning and Goals: Directing the Agent

> *"An agent without a goal is random. An agent with only a goal is naive. The art is in structured intent."*

> [!NOTE]
> **Chapter Goal:** By the end of this chapter, you will understand the difference between goals and plans, how to structure goals that survive multi-turn execution, how plans enable dependency tracking and step sequencing, and how Lemura's `GoalInjector` and `ContinuationPlanner` implement these concepts.

---

### 8.1 The Goal: What the Agent Is Trying to Accomplish
#### 8.1.1 Goals vs. Instructions vs. Prompts
#### 8.1.2 Properties of Good Agent Goals
#### 8.1.3 Short-Term Goals, Sub-Goals, and Objectives

### 8.2 Goal Drift: The Silent Killer of Long Agents
#### 8.2.1 Why Models Forget Their Goal
#### 8.2.2 Goal Injection: Keeping the Goal Alive

### 8.3 Plans: Structured Sequences of Intent
#### 8.3.1 What Is a Plan?
#### 8.3.2 Plan vs. Script: The Key Difference
#### 8.3.3 Step Dependencies and Execution Order
#### 8.3.4 Conditional Steps and Branching

### 8.4 Plan Design Patterns
#### 8.4.1 Linear Plans
#### 8.4.2 Parallel Steps
#### 8.4.3 Dependent Chains with `inputMapping`
#### 8.4.4 Fallback and Retry Steps

### 8.5 Dynamic Planning: When the Plan Changes Mid-Execution
#### 8.5.1 When to Revise the Plan
#### 8.5.2 Keeping the Agent Informed of Plan Changes

### 8.6 Planning in Lemura
#### 8.6.1 `session.setGoal()` and `session.setPlan()`
#### 8.6.2 The PlanStep Interface
#### 8.6.3 `ContinuationPlanner` Overview

---

## Key Takeaways
