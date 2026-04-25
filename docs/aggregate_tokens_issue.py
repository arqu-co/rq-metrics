"""Per-issue token rollup.

Token events emitted from issue branches do not carry ``pr_number``,
so the dashboard's per-PR rollup is empty for in-flight issue work.
This module derives an issue number from the branch name and produces
a per-issue dollar/token rollup keyed by ``"repo#issue"``.
"""

from __future__ import annotations

import re
from collections import defaultdict

from aggregate_tokens import _accumulate, _empty_group_stats, _finalize

_ISSUE_BRANCH_RE = re.compile(r"^issue-(\d+)-")


def _issue_number_from_branch(branch: str | None) -> str | None:
    if not branch:
        return None
    match = _ISSUE_BRANCH_RE.match(branch)
    return match.group(1) if match else None


def compute_per_issue_tokens(events: list[dict]) -> dict[str, dict]:
    """Per-issue token totals keyed by ``"repo#issue"``.

    Issue numbers are parsed from branch names matching ``^issue-(\\d+)-``.
    Events whose branch does not encode an issue are dropped — they show
    up in the per-branch rollup instead. ``pr_number`` is intentionally
    ignored: events from in-flight issue work do not yet carry a PR.
    """
    by_issue: dict[str, dict] = defaultdict(_empty_group_stats)
    for event in events:
        issue = _issue_number_from_branch(event.get("branch"))
        if issue is None:
            continue
        repo = event.get("repo", "unknown")
        key = f"{repo}#{issue}"
        stats = by_issue[key]
        stats["display_name"] = key
        _accumulate(stats, event)
    return {k: _finalize(v) for k, v in by_issue.items()}
