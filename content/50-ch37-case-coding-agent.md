---
title: "Chapter 37 — Case Study: The Coding Agent"
part: "Part VII — Real-World Applications"
chapter: 37
page: 50
status: draft
---

*PART VII — REAL-WORLD APPLICATIONS*

## Chapter 37 — Case Study: The Coding Agent

> *"A coding agent doesn't replace engineers. It removes the boring 30% so engineers can focus on the hard 70%."*

> [!NOTE]
> **Chapter Goal:** By the end of this chapter, you will understand how to design and implement a coding agent that can read, write, test, and fix code — and how to make it reliable enough to trust with real codebases.

---

### 37.1 The Problem: What the Coding Agent Must Do

A coding agent is the most commonly attempted agentic application — and one of the most commonly abandoned. The gap between a demo that writes a Fibonacci function and an agent you can point at a real repository is enormous. Closing that gap requires understanding not just what the agent does, but what it is not allowed to do, and how you will know when it has done it correctly.

#### 37.1.1 Scope: What "Coding Agent" Means Here

The coding agent in this chapter handles implementation tasks: fixing bugs, adding features, refactoring modules, and writing tests. It reads the existing codebase, understands the relevant context, makes changes, runs validation, and reports results. The task arrives as a natural language description: "The `UserService.updateEmail()` method does not validate the email format. Add validation using the existing `validators` module and add a test for the invalid-email case."

The agent is not a pair programmer that engages in conversation across multiple turns of user input. It is a batch-mode autonomous worker: given a task, it runs to completion or escalates to a human when it encounters something it cannot resolve. The distinction matters for tool design and session configuration.

#### 37.1.2 Success Criteria

Success for a coding task is objective and verifiable. The agent has succeeded when:

1. The tests that were passing before the change still pass.
2. The new tests (if any were required) also pass.
3. The code compiles and the linter reports no new errors.
4. The change is scoped to what was asked — no unrelated modifications.

This verifiability is the coding agent's main advantage over research or workflow agents. You do not need LLM-as-judge evaluation. The test suite is the judge. Design every part of the agent around this property.

#### 37.1.3 Non-Goals

The coding agent does not:

- Make architectural decisions. It implements within the existing architecture.
- Resolve ambiguous requirements. If the task description is unclear, it escalates to a human rather than guessing.
- Modify files outside the scope of the task. It reads broadly but writes narrowly.
- Push to version control. It prepares the change; a human reviews and commits.

Keeping these as explicit non-goals shapes the system prompt, the tool safety boundaries, and the escalation conditions. When the agent operates outside these boundaries, it becomes unpredictable. When it stays within them, it becomes trustworthy.

### 37.2 The Challenges

#### 37.2.1 Iterative Correction: Writing Is Rewriting

A coding agent that writes code once and stops is not a coding agent — it is a code generator. The difference is what happens when the first attempt is wrong. Real coding is a loop: write, run tests, observe failures, reason about the cause, fix, repeat. Your agent must implement this loop explicitly.

The challenge is that the loop is expensive. Each iteration costs tokens and latency. An agent that iterates 15 times on a simple bug fix has consumed the equivalent of a full chapter of context. You need to design the plan structure so that the agent terminates the loop on a clear signal (tests pass) and limits itself to a sane maximum iteration count before escalating to a human.

> [!WARNING]
> Set `maxIterations` conservatively for coding tasks. An agent that cannot fix a bug in 10 iterations is unlikely to fix it in 20. It is more likely stuck in a loop that a human needs to break. Escalate rather than iterate indefinitely.

#### 37.2.2 Context: Understanding a Large Codebase

A real codebase is far larger than any context window. The agent cannot read every file — it must read the right files. This means the agent needs a strategy for codebase exploration that is driven by the task, not by naive directory traversal.

The pattern that works is targeted search before reading: use `search_code` to find references, then use `read_file` on only the files that are relevant. An agent that reads every file it encounters will fill its context window with irrelevant code before it ever reaches the file it needs to change.

Context management is more aggressive here than in other agent types. Tool responses from `read_file` can be thousands of tokens each. Use `ToolResponseProcessor` with tight token limits, and configure `SandwichCompressionStrategy` so that older file reads are summarized before the agent begins writing.

#### 37.2.3 Tool Reliability: Filesystem Operations Are Destructive

`write_file` is not like `web_search`. A failed web search returns no results. A failed write might corrupt a file, create a partial edit, or overwrite code that was not meant to change. Your tool design must treat every write as a potentially irreversible action.

