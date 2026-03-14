---
title: "Appendix C — Glossary"
page: 57
status: draft
---

## Appendix C — Glossary

*Definitions as used in this book. Some terms have broader meanings elsewhere.*

---

**Adapter** — An implementation of `IProviderAdapter` that translates between Lemura's internal request/response format and a specific LLM provider's API.

**Agent** — A software system that perceives its environment, reasons about what to do, takes actions via tools, and adjusts based on results — autonomously, over multiple steps.

**Compression** — The process of reducing the size of an agent's context by summarizing, truncating, or otherwise condensing older messages.

**Context** — The full content passed to an LLM on each turn: system prompt, message history, tool definitions, injected goals, and current input.

**Context Window** — The maximum number of tokens an LLM can process in a single request.

**ContinuationPlanner** — The Lemura component responsible for tracking which steps in a plan have been completed, which are ready to execute, and how outputs flow between steps.

**Goal** — A high-level description of what the agent is trying to accomplish. Distinct from a plan, which specifies how.

**Goal Drift** — The phenomenon where an agent progressively loses alignment with its original goal over many turns, typically due to recent context crowding out the goal.

**GoalInjector** — The Lemura component that periodically re-injects the current goal into the context to prevent goal drift.

**MCP** — Model Context Protocol. A standard protocol for LLMs to communicate with external tool servers.

**MCPClient** — Lemura's client for connecting to a single MCP server.

**MCPClientRegistry** — Lemura's manager for connecting to and coordinating multiple MCP servers.

**Plan** — A structured sequence of `PlanStep` objects defining how to accomplish a goal. Plans have dependencies, conditions, and data flow between steps.

**PlanStep** — A single unit of work in a plan, with an ID, description, optional dependencies, and data flow declarations.

**Provider** — An LLM backend that the agent calls: OpenAI, Anthropic, Groq, Ollama, or any OpenAI-compatible endpoint.

**ReAct** — Reasoning + Acting. The dominant agentic loop pattern: the model reasons about what to do, takes an action (tool call), observes the result, and repeats.

**Sandwich Compression** — A compression strategy that preserves the beginning (system/goal) and end (recent turns) of the context, compressing only the middle (older history).

**Session** — A running instance of a Lemura agent, managed by `SessionManager`.

**SessionConfig** — The configuration object passed to `SessionManager` that controls all aspects of agent behavior.

**SessionManager** — The central Lemura class that implements the ReAct loop and coordinates all other components.

**Skill** — A reusable, named block of instructions or knowledge that can be injected into an agent's context.

**SkillInjector** — The Lemura component that manages skill injection with a configurable token budget.

**Sub-Goal** — A smaller, concrete objective that contributes to the main goal. Tracked by `GoalInjector`.

**Tool** — A function that the agent can call to interact with the world. Defined by a name, description, and JSON Schema parameters.

**ToolResponseProcessor** — The Lemura component that intercepts large tool results and compresses them before they enter the context.

**Turn** — One complete request+response cycle: the agent produces a message (and possibly tool calls), the tools execute, and results are collected.
