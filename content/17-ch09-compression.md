---
title: "Chapter 9 — Compression: The Hidden Challenge"
part: "Part II — Architecture Fundamentals"
chapter: 9
page: 17
status: draft
---

*PART II — ARCHITECTURE FUNDAMENTALS*

## Chapter 9 — Compression: The Hidden Challenge

> *"You can't fight the context window. You can only manage it — or be managed by it."*

> [!NOTE]
> **Chapter Goal:** By the end of this chapter, you will understand why context compression is necessary, the fundamental trade-offs between different compression approaches, when each strategy is appropriate, and how to select and configure compression strategies in Lemura.

---

### 9.1 Why Compression Is Inevitable

### 9.2 The Compression Spectrum
#### 9.2.1 No Compression: Works Until It Doesn't
#### 9.2.2 Truncation: Brutal and Simple
#### 9.2.3 Rolling Summaries: Lossy but Cheap
#### 9.2.4 Selective Preservation: The Sandwich Pattern
#### 9.2.5 External Memory: Expensive but Lossless

### 9.3 What to Compress and What to Preserve
#### 9.3.1 Sacred Context: Never Compress
#### 9.3.2 Compressible Context: Middle History
#### 9.3.3 The Sandwich Pattern Visualized

```text
┌─────────────────────────────┐
│    SYSTEM PROMPT (sacred)   │
├─────────────────────────────┤
│    GOAL + PLAN (sacred)     │
├─────────────────────────────┤
│                             │
│   [ COMPRESSED SUMMARY ]   │  ← rolling summary of old turns
│                             │
├─────────────────────────────┤
│   RECENT TURNS (preserved)  │  ← last N turns verbatim
├─────────────────────────────┤
│   CURRENT INPUT (sacred)    │
└─────────────────────────────┘
```

### 9.4 Compression Quality: What Gets Lost
#### 9.4.1 Information Loss Is Unavoidable
#### 9.4.2 Measuring Compression Quality
#### 9.4.3 When Bad Compression Breaks the Agent

### 9.5 The Cost of Compression
#### 9.5.1 Every Summary Is an LLM Call
#### 9.5.2 Balancing Compression Cost vs. Context Cost

### 9.6 Compression Strategies in Lemura
#### 9.6.1 `SandwichCompressionStrategy`
#### 9.6.2 `HistoryCompressionStrategy`
#### 9.6.3 `SummaryInjectionStrategy`
#### 9.6.4 Configuring Priority and Trigger Thresholds

---

## Key Takeaways
