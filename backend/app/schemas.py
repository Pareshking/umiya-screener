from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field


class Filter(BaseModel):
    field: str
    operator: Literal[">", ">=", "<", "<=", "=", "in"]
    value: float | str | list[str]


class SortSpec(BaseModel):
    field: str = "Rank"
    direction: Literal["asc", "desc"] = "asc"


class ScreenerQuery(BaseModel):
    filters: list[Filter] = Field(default_factory=list)
    sort: SortSpec = Field(default_factory=SortSpec)
    search: str | None = Field(default=None, max_length=80)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=200)


class ScreenerRow(BaseModel):
    rank: int
    symbol: str
    company_name: str
    industry: str
    score: float | None = None
    cmp: float | None = None
    roc_3m: float | None = None
    roc_6m: float | None = None
    roc_12m: float | None = None
    sharpe_3m: float | None = None
    sharpe_6m: float | None = None
    r2_1y: float | None = None
    from_high: float | None = None
    ema50_dist: float | None = None
    ema200_dist: float | None = None
    volume_ratio: float | None = None
    market_cap_cr: float | None = None
    acceleration: float | None = None


class ScreenerResponse(BaseModel):
    total: int
    page: int
    page_size: int
    pages: int
    rows: list[dict]
    available_filters: list[str]
    built_at: str | None = None
