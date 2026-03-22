"""Aggregation functions for findings, timing, fix cycles, and phases.

These complement aggregate.py with deeper violation analysis.
"""

from collections import defaultdict

from aggregate_shared import count_gate_violations


DETAIL_KEYS = (
    "violations_details",
    "failures_details",
    "missing_tests_details",
    "below_threshold_details",
    "test_failures_details",
    "issues_details",
    "findings_details",
)

# Map gate names to a human-readable violation type when the detail
# item doesn't carry its own ``type`` or ``rule`` field.
GATE_TYPE_MAP = {
    "filesize": "file_too_large",
    "complexity": "function_too_complex",
    "coverage": "coverage_below_threshold",
    "dead-code": "dead_code",
}


def _extract_violation_details(gate_data, gate_name=""):
    """Extract violation detail list from a gate's data dict.

    Searches multiple ``*_details`` keys (the payload stores each list-type
    proof field as ``<key>_details``).  When an individual detail item lacks
    a ``type`` or ``rule`` field, a synthetic type is derived from the gate
    name so that downstream grouping always has a label.
    """
    details = []
    for key in DETAIL_KEYS:
        val = gate_data.get(key)
        if isinstance(val, list):
            details.extend(val)

    # Legacy field name (singular) used by older payloads
    legacy = gate_data.get("violation_details")
    if isinstance(legacy, list) and not details:
        details = legacy

    # Normalize: ensure every item is a dict with a usable type/rule label
    fallback = GATE_TYPE_MAP.get(gate_name, f"{gate_name}_violation") if gate_name else "unknown"
    normalized = []
    for item in details:
        if isinstance(item, str):
            normalized.append({"type": fallback, "message": item})
            continue
        if not isinstance(item, dict):
            continue
        if not item.get("type") and not item.get("rule"):
            if "pattern" in item:
                item["type"] = item["pattern"]
            else:
                item["type"] = fallback
        normalized.append(item)

    return normalized


def compute_findings_summary(metrics):
    """All violations across all gates, grouped by gate and rule."""
    by_gate = defaultdict(int)
    by_rule = defaultdict(int)

    for m in metrics:
        gates = m.get("gates", {})
        for gate_name, gate_data in gates.items():
            count = count_gate_violations(gate_data)
            if count > 0:
                by_gate[gate_name] += count
            for detail in _extract_violation_details(gate_data, gate_name):
                rule = detail.get("rule") or detail.get("type", "unknown")
                by_rule[rule] += 1

    return {"by_gate": dict(by_gate), "by_rule": dict(by_rule)}


def compute_timing_stats(metrics):
    """Avg/p50/p95 duration per gate and per phase."""
    gate_durations = defaultdict(list)
    phase_durations = defaultdict(list)

    for m in metrics:
        phase = m.get("phase", "unknown")
        duration = m.get("duration_seconds")
        if duration is not None:
            phase_durations[phase].append(duration)

        gates = m.get("gates", {})
        for gate_name, gate_data in gates.items():
            gate_dur = gate_data.get("duration_ms")
            if gate_dur is not None:
                gate_durations[gate_name].append(gate_dur)

    return {
        "by_gate": _summarize_durations(gate_durations, "ms"),
        "by_phase": _summarize_durations(phase_durations, "seconds"),
    }


def _summarize_durations(duration_map, unit_suffix):
    """Compute avg/p50/p95 for each key in a duration map."""
    result = {}
    for key, values in duration_map.items():
        if not values:
            continue
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        avg = sum(sorted_vals) / n
        p50 = _percentile(sorted_vals, 50)
        p95 = _percentile(sorted_vals, 95)
        avg_key = "avg_" + unit_suffix
        p50_key = "p50_" + unit_suffix
        p95_key = "p95_" + unit_suffix
        result[key] = {avg_key: round(avg, 1), p50_key: p50, p95_key: p95}
    return result


def _percentile(sorted_values, pct):
    """Compute a percentile from a pre-sorted list."""
    if not sorted_values:
        return 0
    n = len(sorted_values)
    idx = (pct / 100) * (n - 1)
    lower = int(idx)
    upper = lower + 1
    if upper >= n:
        return sorted_values[-1]
    frac = idx - lower
    return round(
        sorted_values[lower] + frac * (sorted_values[upper] - sorted_values[lower]),
        1,
    )


def compute_fix_cycles(metrics):
    """Distribution of run_number — how many re-runs before green."""
    distribution = defaultdict(int)
    total_runs = 0
    count = 0

    for m in metrics:
        run_num = m.get("run_number")
        if run_num is not None:
            distribution[str(run_num)] += 1
            total_runs += run_num
            count += 1

    avg = round(total_runs / count, 1) if count else 0
    return {"distribution": dict(distribution), "avg": avg}


def compute_phase_breakdown(metrics):
    """Which phase catches the most issues."""
    phases = defaultdict(lambda: {"runs": 0, "failures": 0})

    for m in metrics:
        phase = m.get("phase", "unknown")
        phases[phase]["runs"] += 1
        gates = m.get("gates", {})
        has_failure = any(
            g.get("status") == "fail" for g in gates.values()
        )
        if has_failure:
            phases[phase]["failures"] += 1

    return {k: dict(v) for k, v in phases.items()}


def compute_top_violations(metrics):
    """Most common violation types across all gates, sorted by count."""
    counts = defaultdict(lambda: {"count": 0, "gate": ""})

    for m in metrics:
        gates = m.get("gates", {})
        for gate_name, gate_data in gates.items():
            for detail in _extract_violation_details(gate_data, gate_name):
                vtype = detail.get("type") or detail.get("rule", "unknown")
                counts[vtype]["count"] += 1
                counts[vtype]["gate"] = gate_name

    result = [
        {"type": vtype, "count": info["count"], "gate": info["gate"]}
        for vtype, info in counts.items()
    ]
    result.sort(key=lambda x: x["count"], reverse=True)
    return result


def compute_recent_failures(metrics):
    """Last 20 failures with details."""
    failures = []

    for m in metrics:
        gates = m.get("gates", {})
        for gate_name, gate_data in gates.items():
            if gate_data.get("status") != "fail":
                continue
            violations = _extract_violation_details(gate_data, gate_name)
            failures.append({
                "timestamp": m.get("timestamp", ""),
                "repo": m.get("repo", "unknown"),
                "gate": gate_name,
                "violations": violations,
            })

    failures.sort(key=lambda x: x["timestamp"], reverse=True)
    return failures[:20]
