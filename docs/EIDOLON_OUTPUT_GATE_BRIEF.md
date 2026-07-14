# EIDOLON OUTPUT GATE — Frontier Council Brief
## REC-022: Design the file-mutation output gate that proves self-improvement

**For:** Perplexity Model Council (Opus-class + GitHub connector)
**Repo:** `shagghiesuperstar/Eidolon-Soul-For-Hermes-Agent-Universal`
**Branch:** `main` @ `71fbc84`
**Dashboard:** Live at `docs/dashboard.html` (polls MCP, stores 24h trends in localStorage)

---

## 0. EXECUTIVE SUMMARY — The Problem in One Dashboard Snapshot

```
TIER 1: Mutations over time
  skills_modified:  0  ← flat line, forever
  soul_edicts:     28  ← only non-zero mutation type
  memory_retired:   0
  config_changes:   0
  skills_staged:    0

Proposal gap
  proposals_generated: 25  ← ideas are born
  proposals_applied:    0  ← none ever ship

Inbox depth: 279 ↑  ← growing, not draining
```

**The dashboard is honest.** It correctly shows that Eidolon's ingest→reflect→extract→propose pipeline works perfectly (100% dream reliability, 341 lessons extracted), but the **output gate** produces zero file-level mutations. The machine thinks but doesn't act.

---

## 1. THE FULL PIPELINE — What Exists Today

### 1.1 Ingest → Reflect → Extract → Propose (WORKS)

```
skills/dream-cycle/handler.py  (724 lines)
  main() → ingest() → reflect() → extract_lessons() → propose() → gate_and_apply()
```

**Real numbers from Trinity canary (July 14, 2026):**
- `sessions_observed: 25`
- `lessons_extracted: 341`
- `lessons_judged: 62`
- `proposals_generated: 25`
- `proposals_applied: 0`

The dream cycle ingests from the MemoryAdapter (Hindsight on Trinity), clusters episodes into patterns by `kind`, synthesizes one lesson per pattern, and generates one candidate proposal per lesson. All of this works. 200+ dream cycles, 100% success rate.

### 1.2 The Gate (EXISTS BUT NARROW)

```
skills/dream-cycle/handler.py:574  gate_and_apply()
```

Five risk levels with current behavior:

| Risk | Count (last cycle) | Action |
|------|-------------------|--------|
| LOW | 4 candidates | → `apply_low()` |
| MEDIUM | 0 | → deferred "shadow eval not yet implemented" |
| HIGH | 0 | → audited, refused |
| NEVER_TOUCH | 0 | → audited, refused |
| NO_OP | 0 | → skipped |

All 4 candidates from the last cycle classified as LOW and entered `apply_low()`.

### 1.3 apply_low() → hermes_bridge → Judgment Brain (FIRES BUT ROUTES TO SOFT MEMORY)

```
skills/dream-cycle/handler.py:472  apply_low()
  → src/eidolon/hermes_bridge.py:99  promote_lesson_to_hermes()
    → src/eidolon/judgment/classifier.py:99  classify_lesson()
    → src/eidolon/judgment/executor.py:236  execute_judgment()
    → src/eidolon/judgment/metrics.py       record_judgment()
```

The judgment brain IS wired and DOES fire. Every lesson passing through `apply_low()` is classified into one of five `ActionKind` values:

```python
# src/eidolon/judgment/classifier.py:25-29
class ActionKind(enum.Enum):
    MEMORY_RETAIN = "memory_retain"   # keep in MEMORY.md, no file write
    SKILL_UPDATE  = "skill_update"    # write to skills/_eidolon_staging/
    SOUL_EDICT    = "soul_edict"      # append to SOUL.md EIDOLON EDICTS
    CONFIG_TUNE   = "config_tune"     # write to memories/eidolon-prefs.md
    MEMORY_RETIRE = "memory_retire"   # remove from MEMORY.md (baked elsewhere)
```

The classifier uses regex signal matching (lines 33-91 of `classifier.py`):

