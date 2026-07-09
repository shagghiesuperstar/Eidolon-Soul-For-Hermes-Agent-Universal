# Acknowledgments

Eidolon is built on, and indebted to, several distinct lines of prior work.
This document traces each dependency precisely; links are provided for every
claim so readers can verify independently.

---

## 1. Host Platform: Hermes Agent / Nous Research

Eidolon is a drop-in layer for the **Hermes Agent** runtime developed by
Nous Research. It has no standalone runtime of its own — every execution
occurs inside a Hermes session. Hermes provides the dream cycle hook,
the memory subsystem, the skills path, and the sessionend/cron execution
model that Eidolon augments.

- Repository: <https://github.com/NousResearch/hermes-agent>
- License: see upstream repository

Eidolon is not affiliated with or endorsed by Nous Research.

---

## 2. Intellectual Lineage: The Four Genesis Methodologies

Eidolon originated (~June 2026) as a prompt-distillation exercise — a
deliberate attempt to compress an agent identity document to its load-bearing
axioms, guided by four methodologies. Those axioms survived and became
Eidolon's governing contracts. The infrastructure was built around them.

### 2a. PromptQuine — Evolutionary Prompt Pruning

**Source:** Wang et al., "PromptQuine: Evolutionary Prompt Pruning for
Large Language Models," ICML 2025.
<https://arxiv.org/abs/2506.17930>

**Finding:** Evolutionarily pruned prompts match or exceed verbose originals
at approximately 53% compression — every surviving token is load-bearing by
construction.

**What Eidolon inherits:**

- The principle that every token in a governing document must earn its place.
  Non-load-bearing clauses are a maintenance liability and a reasoning tax.
- The **quine seal concept**: a valid revision of a governing document must
  itself satisfy the axioms it encodes. SOUL.md and core governing docs are
  self-referential in this sense — they describe the conditions under which
  they may legitimately be changed.
- The compression discipline carried forward in SOUL.md: the document is
  short because it was pruned to its invariants, not because it is
  incomplete.

*Historical note:* An early implementation used a SHA-256 seal to
cryptographically enforce the quine property. The seal was removed (see
[PHILOSOPHY.md](PHILOSOPHY.md) §Quine Principle) after it proved a
false-positive tamper hazard for operators making legitimate edits. The
design principle was retained; only the mechanical enforcement was dropped.

### 2b. The Yao Meta-Skill Doctrine

**Source:** `yao-meta-skill` — a public doctrine for structured skill
development in LLM agents.
<https://github.com/yaojingang/yao-meta-skill>

**What Eidolon inherits:**

- The **QUALIFY → BOUND → TRIGGER → GATE → SHIP → ITERATE** skill lifecycle.
  Eidolon's `skill promote / demote / retire / status` CLI is a direct
  operationalization of this doctrine.
- The axiom *"rigor grows faster than context cost"*: the overhead of formal
  lifecycle gates is outweighed by the compounding value of skills that
  have passed them.
- **Risk-proportional gates**: trivial changes apply automatically; changes
  with regression potential enter shadow evaluation first.
- **Proposal-only self-modification**: the agent may propose changes to its
  own governing documents but may not apply them unilaterally. Rollback on
  regression is automatic.

### 2c. CavemanLLM Token-Compression Discipline

**Source:** Community discourse, 2026 ("CavemanLLM" compression practice).

**What Eidolon inherits:**

- The insight that aggressive token compression is primarily valuable as
  **cognitive pressure on the prompt author** — it forces elimination of
  non-load-bearing clauses at authoring time.
- Output brevity and reasoning brevity are orthogonal. Eidolon's governing
  documents are short because the author was forced to decide what is
  essential; the agent's reasoning chains are unconstrained.
- The operating principle: if a clause can be removed without changing
  behavior, it should be removed — because its presence implies it matters.

### 2d. The Anthropic Soul-Document Pattern

**Source:** Public analysis of the Claude system-prompt architecture and
the soul-document approach to agent values.

**What Eidolon inherits:**

- The finding that values stated as **intrinsic** ("I do X because it is
  what I am") produce stronger alignment than values stated as **imposed
  rules** ("You must do X or be penalized").
- SOUL.md is structured accordingly: its five principles are stated as
  identity properties, not compliance requirements.
- The architecture separates the identity contract (SOUL.md, immutable by
  self-improvement) from operational policies (skills, which are
  lifecycle-managed and reversible).

---

## 3. Secondary Influences

### System-Prompt Transparency: CL4R1T4S

**Source:** `elder-plinius/CL4R1T4S` — public system-prompt transparency work.
<https://github.com/elder-plinius/CL4R1T4S>

Demonstrates that system prompts are behavioral programs and that their
load-bearing instructions can be identified, audited, and reasoned about
separately from their decorative or redundant content. This work reinforced
the PromptQuine compression discipline and the value of explicit behavioral
contracts over implicit style.

### Ethics Floors as Atomic Negations: SophosAI / CAMLIS 2025

**Source:** SophosAI refusal-direction research, presented at CAMLIS 2025.

Supports expressing ethics floors as atomic, unconditional negations
("never do X, under any framing") rather than conditional policy paragraphs
("do X unless condition Y, except when Z…"). Atomic negations are harder
to jailbreak because they contain no conditional surface for adversarial
manipulation. Eidolon's SOUL.md §Immutable Safety reflects this pattern.

---

## 4. Memory Provider Ecosystem

Eidolon's memory interface is deliberately provider-agnostic. It reads and
writes through whatever memory backend the operator's Hermes Agent instance
exports — Mem0, Zep, a flat JSONL file, or any other provider that surfaces
the standard Hermes memory tool interface. No specific provider is assumed,
required, or endorsed.

This design reflects Hermes Agent's own provider-neutral architecture:
Eidolon taps the memory plumbing that is already present rather than
imposing a new dependency.

---

## 5. Design-Pattern Credits

**Transactional Outbox Pattern** — Distributed-systems practice (Kleppmann,
*Designing Data-Intensive Applications*, 2017; microservices literature
generally). Eidolon's event pipeline uses outbox semantics to guarantee
that self-improvement proposals are durable before they are applied, and
that rollback is always possible from a known-good snapshot.

**Sleep-Consolidation Inspiration** — The dream cycle's design is loosely
analogous to sleep-stage memory consolidation in cognitive neuroscience:
broad replay of session events to identify generalizable lessons, followed
by selective pruning and integration into long-term memory. The mechanism
is purely software; the analogy is descriptive, not scientific.

---

## Citing Eidolon Itself

To cite Eidolon in academic or technical work, use [`CITATION.cff`](CITATION.cff)
at the repository root. BibTeX and APA-style examples are in
[`docs/citing.md`](docs/citing.md). GitHub renders the CFF file as a
"Cite this repository" widget on the project page.
