from __future__ import annotations

import streamlit as st

from src.data import fetch_ohlcv, load_universe
from src.quant import industry_relative, momentum_acceleration, momentum_score, technical_snapshot

st.set_page_config(page_title="Umiya Screener", page_icon="📊", layout="wide")
st.title("Umiya Screener")
st.caption("Standalone quantitative NSE equity screener")

@st.cache_data(ttl=3600, show_spinner=False)
def load_market_data(symbols: tuple[str, ...]):
    return fetch_ohlcv(symbols, period="2y")

@st.cache_data(ttl=3600, show_spinner=False)
def build_screen():
    universe = load_universe()
    symbols = tuple(universe["Symbol"].tolist())
    data = load_market_data(symbols)
    scores = momentum_score(data["close"])
    latest_score = scores.iloc[-1].rename("Momentum Score")
    tech = technical_snapshot(data["close"], data["high"], data["low"], data["volume"])
    accel = momentum_acceleration(data["close"]).rename("Acceleration")
    rel = industry_relative(latest_score, universe).rename("Industry Relative")
    result = universe.set_index("Symbol").join([latest_score, accel, rel, tech], how="inner")
    result["Rank"] = result["Momentum Score"].rank(ascending=False, method="min")
    return result.reset_index()

with st.spinner("Loading NSE universe and calculating signals…"):
    screen = build_screen()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Stocks", len(screen))
c2.metric("Above 50 EMA", f"{screen['Above EMA 50'].mean() * 100:.1f}%")
c3.metric("Within 20% of 52W High", f"{screen['Within 20% of 52W High'].mean() * 100:.1f}%")
c4.metric("Above 200 EMA", f"{screen['Above EMA 200'].mean() * 100:.1f}%")

st.subheader("Screen")
with st.sidebar:
    st.header("Filters")
    min_rank = st.number_input("Maximum Rank", min_value=1, max_value=max(1, len(screen)), value=min(100, max(1, len(screen))))
    near_high = st.checkbox("Within 20% of 52W High", value=False)
    above_50 = st.checkbox("Above 50 EMA", value=False)
    above_200 = st.checkbox("Above 200 EMA", value=False)
    industry = st.multiselect("Industry", sorted(screen["Industry"].dropna().unique()))

filtered = screen[screen["Rank"] <= min_rank].copy()
if near_high:
    filtered = filtered[filtered["Within 20% of 52W High"]]
if above_50:
    filtered = filtered[filtered["Above EMA 50"]]
if above_200:
    filtered = filtered[filtered["Above EMA 200"]]
if industry:
    filtered = filtered[filtered["Industry"].isin(industry)]

cols = ["Rank", "Symbol", "Company Name", "Industry", "CMP", "Momentum Score", "Industry Relative", "Acceleration", "3M Return", "6M Return", "12M Return", "% From 52W High", "Above EMA 50", "Above EMA 100", "Above EMA 200", "ATR %", "Persistence 6M %", "Volume Ratio"]
cols = [c for c in cols if c in filtered.columns]
st.dataframe(filtered.sort_values("Rank")[cols], use_container_width=True, hide_index=True)

st.download_button("Download CSV", filtered[cols].to_csv(index=False).encode("utf-8"), "umiya_screener.csv", "text/csv")
