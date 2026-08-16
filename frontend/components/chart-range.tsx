"use client";

export function ChartRange({ value, onChange }: { value: number; onChange: (days: number) => void }) {
  return <div className="chart-range" role="group" aria-label="Chart range" style={{display:"flex",gap:4,marginLeft:"auto"}}>
    {[63,126,252].map(days => <button key={days} className={value===days ? "active" : ""} onClick={() => onChange(days)} style={{border:"1px solid #e6eaf0",background:value===days?"#eef2ff":"#fff",color:value===days?"#4338ca":"#667085",borderRadius:6,padding:"5px 8px",fontSize:9,fontWeight:700}}>{days===63 ? "3M" : days===126 ? "6M" : "1Y"}</button>)}
  </div>;
}
