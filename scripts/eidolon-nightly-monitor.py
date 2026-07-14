#!/usr/bin/env python3
"""Eidolon Nightly Monitor — collects metrics, observations, and prepares reports.

Runs hourly.
- Every hour: appends an observation snapshot to ~/.hermes/eidolon-reports/history.json
- At 8am: writes a daily light report (~/.hermes/eidolon-reports/report-YYYYMMDD-0800.md)
- On Sunday at 6am: writes a weekly deep audit (~/.hermes/eidolon-reports/weekly-YYYYMMDD-0600.md)

The weekly audit captures data sufficient to answer the operator's six questions:
  a) Is Eidolon functioning correctly and as expected?
  b) Is it adding measurable value (and how do you know)?
  c) Is it breaking anything else in hermes?
  d) Are there improvements, features, or bugs we need to fix?
  e) What is the agent's general feeling about it as a self-improvement architecture?
  f) What is the specific deterministic value above native Hermes mechanisms?
"""

import json, os, time, subprocess, datetime, hashlib, re, shutil, urllib.request, urllib.error
from pathlib import Path
from collections import defaultdict

STATE_DIR = Path.home() / ".hermes" / "state"
REPORT_DIR = Path.home() / ".hermes" / "eidolon-reports"
HERMES_HOME = Path.home() / ".hermes"
LESSONS_PATH = STATE_DIR / "lessons.md"
DREAM_STATE = STATE_DIR / "dream-cycle.json"
WATCHDOG_STATE = STATE_DIR / "integrity-watchdog.json"
DREAM_HANDLER = HERMES_HOME / "skills" / "dream-cycle" / "handler.py"
WATCHDOG_HANDLER = HERMES_HOME / "skills" / "integrity-watchdog" / "handler.py"
SOUL_PATH = HERMES_HOME / "SOUL.md"
HINDSIGHT_CONFIG = HERMES_HOME / "hindsight" / "config.json"
Path(REPORT_DIR).mkdir(parents=True, exist_ok=True)


# ---------- IO helpers ----------

def load_state(path):
    if path.exists():
        try: return json.loads(path.read_text())
        except: return {}
    return {}


def run_handler(path, mode=None, timeout=60):
    cmd = ["python3", str(path)]
    if mode: cmd.extend(["--mode", mode])
    try:
        r = subprocess.run(cmd, timeout=timeout, capture_output=True, text=True)
        return {"exit": r.returncode, "stdout": r.stdout.strip(),
                "stderr": r.stderr.strip()[-400:] if r.stderr else ""}
    except subprocess.TimeoutExpired:
        return {"exit": -1, "error": "timeout"}
    except Exception as e:
        return {"exit": -1, "error": str(e)}


# ---------- Observation capture (the part that gives the weekly report its teeth) ----------

