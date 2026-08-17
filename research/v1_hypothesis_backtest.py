from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data_cache" / "price_history"
WINDOWS = (21, 63, 126, 189, 252)
WEIGHTS = np.array((0.10, 0.30, 0.30, 0.20, 0.10), dtype=float)
REBALANCE_STEP = 21
HOLDING = 21
MIN_HISTORY = 252


def load_prices() -> pd.DataFrame:
    latest = json.loads((DATA_ROOT / "LATEST.json").read_text())['dataset']
    return pd.read_parquet(DATA_ROOT / latest / "adj_close.parquet").sort_index()


def zscore(s: pd.Series) -> pd.Series:
    valid = s.dropna()
    if len(valid) < 3 or valid.std(ddof=1) == 0:
        return pd.Series(np.nan, index=s.index)
    return (s - valid.mean()) / valid.std(ddof=1)


def fip_quality(logret: pd.DataFrame, window: int, asof: int) -> pd.Series:
    r = logret.iloc[asof - window + 1:asof + 1]
    pos = r.gt(0).sum()
    neg = r.lt(0).sum()
    total = pos + neg
    # Da, Gurun & Warachka information-discreteness proxy:
    # ID = sign(PRET) * (%negative - %positive).
    pret = r.sum()
    id_score = np.sign(pret) * ((neg / total.replace(0, np.nan)) - (pos / total.replace(0, np.nan)))
    return -id_score  # higher = more continuous / stronger FIP quality


def components(prices: pd.DataFrame, asof: int, window: int):
    p = prices.iloc[:asof + 1]
    if len(p) <= window:
        return {k: pd.Series(np.nan, index=prices.columns) for k in ('simple','log','ram_simple','ram_log','sharpe','r2','fip')}
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
    y = np.log(p.tail(window))
    tc = t - t.mean()
    r2 = y.apply(lambda s: (np.corrcoef(tc, s)[0,1] ** 2) if s.notna().all() and s.std(ddof=1) > 0 else np.nan)
    fip = fip_quality(lr, window, asof)
    return dict(simple=simple, log=log, ram_simple=ram_simple, ram_log=ram_log, sharpe=sharpe, r2=r2, fip=fip)


def score_at(prices: pd.DataFrame, asof: int, model: str) -> pd.Series:
    parts = {w: components(prices, asof, w) for w in WINDOWS}
    out = pd.Series(0.0, index=prices.columns)
    avail = pd.Series(0.0, index=prices.columns)
    for i, w in enumerate(WINDOWS):
        c = parts[w]
        if model == 'raw_simple': raw = c['simple']
        elif model == 'raw_log': raw = c['log']
        elif model == 'ram_simple': raw = c['ram_simple']
        elif model == 'ram_log': raw = c['ram_log']
        elif model == 'sharpe': raw = c['sharpe']
        elif model == 'ram_r2': raw = c['ram_log'] * c['r2']
        elif model == 'ram_fip': raw = c['ram_log'] * c['fip']
        elif model == 'ram_only_r2': raw = c['ram_log']
        else: raise ValueError(model)
        z = zscore(raw)
        out = out.add(z.fillna(0) * WEIGHTS[i], fill_value=0)
        avail = avail.add(z.notna().astype(float) * WEIGHTS[i], fill_value=0)
    return out.div(avail.replace(0, np.nan))


def forward_returns(prices: pd.DataFrame, asof: int, horizon: int) -> pd.Series:
    if asof + horizon >= len(prices):
        return pd.Series(np.nan, index=prices.columns)
    p0 = prices.iloc[asof]
    p1 = prices.iloc[asof + horizon]
    return p1 / p0 - 1.0


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
    return {'CAGR': cagr, 'Volatility': vol, 'Sharpe': sharpe, 'Sortino': sortino, 'MaxDrawdown': dd.min(), 'Observations': len(r)}


def main():
    prices = load_prices()
    prices = prices.loc[:, prices.notna().sum() >= MIN_HISTORY]
    # Use current NIFTY-750 constituents consistently across all historical dates.
    dates = range(MIN_HISTORY, len(prices) - HOLDING - 1, REBALANCE_STEP)
    models = ['raw_simple','raw_log','ram_simple','ram_log','sharpe','ram_r2','ram_fip']
    rows = []
    portfolio = {m: [] for m in models}
    ic_rows = []
    for asof in dates:
        for model in models:
            score = score_at(prices, asof, model)
            fwd21 = forward_returns(prices, asof, 21)
            valid = score.notna() & fwd21.notna()
            if valid.sum() < 50:
                continue
            rank_ic = score[valid].corr(fwd21[valid], method='spearman')
            ic = score[valid].corr(fwd21[valid], method='pearson')
            n = max(1, int(valid.sum() * 0.10))
            ranked = score[valid].sort_values(ascending=False)
            top = ranked.index[:n]
            bottom = ranked.index[-n:]
            top_ret = fwd21[top].mean()
            bottom_ret = fwd21[bottom].mean()
            rows.append({'date': prices.index[asof], 'model': model, 'IC': ic, 'RankIC': rank_ic, 'TopDecile': top_ret, 'BottomDecile': bottom_ret, 'TopMinusBottom': top_ret-bottom_ret})
            portfolio[model].append(top_ret)
            ic_rows.append((model, ic, rank_ic))

    detail = pd.DataFrame(rows)
    summary = []
    for model in models:
        d = detail[detail.model == model]
        p = pd.Series(portfolio[model])
        s = stats(p)
        summary.append({'Model': model, 'MeanIC': d.IC.mean(), 'MeanRankIC': d.RankIC.mean(), 'PositiveRankICPct': (d.RankIC > 0).mean(), 'MeanTopDecile': d.TopDecile.mean(), 'MeanTopMinusBottom': d.TopMinusBottom.mean(), **s})
    out = pd.DataFrame(summary).sort_values('MeanRankIC', ascending=False)
    outdir = ROOT / 'research' / 'outputs'
    outdir.mkdir(parents=True, exist_ok=True)
    detail.to_csv(outdir / 'v1_hypothesis_detail.csv', index=False)
    out.to_csv(outdir / 'v1_hypothesis_summary.csv', index=False)
    print(out.to_string(index=False))
    print('\nDATA NOTES: current NIFTY-750 membership is used for the entire history (survivorship bias); results are research evidence, not production validation.')


if __name__ == '__main__':
    main()
