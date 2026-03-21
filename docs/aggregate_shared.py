"""Shared constants and helpers for aggregation modules."""

KNOWN_GATES = [
    "filesize", "complexity", "dead-code",
    "lint", "tests", "test-quality", "coverage",
]


def count_gate_violations(gate_data):
    """Count violations from a single gate's data dict."""
    for key in ("violations", "failures", "test_failures", "below_threshold"):
        if key in gate_data:
            return gate_data[key]
    if gate_data.get("missing_tests", 0) > 0:
        return gate_data["missing_tests"]
    return 0
