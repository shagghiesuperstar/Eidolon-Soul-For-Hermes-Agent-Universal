#!/usr/bin/env python3
"""Eidolon adversarial test harness.

Proves the core guarantees by breaking the system on purpose in a
throwaway sandbox copy of the repo. The live repo is never modified.

The watchdog is de-sealed: it checks that required skills are present and
uses a local HTTP sink to stand in for the operator notification channel,
so the 'alert exactly once per incident' guarantee is verified end-to-end
(counting real delivered notifications), with no external network.

Usage:  python tests/adversarial.py
Exit code is non-zero if any scenario FAILs.

See tests/TESTPLAN.md for the rationale and pass criteria.
"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RESULTS = []


def record(name, passed, detail=""):
    RESULTS.append((name, passed, detail))
    tag = "PASS" if passed else "FAIL"
    print(f"[{tag}] {name}" + (f" :: {detail}" if detail else ""))


class _Sink(BaseHTTPRequestHandler):
    messages = []

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode() if length else ""
        type(self).messages.append(body)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *a):
        pass


def start_sink():
    """Local notify sink. Returns (url, server, reset_fn)."""
    _Sink.messages = []
    server = HTTPServer(("127.0.0.1", 0), _Sink)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    host, port = server.server_address
    return f"http://{host}:{port}", server, lambda: _Sink.messages.clear()


def sandbox():
    """Copy the repo into a temp dir so attacks never touch the live tree."""
    dst = Path(tempfile.mkdtemp(prefix="eidolon-adv-"))
    shutil.copytree(REPO, dst / "repo", dirs_exist_ok=True)
    return dst / "repo"


def run_watchdog(repo, notify_url):
    """Invoke the real watchdog handler in the sandbox; return parsed output."""
    wd = repo / "skills" / "integrity-watchdog" / "handler.py"
    proc = subprocess.run(
        [sys.executable, str(wd)],
        capture_output=True, text=True, cwd=str(repo),
        env={**os.environ, "EIDOLON_NOTIFY": notify_url},
    )
    last = [l for l in proc.stdout.strip().splitlines() if l.strip()]
    try:
        return json.loads(last[-1]) if last else {}
    except json.JSONDecodeError:
        return {"_raw": proc.stdout, "_err": proc.stderr}


def count(substr):
    return sum(1 for m in _Sink.messages if substr in m)


def scenario_1_clean_no_false_alarm(url, reset):
    reset()
    repo = sandbox()  # untouched copy
    first = run_watchdog(repo, url)
    clean = first.get("status") == "ok" and first.get("open", []) == []
    run_watchdog(repo, url)  # second run, still clean
    silent = count("integrity incident:") == 0
    record("S1 clean repo reports ok", clean, str(first.get("open")))
    record("S1 no false-positive alerts", silent, f"notifs={count('integrity incident:')}")
    shutil.rmtree(repo.parent, ignore_errors=True)


def scenario_2_skills_drift(url, reset):
    reset()
    repo = sandbox()
    dc = repo / "skills" / "dream-cycle"
    moved = repo / "skills" / "dream-cycle-MOVED"
    dc.rename(moved)
    first = run_watchdog(repo, url)
    open1 = first.get("open", [])
    detected = open1 == ["skills:dream-cycle"]
    run_watchdog(repo, url)  # second run, still broken
    incident_notifs = count("integrity incident:")
    alert_once = detected and incident_notifs == 1
    moved.rename(dc)  # repair
    third = run_watchdog(repo, url)
    resolved = third.get("open", []) == [] and third.get("status") == "ok" \
        and count("resolved") == 1
    record("S2 skills-drift detected", detected, str(open1))
    record("S2 alert exactly once across runs", alert_once, f"notifs={incident_notifs}")
    record("S2 incident resolves after repair", resolved, str(third.get("open")))
    shutil.rmtree(repo.parent, ignore_errors=True)


def load_dream_module(repo):
    path = repo / "skills" / "dream-cycle" / "handler.py"
    spec = importlib.util.spec_from_file_location("dream_cycle_handler", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def scenario_3_regressing_candidate():
    repo = sandbox()
    mod = load_dream_module(repo)
    soul_before = (repo / "SOUL.md").read_text()
    mod.shadow_test = lambda c: {"delta": -0.5}  # force regression
    state = {"runs": [], "last_known_good": "baseline-v0"}
    mod.gate_and_apply([{"id": "cand-bad", "risk": "high"}], state)
    not_promoted = state["last_known_good"] == "baseline-v0"
    invariants_intact = soul_before == (repo / "SOUL.md").read_text()
    record("S3 regressing candidate discarded (LKG unchanged)",
           not_promoted, f"lkg={state['last_known_good']}")
    record("S3 invariants untouched by candidate", invariants_intact)
    shutil.rmtree(repo.parent, ignore_errors=True)


def main():
    print("Eidolon adversarial tests — sandboxed, live repo untouched\n")
    url, server, reset = start_sink()
    try:
        scenario_1_clean_no_false_alarm(url, reset)
        scenario_2_skills_drift(url, reset)
        scenario_3_regressing_candidate()
    finally:
        server.shutdown()
    passed = sum(1 for _, p, _ in RESULTS if p)
    total = len(RESULTS)
    print(f"\n{passed}/{total} checks passed")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