The practical response to this is: never write without reading first, always write the complete file content rather than line-level patches (which are fragile under model hallucination), and always require human confirmation before writes land on disk. A write tool that stages changes to a temporary path and only commits them on explicit approval is the right pattern for production use.

#### 37.2.4 Testing as the Ground Truth

The test suite is the only objective signal your agent has about whether its change is correct. Design the agent's plan to run tests aggressively: before making changes (to establish a baseline), after every write (to detect regressions), and at the end (to confirm the final state). If the agent cannot access a test runner, it has no ground truth, and you should not deploy it.

This is not optional. An agent that writes code without running tests is a code generator with extra steps. The test-driven loop is what makes it a coding agent.

### 37.3 Tool Design for a Coding Agent

The coding agent requires a tightly designed tool set. Each tool has a specific purpose, and the boundaries between tools matter for safety.

#### 37.3.1 `read_file`, `write_file`, `list_directory`

These are the core filesystem tools. `read_file` returns file contents given a path. `list_directory` returns files and directories at a given path. `write_file` writes a complete file.

```typescript
// Tool definitions for basic filesystem access
import type { ToolDefinition } from 'lemura';
import * as fs from 'fs/promises';
import * as path from 'path';

const WORKSPACE_ROOT = process.env.AGENT_WORKSPACE_ROOT ?? process.cwd();

function assertInsideWorkspace(filePath: string): string {
  const resolved = path.resolve(WORKSPACE_ROOT, filePath);
  if (!resolved.startsWith(WORKSPACE_ROOT)) {
    throw new Error(`Path escapes workspace: ${filePath}`);
  }
  return resolved;
}

export const readFileTool: ToolDefinition = {
  name: 'read_file',
  description: 'Read the contents of a file in the workspace.',
  parameters: {
    type: 'object',
    properties: {
      path: { type: 'string', description: 'Relative path to the file' },
    },
    required: ['path'],
  },
  async execute({ path: filePath }) {
    const resolved = assertInsideWorkspace(filePath as string);
    const content = await fs.readFile(resolved, 'utf-8');
    return { path: filePath, content, lines: content.split('\n').length };
  },
};

export const writeFileTool: ToolDefinition = {
  name: 'write_file',
  description: 'Write complete content to a file. Requires human approval before executing.',
  parameters: {
    type: 'object',
    properties: {
      path: { type: 'string', description: 'Relative path to the file' },
      content: { type: 'string', description: 'Complete file content to write' },
      reason: { type: 'string', description: 'Why this change is needed' },
    },
    required: ['path', 'content', 'reason'],
  },
  async execute({ path: filePath, content, reason }) {
    const resolved = assertInsideWorkspace(filePath as string);
    // In production: route through approval gate before writing
    await fs.writeFile(resolved, content as string, 'utf-8');
    return { path: filePath, written: true, reason };
  },
};
```

Keep the path restriction strict. The `assertInsideWorkspace` check prevents path traversal attacks where the agent (or a prompt injection in a tool result) attempts to write outside the designated workspace.

#### 37.3.2 `run_tests`, `run_command`

`run_tests` executes the test suite and returns structured results: pass/fail counts, failure messages, and timing. `run_command` runs arbitrary shell commands with an allowlist of permitted executables. Never provide an unrestricted shell — the allowlist is the safety boundary.

```typescript
// run_tests tool that returns structured pass/fail results
import { exec } from 'child_process';
import { promisify } from 'util';
const execAsync = promisify(exec);

export const runTestsTool: ToolDefinition = {
  name: 'run_tests',
  description: 'Run the test suite and return pass/fail results with failure messages.',
  parameters: {
    type: 'object',
    properties: {
      pattern: {
        type: 'string',
        description: 'Optional test file pattern (e.g. "src/user/**")',
      },
    },
    required: [],
  },
  async execute({ pattern }) {
    const cmd = pattern
      ? `npx jest --testPathPattern="${pattern}" --json`
      : 'npx jest --json';

    try {
      const { stdout } = await execAsync(cmd, {
        cwd: WORKSPACE_ROOT,
        timeout: 120_000,
      });
      const report = JSON.parse(stdout);
      return {
        passed: report.numPassedTests,
        failed: report.numFailedTests,
        total: report.numTotalTests,
        failures: report.testResults
          .filter((r: { status: string }) => r.status === 'failed')
          .flatMap((r: { testResults: { fullName: string; failureMessages: string[] }[] }) =>
            r.testResults
              .filter((t) => t.status === 'failed')
              .map((t) => ({ name: t.fullName, message: t.failureMessages[0] }))
          )
          .slice(0, 10), // cap to avoid context explosion
      };
    } catch (err) {
      return { passed: 0, failed: -1, error: String(err) };
    }
  },
};
```

