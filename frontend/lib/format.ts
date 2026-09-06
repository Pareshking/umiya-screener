export type Cell = string | number | boolean | null;
export type Row = Record<string, Cell>;

const DASH = "—";

export function num(value: Cell, digits = 2): string {
  if (value === null || value === undefined || value === "") return DASH;
  const n = Number(value);
  if (!Number.isFinite(n)) return DASH;
  return n.toLocaleString("en-IN", { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

export function pct(value: Cell, digits = 1): string {
  if (value === null || value === undefined || value === "") return DASH;
  const n = Number(value);
  if (!Number.isFinite(n)) return DASH;
  return `${n > 0 ? "+" : ""}${n.toFixed(digits)}%`;
}

export function rupee(value: Cell): string {
  if (value === null || value === undefined || value === "") return DASH;
  const n = Number(value);
  if (!Number.isFinite(n)) return DASH;
  return `₹${n.toLocaleString("en-IN", { maximumFractionDigits: n < 100 ? 2 : 0 })}`;
}

/** Sign class for a numeric cell. Returns "" for non-numeric or zero. */
export function sign(value: Cell): string {
  const n = Number(value);
  if (!Number.isFinite(n) || n === 0) return "";
  return n > 0 ? "pos" : "neg";
}

/** How a screener column is rendered. Display rules live here alone so the
 *  table and the stock page cannot drift apart. */
export function display(field: string, value: Cell): string {
  if (value === null || value === undefined) return DASH;
  if (field === "CMP") return rupee(value);
  if (field === "Volume Ratio") return `${num(value, 2)}×`;
  if (field === "Rank") return String(value);
  if (field === "Score Percentile") return String(Math.round(Number(value)));
  if (
    field.includes("Return") ||
    field.includes("EMA") ||
    field === "% From 52W High" ||
    field === "% 200 DMA" ||
    field === "Max DD 12M" ||
    field === "Persistence 6M %"
  ) {
    return pct(value);
  }
  if (
    field.includes("Sharpe") ||
    field === "Momentum Score" ||
    field === "Acceleration" ||
    field === "Industry Relative"
  ) {
    return num(value, 2);
  }
  if (typeof value === "number") return num(value, 2);
  return String(value);
}

/** Columns whose sign should be coloured. Sign colour is reserved for values
 *  where up/down actually means better/worse — never for identifiers. */
export function isSigned(field: string): boolean {
  // Max drawdown is negative by definition, so colouring it red on every row
  // carries no information — it would just tint the column.
  if (field === "Max DD 12M") return false;
  return (
    field.includes("Return") ||
    field.includes("EMA") ||
    field === "% 200 DMA" ||
    field === "% From 52W High" ||
    field === "Momentum Score" ||
    field === "Acceleration" ||
    field === "Industry Relative" ||
    field.includes("Sharpe")
  );
}

export function isNumericField(field: string): boolean {
  return !["Index", "Industry", "Symbol", "Company Name"].includes(field);
}
