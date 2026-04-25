"""Regression tests for the per-issue token rollup (rq-metrics#15)."""

import pytest

from helpers_tokens import make_session_total, make_token_event

from aggregate_tokens import build_token_payload
from aggregate_tokens_issue import compute_per_issue_tokens


def test_per_issue_tokens_extracts_issue_from_branch():
    # Events emitted from issue branches do not carry pr_number, so the
    # per-issue dollar column was empty on the dashboard. Issue numbers
    # are parsed from branch names matching ^issue-(\d+)-.
    events = [
        make_token_event(
            repo="alpha", branch="issue-42-fix-thing", session_id="s1",
            pr_number=None,
            session_total=make_session_total(10, 0, 0, 0, 0.5),
        ),
        make_token_event(
            repo="alpha", branch="issue-42-fix-thing", session_id="s2",
            pr_number=None,
            session_total=make_session_total(20, 0, 0, 0, 0.25),
        ),
        make_token_event(
            repo="beta", branch="issue-7-other", session_id="s3",
            pr_number=None,
            session_total=make_session_total(5, 0, 0, 0, 0.1),
        ),
        # Branch without an issue prefix is dropped from the per-issue rollup
        make_token_event(
            repo="alpha", branch="feat/no-issue", session_id="s4",
            pr_number=None,
            session_total=make_session_total(1, 0, 0, 0, 0.99),
        ),
    ]
    per_issue = compute_per_issue_tokens(events)
    assert set(per_issue.keys()) == {"alpha#42", "beta#7"}
    assert per_issue["alpha#42"]["total_cost_usd"] == pytest.approx(0.75)
    assert per_issue["alpha#42"]["session_count"] == 2
    assert per_issue["beta#7"]["total_cost_usd"] == pytest.approx(0.1)


def test_build_token_payload_includes_per_issue():
    # Acceptance criteria: dashboard payload exposes a non-empty per-issue
    # dollar rollup whenever any event branch encodes an issue number.
    events = [
        make_token_event(
            repo="alpha", branch="issue-15-rq-metrics-fix-broken-column",
            session_id="s1", pr_number=None,
            session_total=make_session_total(10, 0, 0, 0, 1.23),
        ),
    ]
    payload = build_token_payload(events)
    assert "per_issue" in payload
    assert payload["per_issue"]["alpha#15"]["total_cost_usd"] == pytest.approx(1.23)


def test_per_issue_tokens_handles_empty_events():
    assert compute_per_issue_tokens([]) == {}


def test_per_issue_tokens_handles_missing_branch():
    events = [make_token_event(branch=None, pr_number=None)]
    assert compute_per_issue_tokens(events) == {}
