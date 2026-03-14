---
title: "Chapter 36 — Reliability Engineering for Agents"
part: "Part VI — Production Engineering"
chapter: 36
page: 48
status: draft
---

*PART VI — PRODUCTION ENGINEERING*

## Chapter 36 — Reliability Engineering for Agents

> *"Reliability is not a feature you add at the end. It's an architecture decision you make at the beginning."*

> [!NOTE]
> **Chapter Goal:** By the end of this chapter, you will understand how to apply Site Reliability Engineering (SRE) principles to agent systems, define meaningful SLOs, establish incident response procedures, and build a reliability culture for your team.

---

### 36.1 Applying SRE Principles to Agents
#### 36.1.1 Where Standard SRE Applies
#### 36.1.2 Where Agents Break the SRE Model
#### 36.1.3 Non-Determinism and Error Budgets

### 36.2 Defining SLOs for Agent Systems
#### 36.2.1 The Challenge: Subjective Success Criteria
#### 36.2.2 SLO: Task Completion Rate
#### 36.2.3 SLO: End-to-End Latency
#### 36.2.4 SLO: Cost per Successful Task
#### 36.2.5 Error Budgets and Their Meaning

### 36.3 Incident Response for Agent Failures
#### 36.3.1 Detection: Knowing Something Is Wrong
#### 36.3.2 Triage: How Bad Is It?
#### 36.3.3 Mitigation: Stop the Bleeding
#### 36.3.4 Investigation: Root Cause Analysis
#### 36.3.5 Prevention: Post-Mortem Actions

### 36.4 Graceful Degradation
#### 36.4.1 Identifying Degradation Points
#### 36.4.2 Fallback Behaviors at Each Layer
#### 36.4.3 User Communication During Degradation

### 36.5 Dependency Reliability
#### 36.5.1 LLM Provider Outages and Failover
#### 36.5.2 Tool Dependency Failures
#### 36.5.3 Third-Party API Stability

### 36.6 Building a Reliability Culture
#### 36.6.1 Blameless Post-Mortems
#### 36.6.2 Reliability Reviews Before Launch
#### 36.6.3 On-Call Rotation and Runbooks

---

## Key Takeaways
