import numpy as np
import pandas as pd

from src.data import align_trailing_to_as_of, eligible_symbols, latest_market_date


def make_prices():
    dates = pd.to_datetime(["2026-08-10", "2026-08-11", "2026-08-12", "2026-08-13", "2026-08-14"])
    return pd.DataFrame(
        {
            "FRESH": [100, 101, 102, 103, 104],
            "ONE_DAY_OLD": [100, 101, 102, 103, np.nan],
            "THREE_DAYS_OLD": [100, 101, np.nan, np.nan, np.nan],
            "FOUR_DAYS_OLD": [100, np.nan, np.nan, np.nan, np.nan],
        },
        index=dates,
    )


def test_latest_market_date_is_common_universe_date():
    prices = make_prices()
    assert latest_market_date(prices) == pd.Timestamp("2026-08-14")


def test_freshness_uses_common_market_date_not_each_stock_latest_date():
    prices = make_prices()
    # Repeat enough observations so the test isolates freshness rather than history length.
    prices = pd.concat([prices] * 32, ignore_index=True)
    prices.index = pd.bdate_range("2026-06-01", periods=len(prices))
    # Make the last observations stale by removing trailing values.
    prices.loc[prices.index[-1], "ONE_DAY_OLD"] = np.nan
    prices.loc[prices.index[-3]:, "THREE_DAYS_OLD"] = np.nan
    prices.loc[prices.index[-4]:, "FOUR_DAYS_OLD"] = np.nan
    eligibility = eligible_symbols(prices, as_of=prices.index[-1])
    assert set(eligibility["Symbol"]) == {"FRESH", "ONE_DAY_OLD", "THREE_DAYS_OLD"}


def test_align_only_fills_trailing_gap_to_common_as_of():
    prices = make_prices()
    aligned = align_trailing_to_as_of(prices, ["ONE_DAY_OLD"], pd.Timestamp("2026-08-14"))
    assert aligned.loc[pd.Timestamp("2026-08-14"), "ONE_DAY_OLD"] == 103
    # An interior gap is never filled by this helper.
    prices.loc[pd.Timestamp("2026-08-12"), "ONE_DAY_OLD"] = np.nan
    aligned = align_trailing_to_as_of(prices, ["ONE_DAY_OLD"], pd.Timestamp("2026-08-14"))
    assert pd.isna(aligned.loc[pd.Timestamp("2026-08-12"), "ONE_DAY_OLD"])
