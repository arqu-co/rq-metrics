"""Tests for the arqu-co repo allowlist."""

import json

from repo_allowlist import is_known_repo, load_known_repos


def _write_allowlist(path, repos):
    path.write_text(json.dumps({"org": "arqu-co", "repos": list(repos)}))


def test_is_known_repo_accepts_listed_repo(tmp_path):
    load_known_repos.cache_clear()
    _write_allowlist(tmp_path / "_arqu-co-repos.json", ["alpha", "beta"])
    assert is_known_repo("alpha", str(tmp_path)) is True


def test_is_known_repo_rejects_unlisted_repo(tmp_path):
    load_known_repos.cache_clear()
    _write_allowlist(tmp_path / "_arqu-co-repos.json", ["alpha"])
    assert is_known_repo("worktree-style", str(tmp_path)) is False


def test_is_known_repo_rejects_none_when_list_present(tmp_path):
    load_known_repos.cache_clear()
    _write_allowlist(tmp_path / "_arqu-co-repos.json", ["alpha"])
    assert is_known_repo(None, str(tmp_path)) is False


def test_is_known_repo_disabled_when_file_missing(tmp_path):
    # Empty allowlist (file missing) → filter disabled, accept everything.
    # This is the safe bootstrap path before the allowlist ships.
    load_known_repos.cache_clear()
    assert is_known_repo("anything", str(tmp_path)) is True


def test_load_known_repos_returns_frozen_set(tmp_path):
    load_known_repos.cache_clear()
    _write_allowlist(tmp_path / "_arqu-co-repos.json", ["alpha", "beta"])
    result = load_known_repos(str(tmp_path))
    assert isinstance(result, frozenset)
    assert result == frozenset({"alpha", "beta"})


def test_load_known_repos_handles_corrupt_json(tmp_path):
    load_known_repos.cache_clear()
    (tmp_path / "_arqu-co-repos.json").write_text("not json {")
    assert load_known_repos(str(tmp_path)) == frozenset()
