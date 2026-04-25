#!/usr/bin/env python3
"""Regenerate ``data/_arqu-co-repos.json`` from the GitHub API.

Idempotent — sorted output, stable JSON. Safe to run repeatedly.
Offline failure leaves the existing committed file untouched.
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


def write_allowlist(path: str, org: str, repos: list[str]) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        json.dump({"org": org, "repos": repos}, f, indent=2)
        f.write("\n")


def main() -> int:
    try:
        repos = fetch_repo_names(ORG)
    except (subprocess.CalledProcessError, FileNotFoundError,
            subprocess.TimeoutExpired) as exc:
        print(f"refresh_repo_allowlist: skipped ({exc})", file=sys.stderr)
        return 0
    write_allowlist(ALLOWLIST_PATH, ORG, repos)
    print(f"wrote {len(repos)} repos to {ALLOWLIST_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
