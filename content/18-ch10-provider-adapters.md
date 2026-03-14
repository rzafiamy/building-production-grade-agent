---
title: "Chapter 10 — Provider Adapters: Staying Model-Agnostic"
part: "Part II — Architecture Fundamentals"
chapter: 10
page: 18
status: draft
---

*PART II — ARCHITECTURE FUNDAMENTALS*

## Chapter 10 — Provider Adapters: Staying Model-Agnostic

> *"Bet on the pattern, not the provider. The models will change. The interface should not."*

> [!NOTE]
> **Chapter Goal:** By the end of this chapter, you will understand why the adapter pattern is essential for production agents, how the `IProviderAdapter` interface works in Lemura, how to configure and swap providers, and how to write a custom adapter for a non-standard provider.

---

### 10.1 The Lock-In Risk Is Real

### 10.2 The Adapter Pattern for LLM Providers
#### 10.2.1 What the Adapter Must Abstract
#### 10.2.2 What Cannot Be Abstracted (and That's OK)

### 10.3 The `IProviderAdapter` Interface in Lemura
#### 10.3.1 The `complete()` Method Contract
#### 10.3.2 Message Format Normalization
#### 10.3.3 Tool Call Format Normalization
#### 10.3.4 Error Normalization

### 10.4 `OpenAICompatibleAdapter`: The Default Adapter
#### 10.4.1 Configuration Options
#### 10.4.2 Connecting to OpenAI, Groq, Together, Ollama
#### 10.4.3 Custom Base URLs and Auth

### 10.5 Connecting to Anthropic
#### 10.5.1 The Claude API Differences
#### 10.5.2 Using an OpenAI-Compatible Proxy

### 10.6 Writing a Custom Adapter
#### 10.6.1 Implementing `IProviderAdapter`
#### 10.6.2 Testing Your Adapter

### 10.7 Multi-Provider Sessions
#### 10.7.1 Routing by Task Type
#### 10.7.2 Fallback Providers

---

## Key Takeaways