def capture_hindsight_status():
    """Check if Hindsight is reachable. The whole back half of the pipeline is gated on this.

    The actual config schema (as observed on a live Hermes host) is:
      {
        "mode": "remote",
        "api_url": "http://<host>:<port>",
        "bank_id": "hermes",
        "agent_id": "<agent-name>",
        ...
      }
    Older env-based fallback: HINDSIGHT_URL=http://localhost:9077.

    For local_embedded mode, the daemon auto-idles after ``idle_timeout``
    seconds (default 300).  An empty port during idle is NORMAL — not an
    outage.  The probe explicitly wakes the daemon by posting a recall
    request before checking health, so the report reflects actual
    reachability rather than idle-state noise.
    """
    if not HINDSIGHT_CONFIG.exists():
        return {"reachable": False, "reason": "no config"}

    try:
        cfg = json.loads(HINDSIGHT_CONFIG.read_text())
        # New schema: mode + api_url + bank_id
        api_url = cfg.get("api_url")
        mode = cfg.get("mode", "remote")
        bank_id = cfg.get("bank_id")
        agent_id = cfg.get("agent_id")
        idle_timeout = cfg.get("idle_timeout", 300)

        # Legacy fallbacks
        if not api_url:
            api_url = cfg.get("url") or os.environ.get("HINDSIGHT_URL", "http://localhost:9077")
            mode = "legacy"

        if not api_url:
            return {"reachable": False, "reason": "no URL in config", "config": cfg}

        api_base = api_url.rstrip("/")

        # For local_embedded mode, the daemon auto-idles.  Post a lightweight
        # recall request first to wake it, then probe health.  Without this,
        # every 8am report during quiet hours screams "UNREACHABLE" when the
        # daemon is just idle-stopped (normal behaviour).
        if mode == "local_embedded":
            recall_url = f"{api_base}/v1/default/banks/{bank_id}/agents/{agent_id}/memories/recall"
            try:
                recall_req = urllib.request.Request(
                    recall_url,
                    data=json.dumps({"query": "ping", "limit": 1}).encode(),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(recall_req, timeout=10) as r:
                    pass  # successful POST wakes the daemon
            except Exception:
                pass  # daemon may already be awake; proceed to health probe

        # Probe the API endpoint.  For remote mode, try /health.  For legacy,
        # try the v1/default banks endpoint.
        probe_urls = [
            f"{api_base}/health",
            f"{api_base}/v1/default/banks",
        ]
        result = {"mode": mode, "api_url": api_url, "bank_id": bank_id,
                  "agent_id": agent_id, "idle_timeout": idle_timeout, "reachable": False, "probes": []}
        for purl in probe_urls:
            r = subprocess.run(["curl", "-sS", "--max-time", "5", "-o", "/dev/null",
                                "-w", "%{http_code}", purl],
                               capture_output=True, text=True)
            http_code = r.stdout.strip()
            probe_ok = r.returncode == 0 and http_code.isdigit() and int(http_code) < 500
            result["probes"].append({"url": purl, "http_code": http_code,
                                     "ok": probe_ok})
            if probe_ok:
                result["reachable"] = True
                result["response_preview"] = http_code
                return result

        result["reason"] = "all probes failed (service unreachable)"
        return result
    except Exception as e:
        return {"reachable": False, "reason": f"probe error: {e}"}


def capture_lessons_state():
    """Snapshot the lessons.md pipeline output."""
    if not LESSONS_PATH.exists():
        return {"exists": False, "lines": 0, "bytes": 0, "last_modified": None}
    text = LESSONS_PATH.read_text()
    stat = LESSONS_PATH.stat()
    return {"exists": True, "lines": len(text.splitlines()),
            "bytes": stat.st_size, "last_modified": stat.st_mtime,
            "first_100_chars": text[:100]}


def capture_dream_cycle_state():
    """Inspect dream-cycle.json for the structural signals that prove stages 2/3 fired."""
    s = load_state(DREAM_STATE)
    runs = s.get("runs", [])
    # Classify runs by mode
    by_mode = defaultdict(int)
    for r in runs:
        by_mode[r.get("mode", "unknown")] += 1
    # Look for any non-mode fields that would indicate stage 2/3 activity
    structural_keys = sorted(set(k for r in runs for k in r.keys()))
    return {
        "total_runs": len(runs),
        "by_mode": dict(by_mode),
        "last_run_ts": runs[-1]["ts"] if runs else None,
        "last_run_mode": runs[-1].get("mode") if runs else None,
        "structural_keys_observed": structural_keys,
        "has_proposals": any("proposals" in r for r in runs),
        "has_applied": any("applied" in r for r in runs),
        "has_rolled_back": any("rolled_back" in r or "rollback" in r for r in runs),
        "last_known_good_set": s.get("last_known_good") is not None,
        "other_state_keys": sorted(set(k for k in s.keys() if k != "runs")),
    }


def capture_watchdog_state():
    s = load_state(WATCHDOG_STATE)
    incidents = s.get("incidents", {})
    return {
        "status": s.get("status", "unknown"),
        "open_incident_count": len(incidents),
        "incident_keys": sorted(incidents.keys()),
        "last_checked": s.get("checked"),
        "last_repaired": s.get("last_repaired"),
    }


def capture_hermes_health():
    """Snapshot side-effects on the rest of Hermes — to answer (c) honestly."""
    signals = {}

    # Other cron jobs: count, last statuses
    cron_jobs = HERMES_HOME / "cron" / "jobs.json"
    if cron_jobs.exists():
        try:
            jobs = json.loads(cron_jobs.read_text())
            # Handle both list-of-jobs and {jobs: [...]} shapes
            if isinstance(jobs, dict):
                jobs = jobs.get("jobs", [])
            states = defaultdict(int)
            for j in jobs:
                states[j.get("state", j.get("status", "unknown"))] += 1
            signals["cron_jobs_total"] = len(jobs)
            signals["cron_states"] = dict(states)
            signals["cron_last_errors"] = [
                {"name": j.get("name"), "last_status": j.get("last_status"),
                 "last_delivery_error": j.get("last_delivery_error")}
                for j in jobs if j.get("last_status") == "error"
            ][:5]
        except Exception as e:
            signals["cron_read_error"] = str(e)

    # Skills directory size + count
    skills_dir = HERMES_HOME / "skills"
    if skills_dir.exists():
        skills = [p.name for p in skills_dir.iterdir() if p.is_dir()]
        signals["skills_count"] = len(skills)

    # Memory file size
    mem = HERMES_HOME / "memories"
    if mem.exists():
        signals["memory_files"] = sum(1 for _ in mem.rglob("*.md"))
        signals["memory_bytes"] = sum(p.stat().st_size for p in mem.rglob("*.md"))

    # State dir size
    if STATE_DIR.exists():
        signals["state_bytes"] = sum(p.stat().st_size for p in STATE_DIR.rglob("*") if p.is_file())

    # SOUL.md load check
    if SOUL_PATH.exists():
        soul = SOUL_PATH.read_text()
        signals["soul_size"] = len(soul)
        signals["soul_has_seal"] = "SEAL" in soul or "check_soul_tamper" in soul or "known_good_soul" in soul

    return signals


def capture_session_lessons_pending():
    """Read state/lessons.md if it exists and extract pending observations."""
    if not LESSONS_PATH.exists():
        return {"pending": [], "count": 0}
    lines = LESSONS_PATH.read_text().splitlines()
    # Look for any markdown list items or headings as candidate lessons
    pending = []
    for ln in lines:
        ln = ln.strip()
        if ln.startswith("- ") or ln.startswith("* ") or ln.startswith("#"):
            pending.append(ln[:300])
    return {"pending": pending[:50], "count": len(pending)}


def detect_drift_signals():
    """Look for evidence that something has drifted that we should report on.
    These are the agent's own observations, not just process health."""
    signals = []

    # Dream-cycle state file grew?
    if DREAM_STATE.exists():
        s = load_state(DREAM_STATE)
        runs = s.get("runs", [])
        if runs:
            # Are there gaps in hourly cadence?
            if len(runs) >= 2:
                recent = runs[-24:]
                timestamps = [r["ts"] for r in recent]
                gaps = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps)-1)]
                expected_gap = 3600  # 1 hour
                big_gaps = [g for g in gaps if g > expected_gap * 1.5]
                if big_gaps:
                    signals.append(f"dream-cycle missed {len(big_gaps)} expected hourly runs in last 24h (gaps >1.5h)")

    # Hindsight configured but unreachable (root cause for stages 2-3 no-op)
    h = capture_hindsight_status()
    if h.get("reason") == "no config":
        signals.append("hindsight has no config — stage 2/3 pipeline silently no-ops")
    elif not h.get("reachable"):
        api_url = h.get("api_url", "?")
        mode = h.get("mode", "?")
        bank = h.get("bank_id", "?")
        signals.append(
            f"hindsight configured ({mode}, {api_url}, bank={bank}) but UNREACHABLE — "
            f"stage 2/3 silently no-ops. Network/service fix needed, not config fix."
        )

    # Lessons file empty after multiple runs
    dc = capture_dream_cycle_state()
    ls = capture_lessons_state()
    if dc["total_runs"] >= 10 and (not ls["exists"] or ls["lines"] == 0):
        signals.append(f"dream-cycle has {dc['total_runs']} runs but lessons.md is empty — no applied improvements")

    # last_known_good never set
    if dc["total_runs"] >= 5 and not dc["last_known_good_set"]:
        signals.append("last_known_good is null after multiple runs — rollback path structurally disabled")

    # Watchdog incident accumulation
    w = capture_watchdog_state()
    if w["open_incident_count"] > 0:
        signals.append(f"integrity-watchdog has {w['open_incident_count']} open incident(s): {w['incident_keys']}")

    return signals


