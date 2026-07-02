# tests/test_run_pipeline.py
"""
run_pipeline.pipeline() wires together every stage of the app. These tests
mock every stage so the suite runs offline, for free, with no live DB or
API key required — the previous version of this file (now moved to
scripts/live_smoke_test.py) made real network/DB calls, which isn't safe
to run automatically in CI.
"""
import json
from unittest.mock import MagicMock, patch

import run_pipeline


def _patched_pipeline(monkeypatch, tmp_path, repos_on_disk):
    """Set up a fake data/raw/github_repodata.json so the file-read inside
    pipeline() (after github_client.extract) has something to load."""
    data_dir = tmp_path / "data" / "raw"
    data_dir.mkdir(parents=True)
    with open(data_dir / "github_repodata.json", "w") as f:
        json.dump(repos_on_disk, f)
    monkeypatch.chdir(tmp_path)


def test_pipeline_calls_stages_in_order(monkeypatch, tmp_path, raw_repos):
    _patched_pipeline(monkeypatch, tmp_path, raw_repos)

    calls = []

    def record(name):
        return lambda *a, **k: calls.append(name)

    with patch.object(run_pipeline, "create_engine", return_value=MagicMock()), \
         patch.object(run_pipeline.github_client, "extract", side_effect=record("extract")), \
         patch.object(run_pipeline.transform, "transform",
                       side_effect=lambda: (record("transform")() or MagicMock())), \
         patch.object(run_pipeline.load, "load", side_effect=record("load")), \
         patch.object(run_pipeline.narrow, "enrich_and_build_tables",
                       side_effect=record("narrow")), \
         patch.object(run_pipeline, "run_analysis", side_effect=record("analysis")):
        run_pipeline.pipeline()

    assert calls == ["extract", "transform", "load", "narrow", "analysis"]


def test_pipeline_passes_search_url_with_expected_qualifiers(monkeypatch, tmp_path, raw_repos):
    _patched_pipeline(monkeypatch, tmp_path, raw_repos)

    with patch.object(run_pipeline, "create_engine", return_value=MagicMock()), \
         patch.object(run_pipeline.github_client, "extract") as mock_extract, \
         patch.object(run_pipeline.transform, "transform", return_value=MagicMock()), \
         patch.object(run_pipeline.load, "load"), \
         patch.object(run_pipeline.narrow, "enrich_and_build_tables"), \
         patch.object(run_pipeline, "run_analysis"):
        run_pipeline.pipeline()

    url_arg = mock_extract.call_args[0][0]
    assert "api.github.com/search/repositories" in url_arg
    assert "stars:>10" in url_arg


def test_pipeline_runs_analysis_for_python(monkeypatch, tmp_path, raw_repos):
    _patched_pipeline(monkeypatch, tmp_path, raw_repos)

    with patch.object(run_pipeline, "create_engine", return_value=MagicMock()), \
         patch.object(run_pipeline.github_client, "extract"), \
         patch.object(run_pipeline.transform, "transform", return_value=MagicMock()), \
         patch.object(run_pipeline.load, "load"), \
         patch.object(run_pipeline.narrow, "enrich_and_build_tables"), \
         patch.object(run_pipeline, "run_analysis") as mock_run_analysis:
        run_pipeline.pipeline()

    args, _ = mock_run_analysis.call_args
    assert args[1] == "Python"


def test_pipeline_does_not_create_repo_analysis_table_currently(monkeypatch, tmp_path, raw_repos):
    """create_repo_analysis_table() is imported but commented out in pipeline().
    This test documents that current behavior: if repo_analysis doesn't
    already exist in the DB, run_analysis() will fail against a real DB.
    Un-skip / delete this test once that line is uncommented."""
    _patched_pipeline(monkeypatch, tmp_path, raw_repos)

    with patch.object(run_pipeline, "create_engine", return_value=MagicMock()), \
         patch.object(run_pipeline.github_client, "extract"), \
         patch.object(run_pipeline.transform, "transform", return_value=MagicMock()), \
         patch.object(run_pipeline.load, "load"), \
         patch.object(run_pipeline.narrow, "enrich_and_build_tables"), \
         patch.object(run_pipeline, "run_analysis"), \
         patch.object(run_pipeline, "create_repo_analysis_table") as mock_create_table:
        run_pipeline.pipeline()

    mock_create_table.assert_not_called()
