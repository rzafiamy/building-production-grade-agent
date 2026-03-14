---
title: "Chapter 29 — Security and Safety"
part: "Part V — Advanced Patterns"
chapter: 29
page: 40
status: draft
---

*PART V — ADVANCED PATTERNS*

## Chapter 29 — Security and Safety

> *"An autonomous agent with network access, file access, and API keys is a powerful tool — and a significant attack surface."*

> [!NOTE]
> **Chapter Goal:** By the end of this chapter, you will understand the security threats unique to autonomous agents, how to implement prompt injection defenses, how to scope tool permissions correctly, and how to design safety guardrails that don't destroy agent usefulness.

---

### 29.1 The Threat Model for Autonomous Agents
#### 29.1.1 What Makes Agents Uniquely Risky
#### 29.1.2 Who Can Attack an Agent (and How)
#### 29.1.3 The Indirect Prompt Injection Attack

### 29.2 Prompt Injection
#### 29.2.1 Direct Injection: Malicious User Input
#### 29.2.2 Indirect Injection: Malicious Tool Results
#### 29.2.3 Injection via Web Content and Files
#### 29.2.4 Detection and Mitigation Strategies

### 29.3 Tool Permission Design
#### 29.3.1 Principle of Least Privilege for Tools
#### 29.3.2 Read-Only First, Write Second
#### 29.3.3 Confirmation Gates for Destructive Operations
#### 29.3.4 Tool Scoping by Context

### 29.4 Secrets and Credentials
#### 29.4.1 Never Inject Credentials into the Agent Context
#### 29.4.2 Secure Credential Storage and Access
#### 29.4.3 The Credential Exfiltration Risk

### 29.5 Output Validation
#### 29.5.1 Validating Agent Actions Before Execution
#### 29.5.2 Structural Validation of Tool Arguments
#### 29.5.3 Semantic Validation: Does This Make Sense?

### 29.6 Safety Guardrails
#### 29.6.1 Hard Limits: Things the Agent Must Never Do
#### 29.6.2 Implementing Guardrails as Pre-Execution Checks
#### 29.6.3 Behavioral Guardrails via System Prompt
#### 29.6.4 Monitoring for Safety Violations

### 29.7 Regulatory and Compliance Considerations
#### 29.7.1 Data Privacy in Agent Contexts
#### 29.7.2 Audit Logging for Compliance
#### 29.7.3 AI Governance in 2026

---

## Key Takeaways