# ---------- Hourly snapshot ----------

def build_snapshot(history):
    now = datetime.datetime.now()
    dc_state = capture_dream_cycle_state()
    w_state = capture_watchdog_state()
    ls_state = capture_lessons_state()
    hindsight = capture_hindsight_status()
    drift = detect_drift_signals()

    snapshot = {
        "ts": time.time(),
        "datetime": now.isoformat(),
        "dream_cycle": {
            "exit": None,  # filled below
            "stdout_preview": "",
            "stderr": "",
        },
        "watchdog": {
            "exit": None,
            "status": w_state["status"],
            "open_incidents": w_state["open_incident_count"],
        },
        "state": {
            "dream_runs": dc_state["total_runs"],
            "dream_runs_by_mode": dc_state["by_mode"],
            "dream_has_proposals": dc_state["has_proposals"],
            "dream_has_applied": dc_state["has_applied"],
            "dream_has_rolled_back": dc_state["has_rolled_back"],
            "dream_last_known_good_set": dc_state["last_known_good_set"],
            "watchdog_checks": w_state["last_checked"],
            "lessons_exists": ls_state["exists"],
            "lessons_lines": ls_state["lines"],
        },
        "hindsight": hindsight,
        "drift_signals": drift,
    }
    return snapshot


# ---------- Stability assessment ----------

