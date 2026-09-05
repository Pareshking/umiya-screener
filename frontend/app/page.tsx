"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Cell, Row, display, isNumericField, isSigned, sign } from "../lib/format";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type Filter = { field: string; operator: string; value: string | number | string[] };
type SortSpec = { field: string; direction: "asc" | "desc" };
type Metadata = {
  universe: number; universe_name: string; industries: string[]; filters: string[];
  built_at: string | null; market_as_of?: string | null;
};
type QueryResult = { rows?: Row[]; total?: number; pages?: number; detail?: string };

const columns = [
  { field: "Rank", label: "#", w: 46 },
  { field: "Symbol", label: "Symbol" },
  { field: "Momentum Score", label: "Score" },
  { field: "CMP", label: "CMP" },
  { field: "1M Return", label: "1M" },
  { field: "3M Return", label: "3M" },
  { field: "6M Return", label: "6M" },
  { field: "12M Return", label: "12M" },
  { field: "6M Sharpe", label: "6M Sharpe" },
  { field: "% From 52W High", label: "52W" },
  { field: "% EMA 200", label: "EMA200" },
  { field: "Volume Ratio", label: "Vol" },
  { field: "Industry", label: "Industry" },
];

const filterGroups = [
  { title: "Universe", fields: ["Index", "Industry", "Symbol"] },
  { title: "Momentum", fields: ["Momentum Score", "Acceleration", "1M Return", "3M Return", "6M Return", "9M Return", "12M Return", "3M Sharpe", "6M Sharpe", "Industry Relative"] },
  { title: "Trend", fields: ["CMP", "% From 52W High", "% EMA 50", "% EMA 100", "% EMA 200"] },
  { title: "Risk & participation", fields: ["Persistence 6M %", "Volume Ratio"] },
  { title: "Data quality", fields: ["Data Age Days"] },
];
const selectFields = new Set(["Index", "Industry", "Symbol"]);

const defaultFilters: Filter[] = [
  { field: "% From 52W High", operator: ">=", value: -20 },
  { field: "% EMA 200", operator: ">", value: 0 },
  { field: "3M Return", operator: ">", value: 0 },
];