The `slice(0, 10)` on failures matters. A test suite that fails 200 tests will produce a tool result larger than most context windows if you include all failure messages. Cap the output and instruct the agent to focus on the first few failures.

#### 37.3.3 `search_code` (Semantic and Syntactic)

`search_code` is the agent's codebase navigation tool. It combines syntactic search (regex over file contents) with the ability to resolve symbol references. This is the tool the agent uses before reading files, to find which files are relevant.

```typescript
// Syntactic code search using ripgrep under the hood
export const searchCodeTool: ToolDefinition = {
  name: 'search_code',
  description: 'Search the codebase for a pattern. Returns file paths and matching lines.',
  parameters: {
    type: 'object',
    properties: {
      pattern: { type: 'string', description: 'Regex or literal string to search for' },
      fileGlob: {
        type: 'string',
        description: 'Optional file glob filter (e.g. "**/*.ts")',
      },
    },
    required: ['pattern'],
  },
  async execute({ pattern, fileGlob }) {
    const globFlag = fileGlob ? `--glob "${fileGlob}"` : '';
    const { stdout } = await execAsync(
      `rg --json ${globFlag} "${pattern}" .`,
      { cwd: WORKSPACE_ROOT, timeout: 10_000 }
    );
    const matches = stdout
      .split('\n')
      .filter(Boolean)
      .map((line) => JSON.parse(line))
      .filter((e) => e.type === 'match')
      .map((e) => ({
        path: e.data.path.text,
        line: e.data.line_number,
        text: e.data.lines.text.trim(),
      }))
      .slice(0, 30); // cap results
    return { matches, total: matches.length };
  },
};
```

#### 37.3.4 `git_status`, `git_diff`, `git_commit`

Git tools give the agent visibility into what has changed. `git_status` shows modified files. `git_diff` shows the actual diff. These are read-only tools the agent uses to review its own changes before finalizing.

Do not give the agent `git_commit` by default. Review the diff yourself before committing. If your workflow requires the agent to commit, route the commit through an approval gate and enforce conventional commit message format.

#### 37.3.5 Safety Boundaries: What the Agent Cannot Do

Define these boundaries explicitly in the system prompt and enforce them in the tools:

- Cannot delete files (`rm`, `unlink`)
- Cannot modify files outside the workspace root
- Cannot run arbitrary shell commands (only allowlisted tools)
- Cannot push to remote branches
- Cannot modify CI/CD configuration files

> [!DANGER]
> Never give a coding agent unrestricted shell access. A prompt injection in a malicious dependency's README, accidentally read by the agent during exploration, could instruct it to run destructive commands. The allowlist is your last line of defense.

### 37.4 Session Configuration

#### 37.4.1 Goal and Plan Structure for Code Tasks

Structure the goal around the task description and verification criteria. Structure the plan around the coding loop: understand, write, verify.

```typescript
// Session configuration for a coding agent with explicit plan
import { SessionManager, SandwichCompressionStrategy } from 'lemura';
import type { ContinuationStep } from 'lemura';

// Adapter is provided by a separate adapter package (e.g. lemura-openai)
const adapter = new OpenAIAdapter({ apiKey: process.env.OPENAI_API_KEY! });

const plan: ContinuationStep[] = [
  { stepId: 'explore', toolName: 'search_code', description: 'Find UserService and validators module', dependsOn: [], status: 'pending' },
  { stepId: 'read', toolName: 'read_file', description: 'Read UserService.ts and validators', dependsOn: ['explore'], status: 'pending' },
  { stepId: 'baseline', toolName: 'run_tests', description: 'Establish baseline test state', dependsOn: ['read'], status: 'pending' },
  { stepId: 'implement', toolName: 'write_file', description: 'Add email validation', dependsOn: ['baseline'], status: 'pending' },
  { stepId: 'test-new', toolName: 'write_file', description: 'Add test for invalid email', dependsOn: ['implement'], status: 'pending' },
  { stepId: 'verify', toolName: 'run_tests', description: 'Confirm all tests pass', dependsOn: ['test-new'], status: 'pending' },
];

const codingSession = new SessionManager({
  adapter,
  model: 'gpt-4o-2024-08-06',
  maxTokens: 128000,
  systemPrompt: `You are a precise coding agent working on a TypeScript codebase.
