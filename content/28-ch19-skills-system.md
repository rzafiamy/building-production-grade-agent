---
title: "Chapter 19 — Skills: Reusable Agent Capabilities"
part: "Part III — Lemura Framework Deep Dive"
chapter: 19
page: 28
status: draft
---

*PART III — LEMURA FRAMEWORK DEEP DIVE*

## Chapter 19 — Skills: Reusable Agent Capabilities

> *"A skill is a named piece of expertise. Instead of writing the same system prompt instructions over and over, you package them once and inject them on demand."*

> [!NOTE]
> **Chapter Goal:** By the end of this chapter, you will understand Lemura's skills system, how to define and register skills, how the `SkillInjector` manages token budgets, and how to design a library of reusable skills for your agent ecosystem.

---

### 19.1 What Is a Skill?

#### 19.1.1 Skills vs. System Prompt Text

A system prompt is a static block of instructions for a session. It works well for instructions that apply to every turn, every task, and every user. It works poorly when different sessions need different instructions, or when a session's needs change mid-execution.

A skill is a named, versioned, injectable piece of system prompt content. Instead of baking all possible instructions into a monolithic system prompt, you define skills for different domains of expertise and inject only the ones relevant to the current task. The system prompt stays lean; domain knowledge is loaded on demand.

The practical consequence: a single `SessionManager` factory can produce sessions with different behavioral profiles by selecting different skill sets. A coding agent and a writing agent can share the same base configuration and differ only in which skills are active.

#### 19.1.2 Skills vs. Tools

Skills and tools are complementary, not competing abstractions.

A **tool** gives the agent the ability to do something: read a file, search the web, write to a database. It is executable capability with side effects.

A **skill** gives the agent knowledge and instruction: how to approach a security audit, what format to use when writing code review comments, which questions to ask when analyzing requirements. It is declarative guidance with no execution overhead.

The distinction is: tools extend what the agent can do; skills extend how the agent thinks about what it does.

#### 19.1.3 When Skills Are the Right Abstraction

Use skills when:
- The same instructions appear verbatim or nearly verbatim across multiple agent configurations
- Different tasks require different reasoning approaches but the same underlying capability
- You want to version and test instruction sets independently from agent code
- You want to build a library of reusable guidance that multiple teams can share

Do not use skills as a workaround for poor tool design. Instructions like "when reading a file, always look for X" belong in the tool's description, not in a skill.

### 19.2 Defining a Skill

#### 19.2.1 The Skill Interface

Skills implement the `ISkill` interface (see `src/skills/SkillInjector.ts`). The interface supports content tiers for token-budget-aware injection:

```typescript
// A security auditing skill with content tiers
import { ISkill } from "lemura/types";

const securityAuditSkill: ISkill = {
  name: "security_audit",
  version: "1.2.0",
  description: "Expert guidance for security code reviews",
  inject: "system_prompt",
  priority: 10,
  strategy: "fixed",  // always active when registered

  // Nano tier: used when token budget is very tight (~50 tokens)
  nano: "Focus on injection, auth, and data exposure risks.",

  // Micro tier: used at ~150 tokens
  micro: "Review for: SQL injection, XSS, auth bypass, " +
         "insecure deserialization, and data exposure.",

  // Standard tier: used at ~400 tokens (default)
  standard: `Security Audit Guidelines:
- Check all database queries for parameterization
- Verify auth and authorization on every endpoint
- Look for sensitive data in logs, errors, and responses
- Flag use of eval(), Function(), or dynamic require()
- Check for path traversal in file operations`,

  // Extended tier: used when budget is abundant (~1000 tokens)
  extended: `[Full extended security checklist — OWASP Top 10 mapped to code patterns ...]`,
};
```

#### 19.2.2 Skill Content: Instructions and Context

Skill content should be actionable instructions, not vague guidance. "Be thorough" is not a useful skill. "For each function, check that all parameters are validated before use and that error messages do not expose internal implementation details" is.

Write skill content in second person, present tense, as direct instructions to the model. The model receives skill content as part of its system prompt and responds to imperative instructions better than descriptive ones.

#### 19.2.3 Skill Metadata: Name, Description, Token Estimate

`name` must be unique within the session's skill set. `version` enables change tracking — when you update a skill's content, increment the version so you can identify which version was active in any given session via the trace log. `description` is for human readers and for the optional embedding-based skill retrieval covered in section 19.7.

### 19.3 The SkillInjector

`SkillInjector` (see `src/skills/SkillInjector.ts`) manages the collection of skills for a session. Access it via `session.skills` after construction.

#### 19.3.1 How Skills Are Injected into the Session

