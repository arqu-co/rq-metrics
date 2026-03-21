#!/usr/bin/env python3
"""Aggregate rq-metrics data files into a single dashboard payload.

Reads all JSON files from data/ and produces docs/data.json for the dashboard.
"""

import glob
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone

KNOWN_GATES = [
    "filesize", "complexity", "dead-code",
    "lint", "tests", "test-quality", "coverage",
]


def load_metrics(data_dir="data"):
    """Load all metric files from data directory."""
    metrics = []
    pattern = os.path.join(data_dir, "**/*.json")
    for filepath in glob.glob(pattern, recursive=True):
        try:
            with open(filepath) as f:
                data = json.load(f)
                data["_file"] = filepath
                metrics.append(data)
        except (json.JSONDecodeError, OSError):
            continue
    return metrics


def compute_summary(metrics):
    """Compute aggregate statistics from metrics."""
    if not metrics:
        return {"total_builds": 0, "first_pass_rate": 0, "catch_rate": 0}

    total = len(metrics)
    first_pass = sum(1 for m in metrics if m.get("gates_first_pass", False))
    critic_catches = sum(m.get("critic_findings_count", 0) for m in metrics)
    critic_misses = sum(m.get("gate_failures_after_critic", 0) for m in metrics)
    total_violations = critic_catches + critic_misses

    return {
        "total_builds": total,
        "first_pass_count": first_pass,
        "first_pass_rate": round(first_pass / total * 100, 1) if total else 0,
        "critic_catches": critic_catches,
        "critic_misses": critic_misses,
        "catch_rate": (
            round(critic_catches / total_violations * 100, 1)
            if total_violations
            else 100
        ),
    }


def _group_by_date(metrics):
    """Group metrics by date string (YYYY-MM-DD)."""
    by_date = defaultdict(list)
    for m in metrics:
        ts = m.get("timestamp", "")
        date = ts[:10] if len(ts) >= 10 else "unknown"
        by_date[date].append(m)
    return by_date


def compute_trends(metrics):
    """Compute daily trend data."""
    by_date = _group_by_date(metrics)
    trends = []
    for date in sorted(by_date.keys()):
        summary = compute_summary(by_date[date])
        summary["date"] = date
        trends.append(summary)
    return trends


def compute_per_repo(metrics):
    """Compute per-repository breakdown."""
    by_repo = defaultdict(list)
    for m in metrics:
        repo = m.get("repo", "unknown")
        by_repo[repo].append(m)

    return {repo: compute_summary(repo_metrics)
            for repo, repo_metrics in by_repo.items()}


def compute_per_gate(metrics):
    """Compute which gates the critic misses most."""
    gate_misses = defaultdict(int)
    gate_total = defaultdict(int)
    for m in metrics:
        for miss in m.get("missed_gates", []):
            gate_misses[miss] += 1
        for gate in m.get("gates_run", []):
            gate_total[gate] += 1

    gates = {}
    for gate in gate_total:
        total = gate_total[gate]
        misses = gate_misses.get(gate, 0)
        gates[gate] = {
            "total": total,
            "misses": misses,
            "miss_rate": round(misses / total * 100, 1) if total else 0,
        }
    return gates


def _count_gate_violations(gate_data):
    """Count violations from a single gate's data dict."""
    for key in ("violations", "failures", "test_failures", "below_threshold"):
        if key in gate_data:
            return gate_data[key]
    if gate_data.get("missing_tests", 0) > 0:
        return gate_data["missing_tests"]
    return 0


def compute_per_gate_stats(metrics):
    """Per-gate stats: pass rate, avg violations, total runs."""
    stats = {}
    for gate in KNOWN_GATES:
        runs = 0
        passes = 0
        total_violations = 0
        for m in metrics:
            gates = m.get("gates", {})
            if gate not in gates:
                continue
            runs += 1
            gate_data = gates[gate]
            if gate_data.get("status") == "pass":
                passes += 1
            total_violations += _count_gate_violations(gate_data)

        stats[gate] = {
            "runs": runs,
            "passes": passes,
            "pass_rate": round(passes / runs * 100, 1) if runs else 0,
            "total_violations": total_violations,
            "avg_violations": round(total_violations / runs, 2) if runs else 0,
        }
    return stats


def compute_per_gate_per_repo(metrics):
    """Matrix of repo x gate with pass rates."""
    by_repo = defaultdict(lambda: defaultdict(lambda: {"runs": 0, "passes": 0}))
    for m in metrics:
        repo = m.get("repo", "unknown")
        gates = m.get("gates", {})
        for gate in KNOWN_GATES:
            if gate not in gates:
                continue
            bucket = by_repo[repo][gate]
            bucket["runs"] += 1
            if gates[gate].get("status") == "pass":
                bucket["passes"] += 1

    matrix = {}
    for repo, gate_map in by_repo.items():
        matrix[repo] = {}
        for gate, counts in gate_map.items():
            runs = counts["runs"]
            matrix[repo][gate] = {
                "runs": runs,
                "passes": counts["passes"],
                "pass_rate": (
                    round(counts["passes"] / runs * 100, 1) if runs else 0
                ),
            }
    return matrix


def compute_violation_trends(metrics):
    """Daily violation counts per gate."""
    by_date = _group_by_date(metrics)
    trends = []
    for date in sorted(by_date.keys()):
        day_gates = defaultdict(int)
        for m in by_date[date]:
            gates = m.get("gates", {})
            for gate in KNOWN_GATES:
                if gate in gates:
                    day_gates[gate] += _count_gate_violations(gates[gate])
        trends.append({"date": date, "violations": dict(day_gates)})
    return trends


def build_payload(metrics):
    """Assemble the full dashboard payload from metrics."""
    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "known_gates": list(KNOWN_GATES),
        "summary": compute_summary(metrics),
        "trends": compute_trends(metrics),
        "per_repo": compute_per_repo(metrics),
        "per_gate": compute_per_gate(metrics),
        "per_gate_stats": compute_per_gate_stats(metrics),
        "per_gate_per_repo": compute_per_gate_per_repo(metrics),
        "violation_trends": compute_violation_trends(metrics),
        "total_records": len(metrics),
    }


def main():
    data_dir = sys.argv[1] if len(sys.argv) > 1 else "data"
    output_file = sys.argv[2] if len(sys.argv) > 2 else "docs/data.json"

    metrics = load_metrics(data_dir)
    payload = build_payload(metrics)

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(payload, f, indent=2)

    print(f"Aggregated {len(metrics)} records -> {output_file}")


if __name__ == "__main__":
    main()
