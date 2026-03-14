---
title: "Chapter 32 — Deployment Strategies"
part: "Part VI — Production Engineering"
chapter: 32
page: 44
status: draft
---

*PART VI — PRODUCTION ENGINEERING*

## Chapter 32 — Deployment Strategies

> *"How you deploy an agent determines how it fails. Plan for failure before you plan for success."*

> [!NOTE]
> **Chapter Goal:** By the end of this chapter, you will understand the deployment topologies for agent systems, how to choose the right execution environment, how to handle long-running agents in serverless and container environments, and how to implement safe rollouts.

---

### 32.1 Deployment Topologies
#### 32.1.1 Synchronous: Request → Agent → Response
#### 32.1.2 Asynchronous: Submit → Poll → Retrieve
#### 32.1.3 Event-Driven: Trigger → Agent → Publish
#### 32.1.4 Scheduled: Cron → Agent → Store

### 32.2 Execution Environments
#### 32.2.1 Serverless (Lambda, Cloud Run): Benefits and Limits
#### 32.2.2 Containers (Docker, K8s): The Long-Running Sweet Spot
#### 32.2.3 Edge: When Latency Is Everything
#### 32.2.4 Bare Metal: For Maximum Control

### 32.3 Long-Running Agent Challenges in Serverless
#### 32.3.1 Timeout Limits
#### 32.3.2 Cold Starts and State Loss
#### 32.3.3 The Durable Execution Pattern

### 32.4 Queue-Based Agent Systems
#### 32.4.1 Task Queues for Agent Jobs
#### 32.4.2 Priority Queues
#### 32.4.3 Dead Letter Queues for Failed Jobs

### 32.5 Safe Rollout Strategies
#### 32.5.1 Canary Deployments for Agents
#### 32.5.2 Shadow Mode Testing
#### 32.5.3 Feature Flags for Agent Behavior
#### 32.5.4 Rollback Procedures

### 32.6 Configuration Management
#### 32.6.1 Environment-Specific Configs
#### 32.6.2 Secrets Management
#### 32.6.3 Model Version Pinning

### 32.7 Infrastructure as Code for Agent Systems

---

## Key Takeaways
