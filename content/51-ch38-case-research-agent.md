---
title: "Chapter 38 — Case Study: The Research Agent"
part: "Part VII — Real-World Applications"
chapter: 38
page: 51
status: draft
---

*PART VII — REAL-WORLD APPLICATIONS*

## Chapter 38 — Case Study: The Research Agent

> *"A research agent is not a search engine. It reads, evaluates, synthesizes, and concludes — and it knows the difference between evidence and speculation."*

> [!NOTE]
> **Chapter Goal:** By the end of this chapter, you will understand how to build a research agent that explores, synthesizes, and reports on complex topics — and how to handle the unique challenges of uncertainty, source quality, and information overload.

---

### 38.1 The Problem: Deep Research at Scale

A research agent takes a question and produces a structured answer — not a list of links, not a summary of the first page it finds, but a synthesized, cited analysis of what the available evidence says. The tasks it handles are things like: "What are the current best practices for rate limiting in distributed APIs?", "Compare the three main approaches to agent memory and their trade-offs", "What does the available research say about LLM reliability under adversarial prompts?"

These are the tasks that currently take a senior engineer two to four hours: opening a dozen tabs, reading selectively, triangulating across sources, and distilling the findings into something actionable. The research agent compresses that to minutes — not by being faster at reading, but by running the exploration loop autonomously.

#### 38.1.1 What a Research Agent Should Produce

The output of a research agent is a structured report, not a conversational response. A useful research report contains:

1. **An executive summary** — two to three sentences stating the main finding.
2. **Key findings** — three to seven bullet points, each a concrete claim with a source.
3. **Detailed analysis** — prose organized by theme, with inline citations.
4. **Gaps and caveats** — what the agent could not find, where sources conflicted, and what confidence level the agent assigns to major claims.
5. **Source list** — the pages or documents consulted, with brief quality notes.

The structure matters because a research report is only useful if a human can quickly assess its reliability. A report without caveats is a hallucination risk. A report without sources is unverifiable. Build the output format into the system prompt and enforce it via a structured output tool.

#### 38.1.2 The Breadth vs. Depth Trade-off

Every research session faces a fundamental tension: breadth (how many sources you explore) versus depth (how thoroughly you analyze each one). Searching broadly risks spending the entire context budget on surface-level results. Diving deep into the first promising source risks missing contradicting evidence elsewhere.

The solution is a phased plan that deliberately separates exploration from deep reading. Phase one casts wide — search across multiple angles of the question, collect a short list of promising sources. Phase two dives deep — read the top five to eight sources in full. Phase three synthesizes. Without this structure, agents tend to spiral into the first source they find and never surface.

#### 38.1.3 Source Quality and Reliability

Not all sources are equal. A Stack Overflow answer with 200 upvotes, an arXiv preprint, a vendor blog post, and an official specification carry vastly different evidential weight. The agent must evaluate source quality as part of its research process, not treat all results as equivalent facts.

Encode source quality heuristics in the system prompt: prefer primary sources over secondary, prefer peer-reviewed publications over blog posts for factual claims, prefer official documentation over community tutorials. When the agent contradicts a high-quality source with a low-quality one, it should flag the discrepancy rather than silently choosing one.

### 38.2 The Challenges

#### 38.2.1 Context Explosion from Web Content

Web pages are verbose. The average web page that is "useful" for research contains one to three paragraphs of relevant content and thousands of words of navigation, advertisements, boilerplate, and related links. Fetching a page and inserting the raw HTML into context is a catastrophic waste of tokens.

Every `fetch_page` result must be processed before entering context. Strip HTML to text, extract only the main content, and apply a hard token cap. Use `ToolResponseProcessor` configured for aggressive summarization of web content.

> [!WARNING]
> Never insert raw HTML into agent context. A typical web page with markup can easily exceed 15,000 tokens. A session that fetches five pages of raw HTML will fill its context window before it reads a single one completely.

#### 38.2.2 Knowing When to Stop Searching

An agent that searches indefinitely is not a research agent — it is a search loop. You need a concrete stopping condition. The most effective one is a confidence threshold: the agent estimates its current confidence in the main claims and stops searching when it crosses a defined threshold, or when it has consulted a minimum number of sources.

Build a `stop_research` tool that the agent calls when it has reached its conclusion. The tool accepts the agent's confidence level and a short rationale. When called, it signals the session to proceed to synthesis. Without an explicit stopping mechanism, the agent will keep searching because it always finds something new to look at.

