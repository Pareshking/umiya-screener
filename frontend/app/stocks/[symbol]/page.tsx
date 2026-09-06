"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import PriceChart, { ChartPoint, EMA_COLOURS } from "../../../components/price-chart";
import { Cell, Row, crore, display, num, pct, rupee, sign } from "../../../lib/format";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/* Chart windows are named in calendar terms and requested in sessions, matching
   the engine's convention that a horizon means a period, not a row count. */
const RANGES: { label: string; days: number }[] = [
  { label: "3M", days: 63 },
  { label: "6M", days: 126 },
  { label: "1Y", days: 252 },
  { label: "3Y", days: 756 },
  { label: "Max", days: 2520 },
];

type ChartPayload = {
  rows?: ChartPoint[];
  ema_spans?: number[];
  benchmark?: string | null;
  market_as_of?: string;
  detail?: string;
};

/* Most of what a stock page owes the reader is label/value pairs, so they get
   one component rather than six hand-rolled tables. `fundamental` marks rows
   sourced from the third party, so the whole panel can state its provenance
   and disappear cleanly when that source is unavailable. */
type SpecRow = [label: string, value: string, tone?: Cell];

/** 1st, 2nd, 3rd, 4th … — "32th percentile" reads as a typo, because it is. */
function ordinal(n: number): string {
  const rem100 = n % 100;
  if (rem100 >= 11 && rem100 <= 13) return `${n}th`;
  return `${n}${["th", "st", "nd", "rd"][n % 10] ?? "th"}`;
}

