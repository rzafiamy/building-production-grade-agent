---
title: "Chapter 34 — Monitoring in Production"
part: "Part VI — Production Engineering"
chapter: 34
page: 46
status: draft
---

*PART VI — PRODUCTION ENGINEERING*

## Chapter 34 — Monitoring in Production

> *"Your agent is running. Your users are using it. Do you know if it's working?"*

> [!NOTE]
> **Chapter Goal:** By the end of this chapter, you will be able to build a production monitoring system for agents: dashboards, alerts, SLOs, and runbooks that tell you when something is wrong and how to fix it.

---

### 34.1 What Production Monitoring Must Cover
#### 34.1.1 Is the Agent Running?
#### 34.1.2 Is the Agent Completing Tasks?
#### 34.1.3 Is the Agent Completing Tasks Correctly?
#### 34.1.4 Is the Agent Within Budget?

### 34.2 The Agent Monitoring Stack
#### 34.2.1 Metrics Collection
#### 34.2.2 Log Aggregation
#### 34.2.3 Trace Storage
#### 34.2.4 Recommended Tooling

### 34.3 Key Dashboards
#### 34.3.1 The Session Health Dashboard
#### 34.3.2 The Token Economy Dashboard
#### 34.3.3 The Error Rate Dashboard
#### 34.3.4 The Tool Performance Dashboard

### 34.4 Alerting Strategy
#### 34.4.1 What Warrants an Alert (vs. a Log Entry)
#### 34.4.2 Alert Severity Levels
#### 34.4.3 Alert Routing and On-Call
#### 34.4.4 Avoiding Alert Fatigue

### 34.5 Service Level Objectives for Agents
#### 34.5.1 Defining SLOs for Non-Deterministic Systems
#### 34.5.2 Task Completion Rate SLO
#### 34.5.3 Latency P50/P95/P99 SLO
#### 34.5.4 Cost per Task SLO

### 34.6 Production Runbooks
#### 34.6.1 Agent Loop Detected
#### 34.6.2 High Token Usage Alert
#### 34.6.3 Tool Failure Spike
#### 34.6.4 Context Compression Failure

---

## Key Takeaways
