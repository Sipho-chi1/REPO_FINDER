# tests/test_load.py
from unittest.mock import MagicMock, patch
import pandas as pd

from ingest.load import load


def test_calls_to_sql_with_correct_table_name():
    df = pd.DataFrame({"id": [1, 2], "name": ["a", "b"]})
    engine = MagicMock()

    with patch.object(pd.DataFrame, "to_sql") as mock_to_sql:
        load(engine, df)
        mock_to_sql.assert_called_once()
        args, kwargs = mock_to_sql.call_args
        assert args[0] == "repositories"
        assert args[1] is engine


def test_replaces_existing_table():
    df = pd.DataFrame({"id": [1]})
    engine = MagicMock()

    with patch.object(pd.DataFrame, "to_sql") as mock_to_sql:
        load(engine, df)
        _, kwargs = mock_to_sql.call_args
        assert kwargs.get("if_exists") == "replace"


def test_does_not_write_the_index():
    df = pd.DataFrame({"id": [1]})
    engine = MagicMock()

    with patch.object(pd.DataFrame, "to_sql") as mock_to_sql:
        load(engine, df)
        _, kwargs = mock_to_sql.call_args
        assert kwargs.get("index") is False


def test_prints_row_count(capsys):
    df = pd.DataFrame({"id": [1, 2, 3]})
    engine = MagicMock()

    with patch.object(pd.DataFrame, "to_sql"):
        load(engine, df)

    captured = capsys.readouterr()
    assert "3" in captured.out


def test_empty_dataframe_does_not_raise():
    df = pd.DataFrame()
    engine = MagicMock()

    with patch.object(pd.DataFrame, "to_sql") as mock_to_sql:
        load(engine, df)
        mock_to_sql.assert_called_once()
