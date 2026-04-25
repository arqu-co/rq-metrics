"""Aggregate token-usage events into dashboard rollups.

Token events are emitted by the rq plugin's token-observability feature
and live alongside the existing gate metrics events under data/. They
are distinguishable by `event_type == "token_usage"`. Each event
represents one Claude Code session and carries:

  - repo, branch, sha, user, user_email, timestamp
  - session_id, pr_number, pr_url
  - models_seen (list[str])
  - session_total: {input, output, cache_read, cache_create, est_cost_usd}
  - phases: {phase_name: {tokens, cost_usd}}

This module computes:
  - summary (total tokens, total cost, cache ratio, unpriced count)
  - per_user rollup + cost leaderboard
  - per_repo, per_branch, per_pr rollups
  - daily cost trend
  - top N most expensive sessions
"""

from __future__ import annotations

import glob
import json
import os
from collections import defaultdict
from typing import Iterable

_TOKEN_KEYS = ("input", "output", "cache_read", "cache_create")


def is_token_event(record: dict) -> bool:
    """Return True when the record is a token-usage event."""
    return record.get("event_type") == "token_usage"


def load_token_events(data_dir: str = "data") -> list[dict]:
    """Load token-usage events from a data directory.

    Skips gate metric files and any JSON that does not have
    event_type == "token_usage". Safe to run against mixed directories.
    """
    events: list[dict] = []
    pattern = os.path.join(data_dir, "**/*.json")
    for filepath in glob.glob(pattern, recursive=True):
        try:
            with open(filepath) as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        if is_token_event(data):
            data["_file"] = filepath
            events.append(data)
    return events


def _bucket_tokens(session_total: dict) -> int:
    """Sum the four token bucket fields, tolerating missing keys."""
    return sum(session_total.get(k, 0) or 0 for k in _TOKEN_KEYS)


def compute_token_summary(events: list[dict]) -> dict:
    """Compute aggregate token summary across all events."""
    if not events:
        return {
            "total_tokens": 0,
            "total_cost_usd": 0.0,
            "session_count": 0,
            "unpriced_sessions": 0,
            "cache_ratio": 0.0,
        }

    total_tokens = 0
    total_cost = 0.0
    unpriced = 0
    cache_tokens = 0

    for event in events:
        st = event.get("session_total", {})
        total_tokens += _bucket_tokens(st)
        cache_tokens += (st.get("cache_read", 0) or 0) + (st.get("cache_create", 0) or 0)
        cost = st.get("est_cost_usd")
        if cost is None:
            unpriced += 1
        else:
            total_cost += cost

    return {
        "total_tokens": total_tokens,
        "total_cost_usd": round(total_cost, 4),
        "session_count": len(events),
        "unpriced_sessions": unpriced,
        "cache_ratio": (
            round(cache_tokens / total_tokens, 4) if total_tokens else 0.0
        ),
    }


def _resolve_user_key(event: dict) -> str | None:
    """Derive a stable user key (name or email-localpart)."""
    name = event.get("user", "unknown")
    if name and name != "unknown":
        return name
    email = (event.get("user_email") or "").strip()
    if email:
        return email.split("@")[0]
    return None


def _empty_group_stats() -> dict:
    return {
        "display_name": "",
        "total_tokens": 0,
        "total_cost_usd": 0.0,
        "session_count": 0,
        "unpriced_sessions": 0,
    }


def _accumulate(stats: dict, event: dict) -> None:
    """Add an event into a per-group stats dict (user/repo/branch/PR)."""
    st = event.get("session_total", {})
    stats["total_tokens"] += _bucket_tokens(st)
    stats["session_count"] += 1
    cost = st.get("est_cost_usd")
    if cost is None:
        stats["unpriced_sessions"] += 1
    else:
        stats["total_cost_usd"] += cost


def _finalize(stats: dict, *, display_name: str | None = None) -> dict:
    """Round cost and attach display_name to a per-group stats dict."""
    stats["display_name"] = display_name or stats.get("display_name", "")
    stats["total_cost_usd"] = round(stats["total_cost_usd"], 4)
    return stats


def compute_per_user_tokens(events: list[dict]) -> dict[str, dict]:
    """Return per-user token totals keyed by user name."""
    by_user: dict[str, dict] = defaultdict(_empty_group_stats)
    for event in events:
        key = _resolve_user_key(event)
        if key is None:
            continue
        stats = by_user[key]
        stats["display_name"] = key
        _accumulate(stats, event)
    return {k: _finalize(v) for k, v in by_user.items()}


