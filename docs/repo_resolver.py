"""Self-healing repo-name resolution for events whose ``repo`` field is wrong.

The rq plugin has emitted events with a worktree dir name or branch name in
the ``repo`` field on multiple occasions. v1.28.10+ derives ``repo`` from
``git remote get-url origin``, but historical and out-of-date emitters still
produce bogus events. Rather than rely on the emitter being correct, the
aggregator resolves every event through this module at load time.

Resolution order:

1. ``repo`` is already a known arqu-co repo  → accept as-is.
2. ``repo`` matches an explicit rename       → rewrite (e.g. ``claude-skills``
   → ``agent-plugins``).
3. ``repo`` matches a worktree alias        → rewrite to the canonical repo
   (built from one-time SHA archaeology, persisted in
   ``data/_repo-resolution-map.json``).
4. Otherwise                                  → return ``None`` so the caller
   can drop the event.

To extend: edit ``data/_repo-resolution-map.json``. The schema is::

    {
      "renames":          {"old-repo-name": "new-repo-name", ...},
      "worktree_aliases": {"worktree-or-branch-name": "real-repo", ...}
    }
"""

from __future__ import annotations

import json
import os
from functools import lru_cache

from repo_allowlist import is_known_repo

RESOLUTION_MAP_FILENAME = "_repo-resolution-map.json"


@lru_cache(maxsize=8)
def _load_map(data_dir: str) -> dict[str, dict[str, str]]:
    path = os.path.join(data_dir, RESOLUTION_MAP_FILENAME)
    try:
        with open(path) as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {"renames": {}, "worktree_aliases": {}}
    return {
        "renames": dict(data.get("renames") or {}),
        "worktree_aliases": dict(data.get("worktree_aliases") or {}),
    }


def resolve_repo(repo: str | None, data_dir: str = "data") -> str | None:
    """Return the canonical repo name, or ``None`` if unresolvable.

    A non-string ``repo`` (None, missing) returns ``None``. Callers should
    drop events that resolve to ``None``.
    """
    if not repo:
        return None
    if is_known_repo(repo, data_dir):
        return repo
    rmap = _load_map(data_dir)
    if repo in rmap["renames"]:
        return rmap["renames"][repo]
    if repo in rmap["worktree_aliases"]:
        return rmap["worktree_aliases"][repo]
    return None
