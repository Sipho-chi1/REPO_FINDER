# tests/test_api_main.py
from unittest.mock import MagicMock, patch
import pandas as pd
import pytest

from api import main as api_main


# ---------------------------------------------------------------------
# get_available_languages()
# ---------------------------------------------------------------------

def test_get_available_languages_queries_and_returns_dataframe():
    fake_df = pd.DataFrame({"language": ["Python", "Go"], "repos": [10, 3]})
    with patch.object(api_main.pd, "read_sql", return_value=fake_df) as mock_read_sql:
        result = api_main.get_available_languages()

    assert result is fake_df
    query_arg = mock_read_sql.call_args[0][0]
    assert "GROUP BY language" in query_arg
    assert "LIMIT 10" in query_arg


# ---------------------------------------------------------------------
# find_matches()
# ---------------------------------------------------------------------

def test_find_matches_passes_correct_params():
    fake_df = pd.DataFrame()
    with patch.object(api_main.pd, "read_sql", return_value=fake_df) as mock_read_sql:
        api_main.find_matches("Python", "beginner", min_pct=25)

    _, kwargs = mock_read_sql.call_args
    assert kwargs["params"] == {
        "language": "Python",
        "experience": "beginner",
        "min_pct": 25,
    }


def test_find_matches_default_min_pct_is_30():
    with patch.object(api_main.pd, "read_sql", return_value=pd.DataFrame()) as mock_read_sql:
        api_main.find_matches("Go", "advanced")

    _, kwargs = mock_read_sql.call_args
    assert kwargs["params"]["min_pct"] == 30


# ---------------------------------------------------------------------
# main() — interactive CLI flow
# ---------------------------------------------------------------------

def _languages_df():
    return pd.DataFrame({"language": ["Python"], "repos": [5]})


def _results_df():
    return pd.DataFrame({
        "full_name": ["octocat/demo"],
        "html_url": ["https://github.com/octocat/demo"],
        "experience_level": ["beginner"],
        "language_pct": [80.0],
    })


def test_main_skips_pipeline_refresh_when_answer_is_not_y(monkeypatch):
    inputs = iter(["n", "Python", "beginner", ""])
    monkeypatch.setattr("builtins.input", lambda _="": next(inputs))

    with patch.object(api_main, "pipeline") as mock_pipeline, \
         patch.object(api_main, "get_available_languages", return_value=_languages_df()), \
         patch.object(api_main, "find_matches", return_value=pd.DataFrame()):
        api_main.main()

    mock_pipeline.assert_not_called()


def test_main_runs_pipeline_when_answer_is_y(monkeypatch):
    inputs = iter(["y", "Python", "beginner", ""])
    monkeypatch.setattr("builtins.input", lambda _="": next(inputs))

    with patch.object(api_main, "pipeline") as mock_pipeline, \
         patch.object(api_main, "get_available_languages", return_value=_languages_df()), \
         patch.object(api_main, "find_matches", return_value=pd.DataFrame()):
        api_main.main()

    mock_pipeline.assert_called_once()


def test_main_reprompts_until_valid_experience_level(monkeypatch):
    # "n" for refresh, "Python" for language, two bad experience inputs, then valid
    inputs = iter(["n", "Python", "expert", "novice", "intermediate", ""])
    monkeypatch.setattr("builtins.input", lambda _="": next(inputs))

    with patch.object(api_main, "get_available_languages", return_value=_languages_df()), \
         patch.object(api_main, "find_matches", return_value=pd.DataFrame()) as mock_find:
        api_main.main()

    args, _ = mock_find.call_args
    assert args[1] == "intermediate"


def test_main_prints_no_matches_message_when_results_empty(monkeypatch, capsys):
    inputs = iter(["n", "Python", "beginner"])
    monkeypatch.setattr("builtins.input", lambda _="": next(inputs))

    with patch.object(api_main, "get_available_languages", return_value=_languages_df()), \
         patch.object(api_main, "find_matches", return_value=pd.DataFrame()):
        api_main.main()

    assert "No beginner matches found for Python" in capsys.readouterr().out


def test_main_opens_browser_for_valid_selection(monkeypatch):
    inputs = iter(["n", "Python", "beginner", "1"])
    monkeypatch.setattr("builtins.input", lambda _="": next(inputs))

    with patch.object(api_main, "get_available_languages", return_value=_languages_df()), \
         patch.object(api_main, "find_matches", return_value=_results_df()), \
         patch.object(api_main.webbrowser, "open") as mock_open:
        api_main.main()

    mock_open.assert_called_once_with("https://github.com/octocat/demo")


def test_main_handles_out_of_range_selection_without_crashing(monkeypatch, capsys):
    inputs = iter(["n", "Python", "beginner", "99"])
    monkeypatch.setattr("builtins.input", lambda _="": next(inputs))

    with patch.object(api_main, "get_available_languages", return_value=_languages_df()), \
         patch.object(api_main, "find_matches", return_value=_results_df()), \
         patch.object(api_main.webbrowser, "open") as mock_open:
        api_main.main()

    mock_open.assert_not_called()
    assert "Invalid selection" in capsys.readouterr().out


def test_main_quits_gracefully_on_empty_selection(monkeypatch, capsys):
    inputs = iter(["n", "Python", "beginner", ""])
    monkeypatch.setattr("builtins.input", lambda _="": next(inputs))

    with patch.object(api_main, "get_available_languages", return_value=_languages_df()), \
         patch.object(api_main, "find_matches", return_value=_results_df()), \
         patch.object(api_main.webbrowser, "open") as mock_open:
        api_main.main()

    mock_open.assert_not_called()
    assert "Goodbye" in capsys.readouterr().out