#### 38.2.3 Uncertainty: The Agent Must Know What It Doesn't Know

The most dangerous output of a research agent is a confident statement about something the agent does not actually know. Language models are prone to this. The agent must be trained — through the system prompt and through the output structure — to distinguish between:

- **Well-supported claims**: multiple high-quality sources agree.
- **Tentatively supported claims**: one or two sources, lower quality, or some disagreement.
- **Speculative claims**: the agent's inference from related evidence, no direct source.
- **Unknown**: the agent searched and did not find adequate information.

Require the agent to tag every major claim in its report with a confidence marker. This is not optional for production research agents — it is the difference between a useful tool and a liability.

#### 38.2.4 Citation and Attribution

Every factual claim in the report must trace back to a source the agent actually read. This is straightforward in principle and surprisingly difficult in practice because the agent tends to synthesize across sources and lose track of which specific source supported which claim.

The pattern that works is to require citations at the time of writing, not as a post-processing step. When the agent writes a claim, the system prompt instructs it to immediately include the source in brackets. Retroactive citation-adding is where hallucinated citations appear.

### 38.3 Tool Design for a Research Agent

#### 38.3.1 `web_search`: Controlled Web Access

`web_search` runs a search query and returns a list of results — titles, URLs, and brief snippets. It does not fetch pages. The separation between search and fetch is intentional: the agent decides which results are worth reading based on the snippets, rather than blindly fetching everything.

```typescript
// web_search tool returning results list without fetching full pages
import type { ToolDefinition } from 'lemura';

export const webSearchTool: ToolDefinition = {
  name: 'web_search',
  description: 'Search the web and return a list of result titles, URLs, and snippets.',
  parameters: {
    type: 'object',
    properties: {
      query: { type: 'string', description: 'The search query' },
      maxResults: {
        type: 'number',
        description: 'Maximum number of results to return (default: 8, max: 20)',
        default: 8,
      },
    },
    required: ['query'],
  },
  async execute({ query, maxResults = 8 }) {
    const results = await searchProvider.search(query as string, {
      limit: Math.min(maxResults as number, 20),
    });
    return {
      query,
      results: results.map((r) => ({
        title: r.title,
        url: r.url,
        snippet: r.snippet,
      })),
    };
  },
};
```

#### 38.3.2 `fetch_page`: Full Content Retrieval

`fetch_page` retrieves a page and returns extracted text content, not raw HTML. Apply a hard token limit on the returned content.

```typescript
// fetch_page tool that strips HTML and enforces a token cap
import type { ToolDefinition } from 'lemura';

const MAX_PAGE_CHARS = 8000; // Roughly 2000 tokens after extraction

export const fetchPageTool: ToolDefinition = {
  name: 'fetch_page',
  description: 'Fetch a web page and return its main text content (HTML stripped).',
  parameters: {
    type: 'object',
    properties: {
      url: { type: 'string', description: 'URL to fetch' },
    },
    required: ['url'],
  },
  async execute({ url }) {
    const raw = await httpFetch(url as string);
    const text = extractMainContent(raw); // strip nav, ads, boilerplate
    const truncated = text.length > MAX_PAGE_CHARS
      ? text.slice(0, MAX_PAGE_CHARS) + '\n... [truncated]'
      : text;
    return { url, content: truncated, charCount: text.length };
  },
};
```

#### 38.3.3 `save_to_memory`: External Memory Integration

As the agent explores sources, it saves key findings to an external memory store. This serves two purposes: it reduces the need to keep full source content in the context window, and it creates a structured record the agent can query during synthesis.

```typescript
// save_to_memory tool for persisting research findings
export const saveToMemoryTool: ToolDefinition = {
  name: 'save_to_memory',
  description: 'Save a key finding or summary to research memory for later retrieval.',
  parameters: {
    type: 'object',
    properties: {
      key: { type: 'string', description: 'Short identifier for this finding' },
      content: { type: 'string', description: 'The finding or summary to save' },
      source: { type: 'string', description: 'URL or title of the source' },
      confidence: {
        type: 'string',
        enum: ['high', 'medium', 'low'],
        description: 'Confidence level in this finding',
      },
    },
    required: ['key', 'content', 'source', 'confidence'],
  },
  async execute({ key, content, source, confidence }) {
    await memoryStore.set(key as string, { content, source, confidence, timestamp: Date.now() });
    return { saved: true, key };
  },
};
```

