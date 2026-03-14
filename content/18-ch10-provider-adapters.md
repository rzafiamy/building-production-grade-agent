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

In 2026, every major LLM provider is actively competing for long-term commitment from enterprise customers. They offer discounts for volume commitments, early access to new models, and integrations that are convenient to use but difficult to extract from. The technical coupling they create is subtle: a provider-specific message format here, a non-standard tool call schema there, a streaming format that requires provider-specific parsing.

The risk is not that the provider you choose will go away. It is that the provider landscape will change in ways you cannot predict, and your system's ability to respond to those changes will be constrained by how deeply coupled your code is to any single provider's surface area.

Concrete scenarios that happen regularly: a provider raises prices and you need to switch for cost reasons; a new model from a different provider significantly outperforms your current model on your specific task; your current provider has an outage and you need to fail over; your customer requires on-premise deployment using an open-weight model; a compliance requirement prohibits sending data to a specific provider's infrastructure. Each scenario is a provider change. If that change requires a codebase refactor, it will be delayed, incomplete, or never done.

The adapter pattern does not eliminate these scenarios. It makes them a configuration change instead of an engineering project.

### 10.2 The Adapter Pattern for LLM Providers

#### 10.2.1 What the Adapter Must Abstract

The adapter layer must abstract everything that varies between providers: the request format (message array structure, tool definition format, streaming format), the authentication mechanism (API keys, OAuth, service accounts), the error format (provider-specific error codes and structures), and the rate limiting behavior (different providers have different limit structures and retry semantics).

It must not abstract things that are genuinely different across providers and that the rest of the system needs to know about: a model's context window size, its supported modalities (does it handle images?), its pricing tier, and its specific failure modes. These are model characteristics, not implementation details — they belong in model metadata, not hidden behind the adapter.

The adapter is a normalization layer: it takes provider-specific requests and responses and translates them to and from a common normalized format that the rest of the framework uses.

#### 10.2.2 What Cannot Be Abstracted (and That's OK)

Some differences between providers are semantic, not just syntactic. Anthropic's models and OpenAI's models have different strengths on different tasks. Some providers support parallel tool calls; others do not. Some support vision; others do not. Abstracting these differences away would hide information the system needs.

The right approach is to expose model capabilities as metadata — the `getModelInfo()` method on `IProviderAdapter` — and let the system make decisions based on that metadata. "Does this model support vision?" is not a question the adapter answers by normalizing; it is a question the adapter answers by declaring.

Provider-specific features that have no equivalent in the normalized interface — Anthropic's extended thinking, OpenAI's Assistants API, provider-specific file upload APIs — are outside the adapter contract. Use them directly in provider-specific code paths, isolated from the core agent logic. The adapter is not a lowest-common-denominator interface; it is a normalized interface for the common case.

### 10.3 The `IProviderAdapter` Interface in Lemura

#### 10.3.1 The `complete()` Method Contract

`complete(request: CompletionRequest): Promise<CompletionResponse>` is the core of the adapter contract. It takes a normalized completion request — a message array, tool definitions, model name, generation parameters — and returns a normalized response: the model's text response, any tool calls, token usage, and model metadata.

The normalization means that `SessionManager` never calls a provider API directly. It always calls `adapter.complete()`. Swapping the adapter is all that is needed to change the provider.

#### 10.3.2 Message Format Normalization

Different providers use slightly different message formats. Anthropic wraps content in a `content` array of typed blocks. OpenAI uses a simpler string or array format. Some providers use different role names. The adapter's `complete()` method translates from Lemura's normalized `Turn[]` format to the provider's specific format on the way in, and from the provider's response format to Lemura's `CompletionResponse` on the way out.

The normalization must be bidirectional and lossless for the common case. Edge cases — provider-specific content types, non-standard response fields — are acceptable to discard in the normalized representation as long as they are logged for debugging.

#### 10.3.3 Tool Call Format Normalization

Tool call format is the area of greatest divergence between providers. OpenAI uses a `tool_calls` array in the assistant message with a `function` object containing `name` and `arguments` (a JSON string). Anthropic uses a `tool_use` content block with `name` and `input` (a JSON object). Some providers use entirely different schemas.

