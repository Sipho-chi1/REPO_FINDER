# tests/test_transform.py
import json
import pandas as pd
import pytest

from ingest.transform import transform

EXPECTED_COLUMNS = {
    "id", "name", "full_name", "description",
    "html_url", "fork", "owner_login", "owner_type",
}


def _write_repodata(tmp_path, monkeypatch, repos):
    """transform() reads a hardcoded relative path (data/raw/github_repodata.json),
    so we recreate that path under a temp cwd rather than editing the source."""
    data_dir = tmp_path / "data" / "raw"
    data_dir.mkdir(parents=True)
    with open(data_dir / "github_repodata.json", "w") as f:
        json.dump(repos, f)
    monkeypatch.chdir(tmp_path)


def test_returns_dataframe(tmp_path, monkeypatch, sample_repos):
    _write_repodata(tmp_path, monkeypatch, sample_repos)
    df = transform()
    assert isinstance(df, pd.DataFrame)


def test_has_expected_columns(tmp_path, monkeypatch, sample_repos):
    _write_repodata(tmp_path, monkeypatch, sample_repos)
    df = transform()
    assert set(df.columns) == EXPECTED_COLUMNS


def test_rename_happened(tmp_path, monkeypatch, sample_repos):
    _write_repodata(tmp_path, monkeypatch, sample_repos)
    df = transform()
    assert "owner_login" in df.columns
    assert "owner.login" not in df.columns
    assert "owner_type" in df.columns
    assert "owner.type" not in df.columns


def test_row_count_matches_input(tmp_path, monkeypatch, sample_repos):
    _write_repodata(tmp_path, monkeypatch, sample_repos)
    df = transform()
    assert len(df) == len(sample_repos)


def test_values_extracted_correctly(tmp_path, monkeypatch, sample_repos):
    _write_repodata(tmp_path, monkeypatch, sample_repos)
    df = transform()
    first = df.iloc[0]
    assert first["owner_login"] == "alice"
    assert first["owner_type"] == "User"
    assert first["full_name"] == "alice/repo-one"
    assert first["fork"] is False or first["fork"] == False  # noqa: E712


def test_handles_null_description(tmp_path, monkeypatch, sample_repos):
    _write_repodata(tmp_path, monkeypatch, sample_repos)
    df = transform()
    second = df.iloc[1]
    assert pd.isna(second["description"])


def test_empty_input(tmp_path, monkeypatch):
    _write_repodata(tmp_path, monkeypatch, [])
    # pd.json_normalize([]) has no columns to select, so the current
    # implementation raises KeyError on an empty feed rather than
    # returning an empty DataFrame. This test documents that behavior
    # so it's a known, deliberate failure mode rather than a surprise
    # in production if the GitHub search ever returns zero results.
    with pytest.raises(KeyError):
        transform()
