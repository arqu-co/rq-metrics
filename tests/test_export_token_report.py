"""Tests for docs/export_token_report.py — md/json/csv exports."""

import csv as _csv
import io
import json

import pytest

from helpers_tokens import make_session_total, make_token_event

from export_token_report import (
    _per_issue_rollup,
    build_summary,
    filter_events,
    parse_scope,
    render_csv,
    render_json,
    render_markdown,
)


# ── parse_scope ──────────────────────────────────────────────────────────────


def test_parse_scope_all():
    assert parse_scope("all") == ("all", None)


def test_parse_scope_user_with_value():
    assert parse_scope("user:alice") == ("user", "alice")


def test_parse_scope_repo_with_value():
    assert parse_scope("repo:agent-plugins") == ("repo", "agent-plugins")


def test_parse_scope_issue_with_full_key():
    assert parse_scope("issue:agent-plugins#15") == ("issue", "agent-plugins#15")


def test_parse_scope_invalid_kind_raises():
    with pytest.raises(ValueError):
        parse_scope("garbage:foo")


def test_parse_scope_missing_value_raises():
    with pytest.raises(ValueError):
        parse_scope("user:")


# ── filter_events ────────────────────────────────────────────────────────────


def _events():
    return [
        make_token_event(user="alice", repo="alpha",
                         branch="issue-15-fix-thing", timestamp="2026-04-01T00:00:00Z",
                         session_id="s1",
                         session_total=make_session_total(10, 0, 0, 0, 1.0)),
        make_token_event(user="alice", repo="beta",
                         branch="issue-7-other", timestamp="2026-04-10T00:00:00Z",
                         session_id="s2",
                         session_total=make_session_total(20, 0, 0, 0, 2.0)),
        make_token_event(user="bob", repo="alpha",
                         branch="feat/no-issue", timestamp="2026-04-15T00:00:00Z",
                         session_id="s3",
                         session_total=make_session_total(5, 0, 0, 0, 0.5)),
    ]


def test_filter_all_returns_everything():
    assert len(filter_events(_events(), ("all", None), days=None)) == 3


def test_filter_by_user():
    out = filter_events(_events(), ("user", "alice"), days=None)
    assert {e["session_id"] for e in out} == {"s1", "s2"}


def test_filter_by_repo():
    out = filter_events(_events(), ("repo", "alpha"), days=None)
    assert {e["session_id"] for e in out} == {"s1", "s3"}


def test_filter_by_issue_uses_branch_parser():
    """Issue scope keys on '<repo>#<N>' parsed from the branch."""
    out = filter_events(_events(), ("issue", "alpha#15"), days=None)
    assert {e["session_id"] for e in out} == {"s1"}


def test_filter_by_days():
    """`--days=N` keeps only events within the last N days from the
    reference time."""
    from datetime import datetime, timezone
    now = datetime(2026, 4, 16, 0, 0, 0, tzinfo=timezone.utc)
    out = filter_events(_events(), ("all", None), days=10, now=now)
    # 2026-04-06 cutoff → only s2 (04-10) and s3 (04-15) survive.
    assert {e["session_id"] for e in out} == {"s2", "s3"}


# ── per_issue_rollup ─────────────────────────────────────────────────────────


def test_per_issue_rollup_groups_by_repo_and_issue():
    events = [
        make_token_event(repo="alpha", branch="issue-42-foo", session_id="s1",
                         session_total=make_session_total(10, 0, 0, 0, 0.5)),
        make_token_event(repo="alpha", branch="issue-42-foo", session_id="s2",
                         session_total=make_session_total(20, 0, 0, 0, 0.25)),
        make_token_event(repo="beta", branch="issue-7-bar", session_id="s3",
                         session_total=make_session_total(5, 0, 0, 0, 0.1)),
        make_token_event(repo="alpha", branch="feat/no-issue", session_id="s4",
                         session_total=make_session_total(99, 0, 0, 0, 9.99)),
    ]
    rows = _per_issue_rollup(events)
    assert {r["key"] for r in rows} == {"alpha#42", "beta#7"}
    alpha = next(r for r in rows if r["key"] == "alpha#42")
    assert alpha["sessions"] == 2
    assert alpha["cost_usd"] == pytest.approx(0.75)
    assert alpha["tokens"] == 30


# ── render_json ──────────────────────────────────────────────────────────────


def test_render_json_emits_stable_schema():
    events = [make_token_event(repo="alpha", branch="issue-15-fix",
                               session_total=make_session_total(10, 0, 0, 0, 1.0))]
    out = json.loads(render_json(events, ("all", None)))
    assert out["schema_version"] == 1
    assert out["scope"] == {"kind": "all", "value": None}
    assert out["summary"]["session_count"] == 1
    assert out["summary"]["total_cost_usd"] == 1.0
    assert out["per_issue"][0]["key"] == "alpha#15"


# ── render_csv ───────────────────────────────────────────────────────────────


def test_render_csv_has_header_and_rows():
    events = [
        make_token_event(repo="alpha", branch="issue-15-fix", session_id="s1",
                         session_total=make_session_total(10, 0, 0, 0, 1.0)),
        make_token_event(repo="beta", branch="issue-7-thing", session_id="s2",
                         session_total=make_session_total(5, 0, 0, 0, 0.5)),
    ]
    out = render_csv(events)
    rows = list(_csv.reader(io.StringIO(out)))
    assert rows[0] == ["repo", "issue_number", "sessions", "tokens", "cost_usd"]
    assert len(rows) == 3  # header + 2
    # Sorted by cost desc — alpha#15 first.
    assert rows[1][:2] == ["alpha", "15"]


# ── render_markdown ──────────────────────────────────────────────────────────


def test_render_markdown_includes_summary_and_table():
    events = [
        make_token_event(repo="alpha", branch="issue-15-fix",
                         timestamp="2026-04-10T10:00:00Z", session_id="s1",
                         session_total=make_session_total(10, 0, 0, 0, 1.5)),
    ]
    out = render_markdown(events, ("all", None))
    assert "Token cost report" in out
    assert "**Sessions:** 1" in out
    assert "alpha#15" in out
    assert "$1.50" in out
    assert "2026-04-10" in out


def test_render_markdown_handles_no_issue_tagged_events():
    events = [
        make_token_event(repo="alpha", branch="feat/no-issue",
                         session_total=make_session_total(10, 0, 0, 0, 1.0)),
    ]
    out = render_markdown(events, ("all", None))
    assert "No issue-tagged events" in out


def test_render_markdown_truncates_long_issue_lists():
    events = [
        make_token_event(repo="alpha", branch=f"issue-{i}-thing",
                         session_id=f"s{i}",
                         session_total=make_session_total(1, 0, 0, 0, float(i)))
        for i in range(1, 26)
    ]
    out = render_markdown(events, ("all", None))
    assert "5 more issues" in out  # 25 - 20 = 5
