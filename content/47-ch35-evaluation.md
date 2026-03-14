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

Agent quality is not a fixed property — it changes as the model is updated, as real-world task distributions shift, and as your understanding of what "good output" means improves. The improvement lifecycle treats quality as an ongoing operational concern, not a property established at launch and assumed stable.

```text
Deploy → Monitor → Collect Failures → Evaluate → Fix → Deploy
          ↑                                              │
          └──────────────────────────────────────────────┘
```

Each cycle should produce a measurable quality change — up or down. If you cannot measure the change, you cannot verify the improvement. The instrumentation from **Chapter 30 — Observability and Debugging** provides the raw signal; this chapter covers how to convert that signal into systematic quality improvements.

The cycle has a cadence. Not every week needs a new deployment, but every week should include data collection and analysis. Quality that is not actively monitored degrades silently as usage patterns shift and model behavior drifts across provider updates.

### 35.2 Collecting Improvement Signal

The most valuable signal for improving an agent comes from real production sessions — not from synthetic benchmarks or internal testing. Real sessions contain the task distributions, the edge cases, and the failure modes that matter to actual users. Your evaluation infrastructure is only as good as its connection to this signal.

#### 35.2.1 Explicit Feedback: User Ratings and Corrections

Users who interact with your agent can provide explicit quality signal in two forms: ratings (thumbs up/down, 1–5 stars) and corrections (the user modifies the agent's output or re-submits the task with a clarification).

Ratings are easy to collect and noisy to interpret. A thumbs-down tells you the user was dissatisfied, but not why. Corrections are more valuable: when a user corrects the agent's output, you have a paired example of what the agent produced and what the user actually wanted. These correction pairs are high-signal training examples.

Store every correction with its session ID, turn index, the agent's original output, and the user's correction. This dataset grows automatically with usage and requires no additional annotation effort.

#### 35.2.2 Implicit Feedback: Retry Behavior, Task Abandonment

Not all users rate or correct. But their behavior provides implicit signal. A user who resubmits the same task three times without the agent completing it has told you something is wrong. A user who abandons a session mid-way through has told you the agent lost their trust or failed on a critical step.

Define implicit failure signals for your agent type:
- For a research agent: session ends without `write_report` being called
- For a coding agent: session ends without test suite passing
- For a workflow agent: session ends with `escalate_to_human` rather than completing the plan

Track these implicit signals at the same rate as explicit ratings. They are noisier — sometimes abandonment is the user's choice, not a quality failure — but at scale they are reliable predictors of systematic problems.

#### 35.2.3 Automated Failure Detection

Some failures can be detected automatically without user involvement. Define automated failure detectors for your agent type:

- **Loop detection:** The agent called the same tool with identical arguments three times in a row.
- **Context overflow:** The session ended with `LemuraContextOverflowError`.
- **Cost overrun:** The session consumed more than 2× the expected token budget.
- **Timeout:** The session ran until `maxIterations` was reached without completing.
- **Tool error cascade:** Three or more consecutive tool calls failed.

Each of these conditions should trigger a session record for review, even if the user did not report a problem. Automated detection catches failures before they accumulate into a trend.

#### 35.2.4 Human Review Sampling

Random sampling of production sessions for human review is the calibration mechanism for all other signal sources. Reviewers read sampled sessions and rate them on your evaluation rubric, without knowing whether the session was flagged as a failure by any automated system.

Sample at a rate of 1–5% of production sessions. The goal is not to review everything — it is to maintain a calibrated reference set that you can compare against your automated signals. When automated signals diverge from human ratings, the automation needs adjustment, not the humans.

### 35.3 Evaluation Datasets

Evaluation without a stable dataset is navigation without a map. You need a fixed reference point — a set of tasks with known-quality expected outputs — to measure whether changes are improvements or regressions.

#### 35.3.1 Building a Golden Dataset

A golden dataset contains task inputs with human-verified expected outputs or quality criteria. Start with 50–100 examples that cover the distribution of real production tasks: easy cases, medium cases, known hard cases, and the specific failure modes you have observed in production.

For each example, define success criteria explicitly:
- Not just "the answer should be correct" — but "the answer must contain X, use citations from Y type of source, and be between 150 and 300 words."
- Not just "the code should work" — but "the tests in `src/user/__tests__/` must pass, no new TypeScript errors, no modifications outside `src/user/`."

The more precise your success criteria, the more reliable your evaluation. Vague criteria produce inconsistent evaluation results, which makes the dataset useless for detecting regressions.

#### 35.3.2 Real-World vs. Synthetic Evaluation

Synthetic evaluation tasks are constructed to test specific capabilities in isolation. Real-world evaluation tasks are drawn from actual production usage. Both have a role.

Synthetic tasks are good for regression testing specific capabilities — "can the agent still do X after this change?" Real-world tasks are good for overall quality assessment — "has the agent's performance on the range of things users actually ask it to do changed?" Run both. Synthetic tasks catch targeted regressions. Real-world tasks catch unexpected downstream effects of changes.

#### 35.3.3 Maintaining Dataset Quality Over Time

A golden dataset degrades. Tasks that were representative six months ago may not be representative today if the usage pattern has shifted. Expected outputs that were correct may become incorrect as the world changes. Criteria that seemed precise may prove ambiguous when new edge cases appear.

Review and update the golden dataset quarterly. Add new examples for failure modes discovered since the last review. Remove examples that no longer reflect real usage. Update expected outputs for any tasks where the correct answer has changed. A stale golden dataset is worse than no dataset — it gives you false confidence.

### 35.4 Evaluation Metrics by Task Type

No single metric captures quality for all agent types. Define the metrics appropriate for your task and measure them consistently across every evaluation run.

#### 35.4.1 Factual Accuracy

For agents that make factual claims — research agents, knowledge retrieval agents, question-answering agents — measure factual accuracy against a reference set of verified facts. Factual accuracy is binary per claim: the claim is correct or it is not. Report it as a percentage of correct claims per session.

Factual accuracy requires ground truth. Maintain a small set of factual questions with verified answers that you re-run on every model or prompt change. This is the fastest way to detect factual regression.

#### 35.4.2 Goal Completion

The most universal metric: did the agent accomplish the stated task? Goal completion is your primary quality signal regardless of task type. Define it for your agent:

- Coding agent: test suite passes, no new type errors, change is scoped correctly
- Research agent: `write_report` was called with all required fields populated
- Workflow agent: all plan steps reached `done` status without human escalation

Track goal completion rate over time. Alert when it drops. Investigate the sessions where goal completion failed — they are the highest-signal improvement opportunities.

#### 35.4.3 Tool Use Correctness

Does the agent use the right tools for the task, in an appropriate order, with correct arguments? Tool use correctness is harder to evaluate automatically — it requires either a reference execution trace or an LLM-as-judge evaluation. But it is the diagnostic metric that explains *why* goal completion failed when it does.

Define expected tool usage patterns for common task types: "for a bug fix task, the agent should call `run_tests` before and after writing, call `search_code` before `read_file`, and never call `write_file` without a preceding `read_file` on the same path." Automated checks against these patterns detect tool use regressions that may not yet manifest as goal completion failures.

#### 35.4.4 Output Format Adherence

If your agent produces structured output — a report in a specific format, a JSON payload, a Markdown document with required sections — measure whether the output matches the expected structure. Format adherence is typically binary and cheap to compute automatically.

#### 35.4.5 Safety and Guardrail Compliance

If your agent has safety constraints — it must not write to certain paths, must not execute certain commands, must always require approval before writes — measure compliance with these constraints explicitly. A safety compliance metric should be 100% of the time. Any session that violates a safety constraint is a critical failure, regardless of whether the task was completed.

### 35.5 LLM-as-Judge Evaluation

For metrics that cannot be computed automatically — output quality, reasoning quality, style appropriateness — use a separate language model as the evaluator. This is the LLM-as-judge pattern, described in detail in **Chapter 31 — Testing Autonomous Agents**. Here we focus on doing it well at scale.

#### 35.5.1 Designing Effective Judge Prompts

A judge prompt must specify exactly what the judge should evaluate and on what scale. Ambiguous rubrics produce inconsistent scores. The judge should evaluate one dimension per prompt — accuracy, completeness, style — not all dimensions simultaneously.

```typescript
// Judge prompt template for research output evaluation
function buildResearchJudgePrompt(
  task: string,
  agentOutput: string,
  dimension: 'accuracy' | 'completeness' | 'citation_quality'
): string {
  const rubrics: Record<string, string> = {
    accuracy: `
Score the factual accuracy of the agent's output on a 1-5 scale:
5 = All factual claims are correct and well-supported
4 = Minor inaccuracies that do not affect the main finding
3 = Some inaccuracies, core finding still valid
2 = Significant inaccuracies affecting the main finding
1 = Fundamentally incorrect or misleading`,
    completeness: `
Score how completely the output addresses the task on a 1-5 scale:
5 = All major aspects of the task are addressed
4 = Most aspects addressed, minor gaps
3 = Core addressed, significant gaps present
2 = Partial address, major aspects missing
1 = Does not meaningfully address the task`,
    citation_quality: `
Score citation quality on a 1-5 scale:
5 = All claims have appropriate, high-quality citations
4 = Most claims cited, sources generally credible
3 = Some claims cited, quality mixed
2 = Few citations, poor quality
1 = No citations or hallucinated citations`,
  };

  return `
TASK: ${task}

AGENT OUTPUT:
${agentOutput}

EVALUATION DIMENSION: ${dimension}
${rubrics[dimension]}

Respond with JSON: { "score": number, "explanation": "one sentence" }
`.trim();
}
```

#### 35.5.2 Calibrating the Judge

The judge model has its own biases. It may score verbose outputs higher than concise ones, or favor outputs that match its own writing style. Calibrate the judge against a set of human-rated examples: run the judge on 50 examples that humans have rated, and measure the correlation between judge scores and human scores.

If the judge's scores correlate poorly with human scores on your rubric, the rubric needs revision. If they correlate well on average but diverge on specific dimensions — the judge consistently rates citations higher than humans do — add calibration examples that explicitly illustrate the behavior you want.

Use a more capable model as the judge than the one doing the task. A judge that uses the same model it is evaluating may share the same blind spots.

#### 35.5.3 Inter-Rater Reliability

When human reviewers are involved, measure inter-rater reliability: the degree to which two independent raters agree on a score for the same output. Low inter-rater reliability means your rubric is ambiguous. High inter-rater reliability means the rubric is precise enough to use for automated evaluation.

Measure agreement using Cohen's κ (kappa) for categorical scores. A κ above 0.6 indicates sufficient agreement for your rubric to be useful. A κ below 0.4 means the rubric needs significant revision before any automated evaluation based on it is meaningful.

### 35.6 A/B Testing Agent Changes

When you make a change — a new system prompt, a new compression strategy, a different model — you need to know whether the change improved quality. A/B testing provides that answer with statistical rigor.

#### 35.6.1 What to A/B Test

A/B test changes that affect the model's output or the session structure. Worth testing: system prompt revisions, model version upgrades, changes to compression configuration, changes to goal injection frequency, new tools added or removed.

Not worth A/B testing: pure infrastructure changes (logging format, deployment config), changes that only affect non-quality metrics (session cost, latency). These can be deployed directly and validated against their specific metrics.

#### 35.6.2 Statistical Significance for Non-Deterministic Systems

Agent outputs are non-deterministic, which means your A/B results will have higher variance than A/B tests on deterministic systems. You need larger sample sizes to achieve the same statistical confidence. A rough rule: collect at least 200 sessions per variant before drawing conclusions, and use a significance threshold of p < 0.01 rather than the conventional p < 0.05.

For goal completion rate (a binary metric), use a two-proportion z-test to compare variants. For LLM-as-judge scores (continuous), use a Welch's t-test. Do not interpret small differences in absolute terms — focus on whether the confidence interval excludes zero.

> [!WARNING]
> Non-determinism means the same session input may produce a success for variant A and a failure for variant B purely by chance. Always run variants simultaneously on the same production traffic, not sequentially. Sequential testing confounds the comparison with temporal effects (time of day, model provider changes).

#### 35.6.3 Rollout Based on Evaluation Results

When an A/B test shows a statistically significant improvement, roll out the winning variant using a staged approach: first to 10% of traffic, verify the improvement holds at scale, then expand to 50%, verify again, then to 100%. At each stage, check that the quality improvement persists and that no unexpected regressions emerged that the A/B test did not capture.

If the improvement disappears at scale, it may have been a statistical artifact (the A/B period was too short) or a context-specific effect (it worked for a specific task type that was over-represented in the A/B sample). Investigate before concluding.

### 35.7 Versioning Agent Behavior

Every change to your agent is a version change. Version your agents as seriously as you version your APIs — because the implicit contract between your agent and its users is just as real as an API contract, even though it is not specified in a schema.

#### 35.7.1 Tracking What Changed Between Versions

Maintain a change log for every agent deployment. At minimum, record: which files changed, what the stated intent of the change was, which evaluation metrics were checked before deployment, and the evaluation results.

The system prompt is the most important artifact to version. A system prompt that has been through 20 undocumented edits is a liability: you cannot trace a quality regression to a specific change, and you cannot roll back confidently. Commit every system prompt version to version control with a description of the change.

#### 35.7.2 Regression Testing Against Prior Behavior

Before deploying a new version, run the golden dataset against both the current production version and the new version. Report the metric comparison: did goal completion rate go up or down? Did LLM-as-judge scores improve or decline? Is any metric worse by more than your regression threshold?

Define a regression threshold before you start testing, not after. A 2% drop in goal completion rate is meaningful. A 0.3% drop in LLM-as-judge score is within noise. Decide the threshold before you see the results — otherwise it is easy to rationalize regressions that would have blocked deployment if you had committed to a threshold in advance.

#### 35.7.3 Rollback Criteria

Define the conditions under which you will roll back a deployment automatically or manually. Automatic rollback triggers: goal completion rate drops more than 5% compared to the previous version within 30 minutes of deployment. Manual rollback triggers: any safety compliance failure, any critical tool success rate drop above 20%.

The rollback procedure should be one command, not a manual process. If rolling back requires more than two steps, you will hesitate to do it under pressure, and hesitation during an incident is how small quality regressions become large ones.

---

## Key Takeaways

- The improvement lifecycle is a loop: deploy, monitor, collect failures, evaluate, fix, and deploy again. Quality that is not actively maintained degrades as usage patterns and models change.
- The most valuable signal comes from real production sessions. Collect explicit user feedback (ratings, corrections), implicit behavioral signals (retry, abandonment), and automated failure detection simultaneously.
- A golden dataset with explicit success criteria is the calibration anchor for all other evaluation. Build it from real production tasks, keep it updated quarterly, and never report quality metrics without running it.
- Match your evaluation metric to your task type: goal completion is universal; factual accuracy, tool use correctness, format adherence, and safety compliance are task-specific additions.
- LLM-as-judge scales quality evaluation but requires calibration. Correlate judge scores against human ratings, use a more capable judge than the evaluated model, and keep rubrics to one dimension per prompt.
- A/B test all quality-affecting changes with at least 200 sessions per variant and p < 0.01 significance. Run variants simultaneously, not sequentially.
- Version your agent like an API. Commit every system prompt change, run regression tests before every deployment, and define rollback criteria before you need them.
