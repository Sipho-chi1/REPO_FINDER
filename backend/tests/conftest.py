# tests/conftest.py
import pytest

@pytest.fixture
def sample_repos():
    """Reusable sample repo data for tests. Adjust to match your real JSON shape."""
    return [
        {"id": 1, "name": "repo-one", "full_name": "alice/repo-one",
         "description": "First repo", "html_url": "https://github.com/alice/repo-one",
         "fork": False, "owner": {"login": "alice", "type": "User"}},
        {"id": 2, "name": "repo-two", "full_name": "bob/repo-two",
         "description": None, "html_url": "https://github.com/bob/repo-two",
         "fork": True, "owner": {"login": "bob", "type": "Organization"}},
    ]