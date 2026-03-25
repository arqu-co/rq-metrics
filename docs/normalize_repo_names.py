#!/usr/bin/env python3
"""Normalize worktree-named repo directories before aggregation.

Detects Docker-style random names (adjective-surname) that were recorded
by old rq plugin versions when running in git worktrees.

Modes:
  detect:  List bogus repo directories (default, used by GHA).
  repair:  Rewrite repo field in JSON files and move to correct directory.
           Requires a mapping file or --map flags.

Usage:
  python3 normalize_repo_names.py <data_dir>
  python3 normalize_repo_names.py <data_dir> --repair --map gifted-brahmagupta=doubtfire-client
"""

import glob
import json
import os
import re
import shutil
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


def main():
    data_dir = sys.argv[1] if len(sys.argv) > 1 else "data"
    args = sys.argv[2:]

    is_repair = "--repair" in args
    repo_map = {}
    for arg in args:
        if arg.startswith("--map"):
            continue
        if "=" in arg:
            worktree, real = arg.split("=", 1)
            repo_map[worktree] = real

    bogus = find_bogus_repos(data_dir)
    if not bogus:
        print("No worktree-named repos detected.")
        return

    if is_repair and repo_map:
        total = 0
        for name in bogus:
            if name in repo_map:
                count = repair_repo(data_dir, name, repo_map[name])
                print(f"  Repaired {name} -> {repo_map[name]} ({count} files)")
                total += count
            else:
                print(f"  SKIP {name}: no mapping provided")
        print(f"\nRepaired {total} files total")
    else:
        print(f"Found {len(bogus)} worktree-named repo(s):")
        for name in bogus:
            file_count = sum(
                len(files)
                for _, _, files in os.walk(os.path.join(data_dir, name))
            )
            print(f"  {name} ({file_count} files)")


if __name__ == "__main__":
    main()