Before each model call, `SessionManager` calls `skillInjector.buildInjectionBlock(position, tokenBudget)` to get the formatted content for each injection position. The `SkillInjector` selects the appropriate content tier based on the available budget and assembles the block.

The injection block is appended to the system prompt (for `inject: 'system_prompt'` skills) or prepended to the current turn (for `inject: 'pre_turn'` skills). Skills marked `inject: 'post_history'` are appended after the conversation history.

#### 19.3.2 Injection Position and Order

Skills are injected in priority order (lower numbers first) within each injection position. Multiple skills with `inject: 'system_prompt'` are concatenated into a single block appended to the system prompt. Their relative order is determined by `priority`.

Use priorities consistently across your skill library. A convention like 10–19 for foundational skills, 20–29 for domain skills, and 30–39 for output format skills makes the injection order predictable.

#### 19.3.3 `skillTokenBudget`: Preventing Skill Bloat

Configure `skillTokenBudget` in `SessionConfig` to cap the total tokens that skill injection can consume. When the combined standard-tier content of all active skills exceeds the budget, `SkillInjector` falls back to smaller content tiers in priority order.

The priority-based fallback is deliberate: lower-priority skills fall back to nano/micro content first, while higher-priority skills retain their standard content. This ensures the most important skills maintain quality even under tight budgets.

### 19.4 Token Budget Enforcement

#### 19.4.1 What Happens When Skills Exceed the Budget

When total skill content would exceed `skillTokenBudget`, `SkillInjector` resolves the budget using this algorithm:
1. Allocate full standard content to the highest-priority skills first
2. Reduce lower-priority skills to micro tier if needed
3. Reduce further to nano tier if still over budget
4. Omit the lowest-priority skills entirely if nano is still over budget

Skills that are omitted due to budget are flagged in the trace log. If you see important skills being dropped, either increase `skillTokenBudget` or reduce the standard content of lower-priority skills.

#### 19.4.2 Priority-Based Skill Selection

```typescript
// Registering skills with explicit priorities
import { SessionManager, OpenAICompatibleAdapter } from "lemura";

const session = new SessionManager({
  adapter,
  model: "gpt-4o-mini",
  maxTokens: 100_000,
  skillTokenBudget: 2_000,  // skills may use at most 2000 tokens
  skills: [
    { name: "base_agent",     priority: 5,  inject: "system_prompt",
      standard: "You are a precise technical assistant...", strategy: "fixed" },
    { name: "code_review",    priority: 10, inject: "system_prompt",
      standard: "For code reviews, check types, errors, and security...", strategy: "fixed" },
    { name: "verbose_format", priority: 30, inject: "system_prompt",
      standard: "Always include examples and rationale in your responses...", strategy: "dynamic" },
  ],
});
```

`base_agent` and `code_review` are fixed skills — always active. `verbose_format` is a dynamic skill — inactive by default, enabled when needed.

#### 19.4.3 Dynamic Skill Activation

Dynamic skills (`strategy: 'dynamic'`) are inactive by default and must be explicitly enabled:

```typescript
// Enabling a dynamic skill for a specific run
session.skills.enableSkill("verbose_format");
const result = await session.run("Review the auth module.");
session.skills.disableSkill("verbose_format"); // disable after run
```

Dynamic skills can also be enabled by tag:

```typescript
// Enabling all skills tagged 'security' for a security audit session
session.skills.enableByTags(["security"]);
const result = await session.run("Audit /src for vulnerabilities.");
session.skills.disableByTags(["security"]); // clean up
```

### 19.5 Skill Design Patterns

#### 19.5.1 Domain Skills: Expert Knowledge Injection

Domain skills encapsulate the reasoning patterns of a specific expertise area. A security skill teaches the model to think like a security reviewer. A performance skill teaches it to think like a performance engineer. The skill content is the distilled expert knowledge that would otherwise live in a long, monolithic system prompt.

Domain skills work best when they focus on reasoning approaches, not just checklists. "Before calling any external API, verify the caller is authenticated and authorized to access the requested resource" teaches a reasoning pattern. A checklist without context teaches a procedure.

#### 19.5.2 Persona Skills: Role-Based Behavior

Persona skills define the agent's communication style and stance. A "senior engineer" persona produces concise, technically precise responses. A "documentation writer" persona produces structured, reader-friendly explanations. A "security reviewer" persona produces cautious, evidence-based assessments.

Persona skills are typically fixed — the agent's communication style should be consistent across a session. Changing persona mid-session produces inconsistent output that is confusing to read.

#### 19.5.3 Constraint Skills: Rules and Guardrails

