import numpy as np
import pandas as pd

from src.data import align_trailing_to_as_of, eligible_symbols, latest_market_date


def make_prices():
    dates = pd.bdate_range("2026-02-23", periods=130)
    values = np.arange(130, dtype=float) + 100
    prices = pd.DataFrame({"FRESH": values, "ONE_DAY_OLD": values, "THREE_DAYS_OLD": values, "FOUR_DAYS_OLD": values}, index=dates)
    prices.loc[dates[-1], "ONE_DAY_OLD"] = np.nan
    prices.loc[dates[-3]:, "THREE_DAYS_OLD"] = np.nan  # last valid Tuesday; Friday -> 3 calendar days
    prices.loc[dates[-4]:, "FOUR_DAYS_OLD"] = np.nan   # last valid Monday; Friday -> 4 calendar days
    return prices


def test_latest_market_date_is_common_universe_date():
    prices = make_prices()
    assert latest_market_date(prices) == prices.index[-1]


def test_freshness_uses_common_market_date_not_each_stock_latest_date():
    prices = make_prices()
    eligibility = eligible_symbols(prices, as_of=prices.index[-1])
    assert set(eligibility["Symbol"]) == {"FRESH", "ONE_DAY_OLD", "THREE_DAYS_OLD"}


def test_alignment_never_fills_trailing_gap():
    prices = make_prices()
    aligned = align_trailing_to_as_of(prices, ["ONE_DAY_OLD"], prices.index[-1])
    assert pd.isna(aligned.iloc[-1]["ONE_DAY_OLD"])
    assert pd.isna(aligned.iloc[-2]["ONE_DAY_OLD"])


def test_alignment_preserves_interior_missing_data():
    prices = make_prices()
    prices.loc[prices.index[-2], "FRESH"] = np.nan
    aligned = align_trailing_to_as_of(prices, ["FRESH"], prices.index[-1])
    assert pd.isna(aligned.iloc[-2]["FRESH"])
    assert aligned.iloc[-1]["FRESH"] == prices.iloc[-1]["FRESH"]
