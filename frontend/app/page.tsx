"use client";

import { useEffect, useMemo, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type Row = Record<string, string | number | boolean | null>;
type Filter = { field: string; operator: string; value: string | number | string[] };

const demo: Row[] = [
  {Rank:1,Symbol:"CDSL", "Company Name":"CDSL Ltd",Industry:"Capital Markets", "Momentum Score":94.2,CMP:1572.4,"3M Return":28.4,"6M Return":52.1,"3M Sharpe":2.14,"6M Sharpe":1.89,"R² 1Y":.86,"% From 52W High":-4.2,"% EMA 50":7.8,"% EMA 200":24.3,"Volume Ratio":2.35},
  {Rank:2,Symbol:"IRFC", "Company Name":"Indian Railway Fin Corp",Industry:"Finance", "Momentum Score":92.8,CMP:172.35,"3M Return":24.6,"6M Return":46.8,"3M Sharpe":1.98,"6M Sharpe":1.76,"R² 1Y":.82,"% From 52W High":-6.1,"% EMA 50":6.2,"% EMA 200":21.7,"Volume Ratio":1.92},
  {Rank:3,Symbol:"RECLTD", "Company Name":"REC Ltd",Industry:"Finance", "Momentum Score":91.6,CMP:604.8,"3M Return":22.1,"6M Return":41.3,"3M Sharpe":1.87,"6M Sharpe":1.65,"R² 1Y":.79,"% From 52W High":-5.3,"% EMA 50":5.1,"% EMA 200":19.8,"Volume Ratio":1.78},
  {Rank:4,Symbol:"MAHLOG", "Company Name":"Mahindra Logistics",Industry:"Logistics", "Momentum Score":90.3,CMP:428.65,"3M Return":19.8,"6M Return":38.7,"3M Sharpe":1.75,"6M Sharpe":1.52,"R² 1Y":.76,"% From 52W High":-7.2,"% EMA 50":4.3,"% EMA 200":17.6,"Volume Ratio":2.11},
  {Rank:5,Symbol:"PNB", "Company Name":"Punjab National Bank",Industry:"Banking", "Momentum Score":89.7,CMP:112.25,"3M Return":18.7,"6M Return":36.2,"3M Sharpe":1.62,"6M Sharpe":1.41,"R² 1Y":.72,"% From 52W High":-8.9,"% EMA 50":3.8,"% EMA 200":15.9,"Volume Ratio":1.65},
  {Rank:6,Symbol:"HUDCO", "Company Name":"Housing & Urban Dev Corp",Industry:"Finance", "Momentum Score":88.9,CMP:215.6,"3M Return":21.3,"6M Return":34.8,"3M Sharpe":1.68,"6M Sharpe":1.38,"R² 1Y":.74,"% From 52W High":-9.1,"% EMA 50":2.9,"% EMA 200":14.2,"Volume Ratio":2.41}
];

const columns = ["Rank","Symbol","Company Name","Industry","Momentum Score","CMP","3M Return","6M Return","3M Sharpe","6M Sharpe","R² 1Y","% From 52W High","% EMA 50","% EMA 200","Volume Ratio"];

function fmt(v: Row[keyof Row]) { if (v === null || v === undefined) return "—"; if (typeof v === "number") return Math.abs(v) < 10 && v !== Math.trunc(v) ? v.toFixed(2) : v.toLocaleString("en-IN", {maximumFractionDigits:2}); return String(v); }
function pct(v: Row[keyof Row]) { return v == null ? "—" : `${Number(v) > 0 ? "+" : ""}${Number(v).toFixed(1)}%`; }

export default function Home() {
  const [rows,setRows] = useState<Row[]>(demo);
  const [total,setTotal] = useState(126);
  const [filters,setFilters] = useState<Filter[]>([
    {field:"% From 52W High",operator:">=",value:-20},
    {field:"% EMA 200",operator:">",value:0},
    {field:"3M Return",operator:">",value:0},
  ]);
  const [sort,setSort] = useState({field:"Rank",direction:"asc"});
  const [loading,setLoading] = useState(false);
  const [mobileFilter,setMobileFilter] = useState(false);
  const [search,setSearch] = useState("");

  async function runQuery(nextFilters=filters, nextSort=sort) {
    setLoading(true);
    try {
      const r=await fetch(`${API}/api/v1/screener/query`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({filters:nextFilters,sort:nextSort,page:1,page_size:50})});
      if(!r.ok) throw new Error("API unavailable");
      const data=await r.json(); setRows(data.rows); setTotal(data.total);
    } catch { /* Demo data keeps the UI usable before the API is running. */ }
    finally { setLoading(false); }
  }
  useEffect(()=>{runQuery()},[]);
  const shown=useMemo(()=>rows.filter(r=>String(r.Symbol||"").toLowerCase().includes(search.toLowerCase()) || String(r["Company Name"]||"").toLowerCase().includes(search.toLowerCase())),[rows,search]);
  function addFilter(f:Filter){const n=[...filters.filter(x=>x.field!==f.field),f];setFilters(n);runQuery(n,sort);setMobileFilter(false)}
  function removeFilter(field:string){const n=filters.filter(f=>f.field!==field);setFilters(n);runQuery(n,sort)}
  function doSort(field:string){const direction=sort.field===field&&sort.direction==="asc"?"desc":"asc";const n={field,direction};setSort(n);runQuery(filters,n)}

  return <div className="shell">
    <aside className="side"><div className="logo"><span>U</span><div><b>Umiya</b><small>Momentum Research</small></div></div><nav>{["Screener","Qualified","Sectors","RRG","Multi-Strategy","Portfolio","Delivery","Watchlist","Market Breadth","Backtest"].map((x,i)=><button className={i===0?"active":""} key={x}><i>{["⌕","✓","▦","✣","⌁","◇","▥","☆","◌","▣"][i]}</i>{x}</button>)}</nav><div className="sidefoot">NSE 750<br/>Umiya Screener V2</div></aside>
    <main>
      <header className="top"><div className="market"><div><small>MARKET REGIME</small><strong className="green">BULLISH ↗</strong></div><div><small>NIFTY</small><strong>25,502 <em className="green">+1.32%</em></strong></div><div className="desktop"><small>A/D RATIO</small><strong>1.74</strong></div><div className="desktop"><small>BREADTH</small><strong className="green">68%</strong></div></div><div className="topicons">09:35 AM　↻　⚙</div></header>
      <section className="page">
        <div className="alert"><span>● <b>12 stocks</b> triggered buy signals today</span><button>View signals</button></div>
        <div className="heading"><div><h1>Screener</h1><p>NSE 750 multi-factor momentum ranking</p></div><div className="actions"><button>▣ Save Screen</button><button onClick={()=>setMobileFilter(true)}>☰ Filters</button><button>⚙ Columns</button></div></div>
        <div className="filterbar"><button onClick={()=>setMobileFilter(true)}><b>Universe</b><span>NSE 750</span></button><button onClick={()=>setMobileFilter(true)}><b>Price & Trend</b><span>3 active</span></button><button onClick={()=>setMobileFilter(true)}><b>Momentum</b><span>2 active</span></button><button onClick={()=>setMobileFilter(true)}><b>Volatility</b><span>1 filter</span></button><button onClick={()=>setMobileFilter(true)}><b>Volume</b><span>1 filter</span></button><button onClick={()=>setMobileFilter(true)}><b>More Filters</b><span>12 available</span></button></div>
        <div className="chips">{filters.map(f=><button key={f.field} onClick={()=>removeFilter(f.field)}>{f.field} {f.operator} {f.value}　×</button>)}<button className="clear" onClick={()=>{setFilters([]);runQuery([])}}>Clear all</button></div>
        <div className="kpis"><Kpi label="Stocks" value={String(total||750)} sub="NSE 750 Universe"/><Kpi label="Filtered Results" value={String(total)} sub="Current screen"/><Kpi label="Avg Momentum" value="68.4" sub="Cross-sectional"/><Kpi label="Top Score" value="94.2" sub="Highest" good/><Kpi label="Buy Signals" value="12" sub="Today" good/><Kpi label="Data Quality" value="98.2%" sub="Excellent" good/></div>
        <div className="tablecard"><div className="tablehead"><div><b>Ranked Results</b><span> ({total})</span></div><div className="tools"><input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search stock…"/><button className="selected">▤ Table</button><button>⇩ Export</button></div></div>
          <div className="tablewrap"><table><thead><tr>{columns.map(c=><th key={c} onClick={()=>doSort(c)}>{c} <span>↕</span></th>)}</tr></thead><tbody>{shown.map((r,i)=><tr key={String(r.Symbol)}><td>{r.Rank ?? i+1}</td><td className="symbol">{r.Symbol}</td><td>{r["Company Name"]}</td><td>{r.Industry}</td><td><mark>{fmt(r["Momentum Score"])}</mark></td><td>₹{fmt(r.CMP)}</td><td className="green">{pct(r["3M Return"])}</td><td className="green">{pct(r["6M Return"])}</td><td>{fmt(r["3M Sharpe"])}</td><td>{fmt(r["6M Sharpe"])}</td><td>{fmt(r["R² 1Y"])}</td><td className="red">{pct(r["% From 52W High"])}</td><td className="green">{pct(r["% EMA 50"])}</td><td className="green">{pct(r["% EMA 200"])}</td><td>{fmt(r["Volume Ratio"])}x</td></tr>)}</tbody></table></div>
          <div className="mobilecards">{shown.map((r,i)=><article key={String(r.Symbol)}><div className="rowtop"><span>#{r.Rank??i+1}　<b>{r.Symbol}</b></span><mark>{fmt(r["Momentum Score"])}</mark></div><div className="company">{r["Company Name"]} · {r.Industry}</div><div className="metrics"><span>3M ROC<strong className="green">{pct(r["3M Return"])}</strong></span><span>6M ROC<strong className="green">{pct(r["6M Return"])}</strong></span><span>3M Sharpe<strong>{fmt(r["3M Sharpe"])}</strong></span><span>200 EMA<strong className="green">{pct(r["% EMA 200"])}</strong></span></div><div className="cardbottom">₹{fmt(r.CMP)} <span>› Full Analysis</span></div></article>)}</div>
        </div>
        <footer>Data as of 09:35 AM IST · Prices delayed by 15 minutes <span>● API-ready architecture</span></footer>
      </section>
    </main>
    <nav className="bottomnav"><button className="active">⌕<small>Screener</small></button><button>✓<small>Qualified</small></button><button>✣<small>RRG</small></button><button>▦<small>Sectors</small></button><button>⋯<small>More</small></button></nav>
    {mobileFilter&&<div className="drawerback" onClick={()=>setMobileFilter(false)}><div className="drawer" onClick={e=>e.stopPropagation()}><div className="drawerhead"><b>Filters</b><button onClick={()=>setMobileFilter(false)}>×</button></div><label>Search filters<input placeholder="Search…"/></label><div className="filteroptions"><button onClick={()=>addFilter({field:"% From 52W High",operator:">=",value:-10})}><b>Within 10% of 52W High</b><small>Price proximity</small></button><button onClick={()=>addFilter({field:"% EMA 200",operator:">",value:0})}><b>Above 200 EMA</b><small>Trend filter</small></button><button onClick={()=>addFilter({field:"3M Return",operator:">",value:10})}><b>3M Return &gt; 10%</b><small>Momentum</small></button><button onClick={()=>addFilter({field:"3M Sharpe",operator:">",value:1})}><b>3M Sharpe &gt; 1</b><small>Risk-adjusted momentum</small></button></div></div></div>}
  </div>
}
function Kpi({label,value,sub,good=false}:{label:string,value:string,sub:string,good?:boolean}){return <div className="kpi"><small>{label}</small><b className={good?"green":""}>{value}</b><span>{sub}</span></div>}