Constraint skills define boundaries: things the agent must always do or never do. "Never suggest deleting production data without an explicit confirmation step." "Always include a test for every code change." "Never hardcode credentials in generated code."

Constraint skills are the implementation of policy as instruction. They are better than system prompt text because they can be versioned, audited, and updated independently of the session configuration.

#### 19.5.4 Format Skills: Output Shape Control

Format skills define the expected structure of agent outputs. "Always return code in fenced TypeScript blocks." "Structure your analysis as: Findings, Recommendations, and Impact Assessment." "When listing items, use a numbered list with rationale for each item."

Format skills are often dynamic — activated when a specific output format is needed and deactivated for other tasks.

### 19.6 Building a Skill Library

#### 19.6.1 Organizing Skills by Domain

Organize your skill library as a directory of skill definition files. Each file exports one skill:

```text
src/skills/
  domain/
    security-audit.skill.ts
    performance-review.skill.ts
    accessibility-check.skill.ts
  persona/
    senior-engineer.skill.ts
    technical-writer.skill.ts
  constraints/
    production-safety.skill.ts
    coding-standards.skill.ts
  format/
    code-review-format.skill.ts
    bug-report-format.skill.ts
```

Importing skills from this library keeps session configuration clean:

```typescript
// Clean session construction using a shared skill library
import { securityAuditSkill } from "../skills/domain/security-audit.skill.js";
import { seniorEngineerSkill } from "../skills/persona/senior-engineer.skill.js";
import { productionSafetySkill } from "../skills/constraints/production-safety.skill.js";

const session = new SessionManager({
  adapter, model, maxTokens,
  skills: [securityAuditSkill, seniorEngineerSkill, productionSafetySkill],
});
```

#### 19.6.2 Versioning Skills

Increment the `version` field whenever skill content changes. Store skills in version control and treat skill updates as code changes — they require testing and review. The skill's version appears in trace logs, so you can correlate agent behavior to specific skill versions in production.

#### 19.6.3 Testing Skill Effectiveness

Test skills by running evaluation sessions with and without each skill and comparing output quality on representative tasks. A security audit skill should produce findings that a security engineer would recognize as correct; a format skill should produce output that matches the expected structure.

The most important test is regression: if updating a skill causes a previously passing evaluation to fail, the update degraded quality. Track evaluation scores per skill version to detect regressions early.

### 19.7 Dynamic Skill Selection

#### 19.7.1 Selecting Skills Based on Task Type

For agents that handle multiple task types, select skills based on the task:

```typescript
// Routing task-specific skills based on input classification
function selectSkillsForTask(taskDescription: string): string[] {
  const tags: string[] = ["base"];
  if (/security|vulnerability|auth|injection/.test(taskDescription)) {
    tags.push("security");
  }
  if (/performance|latency|throughput|memory/.test(taskDescription)) {
    tags.push("performance");
  }
  if (/review|feedback|improve/.test(taskDescription)) {
    tags.push("code-review");
  }
  return tags;
}

const tags = selectSkillsForTask(userRequest);
session.skills.enableByTags(tags);
const result = await session.run(userRequest);
session.skills.disableByTags(tags);
```

#### 19.7.2 Skill Retrieval with Embeddings

For large skill libraries (50+ skills), selecting skills by regex keyword matching becomes brittle. Embedding-based retrieval offers a more robust alternative: embed each skill's `description` and `name` in a vector store, then retrieve the top-k skills most semantically similar to the current task description before each session.

This approach requires an embedding model and a vector similarity search, but scales to large skill libraries without manual tag maintenance. See **Chapter 20 — Memory Architecture for Long-Running Agents** for the vector store integration patterns that apply here.

> [!TIP]
> Start with 3–5 fixed skills and a clean system prompt. Add dynamic skills when you observe that certain task types need specialized instruction that is not appropriate for all tasks. The skills system's value is in the library you build over time — the investment compounds as the library grows.

---

## Key Takeaways

- A skill is a named, versioned piece of system prompt content that can be injected on demand; it extends how the agent thinks, while tools extend what the agent can do.
- `SkillInjector` manages skill collection, budget enforcement, and content tier selection; access it via `session.skills` after construction.
- Content tiers (`nano`, `micro`, `standard`, `extended`) enable budget-aware injection — lower-priority skills fall back to smaller tiers when the token budget is tight.
- Dynamic skills (`strategy: 'dynamic'`) are inactive by default; enable them per-run with `session.skills.enableSkill()` or `enableByTags()` to provide task-specific expertise.
- Build a skill library organized by domain, persona, constraints, and format; version skills in source control and test skill updates as rigorously as code changes.
