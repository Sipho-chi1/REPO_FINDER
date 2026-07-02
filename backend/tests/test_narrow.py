# tests/test_narrow.py
from unittest.mock import MagicMock, patch
import pandas as pd
import pytest
import requests

from ingest import narrow


# ---------------------------------------------------------------------
# fetch()
# ---------------------------------------------------------------------

def _fake_response(status_code, json_body=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_body
    return resp


def test_fetch_returns_json_on_200(monkeypatch):
    monkeypatch.setattr(
        narrow.requests, "get",
        lambda url, headers=None, timeout=None: _fake_response(200, {"ok": True}),
    )
    result = narrow.fetch("http://x", {})
    assert result == {"ok": True}


def test_fetch_returns_none_on_404(monkeypatch):
    monkeypatch.setattr(
        narrow.requests, "get",
        lambda url, headers=None, timeout=None: _fake_response(404),
    )
    result = narrow.fetch("http://x", {})
    assert result is None


def test_fetch_retries_and_pauses_on_403_then_succeeds(monkeypatch):
    calls = {"n": 0}

    def fake_get(url, headers=None, timeout=None):
        calls["n"] += 1
        if calls["n"] == 1:
            return _fake_response(403)
        return _fake_response(200, {"ok": True})

    monkeypatch.setattr(narrow.requests, "get", fake_get)
    monkeypatch.setattr(narrow.time, "sleep", lambda s: None)  # don't actually wait

    result = narrow.fetch("http://x", {}, retries=3)
    assert result == {"ok": True}
    assert calls["n"] == 2


def test_fetch_gives_up_after_max_retries_on_connection_error(monkeypatch):
    def fake_get(url, headers=None, timeout=None):
        raise requests.exceptions.ConnectionError("boom")

    monkeypatch.setattr(narrow.requests, "get", fake_get)
    monkeypatch.setattr(narrow.time, "sleep", lambda s: None)

    result = narrow.fetch("http://x", {}, retries=2)
    assert result is None


def test_fetch_does_not_retry_on_other_error_codes(monkeypatch):
    calls = {"n": 0}

    def fake_get(url, headers=None, timeout=None):
        calls["n"] += 1
        return _fake_response(500)

    monkeypatch.setattr(narrow.requests, "get", fake_get)
    result = narrow.fetch("http://x", {}, retries=3)
    assert result is None
    assert calls["n"] == 1  # returns immediately, no retry loop for 500s


# ---------------------------------------------------------------------
# enrich_and_build_tables()
# ---------------------------------------------------------------------

@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    """Don't actually pause 0.5s per repo during tests."""
    monkeypatch.setattr(narrow.time, "sleep", lambda s: None)


def test_cheap_filter_excludes_forks_and_no_description(raw_repo_factory):
    repos = [
        raw_repo_factory(id=1, fork=False, description="has one"),
        raw_repo_factory(id=2, fork=True, description="has one"),
        raw_repo_factory(id=3, fork=False, description=None),
        raw_repo_factory(id=4, fork=False, description=""),
    ]
    engine = MagicMock()

    with patch.object(narrow, "fetch", return_value=None) as mock_fetch:
        narrow.enrich_and_build_tables(engine, repos, header={})

    # Only repo 1 should survive the cheap filter. Each surviving repo triggers
    # two fetch() calls (languages + issues), so 1 repo -> 2 calls.
    # repo 2 is a fork, repo 3 has None description, repo 4 has an empty
    # (falsy) description — all three should be excluded before any fetch happens.
    assert mock_fetch.call_count == 2


def test_language_rows_built_from_fetch_result(raw_repo_factory):
    repo = raw_repo_factory(id=1, fork=False, description="x")
    engine = MagicMock()

    def fake_fetch(url, header):
        if "languages" in url:
            return {"Python": 1000, "HTML": 200}
        return None  # issues call

    captured = {}

    def fake_to_sql(self, table_name, eng, if_exists=None, index=None):
        captured[table_name] = self.copy()

    with patch.object(narrow, "fetch", side_effect=fake_fetch), \
         patch.object(pd.DataFrame, "to_sql", fake_to_sql):
        narrow.enrich_and_build_tables(engine, [repo], header={})

    assert "repo_languages" in captured
    langs = captured["repo_languages"]
    assert set(langs["language"]) == {"Python", "HTML"}
    assert all(langs["repo_id"] == 1)


def test_issue_rows_skip_pull_requests(raw_repo_factory, github_issue_factory):
    repo = raw_repo_factory(id=1, fork=False, description="x")
    engine = MagicMock()

    def fake_fetch(url, header):
        if "issues" in url:
            return [
                github_issue_factory(number=1, title="Real issue"),
                github_issue_factory(number=2, title="A PR", is_pr=True),
            ]
        return None  # languages call

    captured = {}

    def fake_to_sql(self, table_name, eng, if_exists=None, index=None):
        captured[table_name] = self.copy()

    with patch.object(narrow, "fetch", side_effect=fake_fetch), \
         patch.object(pd.DataFrame, "to_sql", fake_to_sql):
        narrow.enrich_and_build_tables(engine, [repo], header={})

    assert "repo_issues" in captured
    issues = captured["repo_issues"]
    assert len(issues) == 1
    assert issues.iloc[0]["issue_number"] == 1


def test_issues_url_template_placeholder_is_stripped(raw_repo_factory):
    repo = raw_repo_factory(
        id=1, fork=False, description="x",
        issues_url="https://api.github.com/repos/x/y/issues{/number}",
    )
    engine = MagicMock()
    seen_urls = []

    def fake_fetch(url, header):
        seen_urls.append(url)
        return None

    with patch.object(narrow, "fetch", side_effect=fake_fetch):
        narrow.enrich_and_build_tables(engine, [repo], header={})

    issues_urls = [u for u in seen_urls if "issues" in u]
    assert issues_urls == ["https://api.github.com/repos/x/y/issues"]
    assert "{/number}" not in issues_urls[0]


def test_no_tables_written_when_nothing_survives_cheap_filter(raw_repo_factory):
    repo = raw_repo_factory(fork=True)  # excluded by cheap filter
    engine = MagicMock()

    with patch.object(pd.DataFrame, "to_sql") as mock_to_sql:
        narrow.enrich_and_build_tables(engine, [repo], header={})
        mock_to_sql.assert_not_called()
