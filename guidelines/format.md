# Format, Layout & Design Specification

*"The Autonomous Agent" — authoring reference for writers and tooling.*

---

## Overview

The book is authored in Markdown (CommonMark + GFM extensions). It must render
correctly in all four targets:

- GitHub / GitLab markdown viewers
- Static site generators (VitePress, Docusaurus, Nextra)
- PDF export via Pandoc or similar
- Print-on-demand after PDF export

Each page is one `.md` file. Files are named with a zero-padded numeric prefix
for natural sort order.

---

## File Naming Convention

Format: `{NN}-{slug}.md`

| Range | Section |
|-------|---------|
| `00–07` | Front matter (cover, title, copyright, dedication, foreword, preface, toc) |
| `08–12` | Part I chapters |
| `13–18` | Part II chapters |
| `19–28` | Part III chapters |
| `29–33` | Part IV chapters |
| `34–41` | Part V chapters |
| `42–48` | Part VI chapters |
| `49–53` | Part VII chapters |
| `54–60` | Back matter (appendices, glossary, bibliography, about) |

Slug must be lowercase, hyphen-separated, and match the chapter title closely.
Example: `16-ch08-planning-and-goals.md`.

---

## Typography

### Heading levels

| Level | Markdown | Usage |
|-------|----------|-------|
| H1 | `#` | Book title and part titles only. One per file maximum. |
| H2 | `##` | Chapter titles. One per chapter file. |
| H3 | `###` | Major section headings within a chapter. |
| H4 | `####` | Sub-sections. Use sparingly — maximum 3 per chapter. |
| H5–H6 | — | **Forbidden.** Never use. |

### Inline formatting

| Style | Markdown | When to use |
|-------|----------|-------------|
| *Italic* | `*text*` | Introducing a term for the first time; light stress. |
| **Bold** | `**text**` | Critical warnings; API names in prose; key terms. |
| `Code` | `` `text` `` | Class names, method names, file paths, config keys, any literal string. |

**Never use** underline, strikethrough, or superscript in body text.

---

## Code Blocks

All fenced code blocks must carry a language tag. No exceptions.

```typescript
// Configuring a session with sandwich compression
const session = await lemura.createSession({ compression: "sandwich" });
```

### Approved language tags

| Tag | Use for |
|-----|---------|
| `typescript` | All primary code examples (default) |
| `javascript` | JS-specific examples only |
| `bash` | Terminal commands and shell scripts |
| `json` | Configuration files, API payloads |
| `yaml` | YAML configuration |
| `text` | File paths, terminal output, ASCII diagrams |
| `pseudocode` | Framework-agnostic concepts — must be labeled clearly |

### TypeScript / JavaScript blocks

The first line must be a `//` comment describing what the block demonstrates:

```typescript
// Anti-pattern: storing full tool output in context without compression
const result = await tool.run(input);
context.push({ role: "tool", content: JSON.stringify(result) }); // ← unbounded
```

```typescript
// Better: compress tool output before adding to context
const result    = await tool.run(input);
const condensed = await compressor.summarize(result, { maxTokens: 200 });
context.push({ role: "tool", content: condensed });
```

### Inline code

Use single backticks. Keep inline code under 60 characters. For longer
expressions, prefer a full code block.

---

## Callout Boxes

Use GitHub Flavored Markdown alert syntax. Maximum **3 callouts per chapter**.
Never nest callouts. Keep body to 1–4 sentences.

```markdown
> [!NOTE]
> Supplementary information that enriches understanding.

> [!TIP]
> Non-obvious tricks or shortcuts that save time.

> [!WARNING]
> Common mistakes or patterns that cause bugs in production.

> [!DANGER]
> Security risks, data loss scenarios, irreversible operations.
```

| Type | Rendered as | When to use |
|------|-------------|-------------|
| `[!NOTE]` | Blue info box | Background or supplementary detail |
| `[!TIP]` | Green tip box | Shortcuts, non-obvious tricks |
| `[!WARNING]` | Yellow warning | Production pitfalls, common mistakes |
| `[!DANGER]` | Red danger box | Security risks, data loss, irreversible ops |

---

## Tables

Use GFM tables for structured reference content:

- Configuration keys (`key | type | default | description`)
- Comparison tables (`feature | approach A | approach B`)
- API quick-reference

Rules:
- Always include a header row with `---` separator.
- Align number columns right, text columns left.
- Keep cell content short — use prose paragraphs for explanation.

---

## Diagrams

Use ASCII art for all architecture and flow diagrams. Wrap in a `text` block.

```text
┌──────────────┐     tool call    ┌──────────────┐
│  LLM Engine  │ ──────────────▶  │  Tool Runner │
│              │ ◀──────────────  │              │
└──────────────┘     result       └──────────────┘
```

