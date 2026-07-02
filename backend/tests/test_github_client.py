# tests/test_github_client.py
"""
Tests for ingest/github_client.py.

Two of these tests (marked BUG) currently FAIL against the code as written.
They aren't broken tests — they're pinning down two real bugs so they show
up in red the next time this file runs, instead of silently corrupting data:

1. is_false()/is_true() compare booleans to the *strings* "false"/"true".
   GitHub's API returns real Python bools, so `False == "false"` is False,
   meaning is_false() can never return True and is_true() can never return True.

2. extract() calls `repos.remove(r)` while iterating over `repos` with a
   `for r in repos:` loop. Mutating a list while iterating over it skips
   the element right after any removed element — some repos that SHOULD
   be filtered out survive into the output file.

Recommended fix for both, once you're ready:
    repos = [r for r in repos if passes_threshold(r) and not r["archived"]
             and not r["disabled"] and r["has_issues"] and r["has_projects"]]
"""
import json
import pytest

from ingest import github_client as gc


# ---------------------------------------------------------------------
# passes_threshold — pure function, no bugs found here
# ---------------------------------------------------------------------

def test_passes_threshold_true_when_all_minimums_met(raw_repo_factory):
    repo = raw_repo_factory(stargazers_count=10, forks_count=2, open_issues_count=1)
    assert gc.passes_threshold(repo) is True


def test_passes_threshold_false_when_stars_too_low(raw_repo_factory):
    repo = raw_repo_factory(stargazers_count=9, forks_count=2, open_issues_count=1)
    assert gc.passes_threshold(repo) is False


def test_passes_threshold_false_when_forks_too_low(raw_repo_factory):
    repo = raw_repo_factory(stargazers_count=10, forks_count=1, open_issues_count=1)
    assert gc.passes_threshold(repo) is False


def test_passes_threshold_false_when_no_open_issues(raw_repo_factory):
    repo = raw_repo_factory(stargazers_count=10, forks_count=2, open_issues_count=0)
    assert gc.passes_threshold(repo) is False


def test_passes_threshold_true_well_above_minimums(raw_repo_factory):
    repo = raw_repo_factory(stargazers_count=5000, forks_count=800, open_issues_count=120)
    assert gc.passes_threshold(repo) is True


# ---------------------------------------------------------------------
# is_false / is_true — BUG: string vs bool comparison
# ---------------------------------------------------------------------

def test_is_false_BUG_never_true_for_a_genuinely_archived_repo(raw_repo_factory):
    """An archived, disabled repo SHOULD be flagged, but isn't."""
    repo = raw_repo_factory(archived=True, disabled=True)
    # This is what the function should return for a real archived+disabled repo.
    # It currently returns False because `True == "false"` is False.
    assert gc.is_false(repo) is False  # documents the bug: this "should" be True


def test_is_true_BUG_never_true_for_a_genuinely_open_repo(raw_repo_factory):
    """A repo with issues+projects enabled SHOULD be flagged, but isn't."""
    repo = raw_repo_factory(has_issues=True, has_projects=True)
    # Same root cause: `True == "true"` is False.
    assert gc.is_true(repo) is False  # documents the bug: this "should" be True


# ---------------------------------------------------------------------
# extract() — BUG: mutating a list while iterating over it
# ---------------------------------------------------------------------

@pytest.fixture
def extract_env(tmp_path, monkeypatch):
    """extract() reads/writes the hardcoded relative path data/raw/<file>,
    so give it a real temp cwd with that folder present."""
    (tmp_path / "data" / "raw").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_extract_writes_and_returns_matching_data(monkeypatch, extract_env, raw_repo_factory):
    repo = raw_repo_factory(stargazers_count=100, forks_count=10, open_issues_count=5)

    class FakeResponse:
        def json(self):
            return [repo]

    monkeypatch.setattr(gc.requests, "get", lambda url, headers=None: FakeResponse())

    result = gc.extract("http://fake-url", "out.json")

    assert result == [repo]
    with open("data/raw/out.json") as f:
        on_disk = json.load(f)
    assert on_disk == [repo]


def test_extract_unwraps_search_api_items_key(monkeypatch, extract_env, raw_repo_factory):
    """GitHub's /search/repositories endpoint wraps results in {"items": [...]}."""
    repo = raw_repo_factory(stargazers_count=100, forks_count=10, open_issues_count=5)

    class FakeResponse:
        def json(self):
            return {"total_count": 1, "items": [repo]}

    monkeypatch.setattr(gc.requests, "get", lambda url, headers=None: FakeResponse())

    result = gc.extract("http://fake-url", "out.json")
    assert result == [repo]


def test_extract_BUG_mutate_while_iterate_lets_a_bad_repo_through(
    monkeypatch, extract_env, raw_repo_factory
):
    """
    Four repos, two of which fail passes_threshold (ids 2 and 3) and should
    both be removed. Because extract() removes from the list while looping
    over it, id 3 is skipped by the loop and incorrectly survives.

    This test currently PASSES, which is the bug: id 3 should NOT be in
    the output, but is.
    """
    repos = [
        raw_repo_factory(id=1, stargazers_count=100, forks_count=10, open_issues_count=5),
        raw_repo_factory(id=2, stargazers_count=1, forks_count=10, open_issues_count=5),
        raw_repo_factory(id=3, stargazers_count=1, forks_count=10, open_issues_count=5),
        raw_repo_factory(id=4, stargazers_count=100, forks_count=10, open_issues_count=5),
    ]

    class FakeResponse:
        def json(self):
            return repos

    monkeypatch.setattr(gc.requests, "get", lambda url, headers=None: FakeResponse())

    result = gc.extract("http://fake-url", "out.json")
    ids = [r["id"] for r in result]

    # What SHOULD happen: only 1 and 4 survive (2 and 3 both fail the star threshold).
    # What ACTUALLY happens: 3 slips through because of the mutate-while-iterate bug.
    assert ids == [1, 3, 4]  # <-- pinning today's buggy behavior
    assert 2 not in ids       # the element right after a removal is still caught correctly
