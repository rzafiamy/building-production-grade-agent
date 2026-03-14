---
title: "Chapter 7 — Context: The Agent's Working Memory"
part: "Part II — Architecture Fundamentals"
chapter: 7
page: 15
status: draft
---

*PART II — ARCHITECTURE FUNDAMENTALS*

## Chapter 7 — Context: The Agent's Working Memory

> *"Context is not just what the model sees. It's everything the agent knows about the world right now."*

> [!NOTE]
> **Chapter Goal:** By the end of this chapter, you will understand what constitutes an agent's context, how the context window works and fails, the different types of context content, and how to architect context management to avoid the most common and costly failures.

---

### 7.1 What Is Context?
#### 7.1.1 The Message Array: The Raw Representation
#### 7.1.2 System Prompt vs. Conversation History
#### 7.1.3 Tool Definitions and Their Token Cost

### 7.2 The Context Window: Physical Limits and Real Behavior
#### 7.2.1 Token Counting: It's Never What You Expect
#### 7.2.2 The Lost-in-the-Middle Problem
#### 7.2.3 Attention Degradation Over Long Contexts

### 7.3 Anatomy of a Well-Structured Context
#### 7.3.1 The System Prompt Layer
#### 7.3.2 The Goal and Plan Layer
#### 7.3.3 The Conversation History Layer
#### 7.3.4 The Tool Results Layer

### 7.4 Context Growth Over Time
#### 7.4.1 How Fast Does Context Grow?
#### 7.4.2 The Tool Result Explosion Problem
#### 7.4.3 When Context Becomes an Anchor, Not a Memory

### 7.5 Context Management Strategies (Preview)
#### 7.5.1 Truncation
#### 7.5.2 Summarization
#### 7.5.3 Compression
#### 7.5.4 External Memory with Retrieval

### 7.6 Context in Lemura: The ContextManager
#### 7.6.1 The IContextStrategy Interface
#### 7.6.2 Priority-Based Strategy Selection
#### 7.6.3 Trigger Thresholds and When Compression Fires

---

## Key Takeaways
