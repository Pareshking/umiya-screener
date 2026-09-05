"""Third-party fundamentals, delivery data and NSE sector classification.

WHERE THIS DATA COMES FROM
--------------------------
The upstream is `jadeja-rajdeep/nse-momentum-screener`, a public GitHub repo
that publishes a static site. Its `m.json` is a **PHPMyAdmin export of a
private MySQL database** (`marketwatcher_nse_v4`, table `m`) committed once a
day. That is worth being precise about, because it has consequences:

* The pipeline that produces the data is NOT in that repo. It is a published
  output, not a source, so we cannot reproduce it, audit it, or fix it. If it
  stops updating we cannot tell from the outside whether the numbers are still
  current -- only that the file's own `Date` column has stopped moving.
* It carries no licence file, so no usage rights are granted by default.
* It is one person's repository. It can be made private or deleted without
  notice.

Field naming strongly implies the underlying origins: the four-level
`Macro Economic Sector / Sector / Industry / Basic Industry` hierarchy and ISIN
are NSE's own classification; `No of trades`, `Net Turnover`, `Delivery Volume`
and `Delivery %` match NSE's bhavcopy and security-wise delivery files; the
shareholding split matches NSE's shareholding pattern. The valuation and
earnings fields (PE, ROE, EPS/sales growth, book value, yield) come from some
fundamentals provider that the repo does not identify.

CONSEQUENCES FOR THIS MODULE
----------------------------
Because the source can vanish, every failure here is explicit. This module
never invents a value and never silently returns empty: it returns a status
alongside the data, and callers surface "fundamentals unavailable" with the
reason attached rather than rendering blanks that look like real absences.

Prices are deliberately NOT taken from here. The canonical Adjusted Close and
Volume pipeline stays the single source of truth for anything the ranking
depends on; mixing two price vendors would make the engine unauditable. Only
fields we cannot compute ourselves are consumed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any

import numpy as np
import pandas as pd

SOURCE_REPO = "jadeja-rajdeep/nse-momentum-screener"
SOURCE_URL = f"https://raw.githubusercontent.com/{SOURCE_REPO}/main/m.json"
SOURCE_DATABASE = "marketwatcher_nse_v4"

# How stale the upstream's own Date column may be before we stop trusting it.
# The repo updates on trading days; a week's silence means it has stopped.
MAX_SOURCE_AGE_DAYS = 7

REQUEST_TIMEOUT = 120

# Only fields we cannot derive from the canonical price dataset. Anything the
# engine already computes stays with the engine.
NUMERIC_FIELDS: dict[str, str] = {
    "Market Cap": "Market Cap",
    "PE": "PE",
    "ROE": "ROE",
    "Debt": "Debt",
    "Book Val": "Book Value",
    "Yield": "Dividend Yield",
    "Prom Hold %": "Promoter Holding %",
    "Public Hold %": "Public Holding %",
    "Delivery %": "Delivery %",
    "Delivery Volume": "Delivery Volume",
    "EPS Latest Qtr %": "EPS Growth Qtr %",
    "Sales Latest Qtr %": "Sales Growth Qtr %",
    "EPS Avg 3 Qtr %": "EPS Growth 3Q Avg %",
    "Sales Avg 3 Qtr %": "Sales Growth 3Q Avg %",
}

TEXT_FIELDS: dict[str, str] = {
    "Macro Economic Sector": "Macro Sector",
    "Sector": "NSE Sector",
    "Basic Industry": "Basic Industry",
    "ISIN": "ISIN",
}

COLUMNS: tuple[str, ...] = tuple(NUMERIC_FIELDS.values()) + tuple(TEXT_FIELDS.values())


class FundamentalsUnavailable(RuntimeError):
    """The upstream could not be read, parsed, or trusted."""


@dataclass(frozen=True)
class FundamentalsResult:
    """Fundamentals plus an explicit statement of whether they are usable."""

    available: bool
    frame: pd.DataFrame = field(default_factory=pd.DataFrame)
    source_date: date | None = None
    reason: str | None = None
    rows: int = 0

    def as_metadata(self) -> dict[str, Any]:
        """The status block the API hands to the UI."""
        return {
            "available": self.available,
            "source_repo": SOURCE_REPO,
            "source_database": SOURCE_DATABASE,
            "source_date": self.source_date.isoformat() if self.source_date else None,
            "rows": self.rows,
            "reason": self.reason,
            "fields": list(COLUMNS) if self.available else [],
            "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        }


def _to_number(value: Any) -> float:
    """Parse an upstream string to a float, or NaN.

    Every value in the dump is a string, including the numbers, and blanks are
    the empty string rather than null.
    """
    if value is None:
        return np.nan
    text = str(value).strip().replace(",", "")
    if not text or text.lower() in {"na", "n/a", "-", "null", "none"}:
        return np.nan
    try:
        return float(text)
    except ValueError:
        return np.nan


def parse_dump(payload: Any) -> tuple[pd.DataFrame, date | None]:
    """Turn the PHPMyAdmin export into a Symbol-indexed frame.

    The export is a list of blocks: a header, a database name, then one table
    block whose `data` holds the rows. Anything else is a shape we do not
    recognise and is rejected rather than guessed at.
    """
    if not isinstance(payload, list):
        raise FundamentalsUnavailable("upstream payload is not a PHPMyAdmin export list")

    table = next(
        (b for b in payload if isinstance(b, dict) and b.get("type") == "table" and isinstance(b.get("data"), list)),
        None,
    )
    if table is None:
        raise FundamentalsUnavailable("upstream payload contains no table block")

    rows = table["data"]
    if not rows:
        raise FundamentalsUnavailable("upstream table block is empty")

    frame = pd.DataFrame(rows)
    if "Code" not in frame.columns:
        raise FundamentalsUnavailable("upstream rows have no 'Code' column to key on")

    out = pd.DataFrame(index=pd.Index(frame["Code"].astype(str).str.strip().str.upper(), name="Symbol"))
    for source, target in NUMERIC_FIELDS.items():
        out[target] = frame[source].map(_to_number).to_numpy() if source in frame.columns else np.nan
    for source, target in TEXT_FIELDS.items():
        if source in frame.columns:
            cleaned = frame[source].astype(str).str.strip().replace({"": None, "nan": None})
            out[target] = cleaned.to_numpy()
        else:
            out[target] = None

    # A duplicate listing would silently pick a winner in the join, so collapse
    # deliberately: keep the first occurrence and say nothing was invented.
    out = out[~out.index.duplicated(keep="first")]

    source_date = None
    if "Date" in frame.columns:
        parsed = pd.to_datetime(frame["Date"], errors="coerce").dropna()
        if not parsed.empty:
            source_date = parsed.max().date()

    return out, source_date


def _fetch_payload(url: str, timeout: int) -> Any:
    import requests

    response = requests.get(url, timeout=timeout, headers={"Accept": "application/json"})
    response.raise_for_status()
    return response.json()


def fetch_fundamentals(
    url: str = SOURCE_URL,
    *,
    timeout: int = REQUEST_TIMEOUT,
    max_age_days: int = MAX_SOURCE_AGE_DAYS,
    today: date | None = None,
) -> FundamentalsResult:
    """Fetch and validate the upstream, reporting *why* if it cannot be used.

    Never raises. A missing, private, malformed or stale upstream comes back as
    ``available=False`` with a reason, so the caller can publish the dataset
    without fundamentals and the UI can say so out loud.
    """
    try:
        payload = _fetch_payload(url, timeout)
    except Exception as exc:  # noqa: BLE001 - every failure mode is reported, not raised
        return FundamentalsResult(
            available=False,
            reason=f"could not fetch {url}: {type(exc).__name__}: {exc}",
        )

    try:
        frame, source_date = parse_dump(payload)
    except FundamentalsUnavailable as exc:
        return FundamentalsResult(available=False, reason=str(exc))
    except Exception as exc:  # noqa: BLE001
        return FundamentalsResult(available=False, reason=f"could not parse upstream: {type(exc).__name__}: {exc}")

    if source_date is None:
        return FundamentalsResult(
            available=False, reason="upstream carries no usable Date column, so its freshness cannot be checked",
            rows=int(len(frame)),
        )

    age = ((today or datetime.now(timezone.utc).date()) - source_date).days
    if age > max_age_days:
        return FundamentalsResult(
            available=False,
            source_date=source_date,
            rows=int(len(frame)),
            reason=(
                f"upstream has not updated for {age} days (last {source_date.isoformat()}); "
                f"limit is {max_age_days}. Treating it as abandoned rather than current."
            ),
        )

    return FundamentalsResult(available=True, frame=frame, source_date=source_date, rows=int(len(frame)))


def attach(frame: pd.DataFrame, result: FundamentalsResult) -> pd.DataFrame:
    """Left-join fundamentals onto a Symbol-indexed metric frame.

    When unavailable, the columns are still created and left entirely empty.
    A column that exists and is blank is a fact the UI can report; a column
    that is missing entirely would make every consumer branch on its absence.
    """
    out = frame.copy()
    if not result.available or result.frame.empty:
        for column in COLUMNS:
            out[column] = np.nan if column in NUMERIC_FIELDS.values() else None
        return out
    return out.join(result.frame.reindex(columns=list(COLUMNS)), how="left")
