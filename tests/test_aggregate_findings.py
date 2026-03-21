"""Tests for docs/aggregate_findings.py — findings, timing, cycles, phases."""

from helpers import make_metric

from aggregate_findings import (
    _extract_violation_details,
    _percentile,
    _summarize_durations,
    compute_findings_summary,
    compute_fix_cycles,
    compute_phase_breakdown,
    compute_recent_failures,
    compute_timing_stats,
    compute_top_violations,
)


# --- _extract_violation_details ---


class TestExtractViolationDetails:
    def test_returns_list_from_gate_data(self):
        details = [{"rule": "FILE_SIZE", "file": "big.py"}]
        assert _extract_violation_details({"violation_details": details}) == details

    def test_returns_empty_for_missing_key(self):
        assert _extract_violation_details({}) == []

    def test_returns_empty_for_non_list(self):
        assert _extract_violation_details({"violation_details": "bad"}) == []


# --- _percentile ---


class TestPercentile:
    def test_empty_list(self):
        assert _percentile([], 50) == 0

    def test_single_value(self):
        assert _percentile([42], 50) == 42
        assert _percentile([42], 95) == 42

    def test_two_values(self):
        assert _percentile([10, 20], 50) == 15.0

    def test_p95_of_many(self):
        vals = list(range(1, 101))
        # idx = 0.95 * 99 = 94.05; vals[94]=95, vals[95]=96
        # 95 + 0.05 * 1 = 95.05, rounded to 95.0
        assert _percentile(vals, 95) == 95.0

    def test_p50_of_three(self):
        assert _percentile([1, 2, 3], 50) == 2


# --- _summarize_durations ---


class TestSummarizeDurations:
    def test_computes_stats(self):
        result = _summarize_durations({"gate_a": [10, 20, 30]}, "ms")
        assert "gate_a" in result
        assert result["gate_a"]["avg_ms"] == 20.0
        assert "p50_ms" in result["gate_a"]
        assert "p95_ms" in result["gate_a"]

    def test_empty_map(self):
        assert _summarize_durations({}, "ms") == {}

    def test_skips_empty_values(self):
        assert _summarize_durations({"gate_a": []}, "ms") == {}


# --- compute_findings_summary ---


class TestComputeFindingsSummary:
    def test_counts_by_gate(self):
        metrics = [
            make_metric(gates={
                "filesize": {"status": "fail", "violations": 3},
                "lint": {"status": "fail", "failures": 2},
            }),
        ]
        result = compute_findings_summary(metrics)
        assert result["by_gate"]["filesize"] == 3
        assert result["by_gate"]["lint"] == 2

    def test_counts_by_rule_from_violation_details(self):
        metrics = [
            make_metric(gates={
                "filesize": {
                    "status": "fail",
                    "violations": 2,
                    "violation_details": [
                        {"rule": "FILE_SIZE", "file": "a.py"},
                        {"type": "FUNC_SIZE", "file": "b.py"},
                    ],
                },
            }),
        ]
        result = compute_findings_summary(metrics)
        assert result["by_rule"]["FILE_SIZE"] == 1
        assert result["by_rule"]["FUNC_SIZE"] == 1

    def test_empty_metrics(self):
        result = compute_findings_summary([])
        assert result == {"by_gate": {}, "by_rule": {}}

    def test_no_violations(self):
        metrics = [make_metric(gates={"lint": {"status": "pass", "failures": 0}})]
        result = compute_findings_summary(metrics)
        assert result["by_gate"] == {}


# --- compute_timing_stats ---


class TestComputeTimingStats:
    def test_gate_timing(self):
        metrics = [
            make_metric(gates={
                "lint": {"status": "pass", "duration_ms": 100},
            }),
            make_metric(gates={
                "lint": {"status": "pass", "duration_ms": 200},
            }),
        ]
        result = compute_timing_stats(metrics)
        assert result["by_gate"]["lint"]["avg_ms"] == 150.0

    def test_phase_timing(self):
        metrics = [
            make_metric(phase="build", duration_seconds=10),
            make_metric(phase="build", duration_seconds=20),
        ]
        result = compute_timing_stats(metrics)
        assert result["by_phase"]["build"]["avg_seconds"] == 15.0

    def test_empty_metrics(self):
        result = compute_timing_stats([])
        assert result == {"by_gate": {}, "by_phase": {}}

    def test_missing_duration_fields(self):
        metrics = [make_metric(gates={"lint": {"status": "pass"}})]
        result = compute_timing_stats(metrics)
        assert result["by_gate"] == {}


