"""Tests for aggregate_tokens.py — per-user/repo/branch/PR cost rollups."""

import pytest

from helpers_tokens import make_session_total, make_token_event

from aggregate_tokens import (
    compute_cost_trends,
    compute_per_branch_tokens,
    compute_per_pr_tokens,
    compute_per_repo_tokens,
    compute_per_user_tokens,
    compute_top_sessions,
    compute_token_leaderboard,
    compute_token_summary,
    is_token_event,
    load_token_events,
)


# ── is_token_event ────────────────────────────────────────────────────────


def test_is_token_event_true_for_token_usage_event_type():
    assert is_token_event({"event_type": "token_usage"}) is True


def test_is_token_event_false_for_gate_metric():
    # Gate metrics don't have event_type
    assert is_token_event({"gates_first_pass": True}) is False


def test_is_token_event_false_for_other_event_type():
    assert is_token_event({"event_type": "something_else"}) is False


def test_is_token_event_false_for_empty_dict():
    assert is_token_event({}) is False


# ── compute_token_summary ─────────────────────────────────────────────────


def test_token_summary_empty_returns_zeros():
    summary = compute_token_summary([])
    assert summary["total_tokens"] == 0
    assert summary["total_cost_usd"] == 0
    assert summary["session_count"] == 0
    assert summary["unpriced_sessions"] == 0


def test_token_summary_sums_all_token_buckets():
    events = [
        make_token_event(
            session_total=make_session_total(10, 20, 30, 40, 0.05)
        ),
        make_token_event(
            session_total=make_session_total(5, 15, 25, 35, 0.03)
        ),
    ]
    summary = compute_token_summary(events)
    # total_tokens sums input + output + cache_read + cache_create
    assert summary["total_tokens"] == 180  # (10+20+30+40) + (5+15+25+35)
    assert summary["total_cost_usd"] == pytest.approx(0.08)
    assert summary["session_count"] == 2


def test_token_summary_counts_unpriced_sessions():
    events = [
        make_token_event(
            session_total=make_session_total(10, 20, 0, 0, 0.05)
        ),
        make_token_event(
            session_id="sess-2",
            session_total={"input": 1, "output": 2, "cache_read": 0,
                           "cache_create": 0, "est_cost_usd": None},
        ),
    ]
    summary = compute_token_summary(events)
    assert summary["session_count"] == 2
    assert summary["unpriced_sessions"] == 1
    # total_cost_usd sums only priced rows
    assert summary["total_cost_usd"] == pytest.approx(0.05)


def test_token_summary_includes_cache_ratio():
    events = [
        make_token_event(
            session_total=make_session_total(
                input_tokens=100,
                output=100,
                cache_read=800,
                cache_create=0,
                est_cost_usd=0.1,
            )
        )
    ]
    summary = compute_token_summary(events)
    # total = 1000, cache = 800 → 80%
    assert summary["cache_ratio"] == pytest.approx(0.8)


# ── compute_per_user_tokens ───────────────────────────────────────────────


def test_per_user_tokens_groups_by_user_key():
    events = [
        make_token_event(
            user="alice",
            session_id="s1",
            session_total=make_session_total(10, 20, 30, 40, 0.05),
        ),
        make_token_event(
            user="alice",
            session_id="s2",
            session_total=make_session_total(5, 5, 5, 5, 0.02),
        ),
        make_token_event(
            user="bob",
            session_id="s3",
            session_total=make_session_total(100, 100, 100, 100, 0.5),
        ),
    ]
    per_user = compute_per_user_tokens(events)
    assert set(per_user.keys()) == {"alice", "bob"}
    assert per_user["alice"]["total_tokens"] == 120  # two sessions
    assert per_user["alice"]["session_count"] == 2
    assert per_user["alice"]["total_cost_usd"] == pytest.approx(0.07)
    assert per_user["bob"]["total_tokens"] == 400


def test_per_user_tokens_uses_email_fallback_when_name_unknown():
    events = [
        make_token_event(
            user="unknown",
            user_email="carol@example.com",
            session_total=make_session_total(10, 0, 0, 0, 0.01),
        ),
    ]
    per_user = compute_per_user_tokens(events)
    # Falls back to email local part
    assert "carol" in per_user


# ── compute_token_leaderboard ─────────────────────────────────────────────


def test_token_leaderboard_ranks_by_cost_descending():
    per_user = {
        "alice": {"display_name": "alice", "total_cost_usd": 10.0,
                  "total_tokens": 1000, "session_count": 3},
        "bob": {"display_name": "bob", "total_cost_usd": 25.0,
                "total_tokens": 2000, "session_count": 5},
        "carol": {"display_name": "carol", "total_cost_usd": 5.0,
                  "total_tokens": 500, "session_count": 2},
    }
    leaderboard = compute_token_leaderboard(per_user)
    assert [e["user"] for e in leaderboard] == ["bob", "alice", "carol"]
    assert [e["rank"] for e in leaderboard] == [1, 2, 3]


def test_token_leaderboard_handles_unpriced_users_last():
    per_user = {
        "alice": {"display_name": "alice", "total_cost_usd": 10.0,
                  "total_tokens": 1000, "session_count": 1},
        "bob": {"display_name": "bob", "total_cost_usd": None,
                "total_tokens": 500, "session_count": 1},
    }
    leaderboard = compute_token_leaderboard(per_user)
    # Priced users come first
    assert leaderboard[0]["user"] == "alice"
    assert leaderboard[1]["user"] == "bob"


# ── compute_per_repo_tokens ───────────────────────────────────────────────


