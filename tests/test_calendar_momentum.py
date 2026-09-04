import numpy as np
import pandas as pd

from src.calendar_momentum import (
    ANCHOR_STALENESS_LIMIT,
    WINDOW_START_TOLERANCE_DAYS,
    calendar_start_positions,
    calendar_targets,
    latest_as_of_date,
    winsorised_cross_section_z,
)
from src.quant import clean_holidays, clean_prices, period_window, returns


def price_frame(days=400, symbols=("A", "B", "C", "D"), end="2026-09-01", seed=3):
    idx = pd.bdate_range(end=pd.Timestamp(end), periods=days)
    rng = np.random.default_rng(seed)
    steps = rng.normal(0.0005, 0.012, (days, len(symbols)))
    values = 100.0 * np.exp(np.cumsum(steps, axis=0))
    return pd.DataFrame(values, index=idx, columns=list(symbols))


def test_stale_dataset_anchors_to_its_last_observation():
    """An offline dataset must not acquire a synthetic multi-year lookback."""
    old = pd.DatetimeIndex(pd.bdate_range(end="2020-06-30", periods=100))
    assert latest_as_of_date(old) == pd.Timestamp("2020-06-30")


def test_fresh_dataset_uses_the_current_india_date():
    fresh = pd.DatetimeIndex(pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=100))
    assert latest_as_of_date(fresh) >= pd.Timestamp(fresh[-1])


def test_start_position_is_the_first_session_on_or_after_the_target():
    close = price_frame()
    index = pd.DatetimeIndex(close.index)
    as_of = latest_as_of_date(index)
    starts = calendar_start_positions(index, 6, latest_as_of=as_of)
    targets = calendar_targets(index, 6, latest_as_of=as_of)
    start, target = int(starts[-1]), pd.Timestamp(targets[-1])

    assert index[start] >= target
    assert index[start - 1] < target
    assert target == pd.Timestamp(as_of) - pd.DateOffset(months=6)


def test_horizon_beyond_the_dataset_stays_missing():
    """A 12M label must never be attached to a 6M window."""
    close = price_frame(days=130)
    window = period_window(close, 12)
    assert not window["reachable"]
    assert pd.isna(returns(close).loc["A", "12M Return"])


def test_window_tolerance_admits_a_holiday_but_not_missing_history():
    close = price_frame()
    index = pd.DatetimeIndex(close.index)
    as_of = latest_as_of_date(index)
    target = pd.Timestamp(calendar_targets(index, 3, latest_as_of=as_of)[-1])
    start = int(calendar_start_positions(index, 3, latest_as_of=as_of)[-1])
    # The real anchor is at most a long weekend after the calendar target.
    assert index[start] - target <= pd.Timedelta(days=WINDOW_START_TOLERANCE_DAYS)


def test_anchor_bridges_short_holes_only():
    close = price_frame()
    cleaned = clean_prices(close)
    index = pd.DatetimeIndex(cleaned.index)
    start = int(calendar_start_positions(index, 3, latest_as_of=latest_as_of_date(index))[-1])

    bridged = close.copy()
    bridged.iloc[start - ANCHOR_STALENESS_LIMIT + 1:start + 1, 0] = np.nan
    assert np.isfinite(returns(bridged).loc["A", "3M Return"])

    suspended = close.copy()
    suspended.iloc[start - ANCHOR_STALENESS_LIMIT - 4:start + 1, 1] = np.nan
    assert pd.isna(returns(suspended).loc["B", "3M Return"])


def test_clean_holidays_drops_mostly_empty_sessions():
    close = price_frame(days=50)
    close.iloc[10, :] = np.nan
    close.iloc[20, :3] = np.nan  # 75% missing
    close.iloc[30, :1] = np.nan  # 25% missing, a normal hole
    cleaned = clean_holidays(close)

    assert close.index[10] not in cleaned.index
    assert close.index[20] not in cleaned.index
    assert close.index[30] in cleaned.index


def test_clean_prices_does_not_carry_a_suspended_price_indefinitely():
    idx = pd.bdate_range(end="2026-09-01", periods=30)
    values = np.full(30, np.nan)
    values[:5] = 100.0
    cleaned = clean_prices(pd.DataFrame({"A": values}, index=idx))
    assert cleaned["A"].notna().sum() == 5 + ANCHOR_STALENESS_LIMIT
    assert pd.isna(cleaned["A"].iloc[-1])


def test_winsorised_z_clamps_an_outlier_without_distorting_the_rest():
    frame = pd.DataFrame([[1.0, 2.0, 3.0, 4.0, 500.0]])
    z = winsorised_cross_section_z(frame)
    assert z.abs().max().max() <= 3.0
    # The outlier is pulled in to the winsorisation bound, not left to swamp
    # the cross-section, so the remaining names keep a usable spread.
    assert z.iloc[0, :4].std() > 0
    assert z.iloc[0, 4] == z.iloc[0].max()


def test_winsorised_z_needs_three_names_to_mean_anything():
    assert winsorised_cross_section_z(pd.DataFrame([[1.0, 2.0]])).isna().all().all()
    assert winsorised_cross_section_z(pd.DataFrame([[1.0, 1.0, 1.0]])).isna().all().all()
    assert winsorised_cross_section_z(pd.DataFrame([[1.0, 2.0, 3.0]])).notna().all().all()


def test_latest_sharpe_matches_the_full_history_path_exactly():
    """The last-row fast path is an optimisation, never a different number."""
    from src.quant import latest_sharpe, sharpe

    close = price_frame(days=500, symbols=tuple(f"S{i}" for i in range(12)))
    close = close.mask(np.random.default_rng(11).random(close.shape) < 0.01)
    for months in (1, 3, 6, 9, 12):
        full = sharpe(close, months).iloc[-1]
        fast = latest_sharpe(close, months)
        assert (full.isna() == fast.isna()).all()
        pd.testing.assert_series_equal(full.dropna(), fast.dropna(), check_names=False)


def test_gap_bridging_is_never_applied_twice():
    """Cleaning a frame twice would stretch the 5-session bridge to 10.

    `technical_snapshot` and `momentum_acceleration` both clean their input and
    then delegate, so they must delegate to the clean-input helpers rather than
    to the public entry points, which clean again.
    """
    from src.quant import momentum_acceleration, technical_snapshot

    close = price_frame()
    index = pd.DatetimeIndex(clean_prices(close).index)
    start = int(calendar_start_positions(index, 3, latest_as_of=latest_as_of_date(index))[-1])

    # An 8-session hole ending on the anchor: one bridge leaves it unreachable,
    # two bridges would close it.
    holed = close.copy()
    holed.iloc[start - 7:start + 1, 0] = np.nan
    volume = pd.DataFrame(1000.0, index=close.index, columns=close.columns)

    assert pd.isna(returns(holed).loc["A", "3M Return"])
    assert pd.isna(technical_snapshot(holed, volume).loc["A", "3M Return"])
    assert pd.isna(momentum_acceleration(holed).loc["A"])