You write correct, idiomatic TypeScript. You run tests after every change.
You do not modify files outside the task scope.
You escalate to a human when requirements are ambiguous or tests cannot be fixed.`,

  tools: [readFileTool, writeFileTool, searchCodeTool, runTestsTool, gitStatusTool, gitDiffTool],
  maxIterations: 20,
  enableContinuationPlanning: true,
  enableGoalPlanning: true,
  goalInjectionN: 3,
  compressionStrategies: [
    new SandwichCompressionStrategy(adapter, { preserveFirst: 3, preserveLast: 6, triggerThreshold: 0.80 }),
  ],
});
```

#### 37.4.2 Compression Strategy for Large Codebases

Coding agents read a lot of files. Every `read_file` result can be thousands of tokens. Without aggressive compression, the agent's context fills with old file contents before it reaches the writing phase.

Use `SandwichCompressionStrategy` configured to compress the middle aggressively. The goal context (injected via `GoalInjector`) and the most recent turns (the current test failure and the file being fixed) should always stay in the context. Old file reads from the exploration phase should be summarized.

Also configure `ToolResponseProcessor` to limit how much of any single file read enters the context:

```typescript
// ToolResponseProcessor to cap tool responses by size class
import { ToolResponseProcessor } from 'lemura';

const processor = new ToolResponseProcessor({
  smallMaxTokens: 200,
  mediumMaxTokens: 800,   // caps run_tests output
  largeMaxTokens: 2000,   // caps read_file output
});
```

#### 37.4.3 Human-in-the-Loop for Destructive Operations

Route all `write_file` calls through a human-in-the-loop gate before the bytes hit disk. The approval interface shows the file path, the diff between old and new content, and the agent's stated reason for the change.

```typescript
// Use onTrace to intercept tool_call events and gate writes on human approval
const session = new SessionManager({
  // ... other config
  onTrace: async (event) => {
    if (event.type === 'tool_call' && event.name === 'write_file') {
      const args = event.input as { path: string; content: string; reason: string };
      const approved = await promptHumanApproval({
        title: `Write ${args.path}`,
        diff: await computeDiff(args.path, args.content),
        reason: args.reason,
      });
      if (!approved) {
        // Throwing here surfaces a ToolError the agent can handle
        throw new Error('Write rejected by operator. Escalate to human.');
      }
    }
  },
});
```

### 37.5 The Implementation

#### 37.5.1 Session Setup

The full session setup assembles the pieces from the previous sections: the adapter, the plan, the tools, and the callbacks.

```typescript
// Complete coding agent session setup
async function runCodingTask(taskDescription: string): Promise<void> {
  const adapter = new OpenAIAdapter({ apiKey: process.env.OPENAI_API_KEY! });

  const session = new SessionManager({
    adapter,
    model: 'gpt-4o-2024-08-06',
    maxTokens: 128000,
    systemPrompt: CODING_AGENT_SYSTEM_PROMPT,
    tools: [
      readFileTool,
      writeFileTool,
      listDirectoryTool,
      searchCodeTool,
      runTestsTool,
      gitStatusTool,
      gitDiffTool,
    ],
    toolResponseProcessor: new ToolResponseProcessor({
      smallMaxTokens: 200,
      mediumMaxTokens: 800,
      largeMaxTokens: 2000,
    }),
    compressionStrategies: [
      new SandwichCompressionStrategy(adapter, { preserveFirst: 3, preserveLast: 6 }),
    ],
    maxIterations: 20,
    enableGoalPlanning: true,
    goalInjectionN: 3,
    onTrace: async (event) => {
      if (event.type === 'tool_call' && event.name === 'write_file') {
        await requireHumanApproval(event.input);
      }
      if (event.type === 'system' && event.name === 'session_complete') {
        console.log('Session complete:', event.metadata);
      }
    },
  });

  // Set goal and plan before running
  session.setGoal({ statement: taskDescription, decomposition: [], successCriteria: ['All tests pass'] });
  session.setPlan(buildCodingPlan(), 'sequential');

  const output = await session.run(taskDescription);
  console.log(output);
}
```

#### 37.5.2 The Initial Plan: Read → Understand → Write → Test → Fix

The plan encodes the coding loop explicitly. The agent should not jump to writing without reading and understanding the relevant code. The plan enforces this by making `implement` depend on `baseline` — which depends on `read` — which depends on `explore`.

