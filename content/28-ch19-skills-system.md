---
title: "Chapter 19 — Skills: Reusable Agent Capabilities"
part: "Part III — Lemura Framework Deep Dive"
chapter: 19
page: 28
status: draft
---

*PART III — LEMURA FRAMEWORK DEEP DIVE*

## Chapter 19 — Skills: Reusable Agent Capabilities

> *"A skill is a named piece of expertise. Instead of writing the same system prompt instructions over and over, you package them once and inject them on demand."*

> [!NOTE]
> **Chapter Goal:** By the end of this chapter, you will understand Lemura's skills system, how to define and register skills, how the `SkillInjector` manages token budgets, and how to design a library of reusable skills for your agent ecosystem.

---

### 19.1 What Is a Skill?
#### 19.1.1 Skills vs. System Prompt Text
#### 19.1.2 Skills vs. Tools
#### 19.1.3 When Skills Are the Right Abstraction

### 19.2 Defining a Skill
#### 19.2.1 The Skill Interface
#### 19.2.2 Skill Content: Instructions and Context
#### 19.2.3 Skill Metadata: Name, Description, Token Estimate

### 19.3 The SkillInjector
#### 19.3.1 How Skills Are Injected into the Session
#### 19.3.2 Injection Position and Order
#### 19.3.3 `skillTokenBudget`: Preventing Skill Bloat

### 19.4 Token Budget Enforcement
#### 19.4.1 What Happens When Skills Exceed the Budget
#### 19.4.2 Priority-Based Skill Selection
#### 19.4.3 Dynamic Skill Activation

### 19.5 Skill Design Patterns
#### 19.5.1 Domain Skills: Expert Knowledge Injection
#### 19.5.2 Persona Skills: Role-Based Behavior
#### 19.5.3 Constraint Skills: Rules and Guardrails
#### 19.5.4 Format Skills: Output Shape Control

### 19.6 Building a Skill Library
#### 19.6.1 Organizing Skills by Domain
#### 19.6.2 Versioning Skills
#### 19.6.3 Testing Skill Effectiveness

### 19.7 Dynamic Skill Selection
#### 19.7.1 Selecting Skills Based on Task Type
#### 19.7.2 Skill Retrieval with Embeddings

---

## Key Takeaways
