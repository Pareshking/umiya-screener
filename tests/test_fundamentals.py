"""The upstream is one person's repo with no licence and no pipeline in it.

It can go private or stop updating without notice, so every test here is about
failing *visibly* rather than degrading into blanks that look like real absences.
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

from src import fundamentals as fx


def dump(rows, table_date="2026-09-04"):
    for r in rows:
        r.setdefault("Date", table_date)
    return [
        {"type": "header", "version": "5.2.2", "comment": "Export to JSON plugin for PHPMyAdmin"},
        {"type": "database", "name": fx.SOURCE_DATABASE},
        {"type": "table", "name": "m", "database": fx.SOURCE_DATABASE, "data": rows},
    ]


def row(code="TCS", **over):
    base = {
        "Code": code, "Name": f"{code} Ltd", "ISIN": "INE467B01029",
        "Macro Economic Sector": "Information Technology", "Sector": "Information Technology",
        "Basic Industry": "Computers - Software", "Market Cap": "12400000000000",
        "PE": "28.4", "ROE": "51.2", "Debt": "0", "Book Val": "6.98", "Yield": "1.8",
        "Prom Hold %": "71.77", "Public Hold %": "28.23", "Delivery %": "62.5",
        "Delivery Volume": "1200000", "EPS Latest Qtr %": "7", "Sales Latest Qtr %": "5",
        "EPS Avg 3 Qtr %": "6.5", "Sales Avg 3 Qtr %": "4.2",
    }
    base.update(over)
    return base


def test_parses_the_phpmyadmin_export_shape():
    frame, source_date = fx.parse_dump(dump([row()]))
    assert source_date == date(2026, 9, 4)
    assert frame.index.name == "Symbol"
    assert frame.loc["TCS", "Market Cap"] == 12400000000000.0
    assert frame.loc["TCS", "Promoter Holding %"] == 71.77
    assert frame.loc["TCS", "NSE Sector"] == "Information Technology"


def test_every_upstream_value_is_a_string_and_blanks_are_not_zero():
    """The dump stores numbers as strings and gaps as "", not null.

    Coercing a blank to 0.0 would put a PE of zero on the screen, which reads
    as a real and extremely cheap valuation.
    """
    frame, _ = fx.parse_dump(dump([row("AAA", **{
        "Delivery %": "", "Prom Hold %": "n/a", "Public Hold %": "-",
        "Market Cap": "1,234,500",
    })]))
    assert pd.isna(frame.loc["AAA", "Delivery %"])
    assert pd.isna(frame.loc["AAA", "Promoter Holding %"])
    assert pd.isna(frame.loc["AAA", "Public Holding %"])
    assert frame.loc["AAA", "Market Cap"] == 1234500.0


def test_a_missing_upstream_reports_why_and_does_not_raise(monkeypatch):
    monkeypatch.setattr(fx, "_fetch_payload", lambda *a, **k: (_ for _ in ()).throw(OSError("404 Not Found")))
    result = fx.fetch_fundamentals()
    assert result.available is False
    assert "404" in result.reason
    assert result.as_metadata()["available"] is False
    assert result.as_metadata()["source_repo"] == fx.SOURCE_REPO


def test_a_repo_gone_private_is_reported_as_unavailable(monkeypatch):
    monkeypatch.setattr(fx, "_fetch_payload", lambda *a, **k: (_ for _ in ()).throw(PermissionError("403")))
    result = fx.fetch_fundamentals()
    assert result.available is False
    assert "403" in result.reason


def test_an_unrecognised_payload_shape_is_rejected_rather_than_guessed(monkeypatch):
    monkeypatch.setattr(fx, "_fetch_payload", lambda *a, **k: {"unexpected": "shape"})
    assert fx.fetch_fundamentals().available is False
    monkeypatch.setattr(fx, "_fetch_payload", lambda *a, **k: [{"type": "header"}])
    assert "no table block" in fx.fetch_fundamentals().reason


def test_a_stale_upstream_is_treated_as_abandoned_not_current(monkeypatch):
    """A repo that stopped updating still serves a 200 with old numbers.

    Silently ranking on month-old fundamentals is worse than showing nothing,
    because nothing about the response says the data stopped moving.
    """
    monkeypatch.setattr(fx, "_fetch_payload", lambda *a, **k: dump([row()], table_date="2026-08-01"))
    result = fx.fetch_fundamentals(today=date(2026, 9, 5))
    assert result.available is False
    assert "has not updated" in result.reason
    assert result.source_date == date(2026, 8, 1)


def test_a_fresh_upstream_is_accepted(monkeypatch):
    monkeypatch.setattr(fx, "_fetch_payload", lambda *a, **k: dump([row()], table_date="2026-09-04"))
    result = fx.fetch_fundamentals(today=date(2026, 9, 5))
    assert result.available is True
    assert result.rows == 1


def test_duplicate_listings_do_not_multiply_rows_in_the_join():
    frame, _ = fx.parse_dump(dump([row("DUP", **{"Delivery %": "10"}),
                                   row("DUP", **{"Delivery %": "99"})]))
    assert len(frame) == 1
    assert frame.loc["DUP", "Delivery %"] == 10.0


def test_attach_creates_empty_columns_when_unavailable():
    """The columns must exist even when the source is gone.

    A column that is present and blank is a fact the interface can report. A
    column that vanishes makes every consumer branch on its absence instead.
    """
    metrics = pd.DataFrame({"Momentum Score": [1.0]}, index=pd.Index(["TCS"], name="Symbol"))
    out = fx.attach(metrics, fx.FundamentalsResult(available=False, reason="gone"))
    for column in fx.COLUMNS:
        assert column in out.columns
    assert out["Market Cap"].isna().all()
    assert len(out) == 1


def test_attach_joins_without_dropping_or_duplicating_stocks():
    metrics = pd.DataFrame({"Momentum Score": [1.0, 2.0]}, index=pd.Index(["TCS", "NOTINSOURCE"], name="Symbol"))
    result = fx.fetch_fundamentals.__wrapped__ if hasattr(fx.fetch_fundamentals, "__wrapped__") else None
    frame, _ = fx.parse_dump(dump([row("TCS")]))
    out = fx.attach(metrics, fx.FundamentalsResult(available=True, frame=frame, source_date=date(2026, 9, 4), rows=1))
    assert list(out.index) == ["TCS", "NOTINSOURCE"]
    assert out.loc["TCS", "Delivery %"] == 62.5
    assert pd.isna(out.loc["NOTINSOURCE", "Delivery %"])


def test_prices_are_never_taken_from_the_third_party_source():
    """The ranking must stay auditable against one price vendor.

    Adjusted Close and Volume drive every score; sourcing them from a second,
    unreproducible vendor would make the engine impossible to audit.
    """
    forbidden = {"Open", "High", "Low", "Close", "Previouse Close", "Volume", "Adj Close"}
    assert forbidden.isdisjoint(fx.COLUMNS)
    assert forbidden.isdisjoint(fx.NUMERIC_FIELDS)


def test_book_val_is_a_ratio_and_is_suppressed_for_being_stale():
    """"Book Val" is a price-to-book RATIO, not a per-share value.

    Established from the values: it tracks Screener.in's P/B across peers
    (SHYAMMETL 2.48 vs 2.58, USHAMART 4.58 vs 4.75). But it is computed against
    a stale price, so it is not served -- see UNRELIABLE_FIELDS.
    """
    assert "Book Val" in fx.UNRELIABLE_FIELDS
    assert "Book Val" not in fx.NUMERIC_FIELDS
    assert "Price to Book" not in fx.COLUMNS


def test_stale_price_derived_ratios_are_not_consumed():
    """P/E, P/B and yield are computed against a stale price upstream.

    Verified against Screener.in for WELCORP on 2026-09-04 (close Rs 2,590.60):
    a single factor of 1.623 carries the upstream's P/E 18.23 to 29.59, its
    price-to-book 4.60 to 7.47, and — dividing, because price is in the
    denominator — its yield 0.31 to 0.19. One stale price explains all three.

    The error scales with how far a stock has run, so it is worst on exactly
    the names a momentum screener ranks highest. Serving those numbers is worse
    than serving nothing, so they are not consumed.
    """
    for field in ["PE", "Book Val", "Yield", "ROE", "Debt",
                  "EPS Latest Qtr %", "Sales Latest Qtr %"]:
        assert field in fx.UNRELIABLE_FIELDS, f"{field} must stay suppressed"
        assert field not in fx.NUMERIC_FIELDS, f"{field} must not be consumed"
        assert fx.UNRELIABLE_FIELDS[field], f"{field} must carry a stated reason"

    for gone in ["PE", "ROE", "Price to Book", "Dividend Yield", "Debt",
                 "EPS Growth Qtr %", "Sales Growth Qtr %"]:
        assert gone not in fx.COLUMNS


def test_the_fields_that_reconciled_are_still_served():
    """Market cap and shareholding matched Screener.in exactly; keep them."""
    for kept in ["Market Cap", "Promoter Holding %", "Public Holding %",
                 "Delivery %", "NSE Sector", "ISIN"]:
        assert kept in fx.COLUMNS


def test_a_suppressed_field_never_reaches_the_frame():
    frame, _ = fx.parse_dump(dump([row("WELCORP", PE="18.23", ROE="17.6",
                                       **{"Book Val": "4.6", "Yield": "0.31"})]))
    for gone in ["PE", "ROE", "Price to Book", "Dividend Yield"]:
        assert gone not in frame.columns
    assert frame.loc["WELCORP", "Market Cap"] > 0
