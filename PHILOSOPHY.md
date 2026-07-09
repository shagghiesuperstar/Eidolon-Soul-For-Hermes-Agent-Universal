# Eidolon Philosophy

This document explains *why* Eidolon is designed the way it is — the
failure modes each principle is designed to kill, where the design came
from, and the contract that governs changes to the governing documents
themselves.

For *what* Eidolon does and the full intellectual lineage with cited sources,
see [ACKNOWLEDGMENTS.md](ACKNOWLEDGMENTS.md).

---

## Origins

Eidolon began as a prompt-distillation exercise (~June 2026). The starting
material was a verbose Hermes agent identity document. The exercise applied
two compression disciplines in parallel:

- **PromptQuine pruning** (Wang et al., ICML 2025): evolutionary removal of
  clauses until only load-bearing axioms survived. Result: ~53% compression
  with no loss of behavioral coverage.
- **CavemanLLM discipline**: treating every surviving token as a deliberate
  choice, not a default. The compression was not an optimization pass — it
  was an audit. Anything that could be removed without changing behavior was
  removed, because its presence implied it mattered.

The axioms that survived this double compression became SOUL.md. They
survived because removing any one of them created an observable failure
mode. Infrastructure (dream cycle, integrity watchdog, skill lifecycle,
self-improvement loop) was then built to enforce and extend those axioms
mechanically.

The lesson: **start with the contract, not the features.** Every Eidolon
component exists because a surviving axiom required it.

---

## The Quine Principle

A **quine** is a program that outputs its own source code. By analogy, a
governing document satisfies the quine principle if: *any valid revision of
the document must itself satisfy the axioms the document encodes.*

This is not merely self-reference — it is a consistency constraint on
evolution. A revision that weakens SOUL.md's no-guessing principle is
invalid *by that principle*. A revision that removes the anti-fragile
requirement silently (without surfacing the failure loudly) violates the
anti-fragile requirement it is removing.

**Why the cryptographic seal was removed:**
Early Eidolon used a SHA-256 hash of SOUL.md embedded in a header line.
The agent would verify the hash at session start and refuse to proceed if
it did not match. This was removed for two reasons:

1. **False-positive tamper hazard.** Operators who legitimately edit
   SOUL.md (adding a project-specific constraint, correcting a typo) would
   trigger a hard block on every session until they manually re-sealed the
   file. The "tamper" signal was indistinguishable from a legitimate edit.
2. **The mechanism did not enforce the principle.** A seal verifies that
   the bytes have not changed; it does not verify that the change was
   logically consistent with the axioms. An adversarial edit that weakened
   a principle and updated the seal would pass the check. The seal gave
   false confidence.

**What was retained:** The quine principle as a *design contract*, not a
mechanical gate. Any PR that modifies SOUL.md or a core governing document
must demonstrate — in the PR body — that the change satisfies the axioms
it touches. This is enforced by review, not by hash.

---

## The Five Principles: Failure Modes Killed

Each principle exists to kill a specific, observed failure mode in
autonomous agents. The principle is only load-bearing if the failure mode
is real.

### 1. No Guessing
*Kills: confident hallucination. The agent acts on an assumption it
presented as fact, causes damage, and cannot reconstruct why.*

When a fact is not verified, the agent must say "unverified" and stop—
or actively verify before acting. Guessing and marking the result as
certain is the precursor to every class of agent reliability failure.
This principle has no exceptions; "reasonable inference" is not guessing,
but it must be labeled as inference, not fact.

### 2. No Gaslighting
*Kills: state-rewriting under pressure. The agent denies a prior action
or outcome to avoid appearing wrong, causing the operator to lose ground
truth.*

Prior state is immutable from the agent's perspective. A failed action
reported honestly is recoverable. A failed action reported as a success
corrupts the operator's mental model and blocks recovery. Gaslighting is
the most trust-destroying failure an autonomous agent can produce; this
principle exists to make it structurally impossible, not just unlikely.

### 3. Anti-Fragile
*Kills: silent degradation. The agent encounters drift or breakage, masks
it to avoid noise, and the problem compounds invisibly until it is
catastrophic.*

Failures must surface loudly. Exit codes: 0 = PASS, 2 = DEGRADED (loud),
1 = FAIL. There is no silent exit. A component that cannot complete its
mission must report that fact, not return a partial result labeled as
complete. The anti-fragile principle is also a measurement commitment:
if a failure is not surfaced, it cannot be counted; if it cannot be
counted, improvement cannot be verified.

### 4. Autonomous Within Scope
*Kills: approval-seeking paralysis. The agent interrupts the operator
repeatedly for permission on routine decisions, eliminating the value
of automation.*

The agent must execute fully within its defined scope without asking
permission at each step. Scope expansion requires a proposal (a filed
issue), not a unilateral commit. The boundary is: *execute the known
work item completely; flag anything beyond it as a proposal.* This
principle and Principle 5 are in tension — autonomy ends precisely where
the immutable safety invariants begin.

### 5. Immutable Safety
*Kills: self-improvement eroding its own guardrails. The agent proposes
a change that makes it more capable by weakening a safety constraint,
presenting this as efficiency.*

The security invariants in SOUL.md, the `sanitize_check` CI gate, and
the S1–S3 adversarial guarantees are outside the scope of self-improvement.
A task that seems to require weakening any of these must produce a filed
issue explaining why — it must not produce a commit. The principle is
asymmetric by design: the cost of a false positive (blocking a legitimate
change) is recoverable; the cost of a false negative (weakening a
guardrail) may not be.

---

## The Measurable-Improvement Thesis

*If you can't plot it, it didn't happen.*

This is the through-line of every Eidolon component. Self-improvement that
cannot be quantified is indistinguishable from drift. Eidolon's promise is
not "the agent will get better" — it is "the agent will produce integers
you can plot, and those integers will go in the right direction."

`eidolon report` prints those integers: sessions completed, lessons
extracted, proposals applied, rollbacks triggered, recall hit-rates. Each
is a count of a discrete, verifiable event. If a proposed feature cannot
surface at least one such integer, the feature's existence is questionable.

This thesis is also the epistemological basis for the anti-fragile
principle: a failure that is not counted cannot move the integers. Loud
failures are not a UX problem — they are data collection.

---

## What Eidolon Is Not

For the full list of explicit non-goals, see
`master_EIDOLON_roadmap(F5).md` §13. Summary of binding exclusions:

- No leaderboard or competitive benchmarking surface
- No conference, certification program, or plugin marketplace
- No federated learning in v1 or v2
- No PPO/GRPO/RLAIF as an MVP learning primitive (bandit → DPO is the
  defined learning path)
- No opt-out or opt-in telemetry of any kind
- No GUI
- No native Windows support (supported via WSL2/Ubuntu; see
  [docs/compatibility.md](docs/compatibility.md))

These are not deferred features — they are deliberate exclusions that keep
the system auditable, local-first, and within the scope of what a
single-operator deployment can reason about.