# --- compute_fix_cycles ---


class TestComputeFixCycles:
    def test_distribution(self):
        metrics = [
            make_metric(run_number=1),
            make_metric(run_number=1),
            make_metric(run_number=2),
            make_metric(run_number=3),
        ]
        result = compute_fix_cycles(metrics)
        assert result["distribution"]["1"] == 2
        assert result["distribution"]["2"] == 1
        assert result["distribution"]["3"] == 1
        assert result["avg"] == 1.8

    def test_empty_metrics(self):
        result = compute_fix_cycles([])
        assert result == {"distribution": {}, "avg": 0}

    def test_missing_run_number(self):
        metrics = [make_metric()]
        result = compute_fix_cycles(metrics)
        assert result == {"distribution": {}, "avg": 0}


# --- compute_phase_breakdown ---


class TestComputePhaseBreakdown:
    def test_counts_runs_and_failures(self):
        metrics = [
            make_metric(phase="build", gates={
                "lint": {"status": "fail"},
            }),
            make_metric(phase="build", gates={
                "lint": {"status": "pass"},
            }),
            make_metric(phase="review", gates={
                "tests": {"status": "fail"},
            }),
        ]
        result = compute_phase_breakdown(metrics)
        assert result["build"]["runs"] == 2
        assert result["build"]["failures"] == 1
        assert result["review"]["runs"] == 1
        assert result["review"]["failures"] == 1

    def test_empty_metrics(self):
        assert compute_phase_breakdown([]) == {}

    def test_unknown_phase(self):
        metrics = [make_metric(gates={"lint": {"status": "pass"}})]
        result = compute_phase_breakdown(metrics)
        assert "unknown" in result
        assert result["unknown"]["failures"] == 0


# --- compute_top_violations ---


class TestComputeTopViolations:
    def test_sorted_by_count(self):
        metrics = [
            make_metric(gates={
                "filesize": {
                    "status": "fail",
                    "violation_details": [
                        {"type": "FILE_SIZE"},
                        {"type": "FILE_SIZE"},
                    ],
                },
                "complexity": {
                    "status": "fail",
                    "violation_details": [
                        {"type": "COMPLEXITY"},
                    ],
                },
            }),
        ]
        result = compute_top_violations(metrics)
        assert len(result) == 2
        assert result[0]["type"] == "FILE_SIZE"
        assert result[0]["count"] == 2
        assert result[1]["type"] == "COMPLEXITY"
        assert result[1]["count"] == 1

    def test_empty_metrics(self):
        assert compute_top_violations([]) == []

    def test_no_violation_details(self):
        metrics = [make_metric(gates={"lint": {"status": "fail", "failures": 3}})]
        assert compute_top_violations(metrics) == []


# --- compute_recent_failures ---


class TestComputeRecentFailures:
    def test_returns_last_20(self):
        metrics = [
            make_metric(
                timestamp=f"2026-03-{i:02d}T10:00:00Z",
                repo="repo-a",
                gates={"lint": {
                    "status": "fail",
                    "violation_details": [{"type": "LINT_ERR"}],
                }},
            )
            for i in range(1, 26)
        ]
        result = compute_recent_failures(metrics)
        assert len(result) == 20
        assert result[0]["timestamp"] > result[-1]["timestamp"]

    def test_includes_gate_and_violations(self):
        metrics = [
            make_metric(
                timestamp="2026-03-21T10:00:00Z",
                repo="my-repo",
                gates={"tests": {
                    "status": "fail",
                    "violation_details": [{"type": "MISSING_TEST", "file": "x.py"}],
                }},
            ),
        ]
        result = compute_recent_failures(metrics)
        assert len(result) == 1
        assert result[0]["gate"] == "tests"
        assert result[0]["repo"] == "my-repo"
        assert len(result[0]["violations"]) == 1

    def test_empty_metrics(self):
        assert compute_recent_failures([]) == []

    def test_skips_passing_gates(self):
        metrics = [make_metric(gates={"lint": {"status": "pass"}})]
        assert compute_recent_failures(metrics) == []
