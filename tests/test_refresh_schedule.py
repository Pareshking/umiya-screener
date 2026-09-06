"""The refresh schedule and the cache TTL are one system, not two settings.

They drifted apart in production: builds ran Mon-Fri, leaving a 72h weekend gap
against a 24h TTL, so the API served 503 from Saturday evening until Monday's
build -- every weekend. Nothing tied the two numbers together, so nothing
noticed. These tests tie them together.
"""

from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

import pytest

from src.config import METRICS_CACHE_TTL_HOURS

WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "data-refresh.yml"


def refresh_cron() -> str:
    text = WORKFLOW.read_text(encoding="utf-8")
    match = re.search(r'^\s*-\s*cron:\s*"([^"]+)"', text, re.MULTILINE)
    assert match, "data-refresh workflow has no cron schedule"
    return match.group(1)


def scheduled_runs(cron: str, weeks: int = 3) -> list[dt.datetime]:
    """Expand a 5-field cron over a few weeks. Supports the shapes we use."""
    minute, hour, dom, month, dow = cron.split()
    assert dom == "*" and month == "*", f"unsupported day-of-month/month in {cron!r}"

    if dow == "*":
        days = set(range(7))
    elif "-" in dow:
        lo, hi = (int(x) for x in dow.split("-"))
        # cron: 0=Sunday..6=Saturday; python: 0=Monday..6=Sunday
        days = {(d - 1) % 7 for d in range(lo, hi + 1)}
    else:
        days = {(int(d) - 1) % 7 for d in dow.split(",")}

    start = dt.datetime(2026, 9, 7, tzinfo=dt.timezone.utc)  # a Monday
    return [
        start.replace(hour=int(hour), minute=int(minute)) + dt.timedelta(days=offset)
        for offset in range(7 * weeks)
        if (start + dt.timedelta(days=offset)).weekday() in days
    ]


def test_no_gap_between_builds_outlives_the_cache_ttl():
    """The bug this file exists for: a schedule that lets the dataset expire."""
    runs = scheduled_runs(refresh_cron())
    assert len(runs) > 1
    gaps = [(b - a).total_seconds() / 3600 for a, b in zip(runs, runs[1:])]
    worst = max(gaps)
    assert worst < METRICS_CACHE_TTL_HOURS, (
        f"builds can be {worst:.0f}h apart but the dataset expires after "
        f"{METRICS_CACHE_TTL_HOURS}h, so the API would serve 503 in between"
    )


def test_the_ttl_leaves_room_for_one_missed_run():
    """One failed night must not take the API down."""
    runs = scheduled_runs(refresh_cron())
    worst = max((b - a).total_seconds() / 3600 for a, b in zip(runs, runs[1:]))
    assert METRICS_CACHE_TTL_HOURS >= worst * 1.5, (
        f"TTL {METRICS_CACHE_TTL_HOURS}h gives no slack over a {worst:.0f}h cadence"
    )


def test_the_ttl_still_catches_a_genuinely_dead_pipeline():
    """Headroom must not become 'never notice'."""
    assert METRICS_CACHE_TTL_HOURS <= 48


def test_the_refresh_is_after_the_nse_close_it_reports_on():
    """07:00 IST reports on the previous session, closed at 15:30 IST."""
    minute, hour, *_ = refresh_cron().split()
    ist = (dt.datetime(2026, 1, 1, int(hour), int(minute), tzinfo=dt.timezone.utc)
           + dt.timedelta(hours=5, minutes=30)).time()
    assert dt.time(5, 0) <= ist <= dt.time(9, 0), f"expected an early-morning IST run, got {ist}"


SMOKE = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "production-smoke.yml"


def smoke_crons() -> list[str]:
    return re.findall(r'^\s*-\s*cron:\s*"([^"]+)"', SMOKE.read_text(encoding="utf-8"), re.MULTILINE)


def test_the_watchdog_runs_every_day_the_refresh_does():
    """A monitor that sleeps at weekends is not a monitor.

    The screener was down for hours on a Sunday with nothing reporting it,
    because production-smoke only ran Mon-Fri.
    """
    crons = smoke_crons()
    assert crons, "production-smoke has no schedule"
    for cron in crons:
        dow = cron.split()[4]
        assert dow == "*", f"watchdog cron {cron!r} skips days; the refresh runs daily"


def test_the_watchdog_checks_after_the_refresh_has_had_time_to_finish():
    """It must observe the result of the build, not race it."""
    refresh_hour = int(refresh_cron().split()[1])
    hours = sorted(int(c.split()[1]) for c in smoke_crons())
    after = [h for h in hours if h > refresh_hour]
    assert after, f"no watchdog run after the {refresh_hour:02d}:xx refresh"
    assert min(after) - refresh_hour >= 1, "watchdog would race the refresh"
