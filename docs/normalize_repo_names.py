#!/usr/bin/env python3
"""Normalize worktree-named repo directories before aggregation.

Detects Docker-style random names (adjective-surname) that were recorded
by old rq plugin versions when running in git worktrees. Moves affected
data to a _quarantine/ directory and rewrites the repo field if possible.

Usage: python3 normalize_repo_names.py <data_dir>
"""

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


def quarantine_dir(data_dir, repo_name):
    """Move a worktree-named directory to _quarantine/."""
    src = os.path.join(data_dir, repo_name)
    dst_root = os.path.join(data_dir, "_quarantine")
    dst = os.path.join(dst_root, repo_name)
    os.makedirs(dst_root, exist_ok=True)
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.move(src, dst)
    return dst


def find_bogus_repos(data_dir):
    """Return list of directory names that look like worktree names."""
    bogus = []
    for entry in sorted(os.listdir(data_dir)):
        path = os.path.join(data_dir, entry)
        if os.path.isdir(path) and is_worktree_name(entry):
            bogus.append(entry)
    return bogus


def main():
    data_dir = sys.argv[1] if len(sys.argv) > 1 else "data"

    bogus = find_bogus_repos(data_dir)
    if not bogus:
        print("No worktree-named repos detected.")
        return

    print(f"Found {len(bogus)} worktree-named repo(s):")
    for name in bogus:
        file_count = sum(
            len(files)
            for _, _, files in os.walk(os.path.join(data_dir, name))
        )
        dst = quarantine_dir(data_dir, name)
        print(f"  {name} ({file_count} files) -> {dst}")

    # Write a manifest for CI visibility
    manifest = os.path.join(data_dir, "_quarantine", "manifest.json")
    with open(manifest, "w") as f:
        json.dump({"quarantined": bogus}, f, indent=2)
        f.write("\n")


if __name__ == "__main__":
    main()
