import io

import pandas as pd
import pytest

from src.data import _parse_universe, _validate_index_count


def _csv(rows):
    return pd.DataFrame(rows).to_csv(index=False).encode()


def test_parse_constituent_file_extracts_core_fields():
    raw = _csv([
        {"Symbol": " ABC ", "Company Name": "ABC Ltd", "Industry": "Finance"},
        {"Symbol": "XYZ", "Company Name": "XYZ Ltd", "Industry": "IT"},
        {"Symbol": "ABC", "Company Name": "duplicate", "Industry": "Other"},
    ])
    frame = _parse_universe(raw)
    assert frame["Symbol"].tolist() == ["ABC", "XYZ"]
    assert frame.loc[0, "Company Name"] == "ABC Ltd"
    assert frame.loc[1, "Industry"] == "IT"


def test_parse_supports_ticker_column():
    raw = _csv([
        {"Ticker": "abc", "Name": "ABC Ltd", "Sector": "Finance"},
    ])
    frame = _parse_universe(raw)
    assert frame.iloc[0]["Symbol"] == "ABC"
    assert frame.iloc[0]["Company Name"] == "ABC Ltd"


def test_constituent_count_change_is_allowed_but_reported():
    warning = _validate_index_count("NIFTY 50", 51)
    assert warning is not None
    assert "50" in warning and "51" in warning


def test_catastrophically_incomplete_constituent_source_is_rejected():
    with pytest.raises(ValueError, match="parsed only 30 constituents"):
        _validate_index_count("NIFTY 50", 30)