#### 38.3.4 `query_memory`: Semantic Retrieval

`query_memory` retrieves relevant findings from the memory store by semantic similarity. During synthesis, the agent uses this to pull in what it learned during exploration without re-reading the raw sources.

```typescript
// query_memory tool for semantic retrieval of research findings
export const queryMemoryTool: ToolDefinition = {
  name: 'query_memory',
  description: 'Retrieve relevant findings from research memory by semantic query.',
  parameters: {
    type: 'object',
    properties: {
      query: { type: 'string', description: 'What to look for in memory' },
      topK: { type: 'number', description: 'Number of results to return', default: 5 },
    },
    required: ['query'],
  },
  async execute({ query, topK = 5 }) {
    const results = await memoryStore.semanticSearch(query as string, topK as number);
    return { results };
  },
};
```

#### 38.3.5 `write_report`: Structured Output

`write_report` is the agent's terminal tool. When the agent is ready to conclude, it calls this tool with the structured report content. The tool validates the structure, saves the report, and returns a completion signal.

```typescript
// write_report tool that validates and saves the final research output
export const writeReportTool: ToolDefinition = {
  name: 'write_report',
  description: 'Write the final research report. Call this when you have completed your research.',
  parameters: {
    type: 'object',
    properties: {
      summary: { type: 'string', description: 'Executive summary (2-3 sentences)' },
      keyFindings: {
        type: 'array',
        items: {
          type: 'object',
          properties: {
            finding: { type: 'string' },
            source: { type: 'string' },
            confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
          },
        },
        description: 'Key findings with sources and confidence levels',
      },
      analysis: { type: 'string', description: 'Detailed analysis prose' },
      gaps: { type: 'string', description: 'What was not found or remains uncertain' },
    },
    required: ['summary', 'keyFindings', 'analysis', 'gaps'],
  },
  async execute(report) {
    const validated = validateReportStructure(report);
    await reportStore.save(validated);
    return { saved: true, wordCount: JSON.stringify(report).length };
  },
};
```

### 38.4 The Research Plan Pattern

#### 38.4.1 Phase 1: Broad Exploration

Phase one runs multiple searches across different angles of the question. For "best practices for rate limiting in distributed APIs", the agent searches: "rate limiting distributed systems", "API rate limiting algorithms token bucket leaky bucket", "rate limiting microservices patterns", and "rate limiting at the edge vs. service level". It collects snippets and titles but reads nothing in full yet.

The goal is to build a map of the information landscape before committing to any single path. This phase should complete in five to eight searches. Configure the plan step to run them in parallel where possible.

#### 38.4.2 Phase 2: Deep Dive on Key Sources

Phase two selects the five to eight most promising URLs from phase one and fetches them fully. The agent reads each, extracts key claims, and saves them to memory using `save_to_memory`. It evaluates source quality and notes any contradictions between sources.

This phase is the most token-intensive. Each fetched page can consume 2,000 tokens after extraction. With eight pages, that is up to 16,000 tokens in tool results — more than most context windows. This is why `ToolResponseProcessor` and `save_to_memory` are essential: the agent should not try to hold all page contents in context simultaneously.

#### 38.4.3 Phase 3: Synthesis and Gap Analysis

Phase three uses `query_memory` to retrieve relevant findings and constructs the synthesis in working memory. The agent identifies:

- Claims that appear in multiple independent sources (high confidence)
- Claims from a single high-quality source (medium confidence)
- Claims from low-quality sources or inference (low confidence or flag as speculative)
- Questions the research raised but did not answer (gaps)

If gap analysis reveals an important missing angle, the agent may do a targeted phase 1.5 search before proceeding to synthesis.

#### 38.4.4 Phase 4: Report Generation

Phase four calls `write_report` with the structured output. The agent should not write prose into the context and then copy it to the report — it should build the report fields directly. This prevents the context from filling with draft text that then needs to be re-processed.

### 38.5 Managing Information Overload

#### 38.5.1 Aggressive Tool Response Compression

Configure `ToolResponseProcessor` with tight limits for web content:

