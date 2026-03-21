"""Tests for docs/aggregate.py — loading, summary, trends, repos, payload, main."""

import json
import sys

from helpers import make_metric

from aggregate import (
    KNOWN_GATES,
    build_payload,
    compute_per_repo,
    compute_summary,
    compute_trends,
    load_metrics,
    main,
)


# --- load_metrics ---


class TestLoadMetrics:
    def test_loads_json_files_recursively(self, tmp_path):
        sub = tmp_path / "repo" / "branch"
        sub.mkdir(parents=True)
        m = make_metric(repo="loaded")
        (sub / "data.json").write_text(json.dumps(m))

        result = load_metrics(str(tmp_path))
        assert len(result) == 1
        assert result[0]["repo"] == "loaded"
        assert "_file" in result[0]

    def test_skips_invalid_json(self, tmp_path):
        (tmp_path / "bad.json").write_text("not json")
        result = load_metrics(str(tmp_path))
        assert result == []

    def test_empty_directory(self, tmp_path):
        result = load_metrics(str(tmp_path))
        assert result == []

    def test_multiple_files(self, tmp_path):
        for i in range(3):
            (tmp_path / f"m{i}.json").write_text(
                json.dumps(make_metric(repo=f"repo-{i}"))
            )
        result = load_metrics(str(tmp_path))
        assert len(result) == 3


# --- compute_summary ---


class TestComputeSummary:
    def test_empty_metrics(self):
        s = compute_summary([])
        assert s["total_builds"] == 0
        assert s["first_pass_rate"] == 0
        assert s["catch_rate"] == 0

    def test_all_first_pass(self):
        metrics = [make_metric(gates_first_pass=True) for _ in range(5)]
        s = compute_summary(metrics)
        assert s["total_builds"] == 5
        assert s["first_pass_count"] == 5
        assert s["first_pass_rate"] == 100.0

    def test_mixed_first_pass(self):
        metrics = [
            make_metric(gates_first_pass=True),
            make_metric(gates_first_pass=False),
        ]
        s = compute_summary(metrics)
        assert s["first_pass_rate"] == 50.0

    def test_catch_rate_with_catches_and_misses(self):
        metrics = [
            make_metric(critic_findings_count=3, gate_failures_after_critic=1),
        ]
        s = compute_summary(metrics)
        assert s["critic_catches"] == 3
        assert s["critic_misses"] == 1
        assert s["catch_rate"] == 75.0

    def test_catch_rate_no_violations(self):
        metrics = [make_metric()]
        s = compute_summary(metrics)
        assert s["catch_rate"] == 100


# --- compute_trends ---


class TestComputeTrends:
    def test_groups_by_date(self):
        metrics = [
            make_metric(timestamp="2026-03-20T10:00:00Z"),
            make_metric(timestamp="2026-03-20T14:00:00Z"),
            make_metric(timestamp="2026-03-21T10:00:00Z"),
        ]
        trends = compute_trends(metrics)
        assert len(trends) == 2
        assert trends[0]["date"] == "2026-03-20"
        assert trends[0]["total_builds"] == 2
        assert trends[1]["date"] == "2026-03-21"
        assert trends[1]["total_builds"] == 1

    def test_empty_metrics(self):
        assert compute_trends([]) == []

    def test_short_timestamp_grouped_as_unknown(self):
        metrics = [make_metric(timestamp="short")]
        trends = compute_trends(metrics)
        assert len(trends) == 1
        assert trends[0]["date"] == "unknown"


# --- compute_per_repo ---


class TestComputePerRepo:
    def test_groups_by_repo(self):
        metrics = [
            make_metric(repo="alpha"),
            make_metric(repo="alpha"),
            make_metric(repo="beta"),
        ]
        per_repo = compute_per_repo(metrics)
        assert per_repo["alpha"]["total_builds"] == 2
        assert per_repo["beta"]["total_builds"] == 1

    def test_unknown_repo_default(self):
        metrics = [make_metric()]
        del metrics[0]["repo"]
        per_repo = compute_per_repo(metrics)
        assert "unknown" in per_repo


# --- build_payload ---


class TestBuildPayload:
    def test_payload_structure(self):
        metrics = [make_metric()]
        payload = build_payload(metrics)
        assert "generated_at" in payload
        assert "known_gates" in payload
        assert payload["known_gates"] == list(KNOWN_GATES)
        assert "summary" in payload
        assert "trends" in payload
        assert "per_repo" in payload
        assert "per_gate" in payload
        assert "per_gate_stats" in payload
        assert "per_gate_per_repo" in payload
        assert "violation_trends" in payload
        assert "findings_summary" in payload
        assert "timing_stats" in payload
        assert "fix_cycles" in payload
        assert "phase_breakdown" in payload
        assert "top_violations" in payload
        assert "recent_failures" in payload
        assert payload["total_records"] == 1

    def test_empty_metrics(self):
        payload = build_payload([])
        assert payload["total_records"] == 0
        assert payload["summary"]["total_builds"] == 0
        assert payload["known_gates"] == list(KNOWN_GATES)


# --- main ---


class TestMain:
    def test_main_writes_output_file(self, tmp_path, monkeypatch):
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "m.json").write_text(
            json.dumps(make_metric(repo="main-test"))
        )
        output_file = tmp_path / "out" / "data.json"

        monkeypatch.setattr(
            sys, "argv", ["aggregate.py", str(data_dir), str(output_file)]
        )
        main()

        assert output_file.exists()
        payload = json.loads(output_file.read_text())
        assert payload["total_records"] == 1
        assert payload["known_gates"] == list(KNOWN_GATES)

    def test_main_default_args(self, tmp_path, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["aggregate.py"])
        monkeypatch.chdir(tmp_path)
        (tmp_path / "data").mkdir()
        (tmp_path / "docs").mkdir()

        main()

        output = tmp_path / "docs" / "data.json"
        assert output.exists()
        payload = json.loads(output.read_text())
        assert payload["total_records"] == 0