def assess_stability(history):
    if not history:
        return {"status": "unknown", "reason": "no runs recorded"}
    n_runs = len(history)
    n_errors = sum(1 for h in history if h.get("dream_cycle", {}).get("exit") not in (None, 0))
    if n_runs >= 5 and n_errors == 0:
        return {"status": "stable", "n_runs": n_runs, "n_errors": 0}
    elif n_errors > 0 and n_errors / n_runs > 0.5:
        return {"status": "unstable", "n_runs": n_runs, "n_errors": n_errors}
    else:
        return {"status": "booting", "n_runs": n_runs, "n_errors": n_errors}


# ---------- Daily 8am report (light) ----------

def build_daily_report(history, stability):
    if not history:
        return "# Eidolon Daily Report\n\nNo runs recorded.\n"
    n = len(history)
    dc_ok = sum(1 for h in history if h.get("dream_cycle", {}).get("exit") == 0)
    iw_ok = sum(1 for h in history if h.get("watchdog", {}).get("exit") == 0)
    open_incidents = sum(1 for h in history if h.get("watchdog", {}).get("open_incidents", 0) > 0)
    duration_h = (history[-1]["ts"] - history[0]["ts"]) / 3600 if len(history) > 1 else 0
    last = history[-1]

    drift_section = ""
    if last.get("drift_signals"):
        drift_section = "\n## Drift signals\n" + "\n".join(f"- {s}" for s in last["drift_signals"]) + "\n"

    return f"""# Eidolon Daily Report — {last['datetime']}

## Summary
- **Runtime**: {n} checks over {duration_h:.1f}h
- **Stability**: {stability['status']}
- **Dream-cycle success**: {dc_ok}/{n} ({100*dc_ok/n:.0f}% if n else 0)
- **Watchdog success**: {iw_ok}/{n} ({100*iw_ok/n:.0f}% if n else 0)
- **Watchdog open incidents**: {last['watchdog']['open_incidents']}
- **Total dream-cycle runs (cumulative)**: {last['state']['dream_runs']}
- **Lessons file**: {"present" if last['state']['lessons_exists'] else "absent"} ({last['state']['lessons_lines']} lines)
- **Hindsight**: {"reachable" if last['hindsight'].get('reachable') else f"NOT reachable — {last['hindsight'].get('reason', '?')}"}
{drift_section}
## Watchdog Status
- Status: {last['watchdog']['status']}
- Open incidents: {last['watchdog']['open_incidents']}

## Dream-Cycle Structural Status
- Runs by mode: {last['state']['dream_runs_by_mode']}
- Has proposals in any run: {last['state']['dream_has_proposals']}
- Has applied changes: {last['state']['dream_has_applied']}
- Has rollbacks: {last['state']['dream_has_rolled_back']}
- last_known_good set: {last['state']['dream_last_known_good_set']}
"""


# ---------- Weekly Sunday 6am audit (deep) ----------

def _week_window(history, snapshots_per_day=24):
    """Take the last ~168 snapshots (7 days × 24h)."""
    return history[-168:]


