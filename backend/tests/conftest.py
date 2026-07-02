# tests/conftest.py
import pytest
from unittest.mock import MagicMock


@pytest.fixture
def sample_repos():
    """Reusable sample repo data (as returned by transform-stage code)."""
    return [
        {"id": 1, "name": "repo-one", "full_name": "alice/repo-one",
         "description": "First repo", "html_url": "https://github.com/alice/repo-one",
         "fork": False, "owner": {"login": "alice", "type": "User"}},
        {"id": 2, "name": "repo-two", "full_name": "bob/repo-two",
         "description": None, "html_url": "https://github.com/bob/repo-two",
         "fork": True, "owner": {"login": "bob", "type": "Organization"}},
    ]


def _raw_repo(**overrides):
    """A GitHub search-API repo object with real field types (bools are
    Python bool, not strings) so tests reflect what the API actually sends."""
    base = {
        "id": 100,
        "name": "sample-repo",
        "full_name": "octocat/sample-repo",
        "description": "A sample repo",
        "html_url": "https://github.com/octocat/sample-repo",
        "fork": False,
        "archived": False,
        "disabled": False,
        "has_issues": True,
        "has_projects": True,
        "stargazers_count": 50,
        "forks_count": 5,
        "open_issues_count": 3,
        "languages_url": "https://api.github.com/repos/octocat/sample-repo/languages",
        "issues_url": "https://api.github.com/repos/octocat/sample-repo/issues{/number}",
        "owner": {"login": "octocat", "type": "User"},
    }
    base.update(overrides)
    return base


@pytest.fixture
def raw_repo_factory():
    """Factory so each test can build a repo dict with only the fields it cares about."""
    return _raw_repo


@pytest.fixture
def raw_repos(raw_repo_factory):
    """A small list of raw GitHub API repos: one that should pass every
    filter, and one that should fail (archived)."""
    return [
        raw_repo_factory(id=1, full_name="octocat/good-repo"),
        raw_repo_factory(id=2, full_name="octocat/archived-repo", archived=True),
    ]


@pytest.fixture
def mock_engine():
    """A MagicMock standing in for a SQLAlchemy Engine.
    Supports `with engine.begin() as conn:` and `engine.connect()`."""
    engine = MagicMock(name="engine")
    conn = MagicMock(name="connection")
    engine.begin.return_value.__enter__.return_value = conn
    engine.connect.return_value.__enter__.return_value = conn
    return engine


@pytest.fixture
def github_issue_factory():
    def _make(number=1, title="Fix bug", labels=None, state="open", is_pr=False):
        issue = {
            "number": number,
            "title": title,
            "labels": [{"name": l} for l in (labels or [])],
            "state": state,
        }
        if is_pr:
            issue["pull_request"] = {"url": "https://api.github.com/pulls/1"}
        return issue
    return _make
