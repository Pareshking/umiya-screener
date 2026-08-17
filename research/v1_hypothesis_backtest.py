from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data_cache" / "price_history"
WINDOWS = (21, 63, 126, 189, 252)
WEIGHT_SCHEMES = {
    "current_10_30_30_20_10": np.array((0.10, 0.30, 0.30, 0.20, 0.10)),
    "equal_20_each": np.repeat(0.20, 5),
    "intermediate_heavy": np.array((0.05, 0.20, 0.40, 0.25, 0.10)),
}
REBALANCE_STEP = 21
HOLDING = 21
MIN_HISTORY = 252


def load_prices() -> pd.DataFrame:
    latest = json.loads((DATA_ROOT / "LATEST.json").read_text())["dataset"]
    return pd.read_parquet(DATA_ROOT / latest / "adj_close.parquet").sort_index()


def zscore(s: pd.Series) -> pd.Series:
    valid = s.dropna()
    if len(valid) < 3 or valid.std(ddof=1) == 0:
        return pd.Series(np.nan, index=s.index)
    return (s - valid.mean()) / valid.std(ddof=1)


def fip_quality(logret: pd.DataFrame, window: int) -> pd.Series:
    r = logret.tail(window)
    pos = r.gt(0).sum()
    neg = r.lt(0).sum()
    total = pos + neg
    pret = r.sum()
    # Da, Gurun & Warachka information-discreteness proxy:
    # ID = sign(PRET) * (%negative - %positive). Lower ID is more continuous.
    id_score = np.sign(pret) * ((neg / total.replace(0, np.nan)) - (pos / total.replace(0, np.nan)))
    return -id_score


def components(prices: pd.DataFrame, asof: int, window: int) -> dict[str, pd.Series]:
    p = prices.iloc[: asof + 1]
    if len(p) <= window:
        return {k: pd.Series(np.nan, index=prices.columns) for k in ("simple", "log", "ram_simple", "ram_log", "sharpe", "r2", "fip")}
    end = p.iloc[-1]
    start = p.iloc[-window - 1]
    simple = end / start - 1.0
    log = np.log(end / start)
    lr = np.log(p / p.shift(1).replace(0, np.nan))
    recent = lr.tail(window)
    sd = recent.std(ddof=1)
    ram_simple = simple / (sd * np.sqrt(window))
    ram_log = log / (sd * np.sqrt(window))
    sharpe = (recent.mean() / sd) * np.sqrt(252.0)
    t = np.arange(window, dtype=float)
    tc = t - t.mean()
    y = np.log(p.tail(window))
    r2 = y.apply(lambda s: (np.corrcoef(tc, s)[0, 1] ** 2) if s.notna().all() and s.std(ddof=1) > 0 else np.nan)
    fip = fip_quality(lr, window)
    return {"simple": simple, "log": log, "ram_simple": ram_simple, "ram_log": ram_log, "sharpe": sharpe, "r2": r2, "fip": fip}


def score_at(prices: pd.DataFrame, asof: int, model: str, weights: np.ndarray) -> pd.Series:
    parts = {w: components(prices, asof, w) for w in WINDOWS}
    out = pd.Series(0.0, index=prices.columns)
    avail = pd.Series(0.0, index=prices.columns)
    if model == "12m_minus_1m":
        raw = parts[252]["simple"] - parts[21]["simple"]
        return zscore(raw)
    for i, w in enumerate(WINDOWS):
        c = parts[w]
        if model == "raw_simple": raw = c["simple"]
        elif model == "raw_log": raw = c["log"]
        elif model == "ram_simple": raw = c["ram_simple"]
        elif model in ("ram_log", "ram_log_weight_test"): raw = c["ram_log"]
        elif model == "sharpe": raw = c["sharpe"]
        elif model == "ram_r2": raw = c["ram_log"] * c["r2"]
        elif model == "ram_fip": raw = c["ram_log"] * c["fip"]
        else: raise ValueError(model)
        z = zscore(raw)
        out = out.add(z.fillna(0) * weights[i], fill_value=0)
        avail = avail.add(z.notna().astype(float) * weights[i], fill_value=0)
    return out.div(avail.replace(0, np.nan))


