#!/usr/bin/env python3
"""Generate paste-ready token-cost reports for stakeholders.

Reads the same token-usage events the dashboard renders from and emits
one of three formats:

- ``md``   — self-contained markdown block, paste into a PR/Slack/Confluence.
- ``json`` — stable schema for downstream tools.
- ``csv``  — flat per-issue rows for spreadsheet drop.

The tool generates content; a human delivers it. No HTTP calls, no
scheduled runs, no notifications. arqu-co/rq-metrics#13.

Usage:

    python3 docs/export_token_report.py --format=md
    python3 docs/export_token_report.py --format=csv --scope=repo:agent-plugins
    python3 docs/export_token_report.py --format=json --scope=issue:agent-plugins#15
    python3 docs/export_token_report.py --format=md --days=7
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(__file__))

from aggregate_tokens import load_token_events  # noqa: E402
from aggregate_tokens_issue import _issue_number_from_branch  # noqa: E402

SCHEMA_VERSION = 1

_SCOPE_RE = re.compile(r"^(user|repo|issue|all)(?::(.+))?$")


def parse_scope(spec: str) -> tuple[str, str | None]:
    """Parse a ``--scope`` value into (kind, value).

    ``all`` (or no argument) returns ``("all", None)``.
    """
    match = _SCOPE_RE.match(spec)
    if not match:
        raise ValueError(f"invalid --scope: {spec!r}")
    kind, value = match.group(1), match.group(2)
    if kind != "all" and not value:
        raise ValueError(f"--scope={kind} requires a value")
    return kind, value


def filter_events(events: list[dict], scope: tuple[str, str | None],
                  days: int | None, *, now: datetime | None = None) -> list[dict]:
    """Apply scope and date filters."""
    kind, value = scope
    cutoff = None
    if days is not None and days > 0:
        ref = now or datetime.now(timezone.utc)
        cutoff = (ref - timedelta(days=days)).isoformat()
    out = []
    for event in events:
        if cutoff and event.get("timestamp", "") < cutoff:
            continue
        if kind == "user" and event.get("user") != value:
            continue
        if kind == "repo" and event.get("repo") != value:
            continue
        if kind == "issue":
            issue = _issue_number_from_branch(event.get("branch"))
            key = f"{event.get('repo', 'unknown')}#{issue}" if issue else None
            if key != value:
                continue
        out.append(event)
    return out


def _bucket_tokens(session_total: dict) -> int:
    return sum(session_total.get(k, 0) or 0
               for k in ("input", "output", "cache_read", "cache_create"))


def _per_issue_rollup(events: list[dict]) -> list[dict]:
    """Rows of ``{repo, issue_number, sessions, tokens, cost_usd}``."""
    by_issue: dict[str, dict] = {}
    for event in events:
        issue = _issue_number_from_branch(event.get("branch"))
        if issue is None:
            continue
        repo = event.get("repo", "unknown")
        key = f"{repo}#{issue}"
        st = event.get("session_total", {}) or {}
        row = by_issue.setdefault(key, {
            "key": key, "repo": repo, "issue_number": issue,
            "sessions": 0, "tokens": 0, "cost_usd": 0.0,
        })
        row["sessions"] += 1
        row["tokens"] += _bucket_tokens(st)
        cost = st.get("est_cost_usd")
        if cost is not None:
            row["cost_usd"] += cost
    rows = list(by_issue.values())
    rows.sort(key=lambda r: -r["cost_usd"])
    for r in rows:
        r["cost_usd"] = round(r["cost_usd"], 4)
    return rows


def build_summary(events: list[dict]) -> dict:
    total_tokens = 0
    total_cost = 0.0
    timestamps = []
    for event in events:
        st = event.get("session_total", {}) or {}
        total_tokens += _bucket_tokens(st)
        cost = st.get("est_cost_usd")
        if cost is not None:
            total_cost += cost
        ts = event.get("timestamp")
        if ts:
            timestamps.append(ts)
    timestamps.sort()
    return {
        "session_count": len(events),
        "total_tokens": total_tokens,
        "total_cost_usd": round(total_cost, 4),
        "date_from": timestamps[0] if timestamps else None,
        "date_to": timestamps[-1] if timestamps else None,
    }


def render_json(events: list[dict], scope: tuple[str, str | None]) -> str:
    payload = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "scope": {"kind": scope[0], "value": scope[1]},
        "summary": build_summary(events),
        "per_issue": _per_issue_rollup(events),
    }
    return json.dumps(payload, indent=2) + "\n"


def render_csv(events: list[dict]) -> str:
    rows = _per_issue_rollup(events)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["repo", "issue_number", "sessions", "tokens", "cost_usd"])
    for r in rows:
        writer.writerow([r["repo"], r["issue_number"], r["sessions"],
                         r["tokens"], r["cost_usd"]])
    return buf.getvalue()


def _fmt_cost(n: float) -> str:
    if n >= 10000:
        return f"${round(n):,}"
    if n >= 100:
        return f"${n:.0f}"
    return f"${n:.2f}"


def _fmt_tokens(n: int) -> str:
    if n >= 1_000_000_000:
        return f"{n / 1e9:.2f}B"
    if n >= 1_000_000:
        return f"{n / 1e6:.2f}M"
    if n >= 1_000:
        return f"{n / 1e3:.1f}K"
    return str(n)


def render_markdown(events: list[dict], scope: tuple[str, str | None]) -> str:
    summary = build_summary(events)
    rows = _per_issue_rollup(events)
    scope_label = "all sessions" if scope[0] == "all" else f"{scope[0]}: {scope[1]}"
    date_span = "no events"
    if summary["date_from"] and summary["date_to"]:
        date_span = f"{summary['date_from'][:10]} → {summary['date_to'][:10]}"
    lines = [
        f"## Token cost report — {scope_label}",
        "",
        f"- **Sessions:** {summary['session_count']}",
        f"- **Total cost:** {_fmt_cost(summary['total_cost_usd'])}",
        f"- **Total tokens:** {_fmt_tokens(summary['total_tokens'])}",
        f"- **Date span:** {date_span}",
        "",
    ]
    if rows:
        lines.append("### Per-issue breakdown")
        lines.append("")
        lines.append("| Issue | Sessions | Tokens | Cost |")
        lines.append("|---|---:|---:|---:|")
        for r in rows[:20]:
            lines.append(
                f"| {r['repo']}#{r['issue_number']} | {r['sessions']} | "
                f"{_fmt_tokens(r['tokens'])} | {_fmt_cost(r['cost_usd'])} |"
            )
        if len(rows) > 20:
            lines.append(f"| _…{len(rows) - 20} more issues_ | | | |")
    else:
        lines.append("_No issue-tagged events in scope._")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--format", choices=["md", "json", "csv"], required=True)
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--scope", default="all",
                        help="all | user:<name> | repo:<name> | issue:<repo>#<n>")
    parser.add_argument("--days", type=int, default=None,
                        help="Restrict to events from the last N days.")
    args = parser.parse_args(argv)

    scope = parse_scope(args.scope)
    events = filter_events(load_token_events(args.data_dir), scope, args.days)

    if args.format == "json":
        sys.stdout.write(render_json(events, scope))
    elif args.format == "csv":
        sys.stdout.write(render_csv(events))
    else:
        sys.stdout.write(render_markdown(events, scope))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
