"use client";

import { useEffect, useMemo, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
type Row = Record<string, string | number | boolean | null>;
type Filter = { field: string; operator: string; value: string | number | string[] };
type Metadata = { universe: number; universe_name: string; source_counts: Record<string, number>; industries: string[]; filters: string[]; built_at: string | null };

const columns = ["Rank","Symbol","Company Name","Industry","Index","Momentum Score","CMP","3M Return","6M Return","3M Sharpe","6M Sharpe","R² 1Y","% From 52W High","% EMA 50","% EMA 200","Volume Ratio"];
const indexOptions = ["NIFTY 50","NIFTY NEXT 50","NIFTY MIDCAP 150","NIFTY SMALLCAP 250","NIFTY MICROCAP 250"];

function fmt(v: Row[keyof Row]) { if (v === null || v === undefined) return "—"; if (typeof v === "number") return Math.abs(v) < 10 && v !== Math.trunc(v) ? v.toFixed(2) : v.toLocaleString("en-IN", {maximumFractionDigits:2}); return String(v); }
function pct(v: Row[keyof Row]) { return v == null ? "—" : `${Number(v) > 0 ? "+" : ""}${Number(v).toFixed(1)}%`; }

export default function Home() {
  const [rows,setRows] = useState<Row[]>([]);
  const [total,setTotal] = useState(0);
  const [metadata,setMetadata] = useState<Metadata | null>(null);
  const [filters,setFilters] = useState<Filter[]>([
    {field:"% From 52W High",operator:">=",value:-20},
    {field:"% EMA 200",operator:">",value:0},
    {field:"3M Return",operator:">",value:0},
  ]);
  const [sort,setSort] = useState({field:"Rank",direction:"asc"});
  const [loading,setLoading] = useState(true);
  const [error,setError] = useState("");
  const [mobileFilter,setMobileFilter] = useState(false);
  const [search,setSearch] = useState("");

  async function loadMetadata() {
    const r = await fetch(`${API}/api/v1/screener/metadata`, {cache:"no-store"});
    if (!r.ok) throw new Error((await r.json().catch(()=>({}))).detail || "Screener dataset is unavailable.");
    setMetadata(await r.json());
  }

  async function runQuery(nextFilters=filters, nextSort=sort) {
    setLoading(true); setError("");
    try {
      const r=await fetch(`${API}/api/v1/screener/query`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({filters:nextFilters,sort:nextSort,page:1,page_size:50})});
      const data=await r.json().catch(()=>({}));
      if(!r.ok) throw new Error(data.detail || "Screener dataset is unavailable.");
      setRows(data.rows || []); setTotal(data.total || 0);
    } catch (e) {
      setRows([]); setTotal(0); setError(e instanceof Error ? e.message : "Unable to load screener data.");
    } finally { setLoading(false); }
  }

  useEffect(()=>{ Promise.all([loadMetadata(), runQuery()]).catch(e=>setError(e instanceof Error ? e.message : "Unable to load screener data.")); },[]);
  const shown=useMemo(()=>rows.filter(r=>String(r.Symbol||"").toLowerCase().includes(search.toLowerCase()) || String(r["Company Name"]||"").toLowerCase().includes(search.toLowerCase())),[rows,search]);
  function addFilter(f:Filter){const n=[...filters.filter(x=>x.field!==f.field),f];setFilters(n);runQuery(n,sort);setMobileFilter(false)}
  function removeFilter(field:string){const n=filters.filter(f=>f.field!==field);setFilters(n);runQuery(n,sort)}
  function doSort(field:string){const direction=sort.field===field&&sort.direction==="asc"?"desc":"asc";const n={field,direction};setSort(n);runQuery(filters,n)}

  return <div className="shell">
    <aside className="side"><div className="logo"><span>U</span><div><b>Umiya</b><small>Momentum Research</small></div></div><nav><button className="active"><i>⌕</i>Screener</button></nav><div className="sidefoot">NSE 750<br/>Umiya Screener V2</div></aside>
    <main>
      <header className="top"><div className="market"><div><small>DATASET</small><strong>{metadata?.universe_name || "NSE 750"}</strong></div><div><small>STOCKS</small><strong>{metadata?.universe ?? "—"}</strong></div><div className="desktop"><small>STATUS</small><strong className={metadata ? "green" : ""}>{metadata ? "READY" : "—"}</strong></div><div className="desktop"><small>BUILT</small><strong>{metadata?.built_at ? new Date(metadata.built_at).toLocaleTimeString("en-IN",{hour:"2-digit",minute:"2-digit"}) : "—"}</strong></div></div><div className="topicons">API　↻　⚙</div></header>
      <section className="page">
        {error && <div className="alert error"><span>⚠ <b>Dataset unavailable</b> · {error}</span><button onClick={()=>{loadMetadata().catch(()=>{});runQuery()}}>Retry</button></div>}
        <div className="heading"><div><h1>Screener</h1><p>NSE 750 multi-factor momentum ranking</p></div><div className="actions"><button>▣ Save Screen</button><button onClick={()=>setMobileFilter(true)}>☰ Filters</button><button>⚙ Columns</button></div></div>
        <div className="filterbar"><button onClick={()=>setMobileFilter(true)}><b>Universe</b><span>NSE 750 · 5 indices</span></button><button onClick={()=>setMobileFilter(true)}><b>Price & Trend</b><span>3 active</span></button><button onClick={()=>setMobileFilter(true)}><b>Momentum</b><span>2 active</span></button><button onClick={()=>setMobileFilter(true)}><b>Volatility</b><span>1 filter</span></button><button onClick={()=>setMobileFilter(true)}><b>Volume</b><span>1 filter</span></button><button onClick={()=>setMobileFilter(true)}><b>More Filters</b><span>{metadata?.filters.length ?? "—"} available</span></button></div>
        <div className="chips">{filters.map(f=><button key={f.field} onClick={()=>removeFilter(f.field)}>{f.field} {f.operator} {f.value}　×</button>)}<button className="clear" onClick={()=>{setFilters([]);runQuery([])}}>Clear all</button></div>
        <div className="kpis"><Kpi label="Universe" value={metadata ? String(metadata.universe) : "—"} sub="Canonical NSE 750"/><Kpi label="Filtered Results" value={loading ? "…" : String(total)} sub="Current screen"/><Kpi label="Industries" value={metadata ? String(metadata.industries.length) : "—"} sub="Classified"/><Kpi label="Data Status" value={metadata ? "READY" : "—"} sub={metadata?.built_at ? "Precomputed dataset" : "Waiting for dataset"} good={!!metadata}/></div>
        <div className="tablecard"><div className="tablehead"><div><b>Ranked Results</b><span> ({total})</span>{loading&&<span className="loading"> · updating…</span>}</div><div className="tools"><input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search stock…"/><button className="selected">▤ Table</button><button>⇩ Export</button></div></div>
          {loading ? <div className="empty"><b>Loading screener…</b><span>Fetching the precomputed analytical dataset.</span></div> : error ? <div className="empty"><b>Unable to load screener</b><span>{error}</span><button onClick={()=>runQuery()}>Retry</button></div> : shown.length === 0 ? <div className="empty"><b>No stocks match this screen</b><span>Adjust or clear the active filters.</span></div> : <><div className="tablewrap"><table><thead><tr>{columns.map(c=><th key={c} onClick={()=>doSort(c)}>{c} <span>↕</span></th>)}</tr></thead><tbody>{shown.map((r,i)=><tr key={String(r.Symbol)}><td>{r.Rank ?? i+1}</td><td className="symbol">{r.Symbol}</td><td>{r["Company Name"]}</td><td>{r.Industry}</td><td>{r.Index}</td><td><mark>{fmt(r["Momentum Score"])}</mark></td><td>₹{fmt(r.CMP)}</td><td className="green">{pct(r["3M Return"])}</td><td className="green">{pct(r["6M Return"])}</td><td>{fmt(r["3M Sharpe"])}</td><td>{fmt(r["6M Sharpe"])}</td><td>{fmt(r["R² 1Y"])}</td><td className="red">{pct(r["% From 52W High"])}</td><td className="green">{pct(r["% EMA 50"])}</td><td className="green">{pct(r["% EMA 200"])}</td><td>{fmt(r["Volume Ratio"])}x</td></tr>)}</tbody></table></div><div className="mobilecards">{shown.map((r,i)=><article key={String(r.Symbol)}><div className="rowtop"><span>#{r.Rank??i+1}　<b>{r.Symbol}</b></span><mark>{fmt(r["Momentum Score"])}</mark></div><div className="company">{r["Company Name"]} · {r.Industry} · {r.Index}</div><div className="metrics"><span>3M ROC<strong className="green">{pct(r["3M Return"])}</strong></span><span>6M ROC<strong className="green">{pct(r["6M Return"])}</strong></span><span>3M Sharpe<strong>{fmt(r["3M Sharpe"])}</strong></span><span>200 EMA<strong className="green">{pct(r["% EMA 200"])}</strong></span></div><div className="cardbottom">₹{fmt(r.CMP)} <span>› Full Analysis</span></div></article>)}</div></>}
        </div>
        <footer>{metadata?.built_at ? `Dataset built ${new Date(metadata.built_at).toLocaleString("en-IN")}` : "No dataset loaded"} <span>● API-driven architecture</span></footer>
      </section>
    </main>
    <nav className="bottomnav"><button className="active">⌕<small>Screener</small></button><button>☰<small>Filters</small></button><button>↕<small>Sort</small></button><button>☷<small>Columns</small></button><button>⋯<small>More</small></button></nav>
    {mobileFilter&&<div className="drawerback" onClick={()=>setMobileFilter(false)}><div className="drawer" onClick={e=>e.stopPropagation()}><div className="drawerhead"><b>Filters</b><button onClick={()=>setMobileFilter(false)}>×</button></div><label>Search filters<input placeholder="Search…"/></label><div className="filteroptions"><div className="filtersection">Universe / Index</div>{indexOptions.map(index=><button key={index} onClick={()=>addFilter({field:"Index",operator:"=",value:index})}><b>{index}</b><small>Official NSE constituent set</small></button>)}<div className="filtersection">Price & Momentum</div><button onClick={()=>addFilter({field:"% From 52W High",operator:">=",value:-10})}><b>Within 10% of 52W High</b><small>Price proximity</small></button><button onClick={()=>addFilter({field:"% EMA 200",operator:">",value:0})}><b>Above 200 EMA</b><small>Trend filter</small></button><button onClick={()=>addFilter({field:"3M Return",operator:">",value:10})}><b>3M Return &gt; 10%</b><small>Momentum</small></button><button onClick={()=>addFilter({field:"3M Sharpe",operator:">",value:1})}><b>3M Sharpe &gt; 1</b><small>Risk-adjusted momentum</small></button></div></div></div>}
  </div>
}
function Kpi({label,value,sub,good=false}:{label:string,value:string,sub:string,good?:boolean}){return <div className="kpi"><small>{label}</small><b className={good?"green":""}>{value}</b><span>{sub}</span></div>}