export default function Home() {
  const [rows, setRows] = useState<Row[]>([]);
  const [total, setTotal] = useState(0);
  const [pages, setPages] = useState(1);
  const [metadata, setMetadata] = useState<Metadata | null>(null);
  const [filters, setFilters] = useState<Filter[]>(defaultFilters);
  const [sort, setSort] = useState<SortSpec>({ field: "Rank", direction: "asc" });
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [degraded, setDegraded] = useState(false);
  const [drawer, setDrawer] = useState<"filters" | "columns" | null>(null);
  const [visible, setVisible] = useState(columns.map((c) => c.field));
  const [draft, setDraft] = useState({ field: "Momentum Score", operator: ">", value: "" });
  const [saved, setSaved] = useState(false);

  const shown = useMemo(() => columns.filter((c) => visible.includes(c.field)), [visible]);

  const loadMetadata = useCallback(async (signal?: AbortSignal) => {
    const r = await fetch(`${API}/api/v1/screener/metadata`, { signal });
    const d = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(d.detail || "Screener dataset is unavailable.");
    if (!signal?.aborted) { setMetadata(d); setDegraded(false); }
  }, []);

  const runQuery = useCallback(async (signal?: AbortSignal) => {
    setLoading(true); setError("");
    try {
      const r = await fetch(`${API}/api/v1/screener/query`, {
        method: "POST", headers: { "Content-Type": "application/json" }, signal,
        body: JSON.stringify({ filters, sort, search: search.trim() || null, page, page_size: 50 }),
      });
      const d: QueryResult = await r.json().catch(() => ({}));
      if (!r.ok) throw Object.assign(new Error(d.detail || "Screener request failed."), { status: r.status });
      if (signal?.aborted) return;
      setRows(d.rows || []); setTotal(d.total || 0); setPages(d.pages || 1); setDegraded(false);
    } catch (e) {
      if (e instanceof DOMException && e.name === "AbortError") return;
      if (signal?.aborted) return;
      const status = typeof e === "object" && e !== null && "status" in e ? Number((e as { status: number }).status) : 0;
      setRows([]); setTotal(0); setPages(1);
      setError(e instanceof Error ? e.message : "Unable to load screener data.");
      setDegraded(status === 503);
    } finally { if (!signal?.aborted) setLoading(false); }
  }, [filters, sort, search, page]);

  useEffect(() => {
    const c = new AbortController();
    loadMetadata(c.signal).catch((e) => {
      if (!c.signal.aborted) { setError(e instanceof Error ? e.message : "Unable to load metadata."); setDegraded(true); }
    });
    return () => c.abort();
  }, [loadMetadata]);

  useEffect(() => {
    const c = new AbortController();
    const t = window.setTimeout(() => runQuery(c.signal), 140);
    return () => { window.clearTimeout(t); c.abort(); };
  }, [runQuery]);

  useEffect(() => {
    const h = (e: KeyboardEvent) => { if (e.key === "Escape") setDrawer(null); };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, []);

  useEffect(() => {
    try {
      const raw = localStorage.getItem("umiya_saved_screen");
      if (!raw) return;
      const s = JSON.parse(raw);
      if (Array.isArray(s.filters)) setFilters(s.filters);
      if (s.sort?.field) setSort(s.sort);
      if (typeof s.search === "string") setSearch(s.search);
    } catch { /* malformed local state is not worth surfacing */ }
  }, []);

  function addFilter(f: Filter) {
    setFilters((cur) => [...cur.filter((x) => x.field !== f.field), f]);
    setPage(1);
  }
  function addDraft() {
    if (!draft.field || !draft.value.trim()) return;
    let value: string | number | string[] = draft.value.trim();
    if (draft.operator === "in") value = draft.value.split(",").map((s) => s.trim()).filter(Boolean);
    else if (isNumericField(draft.field)) {
      const n = Number(draft.value);
      if (!Number.isFinite(n)) return;
      value = n;
    }
    addFilter({ field: draft.field, operator: draft.operator, value });
    setDraft({ ...draft, value: "" });
  }
  function doSort(field: string) {
    setSort((c) => ({ field, direction: c.field === field && c.direction === "asc" ? "desc" : "asc" }));
    setPage(1);
  }
  function saveScreen() {
    localStorage.setItem("umiya_saved_screen", JSON.stringify({ filters, sort, search }));
    setSaved(true);
    window.setTimeout(() => setSaved(false), 1600);
  }
  async function exportCsv() {
    setError("");
    try {
      const r = await fetch(`${API}/api/v1/screener/export`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filters, sort, search: search.trim() || null, page: 1, page_size: 200 }),
      });
      if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || "Export failed.");
      const blob = await r.blob(); const url = URL.createObjectURL(blob);
      const a = document.createElement("a"); a.href = url; a.download = "umiya-screener.csv"; a.click();
      URL.revokeObjectURL(url);
    } catch (e) { setError(e instanceof Error ? e.message : "Export failed."); }
  }

  const asOf = metadata?.market_as_of;
  // Median 3M return of the page. The previous "share positive on this page"
  // restated whichever filter was active — with "3M Return > 0" applied it read
  // 100% by construction, which tells the reader nothing.
  const median3m = useMemo(() => {
    const vals = rows.map((r) => Number(r["3M Return"])).filter(Number.isFinite).sort((a, b) => a - b);
    if (!vals.length) return null;
    const mid = Math.floor(vals.length / 2);
    return vals.length % 2 ? vals[mid] : (vals[mid - 1] + vals[mid]) / 2;
  }, [rows]);

  return (
    <>
      <header className="topbar">
        <div className="topbar-inner">
          <a className="mark" href="/">
            <div className="mark-glyph">U</div>
            <div>
              <div className="mark-name">Umiya Screener</div>
              <div className="mark-sub">{metadata?.universe_name || "NSE 750"} · momentum research</div>
            </div>
          </a>
          <div className="spacer" />
          <div className="datastamp" title={metadata?.built_at ? `Metrics built ${new Date(metadata.built_at).toLocaleString("en-IN")}` : undefined}>
            <span className={`dot ${degraded ? "down" : ""}`} />
            {degraded ? "dataset unavailable" : asOf ? `as of ${asOf}` : "loading"}
          </div>
        </div>
      </header>

      <main className="shell">
        <div className="pagehead">
          <h1>Momentum Screener</h1>
          <p>
            Ranked on calendar-period risk-adjusted momentum across 1/3/6/9/12-month horizons.
            Every metric is precomputed server-side from Adjusted Close and Volume.
          </p>
        </div>

        <div className="statrow">
          <div className="stat">
            <div className="stat-label">Matches</div>
            <div className="stat-value num">{total.toLocaleString("en-IN")}</div>
            <div className="stat-sub">of {(metadata?.universe ?? 0).toLocaleString("en-IN")} in universe</div>
          </div>
          <div className="stat">
            <div className="stat-label">Filters</div>
            <div className="stat-value num">{filters.length}</div>
            <div className="stat-sub">{filters.length ? "narrowing the universe" : "whole universe"}</div>
          </div>
          <div className="stat">
            <div className="stat-label">Median 3M</div>
            <div className={`stat-value num ${median3m === null ? "" : median3m > 0 ? "pos" : "neg"}`}>
              {median3m === null ? "—" : `${median3m > 0 ? "+" : ""}${median3m.toFixed(1)}%`}
            </div>
            <div className="stat-sub">midpoint of this page</div>
          </div>
          <div className="stat">
            <div className="stat-label">Market date</div>
            <div className="stat-value num" style={{ fontSize: 17 }}>{asOf || "—"}</div>
            <div className="stat-sub">common as-of across the set</div>
          </div>
        </div>

        {error && (
          <div className="banner">
            <strong style={{ flex: "none" }}>{degraded ? "Dataset unavailable" : "Error"}</strong>
            <span style={{ flex: 1 }}>{error}</span>
            <button className="btn" style={{ padding: "3px 9px" }} onClick={() => { runQuery(); loadMetadata().catch(() => {}); }}>Retry</button>
          </div>
        )}

        <div className="controls">
          <div className="search">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
              <circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" />
            </svg>
            <input
              placeholder="Search symbol or company…"
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            />
          </div>
          <button className="btn" onClick={() => setDrawer("filters")}>
            Filters {filters.length > 0 && <span className="btn-count">{filters.length}</span>}
          </button>
          <button className="btn" onClick={() => setDrawer("columns")}>Columns</button>
          <button className="btn" onClick={saveScreen}>{saved ? "Saved" : "Save screen"}</button>
          <button className="btn primary" onClick={exportCsv} disabled={!rows.length}>Export CSV</button>
        </div>

        {filters.length > 0 && (
          <div className="chips">
            {filters.map((f) => (
              <span className="chip" key={f.field}>
                {f.field} {f.operator} {Array.isArray(f.value) ? f.value.join(", ") : f.value}
                <button onClick={() => { setFilters((c) => c.filter((x) => x.field !== f.field)); setPage(1); }} aria-label={`Remove ${f.field} filter`}>×</button>
              </span>
            ))}
            <button className="chip-clear" onClick={() => { setFilters([]); setPage(1); }}>Clear all</button>
          </div>
        )}

        <div className="panel">
          <div className="panel-head">
            <span className="panel-title">Ranked results</span>
            <span className="panel-note">sorted by {sort.field} {sort.direction === "asc" ? "↑" : "↓"}</span>
            <div className="spacer" />
            {loading && <span className="panel-note">updating…</span>}
          </div>

          <div className="tablewrap">
            <table className="grid">
              <thead>
                <tr>
                  {shown.map((c) => (
                    <th
                      key={c.field}
                      className={c.field === "Symbol" || c.field === "Industry" ? "left" : undefined}
                      style={c.w ? { width: c.w } : undefined}
                      onClick={() => doSort(c.field)}
                      aria-sort={sort.field === c.field ? (sort.direction === "asc" ? "ascending" : "descending") : undefined}
                      title={`Sort by ${c.field}`}
                    >
                      {c.label}{sort.field === c.field ? (sort.direction === "asc" ? " ↑" : " ↓") : ""}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {loading && !rows.length
                  ? Array.from({ length: 12 }, (_, i) => (
                      <tr key={i}>
                        {shown.map((c) => (
                          <td key={c.field}><div className="skel" style={{ width: c.field === "Symbol" ? "70%" : "60%", marginLeft: c.field === "Symbol" || c.field === "Industry" ? 0 : "auto" }} /></td>
                        ))}
                      </tr>
                    ))
                  : rows.map((row) => (
                      <tr key={String(row.Symbol)}>
                        {shown.map((c) => {
                          const v = row[c.field] as Cell;
                          if (c.field === "Rank") return <td key={c.field} className="rank">{v == null ? "—" : String(v)}</td>;
                          if (c.field === "Symbol") {
                            return (
                              <td key={c.field} className="left">
                                <a className="sym" href={`/stocks/${encodeURIComponent(String(row.Symbol))}`}>{String(row.Symbol)}</a>
                                <div className="coname">{String(row["Company Name"] ?? "")}</div>
                              </td>
                            );
                          }
                          if (c.field === "Industry") {
                            return <td key={c.field} className="left"><span className="tag">{v == null ? "—" : String(v)}</span></td>;
                          }
                          if (c.field === "Momentum Score") {
                            const n = Number(v);
                            const w = Number.isFinite(n) ? Math.min(38, Math.max(0, (n + 3) / 6 * 38)) : 0;
                            return (
                              <td key={c.field} className={`num scorecell ${sign(v)}`}>
                                {display(c.field, v)}
                                <span className="scorebar" style={{ width: w }} />
                              </td>
                            );
                          }
                          return (
                            <td key={c.field} className={`num ${isSigned(c.field) ? sign(v) : ""}`}>
                              {display(c.field, v)}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
              </tbody>
            </table>
          </div>

          {!loading && !rows.length && !error && (
            <div className="state">
              <h3>No stocks match</h3>
              <p>Loosen or remove a filter to widen the set.</p>
            </div>
          )}

          <div className="pager">
            <span className="pager-info">
              {total ? `${(page - 1) * 50 + 1}–${Math.min(page * 50, total)} of ${total.toLocaleString("en-IN")}` : "—"}
            </span>
            <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
              <button className="btn" onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page <= 1}>Prev</button>
              <span className="pager-info">{page} / {pages}</span>
              <button className="btn" onClick={() => setPage((p) => Math.min(pages, p + 1))} disabled={page >= pages}>Next</button>
            </div>
          </div>
        </div>

        <p className="faint" style={{ fontSize: 11.5, marginTop: 14 }}>
          Umiya Screener V2 · server-side quantitative engine · calendar-period horizons · no browser-side market-data calculations
        </p>
      </main>

      <nav className="mobilebar">
        <button onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}>
          <span>▲</span> Top
        </button>
        <button aria-pressed={drawer === "filters"} onClick={() => setDrawer("filters")}>
          <span>≡</span> Filters{filters.length ? ` (${filters.length})` : ""}
        </button>
        <button aria-pressed={drawer === "columns"} onClick={() => setDrawer("columns")}>
          <span>▦</span> Columns
        </button>
        <button onClick={exportCsv}><span>↓</span> Export</button>
      </nav>

      {drawer && (
        <>
          <div className="scrim" onClick={() => setDrawer(null)} />
          <aside className="drawer" role="dialog" aria-label={drawer === "filters" ? "Filters" : "Columns"}>
            <div className="drawer-head">
              <strong style={{ fontSize: 14 }}>{drawer === "filters" ? "Filters" : "Columns"}</strong>
              <div className="spacer" />
              <button className="btn" onClick={() => setDrawer(null)}>Done</button>
            </div>

            <div className="drawer-body">
              {drawer === "filters" ? (
                <>
                  <div className="field">
                    <label>Field</label>
                    <select value={draft.field} onChange={(e) => setDraft({ ...draft, field: e.target.value, value: "" })}>
                      {filterGroups.map((g) => (
                        <optgroup key={g.title} label={g.title}>
                          {g.fields.map((f) => <option key={f} value={f}>{f}</option>)}
                        </optgroup>
                      ))}
                    </select>
                  </div>
                  <div className="field">
                    <label>Operator</label>
                    <select value={draft.operator} onChange={(e) => setDraft({ ...draft, operator: e.target.value })}>
                      {(selectFields.has(draft.field) ? ["=", "in"] : [">", ">=", "<", "<=", "="]).map((o) => (
                        <option key={o} value={o}>{o}</option>
                      ))}
                    </select>
                  </div>
                  <div className="field">
                    <label>Value</label>
                    {draft.field === "Industry" && metadata?.industries?.length ? (
                      <select value={draft.value} onChange={(e) => setDraft({ ...draft, value: e.target.value })}>
                        <option value="">Select…</option>
                        {metadata.industries.map((i) => <option key={i} value={i}>{i}</option>)}
                      </select>
                    ) : (
                      <input
                        value={draft.value}
                        placeholder={draft.operator === "in" ? "comma, separated, values" : "value"}
                        onChange={(e) => setDraft({ ...draft, value: e.target.value })}
                        onKeyDown={(e) => { if (e.key === "Enter") addDraft(); }}
                      />
                    )}
                  </div>
                  <button className="btn primary" style={{ width: "100%" }} onClick={addDraft}>Add filter</button>

                  {filters.length > 0 && (
                    <>
                      <div className="groupname">Active</div>
                      {filters.map((f) => (
                        <div key={f.field} className="checkrow" style={{ justifyContent: "space-between" }}>
                          <span className="num" style={{ fontSize: 12 }}>
                            {f.field} {f.operator} {Array.isArray(f.value) ? f.value.join(", ") : f.value}
                          </span>
                          <button className="chip-clear" onClick={() => { setFilters((c) => c.filter((x) => x.field !== f.field)); setPage(1); }}>Remove</button>
                        </div>
                      ))}
                    </>
                  )}
                </>
              ) : (
                filterGroups.map((g) => {
                  const inGroup = columns.filter((c) => g.fields.includes(c.field) || (g.title === "Universe" && ["Symbol", "Rank", "Industry"].includes(c.field)));
                  if (!inGroup.length) return null;
                  return (
                    <div key={g.title}>
                      <div className="groupname">{g.title}</div>
                      {inGroup.map((c) => (
                        <label key={c.field} className="checkrow">
                          <input
                            type="checkbox"
                            checked={visible.includes(c.field)}
                            onChange={() => setVisible((cur) => cur.includes(c.field) ? cur.filter((x) => x !== c.field) : [...cur, c.field])}
                          />
                          {c.field}
                        </label>
                      ))}
                    </div>
                  );
                })
              )}
            </div>

            <div className="drawer-foot">
              {drawer === "filters" && <button className="btn" onClick={() => { setFilters([]); setPage(1); }}>Clear all</button>}
              <div className="spacer" />
              <button className="btn primary" onClick={() => setDrawer(null)}>Apply</button>
            </div>
          </aside>
        </>
      )}
    </>
  );
}
