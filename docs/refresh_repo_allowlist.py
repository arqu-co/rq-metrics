#!/usr/bin/env python3
"""Refresh ``data/_arqu-co-repos.json`` from the GitHub API.

UNION semantics — never shrinks. The committed allowlist is the lower
bound; new repos visible to the current token are added. CI's
``secrets.GITHUB_TOKEN`` can only see public repos (≈10 of 91), so an
overwriting refresh would delete every private-repo entry and the
aggregator would drop every event from work in those repos. arqu-co/
rq-metrics first hit this on the deploy after https://github.com/
arqu-co/rq-metrics/pull/18 — token events fell from 398 to 18 because
the live allowlist shrank to the public-only subset.

To intentionally remove a repo, edit the committed file by hand.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

ALLOWLIST_PATH = "data/_arqu-co-repos.json"
ORG = "arqu-co"


def fetch_repo_names(org: str) -> list[str]:
    """Return sorted repo names for ``org`` via the gh CLI."""
    result = subprocess.run(
        ["gh", "api", "--paginate", f"orgs/{org}/repos", "--jq", ".[].name"],
        capture_output=True,
        check=True,
        text=True,
        timeout=60,
    )
    return sorted(name for name in result.stdout.split() if name)


def load_existing_repos(path: str) -> list[str]:
    """Return the repos already committed at ``path``, or [] when missing."""
    try:
        with open(path) as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return []
    repos = data.get("repos") or []
    return [str(r) for r in repos if r]


def write_allowlist(path: str, org: str, repos: list[str]) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        json.dump({"org": org, "repos": repos}, f, indent=2)
        f.write("\n")


def main() -> int:
    existing = load_existing_repos(ALLOWLIST_PATH)
    try:
        fresh = fetch_repo_names(ORG)
    except (subprocess.CalledProcessError, FileNotFoundError,
            subprocess.TimeoutExpired) as exc:
        print(f"refresh_repo_allowlist: skipped ({exc})", file=sys.stderr)
        return 0
    merged = sorted(set(existing) | set(fresh))
    added = sorted(set(fresh) - set(existing))
    write_allowlist(ALLOWLIST_PATH, ORG, merged)
    print(
        f"refresh_repo_allowlist: {len(existing)} existing + "
        f"{len(fresh)} fetched -> {len(merged)} merged "
        f"({len(added)} new)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
