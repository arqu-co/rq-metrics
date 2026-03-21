"""Tests for docs/aggregate_shared.py — shared constants and helpers."""

from aggregate_shared import KNOWN_GATES, count_gate_violations


class TestKnownGates:
    def test_contains_expected_gates(self):
        expected = [
            "filesize", "complexity", "dead-code",
            "lint", "tests", "test-quality", "coverage",
        ]
        assert KNOWN_GATES == expected

    def test_is_a_list(self):
        assert isinstance(KNOWN_GATES, list)


class TestCountGateViolations:
    def test_violations_key(self):
        assert count_gate_violations({"violations": 5}) == 5

    def test_failures_key(self):
        assert count_gate_violations({"failures": 3}) == 3

    def test_test_failures_key(self):
        assert count_gate_violations({"test_failures": 2}) == 2

    def test_below_threshold_key(self):
        assert count_gate_violations({"below_threshold": 1}) == 1

    def test_missing_tests_key(self):
        assert count_gate_violations({"missing_tests": 4}) == 4

    def test_missing_tests_zero(self):
        assert count_gate_violations({"missing_tests": 0}) == 0

    def test_empty_data(self):
        assert count_gate_violations({}) == 0

    def test_priority_order(self):
        assert count_gate_violations({"violations": 7, "failures": 3}) == 7
