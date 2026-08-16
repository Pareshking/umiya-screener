import pandas as pd

from src.data import HISTORY_YEARS, PRICE_FIELDS, _ten_year_window, align_trailing_to_as_of, eligible_symbols


def test_canonical_price_contract():
    assert PRICE_FIELDS == ("adj_close", "volume")
    assert HISTORY_YEARS == 10


def test_ten_year_window_is_explicit():
    start, end = _ten_year_window()
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)
    assert end_ts > start_ts
    assert end_ts - start_ts >= pd.Timedelta(days=3652)
    assert end_ts - start_ts <= pd.Timedelta(days=3654)


def test_eligibility_uses_common_as_of_and_three_day_freshness():
    dates = pd.bdate_range("2026-01-01", periods=130)
    close = pd.DataFrame(index=dates)
    close["FRESH"] = 100.0
    close["ONE_DAY_OLD"] = 100.0
    close["THREE_DAYS_OLD"] = 100.0
    close["FOUR_DAYS_OLD"] = 100.0
    close.loc[dates[-1], "ONE_DAY_OLD"] = pd.NA
    close.loc[dates[-1], "THREE_DAYS_OLD"] = pd.NA
    close.loc[dates[-1], "FOUR_DAYS_OLD"] = pd.NA
    close.loc[dates[-2], "THREE_DAYS_OLD"] = pd.NA
    close.loc[dates[-2], "FOUR_DAYS_OLD"] = pd.NA
    close.loc[dates[-3], "FOUR_DAYS_OLD"] = pd.NA
    close.loc[dates[-4], "FOUR_DAYS_OLD"] = pd.NA

    as_of = dates[-1]
    result = eligible_symbols(close, as_of=as_of)
    symbols = set(result["Symbol"])

    assert {"FRESH", "ONE_DAY_OLD", "THREE_DAYS_OLD"}.issubset(symbols)
    assert "FOUR_DAYS_OLD" not in symbols


def test_partial_missing_stock_does_not_delete_market_dates():
    dates = pd.bdate_range("2026-01-01", periods=130)
    close = pd.DataFrame({"A": 100.0, "B": 100.0}, index=dates)
    close.loc[dates[20], "B"] = pd.NA
    close.loc[dates[21], "A"] = pd.NA
    assert len(close) == 130
    assert close.loc[dates[20], "A"] == 100.0
    assert pd.isna(close.loc[dates[20], "B"])


def test_trailing_alignment_does_not_fill_interior_gaps():
    dates = pd.bdate_range("2026-01-01", periods=5)
    frame = pd.DataFrame({"A": [1.0, pd.NA, 3.0, pd.NA, pd.NA]}, index=dates)
    aligned = align_trailing_to_as_of(frame, ["A"], dates[-1])
    assert pd.isna(aligned.loc[dates[1], "A"])
    assert pd.isna(aligned.loc[dates[3], "A"]) is False
    assert aligned.loc[dates[3], "A"] == 3.0
    assert aligned.loc[dates[4], "A"] == 3.0
