"""Test helpers for token_usage aggregation tests."""


def make_token_event(**overrides):
    """Build a token-usage event dict with sensible defaults.

    The shape matches what the rq plugin's collect-token-metrics.sh
    emits: one JSON file per session, stored under
    data/<repo>/<branch>/<session_id>-tokens.json.
    """
    base = {
        "event_type": "token_usage",
        "repo": "test-repo",
        "branch": "feat/test",
        "sha": "abc1234",
        "user": "tester",
        "user_email": "tester@example.com",
        "timestamp": "2026-04-10T12:00:00Z",
        "session_id": "sess-1",
        "pr_number": None,
        "pr_url": None,
        "models_seen": ["claude-sonnet-4-6"],
        "session_total": {
            "input": 100,
            "output": 200,
            "cache_read": 3000,
            "cache_create": 400,
            "est_cost_usd": 0.01,
        },
        "phases": {
            "pair-build": {"tokens": 3700, "cost_usd": 0.01},
        },
    }
    base.update(overrides)
    return base


def make_session_total(
    input_tokens=0,
    output=0,
    cache_read=0,
    cache_create=0,
    est_cost_usd=0.0,
):
    """Build a session_total dict for token events."""
    return {
        "input": input_tokens,
        "output": output,
        "cache_read": cache_read,
        "cache_create": cache_create,
        "est_cost_usd": est_cost_usd,
    }