The adapter normalizes these to Lemura's `ToolCall` format: a list of `{ id, name, arguments }` objects. The normalization handles JSON parsing where the provider sends arguments as strings, ID generation where the provider does not provide call IDs, and format variants between provider API versions.

#### 10.3.4 Error Normalization

Provider errors are normalized to `LemuraAdapterError` with a structured format: an error code, a human-readable message, a `retryable` flag, and a `rateLimited` flag. This normalization lets `SessionManager` make retry decisions based on error semantics rather than provider-specific error codes.

A 429 rate limit from any provider becomes `{ code: 'RATE_LIMIT', retryable: true, rateLimited: true }`. A 401 authentication error becomes `{ code: 'AUTH', retryable: false }`. An upstream 500 becomes `{ code: 'PROVIDER_ERROR', retryable: true }`. The retry and circuit-breaker logic in `SessionManager` operates on these normalized codes, not on raw HTTP status codes.

### 10.4 `OpenAICompatibleAdapter`: The Default Adapter

#### 10.4.1 Configuration Options

`OpenAICompatibleAdapter` is Lemura's built-in implementation of `IProviderAdapter` for OpenAI and any OpenAI-compatible API. It is configured with a base URL, an API key, and a default model name:

```typescript
// Configuring OpenAICompatibleAdapter for OpenAI
import { OpenAICompatibleAdapter } from "lemura";

const adapter = new OpenAICompatibleAdapter({
  baseUrl: "https://api.openai.com/v1",
  apiKey: process.env.OPENAI_API_KEY!,
  defaultModel: "gpt-4o-mini",
});
```

The adapter reads from `LEMURA_API_KEY`, `LEMURA_BASE_URL`, and `LEMURA_MODEL` environment variables as fallbacks when the constructor options are not provided, making it easy to configure via environment without changing code.

#### 10.4.2 Connecting to OpenAI, Groq, Together, Ollama

The same adapter class works with any OpenAI-compatible endpoint. Only the `baseUrl` and `apiKey` change:

```typescript
// Connecting to different providers via OpenAICompatibleAdapter
import { OpenAICompatibleAdapter } from "lemura";

// Groq — fast inference for Llama models
const groqAdapter = new OpenAICompatibleAdapter({
  baseUrl: "https://api.groq.com/openai/v1",
  apiKey: process.env.GROQ_API_KEY!,
  defaultModel: "llama-3.3-70b-versatile",
});

// Together AI — open-weight model hosting
const togetherAdapter = new OpenAICompatibleAdapter({
  baseUrl: "https://api.together.xyz/v1",
  apiKey: process.env.TOGETHER_API_KEY!,
  defaultModel: "meta-llama/Llama-3.3-70B-Instruct-Turbo",
});

// Local Ollama — open-weight models on local hardware
const ollamaAdapter = new OpenAICompatibleAdapter({
  baseUrl: "http://localhost:11434/v1",
  apiKey: "ollama", // Ollama accepts any non-empty key
  defaultModel: "qwen2.5:72b",
});
```

<!-- Accurate as of 2026-03 — verify before next edition -->

Swapping the adapter is all that is required to switch providers. The session configuration, tool definitions, compression strategies, and goal configuration are all unchanged.

#### 10.4.3 Custom Base URLs and Auth

Enterprise deployments often route LLM traffic through a proxy that handles authentication, rate limiting, logging, and compliance. The `baseUrl` parameter accepts any URL, making it straightforward to point `OpenAICompatibleAdapter` at an internal proxy:

```typescript
// Using an enterprise proxy for centralized auth and logging
const enterpriseAdapter = new OpenAICompatibleAdapter({
  baseUrl: "https://llm-proxy.internal.example.com/v1",
  apiKey: process.env.ENTERPRISE_PROXY_TOKEN!,
  defaultModel: "gpt-4o",
});
```

The proxy handles authentication to the upstream provider, injects required headers, and logs requests for compliance. The agent code is unchanged.

### 10.5 Connecting to Anthropic

#### 10.5.1 The Claude API Differences

Anthropic's Claude API is structurally similar to the OpenAI API but not fully compatible. Key differences: the system prompt is a top-level parameter, not a role in the message array; the `content` field uses typed blocks rather than plain strings; tool call responses use a different schema; and extended thinking produces content in a separate block type.

