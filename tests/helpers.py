"""Test helpers for rq-metrics tests."""


def make_metric(**overrides):
    """Build a metric dict with sensible defaults."""
    base = {
        "repo": "test-repo",
        "branch": "main",
        "sha": "abc1234",
        "timestamp": "2026-03-21T12:00:00Z",
        "gates_first_pass": True,
        "critic_findings_count": 0,
        "gate_failures_after_critic": 0,
        "missed_gates": [],
        "gates_run": [],
        "gates": {},
    }
    base.update(overrides)
    return base
