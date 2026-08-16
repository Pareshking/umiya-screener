"use client";

export function ChartRange({ value, onChange }: { value: number; onChange: (days: number) => void }) {
  return <div className="chart-range" role="group" aria-label="Chart range">
    {[63,126,252].map(days => <button key={days} className={value===days ? "active" : ""} onClick={() => onChange(days)}>{days===63 ? "3M" : days===126 ? "6M" : "1Y"}</button>)}
  </div>;
}