Lemura does not ship a native Anthropic adapter. This is not an oversight — it is a deliberate choice to keep the core framework focused on the OpenAI-compatible standard. Anthropic support is achieved through one of two approaches.

#### 10.5.2 Using an OpenAI-Compatible Proxy

The simplest way to use Anthropic's models in Lemura is through an OpenAI-compatible proxy layer. Several open-source and commercial services translate OpenAI-format requests to Anthropic format and back. Point `OpenAICompatibleAdapter` at the proxy endpoint:

```typescript
// Using a proxy to access Anthropic models via OpenAI-compatible format
const claudeAdapter = new OpenAICompatibleAdapter({
  baseUrl: "https://your-anthropic-proxy.example.com/v1",
  apiKey: process.env.ANTHROPIC_API_KEY!,
  defaultModel: "claude-sonnet-4-6",
});
```

<!-- Accurate as of 2026-03 — verify before next edition -->

This works for the common case. If you need Anthropic-specific features (extended thinking, native vision with multi-image support, prompt caching), a native adapter — covered in the next section — gives you full access to the API surface.

### 10.6 Writing a Custom Adapter

#### 10.6.1 Implementing `IProviderAdapter`

Writing a custom adapter requires implementing the `IProviderAdapter` interface. The minimum viable adapter implements `complete()`, `estimateTokens()`, and `getModelInfo()`. The streaming and multimodal methods are optional and can throw `UnsupportedCapabilityError` if not needed.

```typescript
// Minimal custom adapter implementation
import { IProviderAdapter, CompletionRequest, CompletionResponse } from "lemura/types";

class MyProviderAdapter implements IProviderAdapter {
  readonly name = "my-provider";
  readonly version = "1.0.0";

  constructor(private readonly apiKey: string, private readonly model: string) {}

  async complete(request: CompletionRequest): Promise<CompletionResponse> {
    // Translate request.messages from Lemura's normalized format to MyProvider's format
    const providerRequest = this.normalizeRequest(request);

    const response = await fetch("https://api.myprovider.example.com/v1/chat", {
      method: "POST",
      headers: { Authorization: `Bearer ${this.apiKey}`, "Content-Type": "application/json" },
      body: JSON.stringify(providerRequest),
    });

    if (!response.ok) {
      throw new Error(`Provider error: ${response.status} ${await response.text()}`);
    }

    const raw = await response.json();
    // Translate raw response back to Lemura's CompletionResponse format
    return this.normalizeResponse(raw);
  }

  async *stream(request: CompletionRequest) {
    throw new Error("Streaming not supported by this adapter");
  }

  estimateTokens(text: string): number {
    // Simple approximation: 1 token ≈ 4 characters
    return Math.ceil(text.length / 4);
  }

  getModelInfo() {
    return {
      name: this.model,
      contextWindow: 32_000,
      supportsTools: true,
      supportsVision: false,
      supportsStreaming: false,
    };
  }

  // Required by interface but not used — throw to signal unsupported capability
  async transcribe() { throw new Error("Not supported"); }
  async *synthesize() { throw new Error("Not supported"); }
  async describeImage() { throw new Error("Not supported"); }
  async generateImage() { throw new Error("Not supported"); }
  async healthCheck(): Promise<boolean> {
    try { await this.complete({ model: this.model, messages: [], tools: [] }); return true; }
    catch { return false; }
  }

  private normalizeRequest(request: CompletionRequest): unknown { /* ... */ return {}; }
  private normalizeResponse(raw: unknown): CompletionResponse { /* ... */ return {} as CompletionResponse; }
}
```

The normalization methods — `normalizeRequest` and `normalizeResponse` — are where the bulk of the implementation lives. They handle format differences between Lemura's normalized types and the provider's specific API contract.

#### 10.6.2 Testing Your Adapter

A custom adapter requires its own test suite. The minimum test set covers: a successful completion with a text response, a successful completion with a tool call response, an error response and its normalization, token estimation accuracy on representative inputs, and `healthCheck` behavior with both a healthy and an unhealthy endpoint.

Use recorded responses (fixture files) rather than live API calls in unit tests. Live API calls in tests are slow, expensive, and non-deterministic. Reserve live calls for integration tests that verify the adapter works against the real API. Run these integration tests before any deployment that changes adapter configuration.

