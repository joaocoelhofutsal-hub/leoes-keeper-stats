import { ZONAS, ZONA_SHORT, DISTANCIAS, GOAL_GRID, GOAL_SHORT } from "@/lib/constants";

const slug = (s) => (s || "").replace(/\s+/g, "-").toLowerCase();

export function CourtZone({ value, onChange }) {
  return (
    <div className="relative rounded-lg overflow-hidden h-[118px]">
      <div className="grid grid-cols-5 h-full gap-1">
        {ZONAS.map((z, i) => (
          <button type="button" key={z} data-testid={`court-zone-${i}`}
            onClick={() => onChange(value === z ? "" : z)}
            className="relative rounded-md flex items-center justify-center transition-colors"
            style={{ background: value === z ? "#F4C430" : (i % 2 ? "rgba(255,255,255,0.07)" : "rgba(255,255,255,0.15)") }}>
            <span className="text-[10px] font-bold whitespace-nowrap"
              style={{ writingMode: "vertical-rl", transform: "rotate(180deg)", color: value === z ? "#0C3B1E" : "#fff" }}>
              {ZONA_SHORT[i]}
            </span>
          </button>
        ))}
      </div>
      <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
        <div className="w-9 h-9 rounded-full border border-white/50" />
      </div>
      <div className="pointer-events-none absolute top-1 bottom-1 left-1/2 w-px bg-white/40" />
      <div className="pointer-events-none absolute left-0 top-1/2 -translate-y-1/2 w-1.5 h-8 bg-white/70 rounded-r" />
      <div className="pointer-events-none absolute right-0 top-1/2 -translate-y-1/2 w-1.5 h-8 bg-white/70 rounded-l" />
    </div>
  );
}

export function CourtDistance({ value, onChange }) {
  return (
    <div className="relative rounded-lg overflow-hidden">
      <div className="text-center text-[9px] uppercase tracking-widest text-[#0C3B1E] bg-white/80 py-0.5 font-bold">Baliza</div>
      <div className="flex flex-col gap-1 p-1">
        {DISTANCIAS.map((d, i) => (
          <button type="button" key={d} data-testid={`court-dist-${i}`}
            onClick={() => onChange(value === d ? "" : d)}
            className="rounded-md py-1.5 text-[11px] font-bold transition-colors"
            style={{ background: value === d ? "#F4C430" : "rgba(255,255,255,0.10)", color: value === d ? "#0C3B1E" : "#fff" }}>
            {d}
          </button>
        ))}
      </div>
      <div className="pointer-events-none absolute top-6 bottom-1 left-1/2 w-px bg-white/25" />
    </div>
  );
}

export function GoalTarget({ value, onChange }) {
  return (
    <div className="mx-auto w-full max-w-[330px] rounded-md p-1.5" style={{ background: "#c0392b" }}>
      <div className="rounded-sm p-1" style={{
        background: "#2b5aa0",
        backgroundImage: "repeating-linear-gradient(0deg,rgba(255,255,255,0.22) 0 1px,transparent 1px 13px),repeating-linear-gradient(90deg,rgba(255,255,255,0.22) 0 1px,transparent 1px 13px)",
      }}>
        {GOAL_GRID.map((row, ri) => (
          <div key={ri} className="grid grid-cols-3 gap-1 mb-1 last:mb-0">
            {row.map((cell) => (
              <button type="button" key={cell} data-testid={`goal-${slug(cell)}`}
                onClick={() => onChange(value === cell ? "" : cell)}
                className="aspect-[5/2] rounded-sm text-[9px] font-bold leading-tight transition-colors flex items-center justify-center px-0.5"
                style={{ background: value === cell ? "#F4C430" : "rgba(255,255,255,0.14)", color: value === cell ? "#0C3B1E" : "#fff" }}>
                {GOAL_SHORT[cell] || cell}
              </button>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
