---
title: "Chapter 24 — Multi-Agent Systems"
part: "Part V — Advanced Patterns"
chapter: 24
page: 35
status: draft
---

*PART V — ADVANCED PATTERNS*

## Chapter 24 — Multi-Agent Systems

> *"One agent hits a wall. A team of agents goes around it."*

> [!NOTE]
> **Chapter Goal:** By the end of this chapter, you will understand the architecture of multi-agent systems, when to use them (and when not to), the communication protocols between agents, and how to implement agent-to-agent tool calls in Lemura.

---

### 24.1 Why Multiple Agents?
#### 24.1.1 Task Decomposition: Divide and Conquer
#### 24.1.2 Specialization: Right Model for the Right Task
#### 24.1.3 Parallelism: Doing Work Concurrently
#### 24.1.4 Isolation: Containing Failures

### 24.2 Multi-Agent Topologies
#### 24.2.1 Pipeline: Sequential Handoffs
#### 24.2.2 Supervisor: One Agent Manages Many
#### 24.2.3 Peer Network: Agents Collaborate as Equals
#### 24.2.4 Hierarchical: Nested Supervisors

### 24.3 Agent Communication Patterns
#### 24.3.1 Tool-as-Agent: Calling an Agent Like a Tool
#### 24.3.2 Message Passing: Async Communication
#### 24.3.3 Shared Memory: Common Context

### 24.4 Implementing Agent-to-Agent Calls in Lemura
#### 24.4.1 Wrapping a Session as a Tool
#### 24.4.2 Passing Context Between Sessions
#### 24.4.3 Handling Agent Failures from a Parent

### 24.5 State and Context in Multi-Agent Systems
#### 24.5.1 What Each Agent Knows
#### 24.5.2 Shared Goals vs. Local Goals
#### 24.5.3 Avoiding Context Explosion

### 24.6 Multi-Agent Anti-Patterns
#### 24.6.1 Too Many Agents for a Simple Task
#### 24.6.2 Agents That Talk to Each Other in Loops
#### 24.6.3 No Clear Ownership of State

### 24.7 When NOT to Use Multiple Agents

---

## Key Takeaways
