"""Tests for the per-group rollups in aggregate_tokens (repo/branch/PR)."""

import pytest

from helpers_tokens import make_session_total, make_token_event

from aggregate_tokens import (
    compute_cost_trends,
    compute_per_branch_tokens,
    compute_per_pr_tokens,
    compute_per_repo_tokens,
    compute_top_sessions,
    load_token_events,
)


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
    assert "alpha/feat/x" in per_branch
    assert "alpha/feat/y" in per_branch
    assert per_branch["alpha/feat/x"]["total_tokens"] == 30
    assert per_branch["alpha/feat/x"]["session_count"] == 2


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
    assert 139 in per_pr
    assert 140 in per_pr
    assert None not in per_pr
    assert per_pr[139]["total_cost_usd"] == pytest.approx(1.5)
    assert per_pr[139]["session_count"] == 2


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
    dates = [t["date"] for t in trends]
    assert dates == ["2026-04-10", "2026-04-11"]
    day1 = next(t for t in trends if t["date"] == "2026-04-10")
    assert day1["cost_usd"] == pytest.approx(1.5)
    assert day1["session_count"] == 2


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
    (d / "sha-gate-ts.json").write_text(json.dumps({
        "repo": "alpha", "branch": "feat-x",
        "gates_first_pass": True,
    }))

    events = load_token_events(str(tmp_path / "data"))
    assert len(events) == 2
    assert {e["session_id"] for e in events} == {"s1", "s2"}
