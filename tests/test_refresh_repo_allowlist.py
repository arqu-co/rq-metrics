"""Tests for refresh_repo_allowlist's UNION semantics.

The CI runner's GITHUB_TOKEN can only see public repos (~10 of 91), so
the refresh must NEVER overwrite the committed allowlist with a smaller
fetched set. This test pins the union behaviour so the regression that
shrank the live dashboard from 398 events to 18 cannot recur.
See: https://github.com/arqu-co/rq-metrics/pull/18 follow-up.
"""

import json

import refresh_repo_allowlist as rra


def _write_existing(tmp_path, repos):
    path = tmp_path / "_arqu-co-repos.json"
    path.write_text(json.dumps({"org": "arqu-co", "repos": list(repos)}))
    return path


def _read_repos(path):
    return json.loads(path.read_text())["repos"]


def test_union_preserves_existing_when_fetched_is_subset(tmp_path, monkeypatch):
    """Fetched 10 + existing 91 → merged 91 (existing preserved)."""
    existing = [f"repo-{i:03d}" for i in range(91)]
    fetched = [f"repo-{i:03d}" for i in range(10)]  # CI token can see fewer

    path = _write_existing(tmp_path, existing)
    monkeypatch.setattr(rra, "ALLOWLIST_PATH", str(path))
    monkeypatch.setattr(rra, "fetch_repo_names", lambda _org: fetched)

    rra.main()
    result = _read_repos(path)
    assert sorted(result) == sorted(existing)
    assert len(result) == 91


def test_union_adds_newly_visible_repos(tmp_path, monkeypatch):
    """Fetched ['a','b','new'] + existing ['a','b'] → merged ['a','b','new']."""
    path = _write_existing(tmp_path, ["a", "b"])
    monkeypatch.setattr(rra, "ALLOWLIST_PATH", str(path))
    monkeypatch.setattr(rra, "fetch_repo_names", lambda _org: ["a", "b", "new"])

    rra.main()
    assert sorted(_read_repos(path)) == ["a", "b", "new"]


def test_no_existing_file_uses_fetched(tmp_path, monkeypatch):
    """First-run with no committed allowlist: write the fetched set."""
    path = tmp_path / "_arqu-co-repos.json"
    monkeypatch.setattr(rra, "ALLOWLIST_PATH", str(path))
    monkeypatch.setattr(rra, "fetch_repo_names", lambda _org: ["alpha", "beta"])

    rra.main()
    assert sorted(_read_repos(path)) == ["alpha", "beta"]


def test_fetch_failure_leaves_existing_untouched(tmp_path, monkeypatch):
    """gh failure → keep the committed allowlist verbatim."""
    import subprocess
    existing = ["alpha", "beta", "gamma"]
    path = _write_existing(tmp_path, existing)
    monkeypatch.setattr(rra, "ALLOWLIST_PATH", str(path))

    def _fail(_org):
        raise subprocess.CalledProcessError(1, "gh", stderr="rate limit")

    monkeypatch.setattr(rra, "fetch_repo_names", _fail)

    rra.main()
    assert sorted(_read_repos(path)) == sorted(existing)


def test_load_existing_handles_corrupt_json(tmp_path):
    path = tmp_path / "_arqu-co-repos.json"
    path.write_text("not json {")
    assert rra.load_existing_repos(str(path)) == []
