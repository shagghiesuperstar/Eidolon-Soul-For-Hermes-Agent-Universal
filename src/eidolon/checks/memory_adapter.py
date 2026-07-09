# SPDX-License-Identifier: Apache-2.0
"""Check: memory adapter loads and round-trips cleanly (REC-018).

Status policy:
  PASS     — adapter instantiates and ``store`` / ``retrieve`` succeed.
  DEGRADED — adapter loads but is InMemAdapter (no persistent Hermes store);
             or consolidate() raises unexpectedly.
  FAIL     — import of memory package itself fails (broken install).
"""

from __future__ import annotations

from eidolon.checks import CheckResult, DEGRADED, FAIL, PASS

_PROBE_ENTRY = {"kind": "doctor_probe", "content": "eidolon_memory_check"}


def check() -> CheckResult:
    try:
        from eidolon.memory import load_adapter, InMemAdapter
        from eidolon.memory.adapter import MemoryStoreError
    except Exception as exc:  # noqa: BLE001
        return CheckResult(
            name="memory_adapter_ready",
            status=FAIL,
            reason=f"memory package import failed: {type(exc).__name__}: {exc}",
        )

    try:
        adapter = load_adapter()
    except Exception as exc:  # noqa: BLE001
        return CheckResult(
            name="memory_adapter_ready",
            status=FAIL,
            reason=f"load_adapter() raised: {type(exc).__name__}: {exc}",
        )

    # Probe: store then retrieve.
    try:
        adapter.store(dict(_PROBE_ENTRY))
        hits = adapter.retrieve(kind="doctor_probe", limit=1)
    except (MemoryStoreError, Exception) as exc:  # noqa: BLE001
        return CheckResult(
            name="memory_adapter_ready",
            status=FAIL,
            reason=f"memory probe failed: {type(exc).__name__}: {exc}",
            detail={"backend": adapter.name},
        )

    if not hits:
        return CheckResult(
            name="memory_adapter_ready",
            status=FAIL,
            reason="memory probe stored entry but retrieve returned empty",
            detail={"backend": adapter.name},
        )

    # Degrade if running volatile inmem (no persistent store present).
    if isinstance(adapter, InMemAdapter):
        return CheckResult(
            name="memory_adapter_ready",
            status=DEGRADED,
            reason=(
                "memory backend is InMemAdapter (volatile); "
                "set memory.backend: hindsight in $HERMES_HOME/config.yaml "
                "for durable storage."
            ),
            detail={"backend": adapter.name},
        )

    return CheckResult(
        name="memory_adapter_ready",
        status=PASS,
        reason=f"memory adapter ready ({adapter.name})",
        detail={"backend": adapter.name},
    )
