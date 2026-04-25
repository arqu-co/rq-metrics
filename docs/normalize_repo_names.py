#!/usr/bin/env python3
"""Normalize bogus repo directories before aggregation.

Two detection strategies:
  1. Pattern match: Docker-style random names (adjective-surname) from
     git worktrees — fast, no network, offline-safe.
  2. GitHub verify: any directory whose name does not correspond to a
     real repo in the configured org — exhaustive, requires `gh` CLI
     and network access. Catches directory-style bogus names (e.g. a
     local clone whose directory differs from the git remote name)
     that the pattern detector misses.

Modes:
  detect:        List worktree-pattern bogus dirs (default, offline).
  detect --verify-org ORG: List ALL bogus dirs via GitHub API.
  repair:        Rewrite repo field and move data. Accepts arbitrary
                 --map key=value regardless of detector opinion.

Usage:
  python3 normalize_repo_names.py data
  python3 normalize_repo_names.py data --verify-org arqu-co
  python3 normalize_repo_names.py data --repair billing-redux=ledger
"""

import glob
import json
import os
import re
import shutil
import subprocess
import sys

# Docker namesgenerator adjectives (subset — enough for reliable detection)
DOCKER_ADJECTIVES = frozenset([
    "admiring", "adoring", "affectionate", "agitated", "amazing",
    "angry", "awesome", "beautiful", "blissful", "bold", "boring",
    "brave", "busy", "charming", "clever", "compassionate", "competent",
    "condescending", "confident", "cool", "cranky", "crazy", "dazzling",
    "determined", "distracted", "dreamy", "eager", "ecstatic", "elastic",
    "elated", "elegant", "eloquent", "epic", "exciting", "fervent",
    "festive", "flamboyant", "focused", "friendly", "frosty", "funny",
    "gallant", "gifted", "goofy", "gracious", "great", "happy",
    "hardcore", "heuristic", "hopeful", "hungry", "infallible",
    "inspiring", "intelligent", "interesting", "jolly", "jovial", "keen",
    "kind", "laughing", "loving", "lucid", "magical", "modest",
    "musing", "mystifying", "naughty", "nervous", "nice", "nifty",
    "nostalgic", "objective", "optimistic", "peaceful", "pedantic",
    "pensive", "practical", "priceless", "quirky", "quizzical",
    "recursing", "relaxed", "reverent", "romantic", "sad", "serene",
    "sharp", "silly", "sleepy", "stoic", "strange", "stupefied",
    "suspicious", "sweet", "tender", "thirsty", "trusting", "unruffled",
    "upbeat", "vibrant", "vigilant", "vigorous", "wizardly", "wonderful",
    "xenodochial", "youthful", "zealous", "zen",
])

# Pattern: adjective-surname (all lowercase, single hyphen)
WORKTREE_NAME_RE = re.compile(r"^[a-z]+-[a-z]+$")


def is_worktree_name(name):
    """Return True if name looks like a Docker-style random worktree name."""
    if not WORKTREE_NAME_RE.match(name):
        return False
    adjective = name.split("-")[0]
    return adjective in DOCKER_ADJECTIVES