```python
_SOUL_SIGNALS = [
    r"\bnever fabricate\b", r"\bnever assume\b", r"\bnever guess\b",
    r"\binvariant\b", r"\boperating rule\b", r"\bcore principle\b",
    r"\bidentity\b.{0,30}\brule\b",
]

_SKILL_SIGNALS = [
    r"\bprobe\b", r"\bskill\b", r"\btool\b.{0,40}\buse\b",
    r"\bwhen.{0,60}\bcommand\b", r"\bwhen.{0,60}\bterminal\b",
    r"\brun the (real |actual )?command\b", r"\bpaste (evidence|output|result)\b",
    r"\bprobe (before|first|not assume)\b", r"\bdebugging pattern\b",
    r"\bworkflow\b", r"\bstep[- ]by[- ]step\b", r"\bprocedure\b", r"\bprotocol\b",
]

_CONFIG_SIGNALS = [
    r"\bformat\b", r"\bresponse (style|length|tone)\b",
    r"\bprefer.{0,50}(table|bullet|list|concis|brief|terse)\b",
    r"\bconfig\b", r"\bsetting\b", r"\btuning\b", r"\boptimiz\b",
]

_RETIRE_SIGNALS = [
    r"\bimplemented\b", r"\bcodified\b", r"\bwired\b.{0,30}(in|into|up)\b",
    r"\bproven\b", r"\bno longer needed\b", r"\bbaked in\b",
]
```

If no signal matches → `MEMORY_RETAIN, "no_signal"` (default fallthrough).

### 1.4 execute_judgment() — File Writes EXIST for Every ActionKind

```python
# src/eidolon/judgment/executor.py:236
ActionKind.SOUL_EDICT    → _write_soul_edict()      → appends to SOUL.md
ActionKind.SKILL_UPDATE  → _write_skill_update()    → writes to skills/_eidolon_staging/eidolon-learned.md
ActionKind.CONFIG_TUNE   → _write_config_tune()     → writes to memories/eidolon-prefs.md
ActionKind.MEMORY_RETIRE → _retire_memory_line()    → removes line from MEMORY.md
ActionKind.MEMORY_RETAIN → no-op                     → lesson stays in MEMORY.md only
```

All file writes are atomic (write-tmp + os.replace). SKILL_UPDATE writes to a STAGING directory (`skills/_eidolon_staging/`), never directly to live skills. This is intentional — the staging area is a safety gate before promotion.

### 1.5 The Dashboard Metrics Counter

The `proposals_applied` dashboard counter comes from `eidolon report --json`, which reads `$EIDOLON_HOME/events.jsonl`. The counter is incremented by:

```python
# skills/dream-cycle/handler.py:514
_law_of_done_after_skill_update(lesson_text, bridge_status, bridge_detail)
```

This function only fires after a REAL skill update staging write. It does NOT increment for MEMORY_RETAIN (no-op) or hermes_bridge "skipped" (duplicate). **This is correct behavior** — the dashboard should not lie. But the classifier routes everything to MEMORY_RETAIN, so the counter stays at 0.

### 1.6 The Real Bottleneck — TWO Independent Problems

**Problem A: The dream cycle's lessons are structurally narrow.**

From the last cycle:
```
Pattern 'lesson' observed 200 time(s). Most recent: CANARY: operator wants measurable learning not vibes
Pattern 'preference' observed 1 time(s). Most recent: CANARY: prefer evidence tables
Pattern 'reflection' observed 1 time(s). Most recent: CANARY: silent no-ops hide failures
Pattern 'episode' observed 3 time(s). Most recent: CANARY: operator wants measurable learning not vibes
```

These 4 clusters produce 4 proposals per cycle — all with `mutation_kind: "preference_update"` and lesson text like:

> "Pattern 'lesson' observed 200 time(s). Most recent: CANARY: operator wants measurable learning not vibes"

The classifier evaluates this text against the regex signal lists. "CANARY: operator wants measurable learning not vibes" contains none of the _SOUL_SIGNALS (no "invariant", "never assume", etc.), none of the _SKILL_SIGNALS (no "probe", "step-by-step", "run the command"), none of the _CONFIG_SIGNALS (no "format", "config", "prefer tables"). It falls to `MEMORY_RETAIN, "no_signal"`.

The hermes_bridge writes it to MEMORY.md. Next cycle: same pattern → `"reason": "duplicate"` → skipped.

**Problem B: Even if the classifier routed to SKILL_UPDATE, the skill write goes to staging.**

`_write_skill_update()` writes to `skills/_eidolon_staging/eidolon-learned.md` — a staging file Hermes doesn't load. For the skill to take effect, it needs promotion to an actual skill file. The promotion pipeline (`skill_cli.py`, `test_skill_cli.py`, `src/eidolon/commands/skill_cli.py`) exists but requires shadow evaluation (REC-017) which isn't implemented yet for MEDIUM risk. Skills in staging are "parked" — they exist on disk but don't affect Hermes behavior.

---

## 2. THE QUESTION — What Should the Output Gate Actually Do?

The dashboard's headline chart — **Mutations over Time** — is the only non-vibes proof that Hermes is self-improving. A mutation is a file change Hermes loads in its next session. Today the chart is flat because:

1. The classifier routes most lessons to `MEMORY_RETAIN` (soft memory, not a mutation)
2. `MEMORY_RETAIN` is a no-op in the executor — the lesson stays in MEMORY.md
3. Even lessons that DO route to SKILL_UPDATE land in staging, not live skills
4. The `proposals_applied` counter correctly doesn't increment for no-ops or duplicates

**The frontier council must answer:**

### 2.1 Classification — When is a lesson a mutation?

Current state: 341 lessons → 4 pattern clusters → all route to MEMORY_RETAIN → 0 mutations.

Should the output gate:
- (a) Relax the classifier regexes to catch more signal? (risk: false positives)
- (b) Add a "novelty threshold" — if the same pattern cluster appears N times without being actioned, escalate it to a higher action kind?
- (c) Route pattern observations with high counts (e.g., "observed 200 time(s)") to SOUL_EDICT or SKILL_UPDATE based on count alone?
- (d) Add a new ActionKind — `PATTERN_ALERT` — that fires when a pattern crosses a frequency threshold, writing to a different surface?
- (e) Something else entirely?

### 2.2 Thresholds — When does proposals_applied tick up?

Current state: `proposals_applied: 0` even though `proposals_generated: 25` and `lessons_judged: 62`. The counter is correct — no file was mutated.

Should `proposals_applied` increment for:
- (a) ONLY real file writes (skill file created/modified, SOUL.md edict appended, config changed)?
- (b) Any non-duplicate lesson landing in MEMORY.md (soft count)?
- (c) Any lesson that passes the judgment brain (even MEMORY_RETAIN)?
- (d) A graduated system: `lessons_retained` for MEMORY.md writes, `proposals_applied` for file mutations, with both shown on the dashboard?

### 2.3 Staging → Promotion — How do skills escape staging?

Current state: `_write_skill_update()` writes to `skills/_eidolon_staging/eidolon-learned.md`. Hermes doesn't load files from `_eidolon_staging/`. The `eidolon skill promote` CLI exists but requires shadow evaluation (REC-017) which defers with "not yet implemented."

Should Eidolon:
- (a) Write SKILL_UPDATE directly to a live skill file (bypassing staging)?
- (b) Keep staging but auto-promote after N successful shadow evaluations?
- (c) Keep staging and require operator approval for promotion?
- (d) Write to `skills/_eidolon_staging/` AND add a symlink or reference so Hermes loads it?

### 2.4 Proactive Transparency — How does the user know?

Current state: The dashboard shows `proposals_applied: 0`. The daily report says "Hindsight: NOT reachable" (false positive, fixed July 14). The weekly audit has agent answer templates but they're never filled in because the pipeline stops at MEMORY_RETAIN.

The user's requirement: **"self-improving on a level that is both differentiated from Hermes Agent's own built-in self-improvement mechanisms and better than those, and measurably/demonstrably so (via the human dashboard)."**

What should the output gate emit to the user when it acts? A Telegram message? A dashboard notification? A new section in the daily report? What does "proactive, transparent to user" look like in practice?

---

## 3. DESIGN CONSTRAINTS (Binding)

### 3.1 From master_EIDOLON_roadmap(F5).md §13 NON-GOALS:
- ❌ No GUI (dashboard is the exception — single HTML file, no framework)
- ❌ No PPO/GRPO/RLAIF as MVP (bandit→DPO only)
- ❌ No telemetry
- ❌ No federated learning in v1/v2
- ❌ Never hardcode any inference engine as a first-class dependency

### 3.2 From SOUL.md security invariants:
- ❌ Never modify SOUL.md above the EIDOLON EDICTS marker
- ❌ Never touch skills the operator curates (protected list)
- ❌ NEVER_TOUCH paths (config.yaml, LICENSE, NOTICE, last_known_good snapshots)
- ✅ All writes are atomic (tmp + os.replace)
- ✅ All writes are append-only or targeted replace; never rewrite whole files

### 3.3 From the operator:
- "Speed/execution > perfection"
- "Measurable Hermes Agent improvement" is the north star
- "Deterministic skill/SOUL/allowlisted-config changes" are the only valid mutations
- Dashboard must show trend analysis — "show me in a graph, don't just say trust me bro"
- Self-improvement must be differentiated from and better than Hermes' native mechanisms
- Proactive transparency — user should know when Eidolon acts, not discover it later