function Specs({ title, note, rows }: { title: string; note?: string; rows: SpecRow[] }) {
  if (!rows.length) return null;
  return (
    <div className="panel">
      <div className="panel-head">
        <span className="panel-title">{title}</span>
        {note && <span className="panel-note">{note}</span>}
      </div>
      <div className="tablewrap">
        <table className="grid">
          <tbody>
            {rows.map(([label, value, tone]) => (
              <tr key={label}>
                <td className="left muted" style={{ fontSize: 12 }}>{label}</td>
                <td className={`num ${tone === undefined ? "" : sign(tone)}`}>{value}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function StockPage() {
  const params = useParams<{ symbol: string }>();
  const symbol = decodeURIComponent(String(params?.symbol ?? "")).toUpperCase();

  const [stock, setStock] = useState<Row | null>(null);
  const [chart, setChart] = useState<ChartPayload>({});
  const [days, setDays] = useState(252);
  const [error, setError] = useState("");
  const [peers, setPeers] = useState<Row[]>([]);
  const [activeEmas, setActiveEmas] = useState<number[]>([50, 200]);
  const [showVolume, setShowVolume] = useState(true);
  const [showRs, setShowRs] = useState(true);

  useEffect(() => {
    if (!symbol) return;
    const c = new AbortController();
    setError(""); setStock(null);
    fetch(`${API}/api/v1/stocks/${encodeURIComponent(symbol)}`, { signal: c.signal })
      .then(async (r) => { if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || "Stock unavailable."); return r.json(); })
      .then((d) => { if (!c.signal.aborted) setStock(d); })
      .catch((e) => { if (!(e?.name === "AbortError")) setError(e instanceof Error ? e.message : "Unable to load stock."); });
    return () => c.abort();
  }, [symbol]);

  useEffect(() => {
    if (!symbol) return;
    const c = new AbortController();
    setChart({});
    fetch(`${API}/api/v1/stocks/${encodeURIComponent(symbol)}/chart?days=${days}`, { signal: c.signal })
      .then(async (r) => { if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || "Chart unavailable."); return r.json(); })
      .then((d) => { if (!c.signal.aborted) setChart(d); })
      .catch((e) => { if (!(e?.name === "AbortError")) setError(e instanceof Error ? e.message : "Unable to load chart."); });
    return () => c.abort();
  }, [symbol, days]);

  // Peers in the same industry — the comparison a ranked screener implies.
  useEffect(() => {
    const industry = stock?.Industry;
    if (!industry) return;
    const c = new AbortController();
    fetch(`${API}/api/v1/screener/query`, {
      method: "POST", headers: { "Content-Type": "application/json" }, signal: c.signal,
      body: JSON.stringify({
        filters: [{ field: "Industry", operator: "=", value: String(industry) }],
        sort: { field: "Rank", direction: "asc" }, search: null, page: 1, page_size: 8,
      }),
    })
      .then((r) => r.ok ? r.json() : null)
      .then((d) => { if (d && !c.signal.aborted) setPeers(d.rows || []); })
      .catch(() => { /* peers are supplementary; their absence is not an error */ });
    return () => c.abort();
  }, [stock?.Industry]);

  const spans = chart.ema_spans ?? [];
  const rows = chart.rows ?? [];

  const fundamentalsOk = stock?.["Fundamentals Available"] !== false;

  function moved(field: string): string {
    const n = Number(stock?.[field]);
    if (!Number.isFinite(n)) return "—";
    if (n === 0) return "unchanged";
    return `${n > 0 ? "▲" : "▼"}${Math.abs(n)} places`;
  }

  const kpis = useMemo(() => stock ? [
    {
      label: "Momentum score", value: num(stock["Momentum Score"], 2), cell: stock["Momentum Score"],
      sub: stock["Score Percentile"] != null ? `${ordinal(Number(stock["Score Percentile"]))} percentile` : "of the universe",
    },
    { label: "Rank", value: String(stock.Rank ?? "—"), cell: null, sub: `${moved("Rank Δ1M")} in 1M` },
    { label: "3M rank move", value: moved("Rank Δ3M"), cell: stock["Rank Δ3M"], sub: "places gained" },
    { label: "12M return", value: pct(stock["12M Return"]), cell: stock["12M Return"], sub: "calendar year" },
    { label: "6M Sharpe", value: num(stock["6M Sharpe"], 2), cell: stock["6M Sharpe"], sub: "risk-adjusted" },
    { label: "Max drawdown", value: pct(stock["Max DD 12M"]), cell: null, sub: "worst 12M fall" },
  ] : [], [stock]);

  // Panels sourced from the third party. Each is omitted entirely when that
  // source is unavailable rather than rendered as a column of dashes.
  const valuation: SpecRow[] = stock && fundamentalsOk ? [
    ["Market cap", crore(stock["Market Cap"])],
  ] : [];

  // P/E, price-to-book, dividend yield, ROE and the quarterly growth figures
  // are deliberately absent. The upstream computes its valuation ratios against
  // a stale price -- see src/fundamentals.py for the reconciliation against
  // Screener.in -- and the error is largest on exactly the risen stocks this
  // screener ranks highest. They return when the source recomputes them.
  const growth: SpecRow[] = [];

  const participation: SpecRow[] = stock ? [
    ...(fundamentalsOk ? [
      ["Promoter holding", stock["Promoter Holding %"] != null ? `${num(stock["Promoter Holding %"], 2)}%` : "—"] as SpecRow,
      ["Public holding", stock["Public Holding %"] != null ? `${num(stock["Public Holding %"], 2)}%` : "—"] as SpecRow,
      ["Delivery", stock["Delivery %"] != null ? `${num(stock["Delivery %"], 1)}%` : "—"] as SpecRow,
      ["Delivery volume", stock["Delivery Volume"] != null ? num(stock["Delivery Volume"], 0) : "—"] as SpecRow,
    ] : []),
    ["Volume", stock.Volume != null ? num(stock.Volume, 0) : "—"] as SpecRow,
    ["Volume vs 20-day", stock["Volume Ratio"] != null ? `${num(stock["Volume Ratio"], 2)}×` : "—"] as SpecRow,
  ] : [];

  const provenance: SpecRow[] = stock ? [
    ["Market as of", String(stock["Market As Of"] ?? "—").slice(0, 10)],
    ["Price age", stock["Data Age Days"] != null ? `${stock["Data Age Days"]} days` : "—"],
    ["History", stock["History Days"] != null ? `${stock["History Days"]} sessions` : "—"],
    ...(fundamentalsOk && stock.ISIN ? [["ISIN", String(stock.ISIN)] as SpecRow] : []),
    ...(fundamentalsOk && stock["Fundamentals As Of"]
      ? [["Fundamentals as of", String(stock["Fundamentals As Of"]).slice(0, 10)] as SpecRow] : []),
  ] : [];

  if (error) {
    return (
      <main className="shell">
        <div className="banner" style={{ marginTop: 28 }}><strong>Unavailable</strong><span>{error}</span></div>
        <a className="btn" href="/">← Back to screener</a>
      </main>
    );
  }

  return (
    <>
      <header className="topbar">
        <div className="topbar-inner">
          <a className="mark" href="/">
            <div className="mark-glyph">U</div>
            <div><div className="mark-name">Umiya Screener</div><div className="mark-sub">stock detail</div></div>
          </a>
          <div className="spacer" />
          {chart.market_as_of && <div className="datastamp"><span className="dot" />as of {chart.market_as_of}</div>}
          <a className="btn" href="/">Screener</a>
        </div>
      </header>

      <main className="shell">
        <div className="stockhead">
          <div>
            <h1>{symbol}</h1>
            <div className="co">{String(stock?.["Company Name"] ?? "")}</div>
            <div style={{ display: "flex", gap: 6, marginTop: 8, flexWrap: "wrap", alignItems: "center" }}>
              {stock?.Setup && stock.Setup !== "—" && (
                <span className={`setup setup-${String(stock.Setup)}`}>{String(stock.Setup)}</span>
              )}
              {stock?.["NSE Sector"] && <span className="tag">{String(stock["NSE Sector"])}</span>}
              {stock?.["Basic Industry"] && <span className="tag">{String(stock["Basic Industry"])}</span>}
              {stock?.Index && <span className="tag">{String(stock.Index)}</span>}
            </div>
          </div>
          <div className="spacer" />
          <div className="price">
            <div className="price-value num">{rupee(stock?.CMP ?? null)}</div>
            <div className={`num ${sign(stock?.["1M Return"] ?? null)}`} style={{ fontSize: 13 }}>
              {pct(stock?.["1M Return"] ?? null)} <span className="faint">1M</span>
            </div>
            {stock?.["Market Cap"] != null && (
              <div className="faint num" style={{ fontSize: 12, marginTop: 2 }}>{crore(stock["Market Cap"])}</div>
            )}
          </div>
        </div>

        {stock && !fundamentalsOk && (
          <div className="notice">
            <strong>Fundamentals unavailable</strong>
            <span>
              Valuation, growth, ownership and delivery come from{" "}
              <code>{String(stock["Fundamentals Source"] ?? "a third-party source")}</code>, which is not
              under our control. Those panels are omitted rather than shown blank. Price, momentum and
              everything else on this page is computed from our own data and is unaffected.
              {stock["Fundamentals Reason"] ? (
                <><br /><span className="notice-reason">Reason: {String(stock["Fundamentals Reason"])}</span></>
              ) : null}
            </span>
          </div>
        )}

        <div className="statrow">
          {kpis.map((k) => (
            <div className="stat" key={k.label}>
              <div className="stat-label">{k.label}</div>
              <div className={`stat-value num ${sign(k.cell as Cell)}`}>{k.value}</div>
              <div className="stat-sub">{k.sub}</div>
            </div>
          ))}
        </div>

        <div className="grid2">
          <div className="panel">
            <div className="panel-head" style={{ flexWrap: "wrap", rowGap: 8 }}>
              <span className="panel-title">Price structure</span>
              <span className="panel-note">Adjusted Close</span>
              <div className="spacer" />
              <div className="segmented">
                {RANGES.map((r) => (
                  <button key={r.label} aria-pressed={days === r.days} onClick={() => setDays(r.days)}>{r.label}</button>
                ))}
              </div>
            </div>

            <div className="panel-head" style={{ background: "transparent", borderBottom: "1px solid var(--line)", flexWrap: "wrap", rowGap: 8 }}>
              <span className="panel-note">Overlays</span>
              <div className="segmented">
                {spans.map((s) => (
                  <button
                    key={s}
                    aria-pressed={activeEmas.includes(s)}
                    onClick={() => setActiveEmas((cur) => cur.includes(s) ? cur.filter((x) => x !== s) : [...cur, s].sort((a, b) => a - b))}
                  >
                    {s} EMA
                  </button>
                ))}
              </div>
              <div className="segmented">
                <button aria-pressed={showVolume} onClick={() => setShowVolume((v) => !v)}>Volume</button>
                {chart.benchmark && <button aria-pressed={showRs} onClick={() => setShowRs((v) => !v)}>RS</button>}
              </div>
            </div>

            <div className="chartbox">
              {rows.length ? (
                <PriceChart
                  rows={rows}
                  emaSpans={spans}
                  benchmark={chart.benchmark ?? null}
                  activeEmas={activeEmas.filter((s) => spans.includes(s))}
                  showVolume={showVolume}
                  showRs={showRs}
                />
              ) : (
                <div style={{ height: 330, display: "grid", placeItems: "center" }}>
                  <div className="skel" style={{ width: "82%", height: 200, borderRadius: 8 }} />
                </div>
              )}
            </div>

            {/* Direct identity for every line: the overlays are never told apart
                by colour alone. */}
            <div className="chartlegend">
              <span className="legend-item"><span className="legend-swatch" style={{ background: "var(--ink)" }} />Adj Close</span>
              {activeEmas.filter((s) => spans.includes(s)).map((s) => (
                <span className="legend-item" key={s}>
                  <span className="legend-swatch" style={{ background: EMA_COLOURS[s] }} />{s} EMA
                </span>
              ))}
              {showVolume && <span className="legend-item"><span className="legend-swatch" style={{ background: "var(--ink-faint)" }} />Volume</span>}
              {chart.benchmark && showRs && (
                <span className="legend-item">
                  <span className="legend-swatch" style={{ background: "var(--rs)" }} />
                  RS vs {chart.benchmark === "^NSEI" ? "NIFTY 50" : chart.benchmark}
                </span>
              )}
              {!chart.benchmark && <span className="legend-item faint">RS unavailable — no benchmark in this dataset</span>}
            </div>
            {(valuation.length > 0 || growth.length > 0) && (
              <div className="sidebyside">
                    <Specs title="Size" note="third-party" rows={valuation} />
                <div className="panel">
                  <div className="panel-head"><span className="panel-title">Valuation ratios</span><span className="panel-note">withheld</span></div>
                  <div style={{ padding: "12px 14px", fontSize: 12.5, color: "var(--ink-secondary)", lineHeight: 1.55 }}>
                    P/E, price-to-book and dividend yield are not shown. The source computes them
                    against a <strong>stale price</strong> while publishing a current close, so they
                    understate P/E by up to 38% — and by most on the stocks that have risen most,
                    which is precisely what this screener ranks highest. Quarterly growth and ROE
                    do not reconcile either. They return when the source recomputes them.
                  </div>
                </div>
              </div>
            )}
          </div>

          <div style={{ display: "grid", gap: 12 }}>
            <div className="panel">
              <div className="panel-head"><span className="panel-title">Key levels</span></div>
              <div className="levels">
                {[
                  ["52W high", rupee(stock?.["52W High"] ?? null)],
                  ["From high", pct(stock?.["% From 52W High"] ?? null)],
                  ["EMA 50", pct(stock?.["% EMA 50"] ?? null)],
                  ["EMA 100", pct(stock?.["% EMA 100"] ?? null)],
                  ["EMA 200", pct(stock?.["% EMA 200"] ?? null)],
                  ["200 DMA", pct(stock?.["% 200 DMA"] ?? null)],
                ].map(([label, value]) => (
                  <div className="level" key={label}>
                    <div className="level-label">{label}</div>
                    <div className="level-value num">{value}</div>
                  </div>
                ))}
              </div>
            </div>

            <div className="panel">
              <div className="panel-head"><span className="panel-title">Return profile</span><span className="panel-note">calendar horizons</span></div>
              <div className="tablewrap">
                <table className="grid">
                  <tbody>
                    {["1M Return", "3M Return", "6M Return", "9M Return", "12M Return", "3M Sharpe", "6M Sharpe", "Persistence 6M %", "Acceleration"].map((f) => (
                      <tr key={f}>
                        <td className="left muted" style={{ fontSize: 12 }}>{f.replace(" Return", "").replace(" %", "")}</td>
                        <td className={`num ${sign(stock?.[f] ?? null)}`}>{stock ? display(f, stock[f]) : "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <Specs title="Ownership & participation" rows={participation} />

            {peers.length > 0 && (
              <div className="panel">
                <div className="panel-head"><span className="panel-title">Industry peers</span><span className="panel-note">{String(stock?.Industry ?? "")}</span></div>
                <div className="tablewrap">
                  <table className="grid">
                    <thead><tr><th className="left">Symbol</th><th>Score</th><th>3M</th></tr></thead>
                    <tbody>
                      {peers.map((p) => {
                        const self = String(p.Symbol) === symbol;
                        return (
                          <tr key={String(p.Symbol)} style={self ? { background: "var(--accent-soft)" } : undefined}>
                            <td className="left">
                              <a className="sym" href={`/stocks/${encodeURIComponent(String(p.Symbol))}`}>{String(p.Symbol)}</a>
                            </td>
                            <td className={`num ${sign(p["Momentum Score"])}`}>{num(p["Momentum Score"], 2)}</td>
                            <td className={`num ${sign(p["3M Return"])}`}>{pct(p["3M Return"])}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
            <Specs title="Data" rows={provenance} />
          </div>
        </div>

        <p className="faint" style={{ fontSize: 11.5, marginTop: 14 }}>
          Adjusted Close and Volume only — the canonical dataset carries no High/Low, so this is a line chart rather than candles.
          EMAs are computed on full history and then windowed, so a short view still shows the true long EMA.
          {stock && fundamentalsOk && (
            <>
              {" "}Valuation, growth, ownership and delivery via{" "}
              <code>{String(stock["Fundamentals Source"])}</code>
              {stock["Fundamentals As Of"] ? ` as of ${String(stock["Fundamentals As Of"]).slice(0, 10)}` : ""}.
            </>
          )}
        </p>
      </main>
    </>
  );
}