def repo_exists_in_org(org, name):
    """Return True if `gh api repos/<org>/<name>` returns 200.

    Uses the `gh` CLI exit code (NOT stdout parsing). On 404 the CLI
    prints the error JSON to stdout but exits non-zero — a naive
    non-empty-output check would falsely report the repo as existing.
    """
    try:
        result = subprocess.run(
            ["gh", "api", f"repos/{org}/{name}"],
            capture_output=True,
            check=False,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        # gh not installed or network slow — treat as unknown (don't
        # false-positive flag a real repo when we can't verify).
        return True
    return result.returncode == 0


def _load_cached_allowlist(data_dir):
    """Load the committed ``data/_arqu-co-repos.json`` allowlist.

    Returns the set of repo names. Returns an empty set when the file is
    missing or corrupt — caller should treat that as "filter disabled"
    rather than "everything bogus" and fall back to the live ``gh api``
    detector.
    """
    path = os.path.join(data_dir, "_arqu-co-repos.json")
    try:
        with open(path) as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return set()
    return {str(r) for r in (data.get("repos") or []) if r}


def find_bogus_repos_via_github(data_dir, org):
    """Return list of directory names that are NOT real repos in ``org``.

    Prefers the committed ``data/_arqu-co-repos.json`` allowlist so CI
    runs (whose ``GITHUB_TOKEN`` can only see public repos) don't
    false-positive every private-repo dir as bogus. Falls back to
    per-directory ``gh api`` only when the allowlist file is missing.
    """
    allowlist = _load_cached_allowlist(data_dir)
    bogus = []
    for entry in sorted(os.listdir(data_dir)):
        path = os.path.join(data_dir, entry)
        if not os.path.isdir(path) or entry.startswith("_"):
            continue
        if allowlist:
            if entry not in allowlist:
                bogus.append(entry)
        elif not repo_exists_in_org(org, entry):
            bogus.append(entry)
    return bogus


def find_bogus_repos(data_dir):
    """Return list of directory names that look like worktree names."""
    bogus = []
    for entry in sorted(os.listdir(data_dir)):
        path = os.path.join(data_dir, entry)
        if os.path.isdir(path) and is_worktree_name(entry):
            bogus.append(entry)
    return bogus


def repair_repo(data_dir, worktree_name, real_repo):
    """Rewrite repo field in all JSON files and move to correct directory.

    Returns the number of files repaired.
    """
    src_dir = os.path.join(data_dir, worktree_name)
    if not os.path.isdir(src_dir):
        return 0

    fixed = 0
    for fp in glob.glob(os.path.join(src_dir, "**/*.json"), recursive=True):
        with open(fp) as f:
            data = json.load(f)

        data["repo"] = real_repo
        branch = data.get("branch", "unknown")
        filename = os.path.basename(fp)
        dest_dir = os.path.join(data_dir, real_repo, branch)
        os.makedirs(dest_dir, exist_ok=True)

        with open(os.path.join(dest_dir, filename), "w") as f:
            json.dump(data, f, indent=2)
            f.write("\n")

        os.remove(fp)
        fixed += 1

    shutil.rmtree(src_dir, ignore_errors=True)
    return fixed


def _parse_args(argv):
    data_dir = argv[1] if len(argv) > 1 else "data"
    args = argv[2:]
    is_repair = "--repair" in args
    verify_org = None
    repo_map = {}
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--verify-org" and i + 1 < len(args):
            verify_org = args[i + 1]
            i += 2
            continue
        if arg.startswith("--"):
            i += 1
            continue
        if "=" in arg:
            worktree, real = arg.split("=", 1)
            repo_map[worktree] = real
        i += 1
    return data_dir, is_repair, verify_org, repo_map


def _do_repair(data_dir, repo_map):
    total = 0
    for name, real in repo_map.items():
        src_dir = os.path.join(data_dir, name)
        if not os.path.isdir(src_dir):
            print(f"  SKIP {name}: directory does not exist")
            continue
        count = repair_repo(data_dir, name, real)
        print(f"  Repaired {name} -> {real} ({count} files)")
        total += count
    print(f"\nRepaired {total} files total")


def _print_bogus_report(data_dir, bogus, label):
    if not bogus:
        print(f"No {label} repos detected.")
        return
    print(f"Found {len(bogus)} {label} repo(s):")
    for name in bogus:
        file_count = sum(
            len(files)
            for _, _, files in os.walk(os.path.join(data_dir, name))
        )
        print(f"  {name} ({file_count} files)")


def main():
    data_dir, is_repair, verify_org, repo_map = _parse_args(sys.argv)

    if is_repair and repo_map:
        _do_repair(data_dir, repo_map)
        return

    if verify_org:
        bogus = find_bogus_repos_via_github(data_dir, verify_org)
        _print_bogus_report(data_dir, bogus, f"non-{verify_org}")
    else:
        bogus = find_bogus_repos(data_dir)
        _print_bogus_report(data_dir, bogus, "worktree-named")


if __name__ == "__main__":
    main()