```typescript
// ToolResponseProcessor configuration for research agent
import { ToolResponseProcessor } from 'lemura';

const processor = new ToolResponseProcessor({
  smallMaxTokens: 200,   // web_search snippets
  mediumMaxTokens: 800,  // query_memory results
  largeMaxTokens: 1200,  // fetch_page content (aggressive cap for web)
});
```

#### 38.5.2 Relevance Filtering Before Storing

Not every finding is worth saving to memory. Before calling `save_to_memory`, instruct the agent to evaluate relevance: does this finding directly address the research question? Does it provide new information not already captured? Instruct the agent to discard tangential findings rather than saving everything and diluting the memory with noise.

#### 38.5.3 Progressive Summarization

When context pressure builds during phase 2, use progressive summarization: the `save_to_memory` entries from earlier sources are already compressed; configure the `SandwichCompressionStrategy` to compress the middle of the context (which contains page reads from earlier in the session) while keeping the most recent page read intact. The agent can always retrieve earlier findings via `query_memory` — they do not need to remain in the live context.

### 38.6 Handling Uncertainty Correctly

#### 38.6.1 Teaching the Agent to Say "I Don't Know"

The system prompt must explicitly create space for uncertainty. Without explicit instruction, language models fill gaps with plausible-sounding answers. This is the research agent's most dangerous failure mode.

```text
When you cannot find adequate evidence for a claim:
- State explicitly: "The research did not reveal adequate evidence for X."
- Do not infer or speculate unless you explicitly label it as inference.
- A gap is a valid finding. Report it as such.
```

This instruction alone significantly reduces hallucinated citations and overconfident claims.

#### 38.6.2 Confidence Markers in Output

Every `keyFinding` in the report must carry a `confidence` field. The agent assigns confidence during phase 3, based on:

- `high`: three or more independent sources with consistent findings
- `medium`: one or two high-quality sources, or multiple lower-quality sources
- `low`: single low-quality source, inference from related evidence, or conflicting sources with no resolution

> [!TIP]
> Use `low` confidence findings as a separate section in the report: "We found the following claims, but the evidence is limited. Verify before acting on them." This makes the uncertainty explicit without hiding the information.

#### 38.6.3 Flagging Contradictory Sources

When two sources make contradictory claims — one says token bucket is always preferred for API rate limiting, another says sliding window is better for burst traffic — the agent must not silently choose one. It must report the contradiction, note the quality of each source, and present both positions.

The system prompt instruction: "When sources contradict each other, report both positions, note the quality of each source, and do not resolve the contradiction unless the evidence strongly favors one side."

### 38.7 Lessons Learned

The research agent is harder to evaluate than the coding agent precisely because its output cannot be verified by running a test. The key lessons from production deployments:

**Start with a narrow question.** An agent asked "What should we know about distributed systems?" will produce either a shallow survey or a context-exhausting deep dive. An agent asked "What are the consistency trade-offs between Raft and Paxos for leader election?" produces something useful.

**Memory is not optional at scale.** Research agents that try to hold all source content in the live context cannot handle more than three or four sources before degrading. The `save_to_memory` / `query_memory` pattern is what makes multi-source synthesis possible.

**The stopping condition is the hardest part.** Build a `stop_research` tool or a confidence threshold check into the plan. Without it, agents will search indefinitely — there is always one more source to check. Bound the exploration phase by source count and turn count, not just by the agent's judgment that it is "done."

**Citation discipline requires structural enforcement.** System prompt instructions alone are insufficient to prevent hallucinated citations. The `write_report` tool's schema, which requires each `keyFinding` to carry a `source`, is what enforces citation discipline. Structure the output, do not just instruct.

---

## Key Takeaways

- A research agent produces a structured, cited report — not a conversational response. Build the report schema into the output tool and enforce it structurally.
- Separate exploration from deep reading with a phased plan. Broad search first, selective deep reading second, synthesis third. Without this separation, agents spiral into the first source they find.
- Web page content explodes context. Use `ToolResponseProcessor` to strip and summarize every `fetch_page` result before it enters the context. Never insert raw HTML.
- External memory (`save_to_memory` / `query_memory`) is what makes multi-source synthesis possible. Save findings as you read; retrieve them during synthesis.
- Uncertainty must be explicit. Give the agent explicit permission to say "I don't know" and require confidence markers on every key finding. Gaps are valid findings — report them.
- The stopping condition requires structural enforcement. Without an explicit `stop_research` mechanism, research agents search indefinitely. Bound by source count and turn count.
