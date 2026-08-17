"use client";

import { useEffect, useMemo, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
type Cell = string | number | boolean | null;
type Row = Record<string, Cell>;
type Filter = { field: string; operator: string; value: string | number | string[] };
type SortSpec = { field: string; direction: "asc" | "desc" };
type Metadata = { universe: number; universe_name: string; industries: string[]; filters: string[]; built_at: string | null; market_as_of?: string | null };
type QueryResult = { rows?: Row[]; total?: number; pages?: number; detail?: string };

const columns = [
  { field: "Rank", label: "Rank" }, { field: "Symbol", label: "Symbol" }, { field: "Company Name", label: "Company" },
  { field: "Industry", label: "Industry" }, { field: "Momentum Score", label: "Score" }, { field: "CMP", label: "CMP" },
  { field: "1M Return", label: "1M" }, { field: "3M Return", label: "3M" }, { field: "6M Return", label: "6M" },
  { field: "12M Return", label: "12M" }, { field: "6M Sharpe", label: "6M Sharpe" },
  { field: "% From 52W High", label: "52W" }, { field: "% EMA 200", label: "EMA 200" }, { field: "Volume Ratio", label: "Vol x" },
];
const filterGroups = [
  { title: "Universe", fields: ["Index", "Industry", "Symbol"] },
  { title: "Momentum", fields: ["Momentum Score", "Acceleration", "1M Return", "3M Return", "6M Return", "9M Return", "12M Return", "3M Sharpe", "6M Sharpe", "Industry Relative"] },
  { title: "Trend", fields: ["CMP", "% From 52W High", "% EMA 50", "% EMA 100", "% EMA 200"] },
  { title: "Risk & Participation", fields: ["Persistence 6M %", "Volume Ratio"] },
  { title: "Data Quality", fields: ["Data Age Days"] },
];
const numericFields = new Set(filterGroups.flatMap((group) => group.fields).filter((field) => !["Index", "Industry", "Symbol"].includes(field)));
const selectFields = new Set(["Index", "Industry", "Symbol"]);
const defaultFilters: Filter[] = [
  { field: "% From 52W High", operator: ">=", value: -20 },
  { field: "% EMA 200", operator: ">", value: 0 },
  { field: "3M Return", operator: ">", value: 0 },
];
function fmt(value: Cell) { if (value === null || value === undefined) return "—"; if (typeof value === "number") return value.toLocaleString("en-IN", { maximumFractionDigits: 2 }); return String(value); }
function pct(value: Cell, digits = 1) { if (value === null || value === undefined || value === "") return "—"; const n = Number(value); if (!Number.isFinite(n)) return "—"; return `${n > 0 ? "+" : ""}${n.toFixed(digits)}%`; }
function isPositive(value: Cell) { return typeof value === "number" && value > 0; }
function isNegative(value: Cell) { return typeof value === "number" && value < 0; }
function displayCell(field: string, value: Cell) { if (field === "CMP") return value == null ? "—" : `₹${fmt(value)}`; if (field === "Volume Ratio") return value == null ? "—" : `${fmt(value)}x`; if (field.includes("Return") || field.includes("EMA") || field === "% From 52W High" || field === "Persistence 6M %") return pct(value); return fmt(value); }

export default function Home() {
  const [rows, setRows] = useState<Row[]>([]), [total, setTotal] = useState(0), [pages, setPages] = useState(1), [metadata, setMetadata] = useState<Metadata | null>(null);
  const [filters, setFilters] = useState<Filter[]>(defaultFilters), [sort, setSort] = useState<SortSpec>({ field: "Rank", direction: "asc" }), [page, setPage] = useState(1), [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true), [error, setError] = useState(""), [degraded, setDegraded] = useState(false), [filterOpen, setFilterOpen] = useState(false), [columnOpen, setColumnOpen] = useState(false), [saved, setSaved] = useState(false);
  const [filterSearch, setFilterSearch] = useState(""), [draftField, setDraftField] = useState("Momentum Score"), [draftOperator, setDraftOperator] = useState(">"), [draftValue, setDraftValue] = useState("");
  const [visibleColumns, setVisibleColumns] = useState(columns.map((column) => column.field));

  const availableFields = useMemo(() => filterGroups.flatMap((group) => group.fields).filter((field, index, all) => all.indexOf(field) === index), []);
  const shownFilterGroups = useMemo(() => filterGroups.map((group) => ({ ...group, fields: group.fields.filter((field) => field.toLowerCase().includes(filterSearch.toLowerCase())) })).filter((group) => group.fields.length), [filterSearch]);
  const query = async (nextPage = page, nextFilters = filters, nextSort = sort, nextSearch = search) => {
    const controller = new AbortController();
    setLoading(true); setError("");
    try {
      const response = await fetch(`${API}/api/v1/screener/query`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ search: nextSearch, filters: nextFilters.map((f) => ({ field: f.field, operator: f.operator, value: f.value })), sort: nextSort, page: nextPage, page_size: 50 }), signal: controller.signal, cache: "no-store" });
      const data: QueryResult = await response.json();
      if (!response.ok) throw new Error(data.detail || "Unable to load screener.");
      setRows(data.rows || []); setTotal(data.total || 0); setPages(data.pages || 1); setPage(nextPage); setDegraded(false);
    } catch (e) { if (!(e instanceof DOMException && e.name === "AbortError")) { setError(e instanceof Error ? e.message : "Unable to load screener."); setDegraded(true); } }
    finally { setLoading(false); }
    return () => controller.abort();
  };
  useEffect(() => { fetch(`${API}/api/v1/screener/metadata`, { cache: "no-store" }).then((r) => r.json()).then(setMetadata).catch(() => undefined); query(1); }, []);
  useEffect(() => { const timer = window.setTimeout(() => { query(1, filters, sort, search); }, 250); return () => window.clearTimeout(timer); }, [search, filters, sort]);

  function updateSort(field: string) { setSort((current) => ({ field, direction: current.field === field && current.direction === "asc" ? "desc" : "asc" })); }
  function addFilter() { if (!draftField || !draftOperator || draftValue === "") return; const value = selectFields.has(draftField) ? draftValue : Number(draftValue); setFilters((current) => [...current.filter((f) => f.field !== draftField), { field: draftField, operator: draftOperator, value }]); setFilterOpen(false); setDraftValue(""); }
  function removeFilter(field: string) { setFilters((current) => current.filter((f) => f.field !== field)); }
  function clearFilters() { setFilters([]); }
  function toggleColumn(field: string) { setVisibleColumns((current) => current.includes(field) ? current.filter((f) => f !== field) : [...current, field]); }

  return <main className="page">
    <header className="topbar"><div><span className="eyebrow">Umiya Screener V2</span><h1>NSE Quantitative Screener</h1></div><div className="topmeta"><span>{metadata ? `${metadata.universe_name} · ${metadata.universe}` : "Loading universe…"}</span><span>{metadata?.market_as_of ? `Market as of ${metadata.market_as_of}` : ""}</span></div></header>
    <section className="toolbar"><div className="searchwrap"><input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search symbol or company" aria-label="Search symbol or company" />{search && <button aria-label="Clear search" onClick={() => setSearch("")}>×</button>}</div><button className="toolbarbutton" onClick={() => setFilterOpen(true)}>Filters {filters.length ? `(${filters.length})` : ""}</button><button className="toolbarbutton" onClick={() => setColumnOpen(true)}>Columns</button><button className="toolbarbutton" onClick={() => setSaved((v) => !v)}>{saved ? "Saved" : "Save view"}</button></section>
    <div className="chips">{filters.map((f) => <button key={f.field} className="chip" onClick={() => removeFilter(f.field)}>{f.field} {f.operator} {Array.isArray(f.value) ? f.value.join(", ") : f.value} ×</button>)}{filters.length > 0 && <button className="clearall" onClick={clearFilters}>Clear all</button>}</div>
    {degraded && <div className="notice">{error}</div>}
    <section className="results"><div className="resulthead"><div><b>{loading ? "Loading…" : `${total.toLocaleString("en-IN")} stocks`}</b><span>{metadata?.built_at ? `Dataset built ${metadata.built_at}` : "Prepared quantitative dataset"}</span></div><div className="pagination"><button disabled={page <= 1 || loading} onClick={() => query(page - 1)}>‹</button><span>{page} / {pages}</span><button disabled={page >= pages || loading} onClick={() => query(page + 1)}>›</button></div></div>
      <div className="tablewrap"><table><thead><tr>{columns.filter((column) => visibleColumns.includes(column.field)).map((column) => <th key={column.field} onClick={() => updateSort(column.field)}>{column.label}{sort.field === column.field ? (sort.direction === "asc" ? " ↑" : " ↓") : ""}</th>)}</tr></thead><tbody>{rows.map((row) => <tr key={String(row.Symbol)} onClick={() => window.location.href = `/stocks/${encodeURIComponent(String(row.Symbol))}`}><td colSpan={0}></td>{columns.filter((column) => visibleColumns.includes(column.field)).map((column) => <td key={column.field} className={isPositive(row[column.field]) ? "positive" : isNegative(row[column.field]) ? "negative" : ""}>{column.field === "Symbol" ? <b>{fmt(row[column.field])}</b> : displayCell(column.field, row[column.field])}</td>)}</tr>)}</tbody></table></div>
      <div className="mobilecards">{rows.map((row) => <button className="mobilecard" key={String(row.Symbol)} onClick={() => window.location.href = `/stocks/${encodeURIComponent(String(row.Symbol))}`}><div><b>{fmt(row.Symbol)}</b><span>{fmt(row["Company Name"])}</span></div><strong>{fmt(row["Momentum Score"])}</strong><small>{pct(row["12M Return"])} · {pct(row["% EMA 200"])}</small></button>)}</div>
    </section>
    {filterOpen && <div className="modalbackdrop" onClick={() => setFilterOpen(false)}><div className="drawer" onClick={(e) => e.stopPropagation()}><div className="drawerhead"><b>Filters</b><button onClick={() => setFilterOpen(false)}>×</button></div><input value={filterSearch} onChange={(e) => setFilterSearch(e.target.value)} placeholder="Find a metric" />{shownFilterGroups.map((group) => <div className="filtergroup" key={group.title}><small>{group.title}</small>{group.fields.map((field) => <button key={field} className={draftField === field ? "selected" : ""} onClick={() => setDraftField(field)}>{field}</button>)}</div>)}<div className="filterform"><select value={draftField} onChange={(e) => setDraftField(e.target.value)}>{availableFields.map((field) => <option key={field}>{field}</option>)}</select><select value={draftOperator} onChange={(e) => setDraftOperator(e.target.value)}><option>&gt;</option><option>&gt;=</option><option>&lt;</option><option>&lt;=</option><option>=</option><option>in</option></select><input value={draftValue} onChange={(e) => setDraftValue(e.target.value)} placeholder="Value" /><button onClick={addFilter}>Apply</button></div></div></div>}
    {columnOpen && <div className="modalbackdrop" onClick={() => setColumnOpen(false)}><div className="drawer" onClick={(e) => e.stopPropagation()}><div className="drawerhead"><b>Columns</b><button onClick={() => setColumnOpen(false)}>×</button></div>{columns.map((column) => <label key={column.field} className="checkrow"><input type="checkbox" checked={visibleColumns.includes(column.field)} onChange={() => toggleColumn(column.field)} />{column.label}</label>)}</div></div>}
    <footer className="footer"><span>Umiya Screener V2</span><span>Prepared server-side · Adjusted Close + Volume</span></footer>
  </main>;
}
