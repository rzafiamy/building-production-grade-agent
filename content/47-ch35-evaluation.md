---
title: "Chapter 35 — Continuous Improvement and Evaluation"
part: "Part VI — Production Engineering"
chapter: 35
page: 47
status: draft
---

*PART VI — PRODUCTION ENGINEERING*

## Chapter 35 — Continuous Improvement and Evaluation

> *"Shipping an agent is the beginning, not the end. The work of making it better never stops."*

> [!NOTE]
> **Chapter Goal:** By the end of this chapter, you will understand how to build an evaluation pipeline, how to use production data to improve your agent, how to measure quality over time, and how to establish a continuous improvement loop.

---

### 35.1 The Agent Improvement Lifecycle

```text
Deploy → Monitor → Collect Failures → Evaluate → Fix → Deploy
          ↑                                              │
          └──────────────────────────────────────────────┘
```

### 35.2 Collecting Improvement Signal
#### 35.2.1 Explicit Feedback: User Ratings and Corrections
#### 35.2.2 Implicit Feedback: Retry Behavior, Task Abandonment
#### 35.2.3 Automated Failure Detection
#### 35.2.4 Human Review Sampling

### 35.3 Evaluation Datasets
#### 35.3.1 Building a Golden Dataset
#### 35.3.2 Real-World vs. Synthetic Evaluation
#### 35.3.3 Maintaining Dataset Quality Over Time

### 35.4 Evaluation Metrics by Task Type
#### 35.4.1 Factual Accuracy
#### 35.4.2 Goal Completion
#### 35.4.3 Tool Use Correctness
#### 35.4.4 Output Format Adherence
#### 35.4.5 Safety and Guardrail Compliance

### 35.5 LLM-as-Judge Evaluation
#### 35.5.1 Designing Effective Judge Prompts
#### 35.5.2 Calibrating the Judge
#### 35.5.3 Inter-Rater Reliability

### 35.6 A/B Testing Agent Changes
#### 35.6.1 What to A/B Test
#### 35.6.2 Statistical Significance for Non-Deterministic Systems
#### 35.6.3 Rollout Based on Evaluation Results

### 35.7 Versioning Agent Behavior
#### 35.7.1 Tracking What Changed Between Versions
#### 35.7.2 Regression Testing Against Prior Behavior
#### 35.7.3 Rollback Criteria

---

## Key Takeaways
