"use client";

import { useEffect, useMemo, useRef, useState } from "react";

/* A price chart drawn as inline SVG.

   Deliberately not a charting library: the whole payload is a few hundred
   points of one series plus overlays, and the interaction we need is a
   crosshair readout — pulling in a bundle for that costs more than it returns.

   The canonical dataset is Adjusted Close + Volume, with no High/Low, so this
   is a line chart rather than candles. Drawing candles would mean synthesising
   an open from the previous close, which produces bodies spanning close to
   close: that is not what a candle means, and it would be a picture of data
   the pipeline does not have. */

export type ChartPoint = {
  date: string;
  adj_close: number | null;
  volume: number | null;
  rs?: number | null;
  [key: string]: string | number | null | undefined;
};

export const EMA_COLOURS: Record<number, string> = {
  20: "var(--ema-20)",
  50: "var(--ema-50)",
  100: "var(--ema-100)",
  200: "var(--ema-200)",
};

type Props = {
  rows: ChartPoint[];
  emaSpans: number[];
  benchmark: string | null;
  activeEmas: number[];
  showVolume: boolean;
  showRs: boolean;
};

const PAD = { top: 12, right: 58, bottom: 20, left: 8 };

function niceTicks(lo: number, hi: number, count = 5): number[] {
  if (!Number.isFinite(lo) || !Number.isFinite(hi) || lo === hi) return [lo];
  const raw = (hi - lo) / count;
  const mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const norm = raw / mag;
  const step = (norm >= 5 ? 10 : norm >= 2 ? 5 : norm >= 1 ? 2 : 1) * mag;
  const out: number[] = [];
  for (let v = Math.ceil(lo / step) * step; v <= hi; v += step) out.push(v);
  return out;
}

