"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ChartRange } from "../../../components/chart-range";

type Row = Record<string, string | number | null>;
type ChartPoint = { date: string; adj_close: number; volume: number | null };
const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function fmt(v: Row[keyof Row]) { return v == null ? "—" : typeof v === "number" ? v.toLocaleString("en-IN", { maximumFractionDigits: 2 }) : String(v); }
function pct(v: Row[keyof Row]) { return v == null ? "—" : `${Number(v) > 0 ? "+" : ""}${Number(v).toFixed(2)}%`; }

export default function StockPage() {
  const params = useParams<{symbol:string}>();
  const router = useRouter();
  const symbol = String(params.symbol || "").toUpperCase();
  const [stock,setStock] = useState<Row | null>(null);
  const [chart,setChart] = useState<ChartPoint[]>([]);
  const [days,setDays] = useState(252);
  const [error,setError] = useState("");

  useEffect(() => {
    if (!symbol) return;
    fetch(`${API}/api/v1/stocks/${encodeURIComponent(symbol)}`, {cache:"no-store"}).then(async r => { if (!r.ok) throw new Error((await r.json().catch(()=>({}))).detail || "Stock unavailable"); return r.json(); }).then(setStock).catch(e => setError(e instanceof Error ? e.message : "Unable to load stock."));
  }, [symbol]);

  useEffect(() => {
    if (!symbol) return;
    fetch(`${API}/api/v1/stocks/${encodeURIComponent(symbol)}/chart?days=${days}`, {cache:"no-store"}).then(async r => { if (!r.ok) throw new Error((await r.json().catch(()=>({}))).detail || "Chart unavailable"); return r.json(); }).then(c => setChart(c.rows || [])).catch(e => setError(e instanceof Error ? e.message : "Unable to load chart."));
  }, [symbol, days]);

  const values = useMemo(() => chart.map(p=>p.adj_close), [chart]);
  const min = Math.min(...values), max = Math.max(...values);
  const path = values.length > 1 ? values.map((v,i) => `${(i/(values.length-1))*100},${100-((v-min)/(max-min || 1))*92-4}`).join(" ") : "";

  if (error && !stock) return <main className="detailpage"><button className="back" onClick={()=>router.push("/")}>← Screener</button><div className="detailerror"><b>{error}</b><span>Return to the screener and try another symbol.</span></div></main>;
  if (!stock) return <main className="detailpage"><button className="back" onClick={()=>router.push("/")}>← Screener</button><div className="detailloading">Loading {symbol}…</div></main>;

  return <main className="detailpage">
    <button className="back" onClick={()=>router.push("/")}>← Screener</button>
    <header className="detailheader"><div><div className="eyebrow">NSE 750 · {stock.Industry}</div><h1>{symbol}</h1><p>{stock["Company Name"]} · {stock.Index}</p></div><div className="detailrank"><small>MOMENTUM RANK</small><b>#{fmt(stock.Rank)}</b><span>{fmt(stock["Momentum Score"])}</span></div></header>
    <section className="detailgrid">
      <div className="detailcard chartcard"><div className="cardtitle"><div><b>Adjusted Close</b><span>{days===63?"3M":days===126?"6M":"1Y"} · As of {stock["Market As Of"] || "—"}</span></div><ChartRange value={days} onChange={setDays}/></div>{path ? <div className="chart"><svg viewBox="0 0 100 100" preserveAspectRatio="none"><polyline points={path} fill="none" stroke="currentColor" strokeWidth="1.2" vectorEffect="non-scaling-stroke" /></svg></div> : <div className="chartempty">No chart data</div>}<div className="chartlabels"><span>{chart[0]?.date?.slice(0,10) || "—"}</span><span>{chart.at(-1)?.date?.slice(0,10) || "—"}</span></div></div>
      <div className="detailcard"><div className="cardtitle"><b>Momentum & Trend</b><span>Quantitative snapshot</span></div><div className="statgrid"><Stat label="Momentum Score" value={fmt(stock["Momentum Score"])} /><Stat label="1M Return" value={pct(stock["1M Return"])} /><Stat label="3M Return" value={pct(stock["3M Return"])} /><Stat label="6M Return" value={pct(stock["6M Return"])} /><Stat label="9M Return" value={pct(stock["9M Return"])} /><Stat label="12M Return" value={pct(stock["12M Return"])} /><Stat label="3M Sharpe" value={fmt(stock["3M Sharpe"])} /><Stat label="6M Sharpe" value={fmt(stock["6M Sharpe"])} /></div></div>
      <div className="detailcard"><div className="cardtitle"><b>Technical Structure</b><span>Current price relationships</span></div><div className="statgrid"><Stat label="CMP" value={`₹${fmt(stock.CMP)}`} /><Stat label="From 52W High" value={pct(stock["% From 52W High"])} /><Stat label="EMA 50" value={pct(stock["% EMA 50"])} /><Stat label="EMA 100" value={pct(stock["% EMA 100"])} /><Stat label="EMA 200" value={pct(stock["% EMA 200"])} /><Stat label="R² 1Y" value={fmt(stock["R² 1Y"])} /><Stat label="Volume Ratio" value={`${fmt(stock["Volume Ratio"])}x`} /><Stat label="Persistence 6M" value={pct(stock["Persistence 6M %"])} /></div></div>
      <div className="detailcard"><div className="cardtitle"><b>Research Context</b><span>Dataset provenance</span></div><dl className="context"><dt>Industry</dt><dd>{stock.Industry}</dd><dt>Index</dt><dd>{stock.Index}</dd><dt>Industry Relative</dt><dd>{fmt(stock["Industry Relative"])}</dd><dt>Acceleration</dt><dd>{fmt(stock.Acceleration)}</dd><dt>Data Age</dt><dd>{fmt(stock["Data Age Days"])} days</dd><dt>Market As Of</dt><dd>{fmt(stock["Market As Of"])}</dd></dl></div>
    </section>
  </main>
}
function Stat({label,value}:{label:string,value:string}) { return <div className="stat"><small>{label}</small><b>{value}</b></div> }