def compute_token_leaderboard(per_user: dict[str, dict]) -> list[dict]:
    """Rank users by total cost descending, None cost last."""
    entries = []
    for user_key, stats in per_user.items():
        entries.append({
            "user": user_key,
            "display_name": stats.get("display_name") or user_key,
            "total_cost_usd": stats.get("total_cost_usd"),
            "total_tokens": stats.get("total_tokens", 0),
            "session_count": stats.get("session_count", 0),
            "unpriced_sessions": stats.get("unpriced_sessions", 0),
        })
    entries.sort(
        key=lambda e: (
            e["total_cost_usd"] is None,
            -(e["total_cost_usd"] or 0.0),
        )
    )
    for i, entry in enumerate(entries):
        entry["rank"] = i + 1
    return entries


def compute_per_repo_tokens(events: list[dict]) -> dict[str, dict]:
    """Return per-repo token totals keyed by repo name."""
    by_repo: dict[str, dict] = defaultdict(_empty_group_stats)
    for event in events:
        repo = event.get("repo", "unknown")
        stats = by_repo[repo]
        stats["display_name"] = repo
        _accumulate(stats, event)
    return {k: _finalize(v) for k, v in by_repo.items()}


def compute_per_branch_tokens(events: list[dict]) -> dict[str, dict]:
    """Return per-branch token totals keyed by "repo/branch"."""
    by_branch: dict[str, dict] = defaultdict(_empty_group_stats)
    for event in events:
        repo = event.get("repo", "unknown")
        branch = event.get("branch") or "(unknown)"
        key = f"{repo}/{branch}"
        stats = by_branch[key]
        stats["display_name"] = key
        _accumulate(stats, event)
    return {k: _finalize(v) for k, v in by_branch.items()}


def compute_per_pr_tokens(events: list[dict]) -> dict[int, dict]:
    """Return per-PR token totals keyed by PR number. Drops None."""
    by_pr: dict[int, dict] = defaultdict(_empty_group_stats)
    for event in events:
        pr = event.get("pr_number")
        if pr is None:
            continue
        stats = by_pr[pr]
        stats["display_name"] = f"#{pr}"
        _accumulate(stats, event)
    return {k: _finalize(v) for k, v in by_pr.items()}


def compute_cost_trends(events: list[dict]) -> list[dict]:
    """Daily cost trend sorted ascending by date."""
    by_date: dict[str, dict] = defaultdict(lambda: {
        "cost_usd": 0.0,
        "tokens": 0,
        "session_count": 0,
    })
    for event in events:
        ts = event.get("timestamp", "")
        date = ts[:10] if len(ts) >= 10 else "unknown"
        day = by_date[date]
        st = event.get("session_total", {})
        day["tokens"] += _bucket_tokens(st)
        day["session_count"] += 1
        cost = st.get("est_cost_usd")
        if cost is not None:
            day["cost_usd"] += cost
    return [
        {"date": d, **{k: round(v, 4) if k == "cost_usd" else v
                       for k, v in stats.items()}}
        for d, stats in sorted(by_date.items())
    ]


def compute_top_sessions(
    events: list[dict], limit: int = 10
) -> list[dict]:
    """Return the top N most expensive sessions by est_cost_usd."""
    priced = [
        e for e in events
        if (e.get("session_total", {}) or {}).get("est_cost_usd") is not None
    ]
    priced.sort(
        key=lambda e: -(e["session_total"]["est_cost_usd"] or 0.0)
    )
    out = []
    for event in priced[:limit]:
        st = event.get("session_total", {})
        out.append({
            "session_id": event.get("session_id", ""),
            "repo": event.get("repo", ""),
            "branch": event.get("branch", ""),
            "user": event.get("user", ""),
            "timestamp": event.get("timestamp", ""),
            "total_tokens": _bucket_tokens(st),
            "total_cost_usd": st.get("est_cost_usd"),
            "pr_number": event.get("pr_number"),
        })
    return out


def build_token_payload(events: list[dict]) -> dict:
    """Build the dashboard-ready token payload from token events."""
    from aggregate_tokens_issue import compute_per_issue_tokens as _per_issue

    per_user = compute_per_user_tokens(events)
    return {
        "summary": compute_token_summary(events),
        "per_user": per_user,
        "leaderboard": compute_token_leaderboard(per_user),
        "per_repo": compute_per_repo_tokens(events),
        "per_branch": compute_per_branch_tokens(events),
        "per_pr": compute_per_pr_tokens(events),
        "per_issue": _per_issue(events),
        "cost_trends": compute_cost_trends(events),
        "top_sessions": compute_top_sessions(events),
        "event_count": len(events),
    }
