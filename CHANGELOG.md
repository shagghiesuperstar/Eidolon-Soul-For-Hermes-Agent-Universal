# Changelog

All notable changes to this project will be documented in this file.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning: [SemVer](https://semver.org/).

## [Unreleased]

### Added
- **REC-021** — Dream write path now routes lesson and proposal writes through
  the transactional outbox (`Outbox.capture` + `Outbox.flush`) instead of
  calling `adapter.store` directly. Entries survive a mid-cycle crash in
  `$EIDOLON_HOME/outbox/pending.jsonl` and are retried on the next run.
  On flush failure the cycle emits `DEGRADED` and continues — it never
  hard-fails. Falls back to direct `adapter.store` on installs where the
  eidolon package is not importable.

## [0.5.0] — 2025-07-09

### Added
- **REC-020** — MemoryAdapter wiring: `ingest`, `reflect`, `extract_lessons`,
  and `propose` now read from and write to the live adapter loaded by
  `eidolon.memory.loader.load_adapter()`. Adapter selection reads
  `$HERMES_HOME/config.yaml`; falls back to `hindsight` → `inmem`.

## [0.4.0] — 2025-07-07

### Added
- **REC-019** — Transactional outbox (`src/eidolon/outbox.py`): crash-safe
  capture + idempotent flush for all memory writes.
  `Outbox.capture` appends to `pending.jsonl`; `Outbox.flush` drains to the
  adapter atomically and retains failed entries for retry.

## [0.3.0] — 2025-06-30

### Added
- **REC-017** — Shadow evaluation scaffold for MEDIUM-risk proposals.
- **REC-018** — Preference-bandit stub wired into the dream cycle.

## [0.2.0] — 2025-06-20

### Added
- **REC-010** — 5-class risk classification (`RiskClass`) in `eidolon.safety`.
- **REC-011** — `gate_and_apply` policy: LOW auto-applies; MEDIUM defers;
  HIGH and NEVER_TOUCH audit-log and refuse.

## [0.1.0] — 2025-06-10

### Added
- Initial Eidolon skeleton: dream-cycle handler, integrity watchdog, SOUL.md
  invariant contract, `eidolon report` CLI stub.
- **REC-003** — Structured event emission to `$EIDOLON_HOME/events.jsonl`.
- **REC-004** — First-run snapshot (`eidolon.safety.take_snapshot`).
