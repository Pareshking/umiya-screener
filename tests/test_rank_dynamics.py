import numpy as np
import pandas as pd

from src.quant import (
    SETUP_RULES,
    classify_setup,
    cross_sectional_rank,
    max_drawdown,
    momentum_score,
    rank_as_of,
    rank_delta,
    score_percentile,
    sma_distance,
    universe_breadth,
)


def universe(n=700, m=40, seed=5):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range(end="2026-09-04", periods=n)
    cols = [f"S{i:02d}" for i in range(m)]
    return pd.DataFrame(
        100 * np.exp(np.cumsum(rng.normal(4e-4, 0.016, (n, m)), axis=0)), index=idx, columns=cols
    )


def test_rank_delta_is_positive_when_a_stock_climbs():
    """Up must read positive, matching every other coloured column.

    A stock going from 40th to 12th has gained 28 places; reporting -28
    because the number got smaller would invert the colour of the whole column.
    """
    close = universe()
    history = momentum_score(close)
    past = rank_as_of(history, 3)
    now = cross_sectional_rank(history.iloc[-1])
    delta = rank_delta(history, 3)

    climbed = (past - now).idxmax()
    assert now[climbed] < past[climbed]
    assert delta[climbed] > 0
    # And the whole column is exactly past minus present.
    pd.testing.assert_series_equal(delta.dropna(), (past - now).dropna(), check_names=False)


def test_rank_delta_is_unavailable_when_history_is_too_short():
    close = universe(n=40)
    history = momentum_score(close)
    assert rank_delta(history, 3).isna().all()


def test_score_percentile_orders_with_the_score():
    scores = pd.Series({"a": -2.0, "b": 0.0, "c": 1.0, "d": 3.0})
    pct = score_percentile(scores)
    assert pct["d"] > pct["c"] > pct["b"] > pct["a"]
    assert pct.max() <= 99


def test_max_drawdown_is_negative_and_matches_a_known_path():
    idx = pd.bdate_range(end="2026-09-04", periods=300)
    # Rise to 200, fall to 120 (-40%), recover a little.
    path = np.concatenate([
        np.linspace(100, 200, 150),
        np.linspace(200, 120, 100),
        np.linspace(120, 150, 50),
    ])
    dd = max_drawdown(pd.DataFrame({"A": path}, index=idx), 12)
    assert np.isclose(dd["A"], -40.0, atol=0.5)


def test_sma_distance_is_zero_on_a_flat_series():
    idx = pd.bdate_range(end="2026-09-04", periods=400)
    flat = pd.DataFrame({"A": np.full(400, 250.0)}, index=idx)
    assert np.isclose(sma_distance(flat, 200)["A"], 0.0)


def test_setup_labels_come_only_from_the_documented_rules():
    frame = pd.DataFrame({
        "Score Percentile": [95, 80, 80, 50, 50, 50, 30, np.nan],
        "% From 52W High": [-1.0, -3.0, -3.0, -1.0, -30.0, -8.0, -40.0, -5.0],
        "% EMA 50": [5.0, 4.0, -2.0, 1.0, 2.0, 1.0, -5.0, 1.0],
        "% EMA 200": [9.0, 8.0, 6.0, 4.0, 3.0, 2.0, -9.0, np.nan],
        "Volume Ratio": [2.0, 0.8, 0.9, 1.5, 0.7, 0.8, 0.5, 1.0],
        "Rank Δ3M": [1, 2, 3, 4, 5, 25, 0, 0],
    })
    setups = classify_setup(frame)
    allowed = {label for label, _ in SETUP_RULES} | {"—"}
    assert set(setups) <= allowed

    assert setups.iloc[0] == "LEADER"      # top decile, above 200 EMA, near high
    assert setups.iloc[1] == "STRONG"      # top quartile, above both EMAs
    assert setups.iloc[2] == "PULLBACK"    # top quartile but under the 50 EMA
    assert setups.iloc[3] == "BREAKOUT"    # at the high on heavy volume
    assert setups.iloc[4] == "BASING"      # above 200 EMA, far off its high
    assert setups.iloc[5] == "RISING"      # climbed 25 places in three months
    assert setups.iloc[6] == "WEAK"        # below the 200 EMA
    assert setups.iloc[7] == "—"           # no trend data at all


def test_breadth_counts_the_whole_universe_not_the_filtered_view():
    frame = pd.DataFrame({
        "% EMA 50": [1.0, 1.0, -1.0, -1.0],
        "% EMA 200": [1.0, 1.0, 1.0, -1.0],
        "% From 52W High": [-2.0, -30.0, -5.0, -50.0],
        "3M Return": [5.0, -1.0, 2.0, -8.0],
        "Rank": [10, 60, 40, 200],
        "Rank Δ1M": [45, -20, 0, 0],   # #1 entered the top 50, #2 fell out
    })
    b = universe_breadth(frame)
    assert b["total"] == 4
    assert b["above_50_ema"] == {"count": 2, "pct": 50.0}
    assert b["near_52w_high"]["count"] == 2      # within 10%
    assert b["positive_3m"]["count"] == 2
    assert b["entered_top_50"] == 1
    assert b["exited_top_50"] == 1


def test_breadth_survives_an_empty_frame():
    assert universe_breadth(pd.DataFrame())["total"] == 0


def test_breadth_and_metadata_survive_a_dataset_missing_the_new_columns():
    """An older published dataset must not take the homepage down.

    The metadata endpoint is the first call the screener makes. If a metrics
    dataset predating these columns made it raise, the whole page would fail
    rather than losing one sidebar panel.
    """
    legacy = pd.DataFrame({"Symbol": ["A", "B"], "Momentum Score": [1.0, 2.0]})
    b = universe_breadth(legacy)
    assert b["total"] == 2
    assert b["above_50_ema"] is None
    assert b["entered_top_50"] is None