export default function PriceChart({ rows, emaSpans, benchmark, activeEmas, showVolume, showRs }: Props) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(900);
  const [hover, setHover] = useState<number | null>(null);

  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => setWidth(entries[0].contentRect.width));
    ro.observe(el);
    setWidth(el.getBoundingClientRect().width);
    return () => ro.disconnect();
  }, []);

  const hasRs = showRs && rows.some((r) => r.rs != null);
  const priceH = 300;
  const volH = showVolume ? 56 : 0;
  const rsH = hasRs ? 78 : 0;
  const height = PAD.top + priceH + volH + rsH + PAD.bottom;

  const geom = useMemo(() => {
    const pts = rows.filter((r) => r.adj_close != null);
    if (pts.length < 2 || width < 80) return null;

    const innerW = Math.max(10, width - PAD.left - PAD.right);
    const x = (i: number) => PAD.left + (i / (pts.length - 1)) * innerW;

    // The price scale must contain every visible overlay, or a 200 EMA far
    // below a recent price would be clipped off the pane and silently missing.
    const visible: number[] = [];
    for (const p of pts) {
      if (p.adj_close != null) visible.push(p.adj_close);
      for (const span of activeEmas) {
        const v = p[`ema_${span}`];
        if (typeof v === "number" && Number.isFinite(v)) visible.push(v);
      }
    }
    const lo = Math.min(...visible);
    const hi = Math.max(...visible);
    const padY = (hi - lo) * 0.06 || 1;
    const yLo = lo - padY;
    const yHi = hi + padY;
    const y = (v: number) => PAD.top + priceH - ((v - yLo) / (yHi - yLo)) * priceH;

    const line = (key: string) => {
      let d = "";
      let open = false;
      pts.forEach((p, i) => {
        const v = p[key];
        if (typeof v !== "number" || !Number.isFinite(v)) { open = false; return; }
        d += `${open ? "L" : "M"}${x(i).toFixed(1)} ${y(v).toFixed(1)}`;
        open = true;
      });
      return d;
    };

    const vols = pts.map((p) => (typeof p.volume === "number" ? p.volume : 0));
    const volMax = Math.max(...vols, 1);
    const volTop = PAD.top + priceH;

    const rsVals = pts.map((p) => (typeof p.rs === "number" ? p.rs : NaN)).filter(Number.isFinite);
    const rsTop = volTop + volH;
    let rsPath = "";
    let rsLo = 0, rsHi = 0;
    if (hasRs && rsVals.length > 1) {
      rsLo = Math.min(...rsVals);
      rsHi = Math.max(...rsVals);
      const pad = (rsHi - rsLo) * 0.12 || 1;
      rsLo -= pad; rsHi += pad;
      const ry = (v: number) => rsTop + rsH - ((v - rsLo) / (rsHi - rsLo)) * rsH;
      let open = false;
      pts.forEach((p, i) => {
        const v = p.rs;
        if (typeof v !== "number" || !Number.isFinite(v)) { open = false; return; }
        rsPath += `${open ? "L" : "M"}${x(i).toFixed(1)} ${ry(v).toFixed(1)}`;
        open = true;
      });
    }
    const rsBaseY = hasRs && rsHi > rsLo ? rsTop + rsH - ((100 - rsLo) / (rsHi - rsLo)) * rsH : null;

    const first = pts[0].adj_close as number;
    const last = pts[pts.length - 1].adj_close as number;

    return {
      pts, x, y, line, vols, volMax, volTop, rsPath, rsBaseY, rsTop,
      yTicks: niceTicks(yLo, yHi, 5).filter((t) => t >= yLo && t <= yHi),
      innerW, up: last >= first,
    };
  }, [rows, width, activeEmas, hasRs, priceH, volH, rsH]);

  if (!geom) {
    return <div ref={wrapRef} style={{ height, display: "grid", placeItems: "center" }} className="muted">Not enough data to chart.</div>;
  }

  const { pts, x, y, line, vols, volMax, volTop, rsPath, rsBaseY, rsTop, yTicks, up } = geom;
  const idx = hover != null ? Math.max(0, Math.min(pts.length - 1, hover)) : null;
  const cur = idx != null ? pts[idx] : null;
  const areaTop = line("adj_close");
  const stroke = up ? "var(--up)" : "var(--down)";

  function onMove(e: React.PointerEvent<SVGSVGElement>) {
    const rect = e.currentTarget.getBoundingClientRect();
    const rel = e.clientX - rect.left - PAD.left;
    const step = (rect.width - PAD.left - PAD.right) / (pts.length - 1);
    setHover(Math.round(rel / step));
  }

  // Date labels: a handful, evenly spaced, never overlapping.
  const labelCount = Math.max(2, Math.min(6, Math.floor(width / 130)));
  const dateLabels = Array.from({ length: labelCount }, (_, k) =>
    Math.round((k / (labelCount - 1)) * (pts.length - 1)),
  );

  return (
    <div ref={wrapRef} style={{ position: "relative" }}>
      <svg
        width="100%"
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        onPointerMove={onMove}
        onPointerLeave={() => setHover(null)}
        style={{ display: "block", touchAction: "pan-y" }}
        role="img"
        aria-label={`Price history with ${activeEmas.join(", ")} EMA overlays`}
      >
        <defs>
          <linearGradient id="fill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={stroke} stopOpacity="0.13" />
            <stop offset="100%" stopColor={stroke} stopOpacity="0" />
          </linearGradient>
        </defs>

        {/* Recessive gridlines and a right-hand price scale. */}
        {yTicks.map((t) => (
          <g key={t}>
            <line x1={PAD.left} x2={width - PAD.right} y1={y(t)} y2={y(t)} stroke="var(--line)" strokeWidth="1" />
            <text x={width - PAD.right + 6} y={y(t) + 3.5} fontSize="10" fill="var(--ink-faint)" fontFamily="var(--mono)">
              {t >= 1000 ? Math.round(t).toLocaleString("en-IN") : t.toFixed(1)}
            </text>
          </g>
        ))}

        <path d={`${areaTop} L ${x(pts.length - 1)} ${PAD.top + priceH} L ${x(0)} ${PAD.top + priceH} Z`} fill="url(#fill)" />
        <path d={areaTop} fill="none" stroke={stroke} strokeWidth="1.75" strokeLinejoin="round" strokeLinecap="round" />

        {activeEmas.map((span) => (
          <path key={span} d={line(`ema_${span}`)} fill="none" stroke={EMA_COLOURS[span]} strokeWidth="1.5" strokeLinejoin="round" opacity="0.95" />
        ))}

        {showVolume && vols.map((v, i) => {
          const h = (v / volMax) * (volH - 8);
          if (h <= 0) return null;
          const prev = i > 0 ? (pts[i - 1].adj_close as number) : (pts[0].adj_close as number);
          const rising = (pts[i].adj_close as number) >= prev;
          return (
            <rect
              key={i}
              x={x(i) - Math.max(0.5, geom.innerW / pts.length / 2.4)}
              y={volTop + volH - h - 4}
              width={Math.max(1, geom.innerW / pts.length * 0.8)}
              height={h}
              fill={rising ? "var(--up)" : "var(--down)"}
              opacity="0.28"
            />
          );
        })}

        {rsPath && (
          <>
            {rsBaseY != null && (
              <line x1={PAD.left} x2={width - PAD.right} y1={rsBaseY} y2={rsBaseY} stroke="var(--line-strong)" strokeWidth="1" strokeDasharray="3 3" />
            )}
            <path d={rsPath} fill="none" stroke="var(--rs)" strokeWidth="1.6" strokeLinejoin="round" />
            <text x={PAD.left + 2} y={rsTop + 11} fontSize="9.5" fill="var(--ink-faint)" fontFamily="var(--mono)">
              RS vs {benchmark === "^NSEI" ? "NIFTY 50" : benchmark} · 100 = start
            </text>
          </>
        )}

        {dateLabels.map((i) => (
          <text key={i} x={x(i)} y={height - 6} fontSize="10" fill="var(--ink-faint)" fontFamily="var(--mono)" textAnchor={i === 0 ? "start" : i === pts.length - 1 ? "end" : "middle"}>
            {new Date(pts[i].date).toLocaleDateString("en-IN", { month: "short", year: "2-digit" })}
          </text>
        ))}

        {idx != null && cur && (
          <g pointerEvents="none">
            <line x1={x(idx)} x2={x(idx)} y1={PAD.top} y2={PAD.top + priceH + volH + rsH} stroke="var(--ink-faint)" strokeWidth="1" strokeDasharray="3 3" />
            {cur.adj_close != null && <circle cx={x(idx)} cy={y(cur.adj_close)} r="3.5" fill={stroke} stroke="#fff" strokeWidth="1.5" />}
          </g>
        )}
      </svg>

      {/* Crosshair readout. Placed over the chart rather than in a floating
          tooltip so it never covers the series being read. */}
      {cur && (
        <div style={{
          position: "absolute", top: 6, left: 10, display: "flex", gap: 12, flexWrap: "wrap",
          background: "rgba(255,255,255,.93)", border: "1px solid var(--line)", borderRadius: 6,
          padding: "5px 9px", fontSize: 11, fontFamily: "var(--mono)", pointerEvents: "none",
        }}>
          <span className="muted">{new Date(cur.date).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" })}</span>
          <span><span className="muted">C</span> {cur.adj_close != null ? Number(cur.adj_close).toFixed(2) : "—"}</span>
          {activeEmas.map((s) => {
            const v = cur[`ema_${s}`];
            return typeof v === "number" ? (
              <span key={s} style={{ color: EMA_COLOURS[s] }}>{s}E {v.toFixed(1)}</span>
            ) : null;
          })}
          {typeof cur.rs === "number" && <span style={{ color: "var(--rs)" }}>RS {cur.rs.toFixed(1)}</span>}
        </div>
      )}
    </div>
  );
}
