# tests/test_transform.py
from ingest.transform import transform   # adjust import to your actual function


def test_returns_dataframe(sample_repos):
    # TODO: call transform_repos, assert the result is a DataFrame
    # hint: import pandas as pd, then assert isinstance(result, pd.DataFrame)
    pass


def test_has_expected_columns(sample_repos):
    # TODO: assert the output columns match your 8 expected columns
    # hint: compare set(df.columns) to your expected set
    pass


def test_rename_happened(sample_repos):
    # TODO: assert "owner_login" exists and "owner.login" does NOT
    pass


def test_row_count_matches_input(sample_repos):
    # TODO: assert len(df) equals the number of input repos
    pass


def test_values_extracted_correctly(sample_repos):
    # TODO: assert specific values, e.g. first row's owner_login == "alice"
    # hint: df.iloc[0]["owner_login"]
    pass


def test_handles_null_description(sample_repos):
    # TODO: assert the repo with description=None is handled (not crashed)
    pass


def test_empty_input():
    # TODO: pass an empty list, assert you get an empty DataFrame (not an error)
    pass