"""Tests for repo_resolver — self-healing canonical repo resolution."""

import json

from repo_allowlist import load_known_repos
from repo_resolver import _load_map, resolve_repo


def _write(tmp_path, allowlist, resolution_map):
    (tmp_path / "_arqu-co-repos.json").write_text(
        json.dumps({"org": "arqu-co", "repos": list(allowlist)})
    )
    (tmp_path / "_repo-resolution-map.json").write_text(
        json.dumps(resolution_map)
    )
    load_known_repos.cache_clear()
    _load_map.cache_clear()


def test_resolve_repo_passes_through_known_repo(tmp_path):
    _write(tmp_path, ["alpha", "beta"], {"renames": {}, "worktree_aliases": {}})
    assert resolve_repo("alpha", str(tmp_path)) == "alpha"


def test_resolve_repo_applies_rename(tmp_path):
    _write(tmp_path, ["agent-plugins"], {
        "renames": {"claude-skills": "agent-plugins"},
        "worktree_aliases": {},
    })
    assert resolve_repo("claude-skills", str(tmp_path)) == "agent-plugins"


def test_resolve_repo_applies_worktree_alias(tmp_path):
    _write(tmp_path, ["c3"], {
        "renames": {},
        "worktree_aliases": {"feat+rate-budget-system": "c3"},
    })
    assert resolve_repo("feat+rate-budget-system", str(tmp_path)) == "c3"


def test_resolve_repo_returns_none_for_unknown(tmp_path):
    _write(tmp_path, ["alpha"], {"renames": {}, "worktree_aliases": {}})
    assert resolve_repo("totally-unknown", str(tmp_path)) is None


def test_resolve_repo_returns_none_for_missing(tmp_path):
    _write(tmp_path, ["alpha"], {"renames": {}, "worktree_aliases": {}})
    assert resolve_repo(None, str(tmp_path)) is None
    assert resolve_repo("", str(tmp_path)) is None


def test_resolve_repo_renames_take_precedence_over_aliases(tmp_path):
    _write(tmp_path, ["new-name"], {
        "renames": {"old-name": "new-name"},
        "worktree_aliases": {"old-name": "wrong-name"},
    })
    assert resolve_repo("old-name", str(tmp_path)) == "new-name"


def test_load_map_handles_missing_file(tmp_path):
    _load_map.cache_clear()
    result = _load_map(str(tmp_path))
    assert result == {"renames": {}, "worktree_aliases": {}}
