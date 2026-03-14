---
title: "Chapter 6 — Tools: The Agent's Hands"
part: "Part II — Architecture Fundamentals"
chapter: 6
page: 14
status: draft
---

*PART II — ARCHITECTURE FUNDAMENTALS*

## Chapter 6 — Tools: The Agent's Hands

> *"A model without tools is a brain without a body. Powerful, but unable to act in the world."*

> [!NOTE]
> **Chapter Goal:** By the end of this chapter, you will be able to design effective tools for agents, understand the JSON Schema contract, implement robust tool handlers with validation and error handling, and know which tool design patterns lead to reliable vs. unreliable agent behavior.

---

### 6.1 What Is a Tool?
#### 6.1.1 The JSON Schema Contract
#### 6.1.2 How the Model Decides to Call a Tool
#### 6.1.3 The Tool Call Lifecycle

### 6.2 Designing Tools That Agents Use Correctly
#### 6.2.1 The Name Is a Prompt
#### 6.2.2 The Description Is a Contract
#### 6.2.3 Parameter Design: Precision Over Flexibility
#### 6.2.4 Idempotency and Side Effects

### 6.3 Tool Categories
#### 6.3.1 Read Tools (Safe, Idempotent)
#### 6.3.2 Write Tools (Destructive, Needs Confirmation)
#### 6.3.3 Search Tools (Probabilistic Results)
#### 6.3.4 Composition Tools (Call Other Agents)

### 6.4 Tool Output Design
#### 6.4.1 What the Model Needs to See
#### 6.4.2 Structured vs. Unstructured Output
#### 6.4.3 Error Messages as Tool Output
#### 6.4.4 Handling Large Tool Results

### 6.5 Tool Implementation Patterns
#### 6.5.1 Validation Before Execution
#### 6.5.2 Timeout and Retry Logic
#### 6.5.3 Logging for Observability
#### 6.5.4 The Dry-Run Pattern

### 6.6 Anti-Patterns in Tool Design
#### 6.6.1 Tools That Do Too Much
#### 6.6.2 Ambiguous Parameters
#### 6.6.3 Returning Raw Exceptions

### 6.7 Registering Tools in Lemura

---

## Key Takeaways
