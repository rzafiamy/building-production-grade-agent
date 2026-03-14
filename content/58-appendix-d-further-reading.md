---
title: "Appendix D — Further Reading and Resources"
page: 58
status: draft
---

## Appendix D — Further Reading and Resources

*Curated resources for going deeper on the topics covered in this book.*
*No URLs — resources are cited by name and author for durability.*

---

### Foundational Papers

**ReAct: Synergizing Reasoning and Acting in Language Models**
*Yao et al., 2022*
The original paper introducing the ReAct framework. Essential reading.

**Toolformer: Language Models Can Teach Themselves to Use Tools**
*Schick et al., 2023*
Early work on tool-augmented language models.

**Tree of Thoughts: Deliberate Problem Solving with Large Language Models**
*Yao et al., 2023*
Extends ReAct with tree-structured exploration.

**Chain-of-Thought Prompting Elicits Reasoning in Large Language Models**
*Wei et al., 2022*
The CoT paper that helped enable ReAct.

---

### Agent Architecture

**The Model Context Protocol Specification**
*Anthropic, 2024*
The authoritative MCP spec.

**Cognitive Architectures for Language Agents**
*Sumers et al., 2023*
Survey of agent architectures and their trade-offs.

---

### Production and Reliability

**Site Reliability Engineering** (book)
*Beyer, Jones, Petoff, Murphy — Google*
The SRE bible. Applies with modifications to agent systems.

**Designing Data-Intensive Applications** (book)
*Martin Kleppmann*
Essential for understanding the data consistency challenges in agent state management.

---

### Security

**OWASP Top 10 for Large Language Model Applications**
*OWASP, 2023–2024*
The standard reference for LLM security vulnerabilities.

**Prompt Injection Attacks and Defenses**
*Various papers, 2023–2025*
Search for this topic on arXiv for the latest research.

---

### Evaluation

**HELM: Holistic Evaluation of Language Models**
*Liang et al., Stanford CRFM*
Comprehensive evaluation framework and methodology.

**Chatbot Arena: An Open Platform for Evaluating LLMs**
*Zheng et al., 2023*
Human preference evaluation methodology.

---

### The Lemura Repository

The Lemura source code, examples, and tests are the best reference for
everything covered in Part III of this book. The `tests/` directory
contains practical examples of every concept discussed.
