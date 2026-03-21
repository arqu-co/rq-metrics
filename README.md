# rq-metrics

Quality metrics collection and dashboard for the rq pair-build workflow.

Tracks gate pass rates, critic effectiveness, violation trends, and per-repository breakdowns across all projects using the rq plugin.

## Dashboard

Live dashboard: <https://arqu-co.github.io/rq-metrics/>

The dashboard displays:

- **Summary cards** -- total builds, first-pass rate, critic catch rate
- **First-pass trend** -- daily gate pass rate over time
- **Gate health matrix** -- heatmap of repo x gate pass rates
- **Per-gate violation trends** -- daily violation counts per gate
- **Violation breakdown** -- stacked bar chart of violations by gate per day
- **Top offenders** -- gates ranked by failure rate
- **Per-repository breakdown** -- build stats per repo

## Data Flow

1. A pair-build session completes (via `rq:builder` + `rq:reviewer`)
2. `collect-metrics.sh` gathers gate results, critic verdict, and timestamps
3. The metrics JSON is pushed to `data/` in this repo
4. A GitHub Actions workflow (`deploy-dashboard.yml`) runs on push to `data/`
5. The workflow runs `python3 docs/aggregate.py` to produce `docs/data.json`
6. GitHub Pages deploys the `docs/` directory as the live dashboard

## Data Format

Each metrics file in `data/` is a JSON object:

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
