# rq-metrics

Quality metrics collection and dashboard for the rq pair-build workflow.

Tracks gate pass rates, critic effectiveness, violation trends, and per-repository breakdowns across all projects using the rq plugin.

## Dashboard

Live dashboard: <https://arqu-co.github.io/rq-metrics/>

The dashboard displays:

**Gate quality**

- **Summary cards** -- total builds, first-pass rate, critic catch rate
- **First-pass trend** -- daily gate pass rate over time
- **Gate health matrix** -- heatmap of repo x gate pass rates
- **Per-gate violation trends** -- daily violation counts per gate
- **Violation breakdown** -- stacked bar chart of violations by gate per day
- **Top offenders** -- gates ranked by failure rate
- **Per-repository breakdown** -- build stats per repo

**Token cost** (emitted by the rq plugin's token observability feature)

- **Cost summary** -- total $, total tokens, cache ratio, session count
- **Cost leaderboard** -- users ranked by total spend
- **Most expensive sessions** -- top N priced by `est_cost_usd`
- **Cost by repo / branch / PR** -- drill-down tables
- **Daily cost trend** -- line chart of per-day spend

## Data Flow

1. A pair-build session completes (via `rq:builder` + `rq:reviewer`)
2. `collect-metrics.sh` gathers gate results, critic verdict, and timestamps
3. The metrics JSON is pushed to `data/` in this repo
4. A GitHub Actions workflow (`deploy-dashboard.yml`) runs on push to `data/`
5. The workflow runs `python3 docs/aggregate.py` to produce `docs/data.json`
6. GitHub Pages deploys the `docs/` directory as the live dashboard

## Data Format

Two event types live side-by-side in `data/`. They are distinguished by
the presence of `event_type` (token events) vs the absence of it (gate
events, the original format).

### Gate metric event

```json
{
  "repo": "my-project",
  "branch": "feat/new-feature",
  "sha": "abc1234",
  "user": "jerrod",
  "timestamp": "2026-03-21T10:30:00Z",
  "critic_verdict": "approve",
  "gates_first_pass": true,
  "gates": {
    "filesize": { "status": "pass", "files_checked": 85, "violations": 0 },
    "complexity": { "status": "pass", "files_checked": 84, "violations": 0 },
    "dead-code": { "status": "pass", "violations": 0 },
    "lint": { "status": "pass", "failures": 0 },
    "tests": { "status": "pass", "test_failures": 0, "missing_tests": 0 },
    "test-quality": { "status": "pass", "violations": 0, "scanned_files": 19 },
    "coverage": { "status": "pass", "below_threshold": 0 }
  }
}
```

### Token usage event

One record per Claude Code session. Emitted by the rq plugin's token
observability feature and stored under
`data/<repo>/<slugified-branch>/<session_id>-tokens.json`.

```json
{
  "event_type": "token_usage",
  "schema_version": 1,
  "repo": "my-project",
  "branch": "feat/new-feature",
  "sha": "abc1234",
  "user": "jerrod",
  "user_email": "jerrod@example.com",
  "timestamp": "2026-04-10T12:00:00Z",
  "session_id": "8be8be18-1d06-4c3c-a894-a6105394824a",
  "pr_number": 139,
  "pr_url": "https://github.com/my-org/my-project/pull/139",
  "models_seen": ["claude-sonnet-4-6", "claude-haiku-4-5"],
  "session_total": {
    "input": 730,
    "output": 532637,
    "cache_read": 17281006,
    "cache_create": 3722754,
    "est_cost_usd": 122.53
  },
  "phases": {
    "brainstorm": { "tokens": 412800, "cost_usd": 0.18 },
    "pair-build": { "tokens": 5124000, "cost_usd": 1.92 },
    "review":     { "tokens": 1428500, "cost_usd": 0.54 }
  }
}
```

`est_cost_usd` may be `null` when any bucket uses a model not listed in
the rq plugin's `model-rates.yaml`. Unpriced sessions are counted in the
dashboard summary so they don't vanish silently.

## Local Aggregation

To regenerate the dashboard data locally:

```bash
python3 docs/aggregate.py
```

This reads all JSON files from `data/` and writes `docs/data.json`.

You can also specify custom paths:

```bash
python3 docs/aggregate.py <data-dir> <output-file>
```

To preview the dashboard, serve the `docs/` directory:

```bash
python3 -m http.server -d docs 8080
```

Then open `http://localhost:8080` in a browser.
