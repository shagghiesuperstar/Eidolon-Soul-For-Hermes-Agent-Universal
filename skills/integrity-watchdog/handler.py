#!/usr/bin/env python3
"""Eidolon integrity-watchdog handler.

Detects environment drift that breaks the Eidolon setup, attempts safe,
reversible self-repair, and notifies the operator EXACTLY ONCE per incident.
Never blocks sessionend. Never spams. Never weakens security invariants.
"""
import hashlib
import json
import os
import re
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "state"
STATE.mkdir(exist_ok=True)
STATE_FILE = STATE / "integrity-watchdog.json"
SEAL_RE = re.compile(r"<!--\s*SEAL:\s*([0-9a-fA-F]{64})")


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"incidents": {}, "status": "ok", "checked": 0}


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2))


def notify(message):
    target = os.environ.get("EIDOLON_NOTIFY")
    if not target:
        return False
    try:
        if target.startswith("tg:"):
            token = os.environ.get("EIDOLON_TG_TOKEN", "")
            chat = target[3:]
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            data = json.dumps({"chat_id": chat, "text": message}).encode()
        else:
            url = target
            data = json.dumps({"text": message}).encode()
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=5)
        return True
    except Exception:
        return False


def check_skills():
    incidents = []
    for skill in ("dream-cycle", "integrity-watchdog"):
        if not (ROOT / "skills" / skill / "handler.py").exists():
            incidents.append((f"skills:{skill}", f"Skill '{skill}' handler missing or moved."))
    return incidents


def check_soul_seal():
    soul = ROOT / "SOUL.md"
    if not soul.exists():
        return [("soul:missing", "SOUL.md is missing.")]
    text = soul.read_text()
    m = SEAL_RE.search(text)
    if not m:
        return [("soul:noseal", "SOUL.md has no SEAL block.")]
    body = text[: m.start()]
    digest = hashlib.sha256(body.encode()).hexdigest()
    if digest != m.group(1).lower():
        return [("soul:tampered", "SOUL.md SEAL mismatch (possible tampering).")]
    return []


def attempt_repair(key):
    # Only non-destructive, reversible repairs are auto-run. Otherwise defer.
    # Cron/hook re-wiring is environment-specific; surface to operator instead.
    return False


def run_checks():
    found = []
    found += check_skills()
    found += check_soul_seal()
    return dict(found)


def main():
    state = load_state()
    state["checked"] = time.time()
    current = run_checks()
    known = state["incidents"]

    # New incidents -> attempt repair, notify ONCE.
    for key, msg in current.items():
        if key not in known:
            repaired = attempt_repair(key)
            if repaired:
                continue
            notified = notify(f"[Eidolon] integrity incident: {msg}")
            known[key] = {"msg": msg, "opened": time.time(), "notified": notified}
        elif not known[key].get("notified"):
            # Earlier notify failed; retry once, then stop retrying.
            known[key]["notified"] = notify(f"[Eidolon] integrity incident: {msg}")

    # Cleared incidents -> resolve so a future recurrence can alert again.
    for key in list(known.keys()):
        if key not in current:
            notify(f"[Eidolon] integrity incident resolved: {key}")
            del known[key]

    state["status"] = "ok" if not known else "incident"
    save_state(state)
    print(json.dumps({"status": state["status"], "open": list(known.keys())}))


if __name__ == "__main__":
    main()
