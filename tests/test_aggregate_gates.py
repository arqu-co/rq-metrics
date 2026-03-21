"""Tests for docs/aggregate.py — gate-specific functions."""

from helpers import make_metric

from aggregate import (
    KNOWN_GATES,
    _count_gate_violations,
    compute_per_gate,
    compute_per_gate_per_repo,
    compute_per_gate_stats,
    compute_violation_trends,
)


# --- compute_per_gate ---


class TestComputePerGate:
    def test_counts_misses_and_totals(self):
        metrics = [
            make_metric(
                missed_gates=["lint", "tests"],
                gates_run=["lint", "tests", "filesize"],
            ),
            make_metric(
                missed_gates=["lint"],
                gates_run=["lint", "filesize"],
            ),
        ]
        per_gate = compute_per_gate(metrics)
        assert per_gate["lint"]["misses"] == 2
        assert per_gate["lint"]["total"] == 2
        assert per_gate["lint"]["miss_rate"] == 100.0
        assert per_gate["tests"]["misses"] == 1
        assert per_gate["filesize"]["misses"] == 0
        assert per_gate["filesize"]["miss_rate"] == 0.0

    def test_empty_metrics(self):
        assert compute_per_gate([]) == {}


# --- _count_gate_violations ---


class TestCountGateViolations:
    def test_violations_key(self):
        assert _count_gate_violations({"violations": 5}) == 5

    def test_failures_key(self):
        assert _count_gate_violations({"failures": 3}) == 3

    def test_test_failures_key(self):
        assert _count_gate_violations({"test_failures": 2}) == 2

    def test_below_threshold_key(self):
        assert _count_gate_violations({"below_threshold": 1}) == 1

    def test_missing_tests_key(self):
        assert _count_gate_violations({"missing_tests": 4}) == 4

    def test_missing_tests_zero(self):
        assert _count_gate_violations({"missing_tests": 0}) == 0

    def test_empty_data(self):
        assert _count_gate_violations({}) == 0

    def test_priority_order(self):
        assert _count_gate_violations({"violations": 7, "failures": 3}) == 7


# --- compute_per_gate_stats ---


class TestComputePerGateStats:
    def test_calculates_pass_rate_and_violations(self):
        metrics = [
            make_metric(gates={
                "lint": {"status": "pass", "failures": 0},
                "tests": {"status": "fail", "test_failures": 2},
            }),
            make_metric(gates={
                "lint": {"status": "pass", "failures": 0},
                "tests": {"status": "pass", "test_failures": 0},
            }),
        ]
        stats = compute_per_gate_stats(metrics)
        assert stats["lint"]["runs"] == 2
        assert stats["lint"]["passes"] == 2
        assert stats["lint"]["pass_rate"] == 100.0
        assert stats["tests"]["runs"] == 2
        assert stats["tests"]["passes"] == 1
        assert stats["tests"]["pass_rate"] == 50.0
        assert stats["tests"]["total_violations"] == 2

    def test_gate_not_in_metric(self):
        metrics = [make_metric(gates={})]
        stats = compute_per_gate_stats(metrics)
        assert stats["lint"]["runs"] == 0
        assert stats["lint"]["pass_rate"] == 0

    def test_all_known_gates_present(self):
        stats = compute_per_gate_stats([])
        for gate in KNOWN_GATES:
            assert gate in stats

    def test_avg_violations(self):
        metrics = [
            make_metric(gates={"lint": {"status": "fail", "failures": 4}}),
            make_metric(gates={"lint": {"status": "fail", "failures": 6}}),
        ]
        stats = compute_per_gate_stats(metrics)
        assert stats["lint"]["avg_violations"] == 5.0


# --- compute_per_gate_per_repo ---


class TestComputePerGatePerRepo:
    def test_matrix_structure(self):
        metrics = [
            make_metric(repo="alpha", gates={
                "lint": {"status": "pass"},
                "tests": {"status": "fail"},
            }),
            make_metric(repo="alpha", gates={
                "lint": {"status": "pass"},
                "tests": {"status": "pass"},
            }),
            make_metric(repo="beta", gates={
                "lint": {"status": "fail"},
            }),
        ]
        matrix = compute_per_gate_per_repo(metrics)
        assert matrix["alpha"]["lint"]["runs"] == 2
        assert matrix["alpha"]["lint"]["passes"] == 2
        assert matrix["alpha"]["lint"]["pass_rate"] == 100.0
        assert matrix["alpha"]["tests"]["pass_rate"] == 50.0
        assert matrix["beta"]["lint"]["passes"] == 0
        assert matrix["beta"]["lint"]["pass_rate"] == 0.0

    def test_empty_metrics(self):
        assert compute_per_gate_per_repo([]) == {}


# --- compute_violation_trends ---


class TestComputeViolationTrends:
    def test_daily_violation_counts(self):
        metrics = [
            make_metric(
                timestamp="2026-03-20T10:00:00Z",
                gates={"lint": {"status": "fail", "failures": 3}},
            ),
            make_metric(
                timestamp="2026-03-20T14:00:00Z",
                gates={"lint": {"status": "fail", "failures": 2}},
            ),
            make_metric(
                timestamp="2026-03-21T10:00:00Z",
                gates={"tests": {"status": "fail", "test_failures": 1}},
            ),
        ]
        trends = compute_violation_trends(metrics)
        assert len(trends) == 2
        assert trends[0]["date"] == "2026-03-20"
        assert trends[0]["violations"]["lint"] == 5
        assert trends[1]["violations"].get("tests", 0) == 1

    def test_empty_metrics(self):
        assert compute_violation_trends([]) == []
