import numpy as np
import pandas as pd

from src.quant import CHART_EMA_SPANS, chart_overlays, relative_strength


def price_series(n=600, seed=4, drift=0.0006):
    idx = pd.bdate_range(end="2026-09-04", periods=n)
    rng = np.random.default_rng(seed)
    return pd.Series(100 * np.exp(np.cumsum(rng.normal(drift, 0.014, n))), index=idx)


def test_relative_strength_is_indexed_to_100_at_the_window_start():
    stock, bench = price_series(seed=1), price_series(seed=2)
    rs = relative_strength(stock, bench)
    assert np.isclose(rs.iloc[0], 100.0)


def test_relative_strength_reads_above_100_only_when_the_stock_outperforms():
    bench = price_series(seed=3, drift=0.0002)
    # Same path, scaled up over time: unambiguous outperformance.
    winner = bench * np.exp(np.linspace(0, 0.5, len(bench)))
    loser = bench * np.exp(np.linspace(0, -0.5, len(bench)))
    assert relative_strength(winner, bench).iloc[-1] > 100
    assert relative_strength(loser, bench).iloc[-1] < 100
    # A stock that simply tracks the index is neither.
    assert np.isclose(relative_strength(bench, bench).iloc[-1], 100.0)


def test_relative_strength_needs_overlapping_history():
    stock = price_series(n=100)
    disjoint = pd.Series(
        [1.0, 2.0], index=pd.DatetimeIndex(["2001-01-01", "2001-01-02"])
    )
    assert relative_strength(stock, disjoint).empty


def test_overlays_cover_every_configured_span():
    close = price_series()
    overlays = chart_overlays(close)
    assert set(overlays) == set(CHART_EMA_SPANS)
    for span, values in overlays.items():
        # An EMA is undefined until it has its own span of observations.
        assert values.iloc[: span - 1].isna().all()
        assert values.iloc[-1] == values.iloc[-1]  # not NaN


def test_a_long_ema_is_not_silently_restarted_on_a_short_window():
    """The 200 EMA on a 3-month view must still be the 200 EMA.

    Computing overlays after slicing would produce a 60-observation average
    wearing the 200 EMA's name -- close enough to look right and wrong enough
    to trade on.
    """
    close = price_series(n=600)
    full = chart_overlays(close)[200]
    window = close.tail(63).index

    sliced_after = full.reindex(window)
    computed_on_window = chart_overlays(close.tail(63))[200]

    assert sliced_after.notna().all()
    assert computed_on_window.isna().all()