def forward_returns(prices: pd.DataFrame, asof: int, horizon: int) -> pd.Series:
    if asof + horizon >= len(prices):
        return pd.Series(np.nan, index=prices.columns)
    return prices.iloc[asof + horizon] / prices.iloc[asof] - 1.0


def stats(series: pd.Series) -> dict:
    r = series.dropna()
    if r.empty:
        return {}
    wealth = (1 + r).cumprod()
    years = len(r) / 252.0
    cagr = wealth.iloc[-1] ** (1 / years) - 1 if years > 0 else np.nan
    vol = r.std(ddof=1) * np.sqrt(252)
    sharpe = r.mean() / r.std(ddof=1) * np.sqrt(252) if r.std(ddof=1) else np.nan
    downside = r[r < 0].std(ddof=1)
    sortino = r.mean() / downside * np.sqrt(252) if pd.notna(downside) and downside else np.nan
    dd = wealth / wealth.cummax() - 1
    return {"CAGR": cagr, "Volatility": vol, "Sharpe": sharpe, "Sortino": sortino, "MaxDrawdown": dd.min(), "Observations": len(r)}


def main() -> None:
    prices = load_prices()
    prices = prices.loc[:, prices.notna().sum() >= MIN_HISTORY]
    dates = range(MIN_HISTORY, len(prices) - HOLDING - 1, REBALANCE_STEP)
    base_models = ["raw_simple", "raw_log", "ram_simple", "ram_log", "sharpe", "ram_r2", "ram_fip", "12m_minus_1m"]
    rows: list[dict] = []
    portfolio: dict[str, list[float]] = {}

    for weight_name, weights in WEIGHT_SCHEMES.items():
        models = base_models if weight_name == "current_10_30_30_20_10" else ["ram_log"]
        for model in models:
            key = model if weight_name == "current_10_30_30_20_10" else f"ram_log__{weight_name}"
            portfolio[key] = []
            for asof in dates:
                score = score_at(prices, asof, model, weights)
                fwd21 = forward_returns(prices, asof, 21)
                valid = score.notna() & fwd21.notna()
                if valid.sum() < 50:
                    continue
                ic = score[valid].corr(fwd21[valid], method="pearson")
                rank_ic = score[valid].corr(fwd21[valid], method="spearman")
                n = max(1, int(valid.sum() * 0.10))
                ranked = score[valid].sort_values(ascending=False)
                top = ranked.index[:n]
                bottom = ranked.index[-n:]
                top_ret = fwd21[top].mean()
                bottom_ret = fwd21[bottom].mean()
                rows.append({"date": prices.index[asof], "model": key, "weight_scheme": weight_name, "IC": ic, "RankIC": rank_ic, "TopDecile": top_ret, "BottomDecile": bottom_ret, "TopMinusBottom": top_ret - bottom_ret})
                portfolio[key].append(top_ret)

    detail = pd.DataFrame(rows)
    summary = []
    for model, pvals in portfolio.items():
        d = detail[detail.model == model]
        s = stats(pd.Series(pvals))
        summary.append({"Model": model, "MeanIC": d.IC.mean(), "MeanRankIC": d.RankIC.mean(), "PositiveRankICPct": (d.RankIC > 0).mean(), "MeanTopDecile": d.TopDecile.mean(), "MeanTopMinusBottom": d.TopMinusBottom.mean(), **s})
    out = pd.DataFrame(summary).sort_values("MeanRankIC", ascending=False)
    outdir = ROOT / "research" / "outputs"
    outdir.mkdir(parents=True, exist_ok=True)
    detail.to_csv(outdir / "v1_hypothesis_detail.csv", index=False)
    out.to_csv(outdir / "v1_hypothesis_summary.csv", index=False)
    print(out.to_string(index=False))
    print("\nFORWARD HORIZONS: the primary ranking test uses a 21-trading-day forward return; the detail file preserves each rebalance observation.")
    print("DATA NOTE: current NIFTY-750 membership is used for the entire history, so survivorship bias remains. This is research evidence, not production validation.")


if __name__ == "__main__":
    main()