### 10.7 Multi-Provider Sessions

#### 10.7.1 Routing by Task Type

A session typically uses one provider for all model calls, but there is no architectural reason for this. Some tasks benefit from different models: a reasoning-heavy planning step might use a large frontier model, while summarization steps during compression use a smaller, cheaper model.

Lemura's compression strategies accept an adapter as a constructor parameter. This means the summarization model can be a different adapter — and therefore a different provider or model — from the session's main adapter. This is the most common multi-provider pattern and the easiest to implement:

```typescript
// Using a cheap model for compression, a capable model for reasoning
import {
  SessionManager, OpenAICompatibleAdapter,
  SandwichCompressionStrategy, SummaryInjectionStrategy
} from "lemura";

const mainAdapter = new OpenAICompatibleAdapter({
  apiKey: process.env.OPENAI_API_KEY!,
  defaultModel: "gpt-4o",         // used for reasoning
});

const cheapAdapter = new OpenAICompatibleAdapter({
  apiKey: process.env.OPENAI_API_KEY!,
  defaultModel: "gpt-4o-mini",    // used for summarization only
});

const session = new SessionManager({
  adapter: mainAdapter,
  model: "gpt-4o",
  maxTokens: 100_000,
  compressionStrategies: [
    new SummaryInjectionStrategy({ priority: 1 }),
    new SandwichCompressionStrategy(cheapAdapter, { // ← cheap model for compression
      priority: 20,
      preserveFirst: 4,
      preserveLast: 10,
      triggerThreshold: 0.80,
    }),
  ],
});
```

#### 10.7.2 Fallback Providers

A fallback provider is an adapter that is used when the primary adapter fails. This provides resilience against provider outages, rate limits, and unexpected errors. The implementation pattern is a wrapper adapter that tries the primary, catches retryable errors, and delegates to a fallback:

```typescript
// A simple fallback adapter that wraps primary and secondary providers
import { IProviderAdapter, CompletionRequest, CompletionResponse } from "lemura/types";

class FallbackAdapter implements IProviderAdapter {
  readonly name = "fallback-adapter";
  readonly version = "1.0.0";

  constructor(
    private readonly primary: IProviderAdapter,
    private readonly fallback: IProviderAdapter
  ) {}

  async complete(request: CompletionRequest): Promise<CompletionResponse> {
    try {
      return await this.primary.complete(request);
    } catch (err) {
      // Log the primary failure and try the fallback
      console.warn("Primary provider failed, trying fallback:", err);
      return await this.fallback.complete(request);
    }
  }

  async *stream(request: CompletionRequest) { yield* this.primary.stream(request); }
  estimateTokens(text: string) { return this.primary.estimateTokens(text); }
  getModelInfo() { return this.primary.getModelInfo(); }
  async transcribe(r: any) { return this.primary.transcribe(r); }
  async *synthesize(r: any) { yield* this.primary.synthesize(r); }
  async describeImage(r: any) { return this.primary.describeImage(r); }
  async generateImage(r: any) { return this.primary.generateImage(r); }
  async healthCheck() { return this.primary.healthCheck(); }
}
```

> [!TIP]
> In production, always pair a fallback adapter with alerting on primary failures. Silently falling back to a secondary provider is resilient, but it should not be invisible. If the primary provider is failing consistently, you want to know — both to investigate the cause and to monitor whether the fallback is performing acceptably for the task.

---

## Key Takeaways

- The adapter pattern separates agent logic from provider-specific formats; swapping a provider becomes a configuration change rather than a refactor.
- `IProviderAdapter` is Lemura's provider contract; `complete()`, `estimateTokens()`, and `getModelInfo()` are the minimum a custom adapter must implement.
- `OpenAICompatibleAdapter` connects to any OpenAI-compatible provider — OpenAI, Groq, Together, Ollama, local models — by changing `baseUrl` and `apiKey` only.
- Anthropic's Claude API is accessible via an OpenAI-compatible proxy; use this for the common case and write a native adapter only if you need Anthropic-specific features.
- Compression strategies accept their own adapter parameter, enabling cheap models for summarization and expensive models for reasoning within the same session.
- Fallback adapters provide resilience against provider outages; always pair them with alerting so silent fallbacks do not become invisible degradation.
