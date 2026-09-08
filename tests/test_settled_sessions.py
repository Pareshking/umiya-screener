"""A session that is still trading must never be published as a close.

On 2026-09-08 the refresh built at 06:29 UTC -- 11:59 IST, two and a half
hours into a six-hour session -- and published it as the latest close. The
screener served RELIANCE at 4.0M shares against a 10-13M daily norm, and every
price-derived field (CMP, distance from the 52-week high, EMA distances, the
volume ratio) described a market state that had not happened yet.

Cron placement cannot prevent this. GitHub delivers scheduled runs hours late,
which is documented and has been observed repeatedly in this repository, so the
pipeline refuses the partial bar rather than trusting the clock.
"""

from __future__ import annotations

import datetime as dt

import pandas as pd
import pytest

from src.data import IST, drop_unsettled_sessions, last_settled_session


def at_ist(year, month, day, hour, minute=0):
    return dt.datetime(year, month, day, hour, minute, tzinfo=IST)


def frame_through(last_day: str, rows: int = 5):
    index = pd.bdate_range(end=last_day, periods=rows)
    return pd.DataFrame({"RELIANCE": range(len(index))}, index=index)


def test_the_session_in_progress_is_dropped():
    """The exact failure: a build during Tuesday's session."""
    frame = frame_through("2026-09-08")
    kept = drop_unsettled_sessions(frame, now=at_ist(2026, 9, 8, 11, 59))
    assert pd.Timestamp("2026-09-08") not in kept.index
    assert kept.index[-1] == pd.Timestamp("2026-09-07")


def test_a_settled_session_is_kept():
    frame = frame_through("2026-09-08")
    kept = drop_unsettled_sessions(frame, now=at_ist(2026, 9, 8, 17, 0))
    assert kept.index[-1] == pd.Timestamp("2026-09-08"), "a closed session must be published"


@pytest.mark.parametrize("hour,minute,settled", [
    (9, 0, False),    # before the open
    (11, 59, False),  # what actually happened
    (15, 29, False),  # one minute before the bell
    (15, 45, False),  # closed, but the closing print is not final yet
    (16, 30, True),   # settlement buffer elapsed
    (23, 0, True),
])
def test_settlement_boundary(hour, minute, settled):
    expected = "2026-09-08" if settled else "2026-09-07"
    assert last_settled_session(at_ist(2026, 9, 8, hour, minute)) == pd.Timestamp(expected)


def test_a_late_run_still_publishes_the_previous_close():
    """The guard must make a late-firing cron harmless, not fatal."""
    frame = frame_through("2026-09-08")
    for hour in (7, 10, 12, 14):
        kept = drop_unsettled_sessions(frame, now=at_ist(2026, 9, 8, hour))
        assert kept.index[-1] == pd.Timestamp("2026-09-07")
        assert not kept.empty, "a late run must still publish something"


def test_earlier_history_is_untouched():
    frame = frame_through("2026-09-08", rows=200)
    kept = drop_unsettled_sessions(frame, now=at_ist(2026, 9, 8, 11, 59))
    assert len(kept) == len(frame) - 1
    pd.testing.assert_frame_equal(kept, frame.iloc[:-1])


def test_an_empty_frame_is_returned_unchanged():
    empty = pd.DataFrame()
    assert drop_unsettled_sessions(empty, now=at_ist(2026, 9, 8, 11, 59)).empty
    assert drop_unsettled_sessions(None) is None


def test_the_build_applies_the_guard():
    """A correct helper nobody calls leaves the site publishing partial bars."""
    import inspect

    import scripts.build_data as build_data

    source = inspect.getsource(build_data.build)
    assert source.count("drop_unsettled_sessions") >= 2, (
        "prices and volume must both be trimmed to settled sessions"
    )