Preferred box-drawing characters: `┌ ┐ └ ┘ │ ─ ├ ┤ ┬ ┴ ┼ ▶ ◀ ↑ ↓`

These render correctly in all monospace fonts and in Pandoc PDF export.

---

## YAML Front Matter

Every `.md` file must begin with a YAML front matter block.

```yaml
---
title: "Chapter 8 — Planning and Goals: Directing the Agent"
part: "Part II — Architecture Fundamentals"
chapter: 8
page: 16
status: draft
---
```

| Field | Required for | Valid values |
|-------|-------------|--------------|
| `title` | All files | Exact chapter/page title string |
| `status` | All files | `draft` · `review` · `final` |
| `part` | Chapter files | Exact part label string |
| `chapter` | Chapter files | Integer |
| `page` | Chapter files | Integer matching the file's numeric prefix |

The `status` field gates the publish pipeline: only `final` pages are included
in the production PDF build.

---

## Chapter Page Structure

Every chapter file must follow this element order exactly:

1. YAML front matter
2. Part label in italic: `*PART III — LEMURA FRAMEWORK*`
3. Chapter title as H2: `## Chapter 12 — Installing and Configuring Lemura`
4. Epigraph *(optional)*: a short relevant quote in italic, in a blockquote
5. Chapter Goal callout — `> [!NOTE]` block containing "Chapter Goal:"
6. Horizontal rule `---`
7. Body sections: H3 → H4 → prose → code blocks
8. Horizontal rule `---`
9. Key Takeaways: `## Key Takeaways` followed by 3–7 bullet points
10. Further Reading *(optional)*: 1–3 named resources, no URLs

### Minimal chapter template

```markdown
---
title: "Chapter N — Title"
part: "Part X — Part Name"
chapter: N
page: NN
status: draft
---

*PART X — PART NAME*

## Chapter N — Title

> *"Epigraph quote here."*

> [!NOTE]
> **Chapter Goal:** By the end of this chapter, you will understand X,
> be able to do Y, and know when to apply Z.

---

### N.1 First Major Section

### N.2 Second Major Section

---

## Key Takeaways

- First key point, one sentence.
- Second key point, one sentence.
```

---

## Part Intro Page Structure

Part intro pages (`XX-part-N-intro.md`) use a distinct structure:

1. YAML front matter
2. Part number as H1: `# Part III`
3. Part title as H2: `## Lemura Framework Deep Dive`
4. Part overview: 2–4 paragraphs explaining what this part covers and why
5. Chapter list: a simple bullet list with one-line descriptions per chapter

---

## Front Matter Pages

| File | Purpose |
|------|---------|
| `00-cover.md` | Book cover — title, subtitle, author, version |
| `01-title-page.md` | Full title page with publisher info |
| `02-copyright.md` | Copyright notice, license, credits |
| `03-dedication.md` | Author's dedication |
| `04-foreword.md` | Foreword — contextual, written by a trusted voice |
| `05-preface.md` | Author's preface: motivation, audience, how to read |
| `06-introduction.md` | Book introduction |
| `07-toc.md` | Table of contents — links to all pages (**frozen**) |

---

## Back Matter Pages

| File | Purpose |
|------|---------|
| `55-appendix-a-api-reference.md` | Lemura full API reference |
| `56-appendix-b-config-reference.md` | `SessionConfig` key reference |
| `57-appendix-c-glossary.md` | Glossary of terms |
| `58-appendix-d-further-reading.md` | Further reading and resources |
| `59-bibliography.md` | Works cited and referenced |
| `60-about-author.md` | Author bio |

---

## Page Layout (Print / PDF Export)

| Property | Value |
|----------|-------|
| Page size | 6″ × 9″ (standard trade paperback) |
| Margins | 0.75″ all sides |
| Body font | Source Serif 4, 11pt |
| Code font | JetBrains Mono, 9pt |
| Heading font | Inter, 600 weight (H3/H4) · 700 weight (H1/H2) |
| Line height | 1.55 body · 1.3 code |
| Chapter title | 24pt (H2) |
| Section heading | 16pt (H3) |
| Sub-section | 13pt (H4) |

### Color palette

| Element | Print | Dark web |
|---------|-------|----------|
| Background | `#FFFFFF` | `#0F0F11` |
| Body text | `#1A1A1A` | `#E8E8E8` |
| Code background | `#F5F5F5` | `#1A1A2E` |
| Accent / headers | `#1A56DB` | `#1A56DB` |
| Note box bg / border | `#D1ECF1` / `#0C5460` | same |
| Tip box bg / border | `#D4EDDA` / `#155724` | same |
| Warning box bg / border | `#FFF3CD` / `#856404` | same |
| Danger box bg / border | `#F8D7DA` / `#721C24` | same |
