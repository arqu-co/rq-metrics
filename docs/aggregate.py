#!/usr/bin/env python3
"""Aggregate rq-metrics data files into a single dashboard payload.

Reads all JSON files from data/ and produces docs/data.json for the dashboard.
"""

import glob
import json
import os
import sys
from collections import defaultdict
from datetime import datetime


def load_metrics(data_dir="data"):
    """Load all metric files from data directory."""
    metrics = []
    for filepath in glob.glob(os.path.join(data_dir, "**/*.json"), recursive=True):
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


def compute_trends(metrics):
    """Compute daily trend data."""
    by_date = defaultdict(list)
    for m in metrics:
        ts = m.get("timestamp", "")
        date = ts[:10] if len(ts) >= 10 else "unknown"
        by_date[date].append(m)

    trends = []
    for date in sorted(by_date.keys()):
        day_metrics = by_date[date]
        summary = compute_summary(day_metrics)
        summary["date"] = date
        trends.append(summary)
    return trends


def compute_per_repo(metrics):
    """Compute per-repository breakdown."""
    by_repo = defaultdict(list)
    for m in metrics:
        repo = m.get("repo", "unknown")
        by_repo[repo].append(m)

    repos = {}
    for repo, repo_metrics in by_repo.items():
        repos[repo] = compute_summary(repo_metrics)
    return repos


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


def main():
    data_dir = sys.argv[1] if len(sys.argv) > 1 else "data"
    output_file = sys.argv[2] if len(sys.argv) > 2 else "docs/data.json"

    metrics = load_metrics(data_dir)

    payload = {
        "generated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "summary": compute_summary(metrics),
        "trends": compute_trends(metrics),
        "per_repo": compute_per_repo(metrics),
        "per_gate": compute_per_gate(metrics),
        "total_records": len(metrics),
    }

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(payload, f, indent=2)

    print(f"Aggregated {len(metrics)} records -> {output_file}")


if __name__ == "__main__":
    main()
