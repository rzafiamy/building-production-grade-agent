---
title: "Chapter 15 — Goal Injection: Keeping the Agent on Track"
part: "Part III — Lemura Framework Deep Dive"
chapter: 15
page: 24
status: draft
---

*PART III — LEMURA FRAMEWORK DEEP DIVE*

## Chapter 15 — Goal Injection: Keeping the Agent on Track

> *"A model with a 200,000-token context window can still forget what it was doing by turn twenty. Goal injection is your insurance."*

> [!NOTE]
> **Chapter Goal:** By the end of this chapter, you will understand how goal drift happens, how Lemura's `GoalInjector` prevents it, how to configure injection frequency and position, and how sub-goal tracking works.

---

### 15.1 Why Goals Drift
#### 15.1.1 The Recency Bias Problem
#### 15.1.2 Tool Results Burying the Goal
#### 15.1.3 Compounding Drift Over Many Turns

### 15.2 The GoalInjector
#### 15.2.1 What It Does
#### 15.2.2 The Injection Block: What Gets Injected
#### 15.2.3 `getFormattedBlock()`: The Injected Content

### 15.3 Injection Position
#### 15.3.1 `pre_system`: Before the System Prompt
#### 15.3.2 `post_system`: After the System Prompt
#### 15.3.3 `pre_turn`: Before the Latest User Message
#### 15.3.4 Choosing the Right Position

### 15.4 Injection Frequency
#### 15.4.1 `goalInjectionN`: Every N Turns
#### 15.4.2 `shouldInjectThisTurn()`: The Logic
#### 15.4.3 Always Inject on First Turn

### 15.5 Sub-Goal Tracking
#### 15.5.1 What Is a Sub-Goal?
#### 15.5.2 Setting and Completing Sub-Goals
#### 15.5.3 How Sub-Goals Appear in the Injected Block

### 15.6 Advanced Goal Patterns
#### 15.6.1 Dynamic Goal Updates
#### 15.6.2 Goal Confirmation with the Agent
#### 15.6.3 Goal Versioning for Long Sessions

---

## Key Takeaways
