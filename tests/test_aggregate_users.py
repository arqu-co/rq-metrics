"""Tests for per-user aggregation and leaderboard."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "docs"))

from aggregate_users import (
    resolve_user_key,
    compute_leaderboard,
    compute_per_user,
)
from helpers import make_metric


def test_resolve_user_key_uses_name():
    m = make_metric(user="Alice", user_email="alice@co.com")
    assert resolve_user_key(m) == "Alice"


def test_resolve_user_key_name_only():
    m = make_metric(user="Bob")
    assert resolve_user_key(m) == "Bob"


def test_resolve_user_key_skips_unknown_without_email():
    m = make_metric(user="unknown")
    assert resolve_user_key(m) is None


def test_resolve_user_key_uses_email_local_part_for_unknown():
    m = make_metric(user="unknown", user_email="bob@co.com")
    assert resolve_user_key(m) == "bob"


def test_per_user_groups_by_name():
    metrics = [
        make_metric(user="Alice", gates_first_pass=True),
        make_metric(user="Alice", gates_first_pass=False),
        make_metric(user="Bob", gates_first_pass=True),
    ]
    result = compute_per_user(metrics)
    assert result["Alice"]["total_builds"] == 2
    assert result["Alice"]["first_pass_rate"] == 50.0
    assert result["Bob"]["total_builds"] == 1
    assert result["Bob"]["first_pass_rate"] == 100.0


def test_per_user_merges_old_and_new_records():
    """Old records (name only) and new records (name + email) merge."""
    metrics = [
        make_metric(user="Alice", gates_first_pass=True),
        make_metric(user="Alice", user_email="alice@co.com",
                     gates_first_pass=False),
    ]
    result = compute_per_user(metrics)
    assert "Alice" in result
    assert result["Alice"]["total_builds"] == 2
    assert "alice@co.com" not in result


def test_per_user_deduplicates_email_only_via_mapping():
    """Email-only records merge into name bucket if mapping exists."""
    metrics = [
        make_metric(user="Alice", user_email="alice@co.com",
                     gates_first_pass=True),
        make_metric(user="unknown", user_email="alice@co.com",
                     gates_first_pass=False),
    ]
    result = compute_per_user(metrics)
    assert "Alice" in result
    assert result["Alice"]["total_builds"] == 2


def test_per_user_tracks_violations():
    metrics = [
        make_metric(user="Alice", critic_findings_count=2,
                     gate_failures_after_critic=1),
    ]
    result = compute_per_user(metrics)
    assert result["Alice"]["total_violations"] == 3
    assert result["Alice"]["avg_violations_per_build"] == 3.0


def test_leaderboard_sorts_by_first_pass_rate():
    per_user = {
        "Alice": {
            "display_name": "Alice", "email": None,
            "total_builds": 10, "first_pass_count": 8,
            "first_pass_rate": 80.0, "total_violations": 2,
            "avg_violations_per_build": 0.2, "avg_fix_cycles": 1.2,
        },
        "Bob": {
            "display_name": "Bob", "email": None,
            "total_builds": 10, "first_pass_count": 9,
            "first_pass_rate": 90.0, "total_violations": 1,
            "avg_violations_per_build": 0.1, "avg_fix_cycles": 1.1,
        },
    }
    lb = compute_leaderboard(per_user)
    assert lb[0]["user"] == "Bob"
    assert lb[0]["rank"] == 1
    assert lb[1]["user"] == "Alice"
    assert lb[1]["rank"] == 2


def test_leaderboard_breaks_ties_by_build_count():
    per_user = {
        "Alice": {
            "display_name": "Alice", "email": None,
            "total_builds": 20, "first_pass_count": 16,
            "first_pass_rate": 80.0, "total_violations": 0,
            "avg_violations_per_build": 0, "avg_fix_cycles": 1.0,
        },
        "Bob": {
            "display_name": "Bob", "email": None,
            "total_builds": 5, "first_pass_count": 4,
            "first_pass_rate": 80.0, "total_violations": 0,
            "avg_violations_per_build": 0, "avg_fix_cycles": 1.0,
        },
    }
    lb = compute_leaderboard(per_user)
    assert lb[0]["user"] == "Alice"


def test_leaderboard_empty_for_no_users():
    assert compute_leaderboard({}) == []
