"""Tests for docs/normalize_repo_names.py — pattern + GitHub verification."""

import os
import subprocess
import tempfile
from unittest.mock import patch

import pytest

from normalize_repo_names import (
    find_bogus_repos,
    find_bogus_repos_via_github,
    is_worktree_name,
    repo_exists_in_org,
)


# --- is_worktree_name ---


@pytest.mark.parametrize("name,expected", [
    ("gifted-brahmagupta", True),
    ("bold-wilson", True),
    ("zen-hamilton", True),
    # Directory-style names — NOT worktree pattern
    ("doubtfire-client", False),
    ("risklab-python", False),
    ("billing-redux", False),
    ("core-api", False),
    # Non-matches
    ("arqu-atlas", False),  # "arqu" not in adjective list
    ("single", False),
    ("too-many-parts", False),
    ("UPPER-case", False),
])
def test_is_worktree_name(name, expected):
    assert is_worktree_name(name) is expected


# --- find_bogus_repos (pattern-based, offline) ---


def test_find_bogus_repos_only_detects_worktree_pattern():
    """The offline detector only catches adjective-surname names.
    Directory-style bogus names slip through — that's why the GHA
    switched to find_bogus_repos_via_github."""
    with tempfile.TemporaryDirectory() as d:
        for name in [
            "bold-wilson",       # worktree-pattern → detected
            "gifted-brahmagupta",  # worktree-pattern → detected
            "billing-redux",     # directory-style → NOT detected (historical gap)
            "doubtfire-client",  # real repo → not detected
        ]:
            os.makedirs(os.path.join(d, name))
        bogus = find_bogus_repos(d)
        assert "bold-wilson" in bogus
        assert "gifted-brahmagupta" in bogus
        assert "billing-redux" not in bogus
        assert "doubtfire-client" not in bogus


# --- repo_exists_in_org ---


def test_repo_exists_in_org_returns_true_on_exit_zero():
    """Uses the `gh` CLI exit code, not stdout parsing."""
    fake_result = subprocess.CompletedProcess(
        args=[], returncode=0, stdout=b'{"name":"engineer"}', stderr=b""
    )
    with patch("subprocess.run", return_value=fake_result):
        assert repo_exists_in_org("arqu-co", "engineer") is True


def test_repo_exists_in_org_returns_false_on_404():
    """On 404 gh still writes the error JSON to stdout — we MUST
    check the exit code, not parse the output, to avoid false positives.
    This regression test guards against the bug fixed in PR #9 where
    `--jq .name` output parsing falsely reported 404s as OK."""
    fake_result = subprocess.CompletedProcess(
        args=[],
        returncode=1,
        stdout=b'{"message":"Not Found","status":"404"}',
        stderr=b"gh: Not Found (HTTP 404)",
    )
    with patch("subprocess.run", return_value=fake_result):
        assert repo_exists_in_org("arqu-co", "billing-redux") is False


def test_repo_exists_in_org_returns_true_when_gh_missing():
    """If `gh` is not installed, assume the repo exists rather than
    false-flagging real data as bogus."""
    with patch("subprocess.run", side_effect=FileNotFoundError("gh")):
        assert repo_exists_in_org("arqu-co", "any") is True


def test_repo_exists_in_org_returns_true_on_timeout():
    """Network timeout → don't flag a real repo as bogus."""
    with patch(
        "subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="gh", timeout=10),
    ):
        assert repo_exists_in_org("arqu-co", "any") is True


# --- find_bogus_repos_via_github ---


def test_find_bogus_repos_via_github_flags_non_org_dirs():
    """Exhaustive check flags any dir whose name isn't a real repo,
    regardless of pattern."""
    def fake_exists(org, name):
        return name in {"engineer", "core-api"}  # only these are "real"

    with tempfile.TemporaryDirectory() as d:
        for name in [
            "engineer",       # real → not bogus
            "core-api",       # real → not bogus
            "billing-redux",  # fake → bogus (directory-style)
            "bold-wilson",    # fake → bogus (worktree-pattern)
            "_quarantine",    # reserved prefix → skip
        ]:
            os.makedirs(os.path.join(d, name))
        with patch(
            "normalize_repo_names.repo_exists_in_org",
            side_effect=fake_exists,
        ):
            bogus = find_bogus_repos_via_github(d, "arqu-co")
    assert set(bogus) == {"billing-redux", "bold-wilson"}


def test_find_bogus_repos_via_github_skips_files():
    """Files at the top level are ignored, only directories are checked."""
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "engineer"))
        with open(os.path.join(d, "README.md"), "w") as f:
            f.write("not a dir")
        with patch(
            "normalize_repo_names.repo_exists_in_org",
            return_value=True,
        ):
            bogus = find_bogus_repos_via_github(d, "arqu-co")
    assert bogus == []


def test_find_bogus_repos_via_github_skips_reserved_prefixes():
    """Directories starting with _ (e.g. _quarantine) are skipped."""
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "_quarantine"))
        os.makedirs(os.path.join(d, "_archived"))
        with patch(
            "normalize_repo_names.repo_exists_in_org",
            return_value=False,
        ) as mock:
            bogus = find_bogus_repos_via_github(d, "arqu-co")
    assert bogus == []
    assert mock.call_count == 0  # reserved dirs never checked


# --- allowlist preference (avoids GHA token's public-repos-only blindness) ---


def test_find_bogus_uses_committed_allowlist_when_present():
    """When ``data/_arqu-co-repos.json`` exists, the detector trusts it
    instead of calling ``gh api`` per-dir. CI's GITHUB_TOKEN can only
    see public repos, so a per-dir live check false-positives every
    private-repo dir as bogus.
    """
    import json as _json
    with tempfile.TemporaryDirectory() as d:
        # Committed allowlist contains private + public repos
        with open(os.path.join(d, "_arqu-co-repos.json"), "w") as f:
            _json.dump({"org": "arqu-co",
                        "repos": ["arqu-atlas", "engineer", "auto-claude"]}, f)
        for name in [
            "arqu-atlas",        # in allowlist → not bogus
            "engineer",          # in allowlist → not bogus
            "auto-claude",       # in allowlist → not bogus
            "bold-wilson",       # not in allowlist → bogus
            "claude-skills",     # not in allowlist (renamed) → bogus
        ]:
            os.makedirs(os.path.join(d, name))
        # gh api should NEVER be called when allowlist is present.
        with patch(
            "normalize_repo_names.repo_exists_in_org",
            side_effect=AssertionError("gh api must not be called"),
        ):
            bogus = find_bogus_repos_via_github(d, "arqu-co")
    assert set(bogus) == {"bold-wilson", "claude-skills"}


def test_find_bogus_falls_back_to_gh_api_when_allowlist_missing():
    """No committed allowlist → fall back to per-dir gh api (legacy path)."""
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "engineer"))
        os.makedirs(os.path.join(d, "bogus-thing"))
        with patch(
            "normalize_repo_names.repo_exists_in_org",
            side_effect=lambda _o, name: name == "engineer",
        ):
            bogus = find_bogus_repos_via_github(d, "arqu-co")
    assert bogus == ["bogus-thing"]
