# tests/test_analyze.py
import json
from unittest.mock import MagicMock, patch
import pandas as pd
import pytest

from analysis import analyze


# ---------------------------------------------------------------------
# analyze_issue() — pure prompt builder
# ---------------------------------------------------------------------

def test_analyze_issue_includes_all_inputs():
    prompt = analyze.analyze_issue(
        title="Fix typo in README",
        body="Spelling mistake in setup section",
        labels="good first issue,documentation",
        language="Python",
    )
    assert "Fix typo in README" in prompt
    assert "Spelling mistake in setup section" in prompt
    assert "good first issue,documentation" in prompt
    assert "Python" in prompt


def test_analyze_issue_requests_json_only_output():
    prompt = analyze.analyze_issue("t", "b", "l", "Go")
    assert "JSON" in prompt
    assert '"level"' in prompt
    assert "beginner" in prompt and "intermediate" in prompt and "advanced" in prompt


def test_analyze_issue_handles_empty_body():
    prompt = analyze.analyze_issue("Title only", "", "bug", "Rust")
    assert "Title only" in prompt  # doesn't crash on empty body


# ---------------------------------------------------------------------
# get_issues_to_analyze() — verifies the query/params contract, not the DB
# ---------------------------------------------------------------------

def test_get_issues_to_analyze_passes_expected_params():
    fake_df = pd.DataFrame({"repo_id": [1], "issue_number": [10]})
    engine = MagicMock()

    with patch.object(analyze.pd, "read_sql", return_value=fake_df) as mock_read_sql:
        result = analyze.get_issues_to_analyze(engine, "Python", min_pct=40)

    assert result is fake_df
    _, kwargs = mock_read_sql.call_args
    assert kwargs["params"] == {"language": "Python", "min_pct": 40}


def test_get_issues_to_analyze_default_min_pct_is_30():
    fake_df = pd.DataFrame()
    engine = MagicMock()

    with patch.object(analyze.pd, "read_sql", return_value=fake_df) as mock_read_sql:
        analyze.get_issues_to_analyze(engine, "Go")

    _, kwargs = mock_read_sql.call_args
    assert kwargs["params"]["min_pct"] == 30


def test_get_issues_to_analyze_query_excludes_already_analyzed():
    fake_df = pd.DataFrame()
    engine = MagicMock()

    with patch.object(analyze.pd, "read_sql", return_value=fake_df) as mock_read_sql:
        analyze.get_issues_to_analyze(engine, "Python")

    query_arg = mock_read_sql.call_args[0][0]
    assert "NOT EXISTS" in query_arg
    assert "repo_analysis" in query_arg


# ---------------------------------------------------------------------
# save_analysis() — verifies the insert is executed with the right values
# ---------------------------------------------------------------------

def test_save_analysis_executes_insert_with_correct_params(mock_engine):
    analyze.save_analysis(mock_engine, repo_id=5, issue_number=7,
                           level="beginner", reasoning="clear scope")

    conn = mock_engine.begin.return_value.__enter__.return_value
    conn.execute.assert_called_once()
    args, _ = conn.execute.call_args
    params = args[1]
    assert params == {
        "repo_id": 5,
        "issue_number": 7,
        "level": "beginner",
        "reasoning": "clear scope",
    }


# ---------------------------------------------------------------------
# run_analysis() — orchestration
# ---------------------------------------------------------------------

def test_run_analysis_processes_up_to_limit(mock_engine):
    issues = pd.DataFrame([
        {"repo_id": 1, "issue_number": 1, "title": "a", "labels": "", "full_name": "x/a"},
        {"repo_id": 1, "issue_number": 2, "title": "b", "labels": "", "full_name": "x/a"},
        {"repo_id": 1, "issue_number": 3, "title": "c", "labels": "", "full_name": "x/a"},
    ])
    llm_reply = json.dumps({"level": "beginner", "skills": [], "estimated_hours": 1,
                             "reasoning": "simple"})

    with patch.object(analyze, "get_issues_to_analyze", return_value=issues), \
         patch.object(analyze, "ask_gemini", return_value=llm_reply) as mock_ask, \
         patch.object(analyze, "save_analysis") as mock_save:
        analyze.run_analysis(mock_engine, "Python", limit=2)

    assert mock_ask.call_count == 2   # respects the limit, doesn't process all 3
    assert mock_save.call_count == 2


def test_run_analysis_strips_markdown_code_fences(mock_engine):
    issues = pd.DataFrame([
        {"repo_id": 1, "issue_number": 1, "title": "a", "labels": "", "full_name": "x/a"},
    ])
    fenced_reply = "```json\n" + json.dumps({"level": "advanced", "reasoning": "complex"}) + "\n```"

    with patch.object(analyze, "get_issues_to_analyze", return_value=issues), \
         patch.object(analyze, "ask_gemini", return_value=fenced_reply), \
         patch.object(analyze, "save_analysis") as mock_save:
        analyze.run_analysis(mock_engine, "Python", limit=1)

    mock_save.assert_called_once_with(mock_engine, 1, 1, "advanced", "complex")


def test_run_analysis_continues_after_one_issue_fails(mock_engine, capsys):
    issues = pd.DataFrame([
        {"repo_id": 1, "issue_number": 1, "title": "bad json", "labels": "", "full_name": "x/a"},
        {"repo_id": 1, "issue_number": 2, "title": "good json", "labels": "", "full_name": "x/a"},
    ])
    good_reply = json.dumps({"level": "beginner", "reasoning": "ok"})

    with patch.object(analyze, "get_issues_to_analyze", return_value=issues), \
         patch.object(analyze, "ask_gemini", side_effect=["not json at all", good_reply]), \
         patch.object(analyze, "save_analysis") as mock_save:
        analyze.run_analysis(mock_engine, "Python", limit=2)

    # First issue fails to parse and is skipped; second still gets saved.
    mock_save.assert_called_once_with(mock_engine, 1, 2, "beginner", "ok")
    assert "Failed on #1" in capsys.readouterr().out


def test_run_analysis_handles_zero_issues(mock_engine):
    with patch.object(analyze, "get_issues_to_analyze", return_value=pd.DataFrame(
            columns=["repo_id", "issue_number", "title", "labels", "full_name"])), \
         patch.object(analyze, "ask_gemini") as mock_ask, \
         patch.object(analyze, "save_analysis") as mock_save:
        analyze.run_analysis(mock_engine, "Python", limit=5)

    mock_ask.assert_not_called()
    mock_save.assert_not_called()