This dependency chain prevents the pattern where the agent starts writing based on its training knowledge of the codebase rather than the actual current state of the files. It costs a few extra turns, but it catches real issues: the module you thought exported `validateEmail` actually exports `isValidEmail`, and your code would have been wrong from the start.

#### 37.5.3 Handling Test Failures

When tests fail after a write, the agent receives structured failure output from `run_tests`. The key information is the failing test name and the first failure message. The agent uses this to reason about what went wrong and produce a targeted fix.

Design the system prompt to guide this reasoning:

```text
When tests fail:
1. Read the exact failure message carefully.
2. Identify the root cause (wrong assertion, missing case, broken import, type error).
3. Read only the files directly relevant to the failure.
4. Make the minimal change that fixes the root cause.
5. Run tests again. Do not make speculative changes.
```

This prompt structure reduces the agent's tendency to make large changes in response to small failures — a common failure mode that produces "fix soup" where each iteration makes the situation harder to understand.

#### 37.5.4 Managing Context as the Codebase Grows

As the session progresses through exploration, reading, and multiple fix iterations, the context fills with file contents that are no longer relevant. The compression strategy handles this automatically, but you should also configure the `ToolResponseProcessor` to aggressively trim `search_code` results that appear early in the session.

Monitor token usage via `onTurnEnd`. If you see token counts growing linearly without compression firing, your `SandwichCompressionStrategy` threshold may be set too high. Bring it down.

```typescript
// Monitor token growth per turn via the onTrace callback
onTrace: (event) => {
  if (event.type === 'system' && event.name === 'turn_complete') {
    const tokens = event.metadata?.tokenCount as number;
    console.log(`Turn complete: ${tokens} tokens in context`);
    if (tokens > 0.8 * MAX_CONTEXT_TOKENS) {
      console.warn('Approaching context limit — compression may be insufficient');
    }
  }
},
```

### 37.6 Lessons Learned

#### 37.6.1 Tool Output Verbosity Is the Biggest Context Drain

The single most effective optimization for coding agent performance is reducing `read_file` output size. In our experience, the average TypeScript source file that an agent reads is 250–600 lines — 2,000 to 5,000 tokens. A session that reads 10 files has consumed more tokens on file reads alone than on reasoning.

The fix is two-part: first, use `search_code` to identify the specific functions you need before reading the whole file; second, use `ToolResponseProcessor` to summarize file reads that exceed your token budget. A well-configured coding agent reads files surgically, not exhaustively.

#### 37.6.2 Test Feedback Is the Best Compression Signal

When context pressure is high and the agent must choose what to keep, the test failure message is the most valuable piece of information. Structure your compression summaries to always preserve the current test failure verbatim, even if everything else is summarized.

Configure the `GoalInjector` to include the current test status in the goal reminder:

```typescript
// Dynamic goal update to include current test state
session.setGoal(
  `${originalGoal}\n\nCurrent test state: ${passedCount} passing, ${failedCount} failing.`
);
```

This keeps the agent oriented even after compression has removed the detailed test output from earlier in the session.

#### 37.6.3 Human Confirmation Before Any Write Is Non-Negotiable in Production

The staging-and-approval pattern feels like friction during development. In production, it is the property that makes the agent trustworthy. Every team that has bypassed human-in-the-loop on writes for "well-understood" tasks has eventually shipped an incorrect change — because the task was not as well understood as it seemed, or because the agent interpreted the task description differently than intended.

The approval UI is part of the product. Make it good: show the diff clearly, include the agent's stated reason for the change, and make the reject path easy. An agent that users trust to propose changes is more valuable than one that makes changes they have to undo.

---

## Key Takeaways

- A coding agent's success is uniquely objective: the test suite either passes or it does not. Design everything — tools, plans, compression — around this ground truth.
- The coding loop is write → test → observe → fix → repeat. Make this loop explicit in the plan structure. Cap iterations at a sane limit and escalate rather than loop indefinitely.
- Tool output verbosity is the primary context threat. Use `ToolResponseProcessor` to cap `read_file` and `search_code` results, and `SandwichCompressionStrategy` to summarize older file reads.
- `search_code` before `read_file`: always find the relevant files before reading them. Reading every file in a directory is a context sink, not a navigation strategy.
- Require human approval for every write. Stage changes to a diff, show the reason, make rejection easy. The approval gate is the property that makes the agent trustworthy.
- Safety boundaries must be enforced in tool implementations, not just the system prompt. Path restriction, command allowlisting, and write gating are non-negotiable in production.
