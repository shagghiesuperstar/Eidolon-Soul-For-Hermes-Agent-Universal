# Nightly regression eval

Eidolon runs a deterministic 20-case regression suite every night at
**07:17 UTC** via `.github/workflows/nightly-eval.yml`. The workflow:

1. Runs `tests/eval/regression_suite.py --seed 42 --json` (mock-provider only,
   no live inference).
2. Compares `pass_rate` against the last record in `docs/eval-history.jsonl`.
3. Appends the new record.
4. Opens a GitHub issue tagged `regression` if `pass_rate` drops by more than
   **5%** vs. the previous entry.

The threshold is a constant in `tests/eval/nightly.py`
(`REGRESSION_THRESHOLD = 0.05`) and can be tuned without a new REC.

## Reading `docs/eval-history.jsonl`

Each line is a single JSON object; append-only. Schema v1:

```json
{
  "schema": 1,
  "ts": "2026-07-08T07:17:00Z",
  "seed": 42,
  "total": 20,
  "passed": 20,
  "pass_rate": 1.0,
  "misses": []
}
```

Fields:

| Field       | Type                | Meaning |
|-------------|---------------------|---------|
| `schema`    | int                 | JSONL schema version. Currently `1`. |
| `ts`        | RFC 3339 UTC string | When the record was appended. |
| `seed`      | int                 | RNG seed used (default 42, deterministic). |
| `total`     | int                 | Total cases in the fixture set. |
| `passed`    | int                 | Cases whose expected winner scored > 0. |
| `pass_rate` | float in [0, 1]     | `passed / total`. |
| `misses`    | array of objects    | `{case, winner, score}` for each miss. |

## Running locally

```bash
# Dry run: prints the delta the next commit would produce.
PYTHONPATH=src python tests/eval/nightly.py --dry-run
# would append delta=+0.00 (threshold 5%)

# Full run (mutates docs/eval-history.jsonl):
PYTHONPATH=src python tests/eval/nightly.py --seed 42

# JSON metrics only (no history mutation):
PYTHONPATH=src python -m tests.eval.regression_suite --seed 42 --json
```

## Operator setup

The workflow needs push access to update `docs/eval-history.jsonl`. Two
supported paths:

- **`eidolon-agent[bot]`** — a GitHub App set up out-of-band. Preferred.
- **`NIGHTLY_EVAL_PAT` repo secret** — fine-grained PAT with
  `contents: write` on this repo, tied to a bot user. Simpler to configure.

If neither is set, the workflow falls back to `GITHUB_TOKEN`; that token
can push to unprotected branches but will fail on protected `main`.

## Regression-issue path

To manually verify the regression-issue path on a throwaway branch:

1. Copy an old, worse record into `docs/eval-history.jsonl` on a scratch
   branch, then trigger the workflow via `workflow_dispatch` (with
   `dry_run: false`).
2. If the current suite outperforms the seeded record, no issue is opened;
   if it regresses > 5%, an issue tagged `regression` is created.

Refs: `master_EIDOLON_roadmap(F5).md` § REC-014.
