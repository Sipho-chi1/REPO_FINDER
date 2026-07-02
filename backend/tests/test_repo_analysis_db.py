# tests/test_repo_analysis_db.py
from unittest.mock import patch

from db import repo_analysis


def test_create_repo_analysis_table_executes_schema_sql(tmp_path, monkeypatch, mock_engine):
    """create_repo_analysis_table() reads the hardcoded relative path
    db/create_repo_analysis.sql, so recreate that path under a temp cwd."""
    schema_dir = tmp_path / "db"
    schema_dir.mkdir()
    schema_sql = "CREATE TABLE IF NOT EXISTS repo_analysis (id INTEGER);"
    (schema_dir / "create_repo_analysis.sql").write_text(schema_sql)
    monkeypatch.chdir(tmp_path)

    with patch.object(repo_analysis, "engine", mock_engine):
        repo_analysis.create_repo_analysis_table()

    conn = mock_engine.begin.return_value.__enter__.return_value
    conn.execute.assert_called_once()
    executed_sql = str(conn.execute.call_args[0][0])
    assert "repo_analysis" in executed_sql


def test_create_repo_analysis_table_prints_confirmation(tmp_path, monkeypatch, mock_engine, capsys):
    schema_dir = tmp_path / "db"
    schema_dir.mkdir()
    (schema_dir / "create_repo_analysis.sql").write_text("CREATE TABLE t (id INT);")
    monkeypatch.chdir(tmp_path)

    with patch.object(repo_analysis, "engine", mock_engine):
        repo_analysis.create_repo_analysis_table()

    assert "repo_analysis table created" in capsys.readouterr().out
