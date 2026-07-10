# Memory Backend Abstraction

> REC-018 · Priority P3 · Type architecture

Eidolon's memory subsystem is accessed exclusively through the `MemoryAdapter`
interface.  No component in `src/eidolon` reads Hermes memory files directly.
This decouples Eidolon from any specific Hermes memory plugin and lets the full
test suite run without a live Hermes host.

---

## Adapters

| Adapter | Name token | Persistence | Use case |
|---|---|---|---|
| `HindsightAdapter` | `hindsight` | `$EIDOLON_HOME/memory/hindsight.jsonl` | Production (default) |
| `InMemAdapter` | `inmem` | None (process-local) | CI, unit tests |

---

## Configuration

Set `memory.backend` in your Hermes config:

```yaml
# $HERMES_HOME/config.yaml
memory.backend: hindsight   # or: inmem
```

If the key is absent or the file is unreadable, Eidolon defaults to
`hindsight` and emits an INFO event.

If an unrecognised value is supplied, Eidolon degrades to `inmem` and emits a
DEGRADED event rather than raising.

---

## Doctor check

```bash
eidolon doctor --json | jq '.checks[] | select(.name=="memory_adapter_ready")'
```

| Status | Meaning |
|---|---|
| `PASS` | `HindsightAdapter` loaded and round-tripped cleanly |
| `DEGRADED` | Running `InMemAdapter` — no persistent store |
| `FAIL` | Memory package import or probe failed — broken install |

---

## Entry schema

Every entry stored through `MemoryAdapter.store()` must contain:

| Field | Type | Description |
|---|---|---|
| `kind` | `str` | Category: `lesson`, `preference`, `reflection` … |
| `content` | `str` | Sanitized, operator-visible text |
| `ts` | `float` | Epoch seconds — set automatically if absent |

Adapters may add fields.  The three above are always present after `store()`.

---

## Writing a custom adapter

```python
from eidolon.memory.adapter import MemoryAdapter, MemoryEntry, MemoryStoreError

class MyAdapter(MemoryAdapter):
    name = "my-adapter"

    def store(self, entry: MemoryEntry) -> None:
        self._validate_entry(entry)
        entry = self._stamp(entry)
        # ... write to your backend ...

    def retrieve(self, *, kind=None, limit=50, since_ts=None):
        # ... read from your backend; never raise ...
        return []

    def consolidate(self) -> int:
        # ... optional dedup logic ...
        return 0
```

Register it in `src/eidolon/memory/loader.py` by adding it to `_KNOWN` and
opening a PR to add it to the test matrix.

---

## Consolidation

`HindsightAdapter.consolidate()` removes exact-content duplicates within each
`kind`, keeping the newest entry.  Designed for nightly cron:

```bash
python -c "from eidolon.memory import load_adapter; print(load_adapter().consolidate(), 'entries removed')"
```

Consolidation emits an `INFO` event with the `removed` count regardless of
whether any duplicates were found.

---

## Events emitted

| kind | status | When |
|---|---|---|
| `memory.loader` | INFO | Backend selected from config (or default) |
| `memory.loader` | DEGRADED | Unknown backend configured; fell back to inmem |
| `memory.retrieve` | DEGRADED | IO error reading hindsight store |
| `memory.consolidate` | INFO | Consolidation run complete |
| `memory.consolidate` | DEGRADED | IO error during consolidation |