def test_per_repo_tokens_sums_by_repo():
    events = [
        make_token_event(
            repo="alpha", session_id="s1",
            session_total=make_session_total(1, 1, 1, 1, 0.1)
        ),
        make_token_event(
            repo="alpha", session_id="s2",
            session_total=make_session_total(1, 1, 1, 1, 0.2)
        ),
        make_token_event(
            repo="beta", session_id="s3",
            session_total=make_session_total(10, 10, 10, 10, 1.0)
        ),
    ]
    per_repo = compute_per_repo_tokens(events)
    assert set(per_repo.keys()) == {"alpha", "beta"}
    assert per_repo["alpha"]["total_cost_usd"] == pytest.approx(0.3)
    assert per_repo["alpha"]["session_count"] == 2
    assert per_repo["beta"]["total_tokens"] == 40


# ── compute_per_branch_tokens ─────────────────────────────────────────────


def test_per_branch_tokens_groups_by_repo_and_branch():
    events = [
        make_token_event(
            repo="alpha", branch="feat/x", session_id="s1",
            session_total=make_session_total(10, 0, 0, 0, 0.1)
        ),
        make_token_event(
            repo="alpha", branch="feat/x", session_id="s2",
            session_total=make_session_total(20, 0, 0, 0, 0.2)
        ),
        make_token_event(
            repo="alpha", branch="feat/y", session_id="s3",
            session_total=make_session_total(5, 0, 0, 0, 0.05)
        ),
    ]
    per_branch = compute_per_branch_tokens(events)
    # Key is "repo/branch" to avoid collisions across repos
    assert "alpha/feat/x" in per_branch
    assert "alpha/feat/y" in per_branch
    assert per_branch["alpha/feat/x"]["total_tokens"] == 30
    assert per_branch["alpha/feat/x"]["session_count"] == 2


# ── compute_per_pr_tokens ─────────────────────────────────────────────────


def test_per_pr_tokens_groups_by_pr_number():
    events = [
        make_token_event(
            pr_number=139, session_id="s1",
            session_total=make_session_total(100, 0, 0, 0, 1.0)
        ),
        make_token_event(
            pr_number=139, session_id="s2",
            session_total=make_session_total(50, 0, 0, 0, 0.5)
        ),
        make_token_event(
            pr_number=140, session_id="s3",
            session_total=make_session_total(10, 0, 0, 0, 0.1)
        ),
        make_token_event(
            pr_number=None, session_id="s4",
            session_total=make_session_total(5, 0, 0, 0, 0.05)
        ),
    ]
    per_pr = compute_per_pr_tokens(events)
    # Only PRs with a number are included
    assert 139 in per_pr
    assert 140 in per_pr
    assert None not in per_pr
    assert per_pr[139]["total_cost_usd"] == pytest.approx(1.5)
    assert per_pr[139]["session_count"] == 2


# ── compute_cost_trends ───────────────────────────────────────────────────


def test_cost_trends_buckets_by_date():
    events = [
        make_token_event(
            timestamp="2026-04-10T10:00:00Z", session_id="s1",
            session_total=make_session_total(100, 0, 0, 0, 1.0)
        ),
        make_token_event(
            timestamp="2026-04-10T14:00:00Z", session_id="s2",
            session_total=make_session_total(50, 0, 0, 0, 0.5)
        ),
        make_token_event(
            timestamp="2026-04-11T08:00:00Z", session_id="s3",
            session_total=make_session_total(10, 0, 0, 0, 0.1)
        ),
    ]
    trends = compute_cost_trends(events)
    # Sorted by date ascending
    dates = [t["date"] for t in trends]
    assert dates == ["2026-04-10", "2026-04-11"]
    day1 = next(t for t in trends if t["date"] == "2026-04-10")
    assert day1["cost_usd"] == pytest.approx(1.5)
    assert day1["session_count"] == 2


# ── compute_top_sessions ──────────────────────────────────────────────────


def test_top_sessions_sorts_by_cost_descending():
    events = [
        make_token_event(
            session_id="cheap",
            session_total=make_session_total(10, 0, 0, 0, 0.1)
        ),
        make_token_event(
            session_id="expensive",
            session_total=make_session_total(100, 0, 0, 0, 10.0)
        ),
        make_token_event(
            session_id="medium",
            session_total=make_session_total(50, 0, 0, 0, 1.0)
        ),
    ]
    top = compute_top_sessions(events, limit=2)
    assert len(top) == 2
    assert top[0]["session_id"] == "expensive"
    assert top[1]["session_id"] == "medium"


def test_top_sessions_default_limit():
    """Default limit should be reasonable (10)."""
    events = [
        make_token_event(
            session_id=f"s{i}",
            session_total=make_session_total(i, 0, 0, 0, float(i))
        )
        for i in range(1, 21)
    ]
    top = compute_top_sessions(events)
    assert len(top) == 10
    assert top[0]["session_id"] == "s20"


# ── load_token_events ─────────────────────────────────────────────────────


def test_load_token_events_reads_json_files(tmp_path):
    import json

    d = tmp_path / "data" / "alpha" / "feat-x"
    d.mkdir(parents=True)
    (d / "sess-1-tokens.json").write_text(json.dumps(make_token_event(
        session_id="s1",
        session_total=make_session_total(10, 0, 0, 0, 0.1),
    )))
    (d / "sess-2-tokens.json").write_text(json.dumps(make_token_event(
        session_id="s2",
        session_total=make_session_total(20, 0, 0, 0, 0.2),
    )))
    # Gate metric (not a token event) — should be filtered out
    (d / "sha-gate-ts.json").write_text(json.dumps({
        "repo": "alpha", "branch": "feat-x",
        "gates_first_pass": True,
    }))

    events = load_token_events(str(tmp_path / "data"))
    assert len(events) == 2
    assert {e["session_id"] for e in events} == {"s1", "s2"}