### 3.4 Architecture constraints:
- All code is stdlib-only or uses existing eidolon package imports
- MCP server binds 127.0.0.1 only, serves 4 tools
- Memory backend is provider-agnostic (Hindsight, Mem0, Byterover, inmem)
- Dream cycle runs hourly via cron, sessionend via hook
- All handlers exit 0 on success, 2 on DEGRADED, 1 on FAIL

---

## 4. RELEVANT FILES IN THE PUBLIC REPO

All paths relative to repo root:

| File | Lines | Role |
|------|-------|------|
| `skills/dream-cycle/handler.py` | 724 | Main dream pipeline (ingest→reflect→extract→propose→apply) |
| `src/eidolon/judgment/classifier.py` | 125 | Lesson-to-ActionKind classifier (regex signal matching) |
| `src/eidolon/judgment/executor.py` | 267 | File writes for each ActionKind (soul, skill, config, retire) |
| `src/eidolon/judgment/metrics.py` | 176 | Judgment counters (load/increment/record) |
| `src/eidolon/hermes_bridge.py` | 205 | MEMORY.md section writer + judgment brain integration |
| `src/eidolon/safety/risk.py` | 131 | 5-class risk classifier (LOW/MEDIUM/HIGH/NEVER_TOUCH/NO_OP) |
| `src/eidolon/safety/classifier.py` | 34 | Risk classification from mutation_kind |
| `src/eidolon/memory/adapter.py` | 120 | MemoryAdapter interface (store/retrieve/consolidate/mark_done) |
| `src/eidolon/memory/hindsight.py` | 243 | HindsightAdapter (append-only JSONL store) |
| `src/eidolon/outbox.py` | 184 | Transactional outbox (capture→flush with idempotency) |
| `docs/dashboard.html` | 23* | Self-contained dashboard (13.4KB minified, 9 metric sections) |
| `scripts/eidolon-nightly-monitor.py` | 653 | Hourly snapshot + daily/weekly report generator |
| `master_EIDOLON_roadmap(F5).md` | — | Authoritative work order (RECs 001-020, §13 NON-GOALS) |
| `SOUL.md` | — | Identity contract + security invariants |

---

## 5. DEFINITION OF DONE

### GATE 1: Classification fix
The classifier must route at least one non-trivial lesson from the dream cycle to `SKILL_UPDATE`, `SOUL_EDICT`, or `CONFIG_TUNE` within 24 hours of deployment on the canary. Evidence: `eidolon report --json` shows `proposals_applied > 0` after at least one dream cycle.

### GATE 2: File mutation occurs
At least one file write must land in a surface Hermes loads (MEMORY.md, SOUL.md, a skill file, or memories/). Evidence: `ls -la` the file, paste the written content.

### GATE 3: Dashboard reflects the change
The TIER 1 mutations chart must show a non-zero data point for at least one mutation type. Evidence: screenshot of dashboard or `eidolon report --json | jq '.skills_modified, .soul_edicts, .memory_retired, .config_changes'`.

### GATE 4: No regressions
- `PYTHONPATH=src python -m unittest discover -s tests/unit` → OK (407 tests)
- `python tests/adversarial.py` → 7/7 PASS
- `python scripts/sanitize_check.py` → clean

### GATE 5: The inbox drains
After the fix, the inbox depth trend on the dashboard should oscillate (spike then drain) rather than only climbing. Evidence: dashboard shows `↓` arrow on at least one poll cycle.

### GATE 6: Documentation
Update `CHANGELOG.md` Unreleased section with the REC number and one-line description. Update `docs/judgment-brain.md` if the classifier logic changes.

---

## 6. HOW TO VERIFY EMPIRICALLY

After deploying to the canary (Trinity), run:

```bash
# 1. Force a dream cycle
PYTHONPATH=src python skills/dream-cycle/handler.py --mode scheduled

# 2. Check what changed
eidolon report --json | python3 -c "import json,sys; d=json.load(sys.stdin);
print(f'skills_modified: {d[\"skills_modified\"]}');
print(f'soul_edicts: {d[\"soul_edicts\"]}');
print(f'proposals_applied: {d[\"proposals_applied\"]}')"

# 3. Check which files were written
ls -la ~/.hermes/skills/_eidolon_staging/
grep -c "EIDOLON EDICTS" ~/.hermes/SOUL.md
wc -l ~/.hermes/memories/MEMORY.md

# 4. Check the dashboard
open http://localhost:8000/docs/dashboard.html
```

---

**This brief contains every observable, file path, line number, metric value, and design constraint the council needs. The repo is live. The dashboard is live. The canary is Trinity (m4mbp). The output gate is the last piece between a thinking machine and a self-improving one.**
