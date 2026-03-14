---
title: "Chapter 26 — Error Recovery and Resilience"
part: "Part V — Advanced Patterns"
chapter: 26
page: 37
status: draft
---

*PART V — ADVANCED PATTERNS*

## Chapter 26 — Error Recovery and Resilience

> *"The question is not whether your agent will fail. It's what it does next."*

> [!NOTE]
> **Chapter Goal:** By the end of this chapter, you will be able to classify agent errors, implement retry strategies, design fallback behaviors, build recovery flows, and prevent the most common failure cascades in production.

---

### 26.1 Error Classification for Agents
#### 26.1.1 Transient Errors: Retry and Continue
#### 26.1.2 Permanent Errors: Fail Fast and Escalate
#### 26.1.3 Semantic Errors: The Agent Did Something Wrong
#### 26.1.4 Environmental Errors: The World Changed

### 26.2 Retry Strategies
#### 26.2.1 Simple Retry with Backoff
#### 26.2.2 Retry with Context Modification
#### 26.2.3 Retry Budgets and Circuit Breakers
#### 26.2.4 What Not to Retry

### 26.3 Fallback Strategies
#### 26.3.1 Degraded Functionality
#### 26.3.2 Alternative Tool or Approach
#### 26.3.3 Human Escalation as a Fallback

### 26.4 Self-Healing Agents
#### 26.4.1 Detecting When the Agent Is Stuck
#### 26.4.2 The Recovery Prompt: Helping the Agent Unstick
#### 26.4.3 Injecting Error Context for Self-Correction
#### 26.4.4 Limits of Self-Healing

### 26.5 Failure Cascades and How to Prevent Them
#### 26.5.1 How One Failure Becomes Many
#### 26.5.2 Bulkhead Pattern for Agent Isolation
#### 26.5.3 Timeout Hierarchies

### 26.6 Recovery from Specific Failure Modes
#### 26.6.1 Recovering from Goal Drift
#### 26.6.2 Recovering from a Stuck Loop
#### 26.6.3 Recovering from a Bad Tool Result
#### 26.6.4 Recovering from Context Overflow

### 26.7 Resilience Testing
#### 26.7.1 Chaos Engineering for Agents
#### 26.7.2 Simulating Failure in Tests

---

## Key Takeaways