def build_weekly_audit(history):
    week = _week_window(history)
    if not week:
        return "# Eidolon Weekly Audit\n\nNo runs recorded this week.\n"

    n = len(week)
    dc_ok = sum(1 for h in week if h.get("dream_cycle", {}).get("exit") == 0)
    iw_ok = sum(1 for h in week if h.get("watchdog", {}).get("exit") == 0)
    first, last = week[0], week[-1]

    # Cadence analysis
    timestamps = [h["ts"] for h in week]
    if len(timestamps) >= 2:
        gaps = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps)-1)]
        median_gap_min = sorted(gaps)[len(gaps)//2] / 60 if gaps else 0
        missed_runs = sum(1 for g in gaps if g > 5400)  # >1.5h gap
    else:
        median_gap_min = 0
        missed_runs = 0

    # Drift signal aggregation
    all_drift = []
    for h in week:
        for s in h.get("drift_signals", []):
            if s not in all_drift:
                all_drift.append(s)

    # Stage 2/3 evidence
    stage_evidence = {
        "hindsight_reachable_this_week": any(h.get("hindsight", {}).get("reachable") for h in week),
        "hindsight_reachable_now": last.get("hindsight", {}).get("reachable", False),
        "lessons_growth_lines": last["state"]["lessons_lines"] - (
            week[0]["state"].get("lessons_lines", 0) if week[0]["state"].get("lessons_exists") else 0
        ),
        "lessons_present_now": last["state"]["lessons_exists"] and last["state"]["lessons_lines"] > 0,
        "has_any_proposal": last["state"]["dream_has_proposals"],
        "has_any_apply": last["state"]["dream_has_applied"],
        "has_any_rollback": last["state"]["dream_has_rolled_back"],
        "last_known_good_set": last["state"]["dream_last_known_good_set"],
        "total_dream_runs_cumulative": last["state"]["dream_runs"],
    }

    # Hermes-side impact (last sample)
    hermes = capture_hermes_health()

    # Per-question answer blocks. The agent reading this fills in the prose answers
    # using the deterministic evidence gathered here. The agent MUST cite the evidence
    # in each answer — this is what makes the report auditable, not vibes.
    audit = f"""# Eidolon Weekly Audit — week ending {last['datetime']}

**Window:** {first['datetime']} → {last['datetime']} ({n} snapshots, {n/24:.1f} days)

## Raw Metrics

| Metric | Value |
|---|---|
| Snapshots in window | {n} |
| Dream-cycle success rate | {dc_ok}/{n} ({100*dc_ok/n:.0f}%) |
| Watchdog success rate | {iw_ok}/{n} ({100*iw_ok/n:.0f}%) |
| Median gap between runs (min) | {median_gap_min:.1f} |
| Missed-run gaps (>1.5h) | {missed_runs} |
| Cumulative dream-cycle runs | {stage_evidence['total_dream_runs_cumulative']} |
| Lessons file lines now | {last['state']['lessons_lines']} |
| Hindsight reachable (now / this-week) | {stage_evidence['hindsight_reachable_now']} / {stage_evidence['hindsight_reachable_this_week']} |
| Any proposals observed | {stage_evidence['has_any_proposal']} |
| Any apply observed | {stage_evidence['has_any_apply']} |
| Any rollback observed | {stage_evidence['has_any_rollback']} |
| last_known_good set | {stage_evidence['last_known_good_set']} |

## Drift signals observed this week
{chr(10).join(f"- {s}" for s in all_drift) if all_drift else "- (none)"}

## Hermes-side health snapshot
- Cron jobs total: {hermes.get('cron_jobs_total', '?')}
- Cron states: {hermes.get('cron_states', {})}
- Cron errors (last 5): {hermes.get('cron_last_errors', [])}
- Skills count: {hermes.get('skills_count', '?')}
- Memory files / bytes: {hermes.get('memory_files', '?')} / {hermes.get('memory_bytes', '?')}
- State dir bytes: {hermes.get('state_bytes', '?')}
- SOUL.md size: {hermes.get('soul_size', '?')} (has SEAL: {hermes.get('soul_has_seal', '?')})

---

## Agent audit — answers to the operator's six questions

> The agent filling in this report MUST cite the raw metrics above when answering each
> question. A claim without a cited metric is a vibe and should be replaced with the metric.

### a) Functioning correctly and as expected?
**Evidence to consult:**
- Dream-cycle + watchdog success rates ({dc_ok}/{n}, {iw_ok}/{n})
- Missed-run cadence gaps ({missed_runs})
- Drift signals list above
- last_known_good set: {stage_evidence['last_known_good_set']}

**Answer template:** [agent fills in]

### b) Adding measurable value? How do you know?
**Evidence to consult:**
- Stage 2/3 structural evidence: {stage_evidence}
- Lessons file growth this week: {stage_evidence['lessons_growth_lines']} lines
- Hindsight reachability (now {stage_evidence['hindsight_reachable_now']} / this-week {stage_evidence['hindsight_reachable_this_week']})

**Answer template:** [agent fills in]

### c) Breaking anything else in hermes?
**Evidence to consult:**
- Cron states: {hermes.get('cron_states', {})}
- Cron last errors: {hermes.get('cron_last_errors', [])}
- Skills/memory/state sizes

**Answer template:** [agent fills in]

### d) Improvements / features / bugs to fix?
**Evidence to consult:**
- Drift signals list (these are the agent's own observations of what needs fixing)
- Missing structural elements (e.g., last_known_good null)

**Answer template:** [agent fills in]

### e) General feeling about the architecture
**Evidence to consult:**
- Stage 2/3 evidence + lessons growth + Hindsight reachability → answers whether the architecture is delivering on its design

**Answer template:** [agent fills in]

### f) Deterministic value above native Hermes mechanisms
**Evidence to consult:**
- Drift signals (these are exactly the things native Hermes does NOT detect — silent drift)
- One-time-alert dedup behavior (integrity-watchdog incidents: {last['watchdog']['open_incidents']})
- Stage 2/3 outputs (proposals/applies/rollbacks) — these are the structural deltas vs native memory

**Answer template:** [agent fills in]

---

## Bottom-line summary table

| Question | One-line verdict |
|---|---|
| a) Functioning? | [agent fills in] |
| b) Value? | [agent fills in] |
| c) Breaking anything? | [agent fills in] |
| d) Improvements needed? | [agent fills in] |
| e) Agent's feeling? | [agent fills in] |
| f) Value vs native Hermes? | [agent fills in] |
"""
    return audit


# ---------- Main loop ----------

def main():
    now = datetime.datetime.now()
    history_path = REPORT_DIR / "history.json"
    history = json.loads(history_path.read_text()) if history_path.exists() else []

    # Run both handlers (run_handler swallows errors safely)
    dc_result = run_handler(DREAM_HANDLER, mode="scheduled")
    iw_result = run_handler(WATCHDOG_HANDLER)

    # Build snapshot with deterministic observation data
    snapshot = build_snapshot(history)
    snapshot["dream_cycle"]["exit"] = dc_result["exit"]
    snapshot["dream_cycle"]["stdout_preview"] = dc_result.get("stdout", "")[:200]
    snapshot["dream_cycle"]["stderr"] = dc_result.get("stderr", "")
    snapshot["watchdog"]["exit"] = iw_result["exit"]

    history.append(snapshot)
    history = history[-2016:]  # keep ~12 weeks of hourly snapshots
    history_path.write_text(json.dumps(history, indent=2))

    # Hourly checkpoint
    stability = assess_stability(history[-24:])
    snapshot["stability"] = stability
    checkpoint = REPORT_DIR / f"checkpoint-{now.strftime('%Y%m%d-%H%M')}.json"
    checkpoint.write_text(json.dumps(snapshot, indent=2))

    # Daily 8am report (light)
    if now.strftime("%H:%M") == "08:00":
        report = build_daily_report(history[-24:], stability)
        report_path = REPORT_DIR / f"report-{now.strftime('%Y%m%d')}-0800.md"
        report_path.write_text(report)
        print(f"DAILY_REPORT_WRITTEN: {report_path}")
        print(json.dumps({"phase": "daily_8am", "path": str(report_path)}))

    # Weekly Sunday 6am audit (deep) — Sunday is weekday() == 6
    if now.weekday() == 6 and now.strftime("%H:%M") == "06:00":
        audit = build_weekly_audit(history)
        audit_path = REPORT_DIR / f"weekly-{now.strftime('%Y%m%d')}-0600.md"
        audit_path.write_text(audit)
        print(f"WEEKLY_AUDIT_WRITTEN: {audit_path}")
        print(json.dumps({"phase": "weekly_sunday_6am", "path": str(audit_path)}))

    print(json.dumps(snapshot))


if __name__ == "__main__":
    main()