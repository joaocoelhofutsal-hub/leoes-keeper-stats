import { cn } from "@/lib/utils";
import { ZONAS, ZONA_SHORT, DISTANCIAS, GOAL_GRID } from "@/lib/constants";

const slug = (s) => s.replace(/\s+/g, "-").toLowerCase();

export function CourtZone({ value, onChange }) {
  return (
    <div className="space-y-1.5">
      <div className="text-xs font-bold uppercase tracking-[0.15em] text-[#0F3B43]">Zona (campo)</div>
      <div className="relative rounded-lg overflow-hidden border-2 border-[#0C3B1E]/40" style={{ background: "#1c7a44" }}>
        <div className="absolute left-1/2 top-0 bottom-0 w-px bg-white/50" />
        <div className="grid grid-cols-5 h-20">
          {ZONAS.map((z, i) => (
            <button type="button" key={z} data-testid={`court-zone-${i}`}
              onClick={() => onChange(value === z ? "" : z)}
              className={cn("border-r border-white/40 last:border-r-0 text-white text-[10px] font-bold flex items-end justify-center pb-1 transition-colors",
                value === z ? "bg-[#0C3B1E]/80" : "hover:bg-white/15")}>
              {ZONA_SHORT[i]}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

export function CourtDistance({ value, onChange }) {
  return (
    <div className="space-y-1.5">
      <div className="text-xs font-bold uppercase tracking-[0.15em] text-[#0F3B43]">Distância bola-baliza</div>
      <div className="rounded-lg overflow-hidden border-2 border-[#0C3B1E]/40" style={{ background: "#1c7a44" }}>
        <div className="text-center text-[9px] uppercase tracking-widest text-white bg-[#0C3B1E] py-0.5">Baliza</div>
        {DISTANCIAS.map((d, i) => (
          <button type="button" key={d} data-testid={`court-dist-${i}`}
            onClick={() => onChange(value === d ? "" : d)}
            className={cn("w-full border-b border-white/30 last:border-b-0 text-white text-[11px] font-bold py-1.5 transition-colors",
              value === d ? "bg-[#0C3B1E]/80" : "hover:bg-white/15")}>
            {d}
          </button>
        ))}
      </div>
    </div>
  );
}

export function GoalTarget({ value, onChange }) {
  return (
    <div className="space-y-1.5">
      <div className="text-xs font-bold uppercase tracking-[0.15em] text-[#0F3B43]">Tipo de finalização (baliza)</div>
      <div className="mx-auto max-w-[320px]">
        <div className="border-[3px] border-[#0C3B1E] border-b-0 bg-white/60"
          style={{ backgroundImage: "repeating-linear-gradient(90deg,#e5e7eb 0 6px,transparent 6px 12px)" }}>
          {GOAL_GRID.map((row, ri) => (
            <div key={ri} className="grid grid-cols-3">
              {row.map((cell) => (
                <button type="button" key={cell} data-testid={`goal-${slug(cell)}`}
                  onClick={() => onChange(value === cell ? "" : cell)}
                  className={cn("aspect-[5/3] border border-[#0C3B1E]/30 text-[9px] font-semibold p-1 leading-tight transition-colors",
                    value === cell ? "bg-[#0C3B1E] text-white" : "bg-white/70 text-[#0C3B1E] hover:bg-[#0C3B1E]/10")}>
                  {cell}
                </button>
              ))}
            </div>
          ))}
        </div>
        <div className="h-1.5 bg-[#0C3B1E]" />
      </div>
      <button type="button" data-testid="goal-tornozelos"
        onClick={() => onChange(value === "Tornozelos do GR" ? "" : "Tornozelos do GR")}
        className={cn("w-full mt-1 min-h-[40px] rounded-lg border-2 text-[11px] sm:text-sm font-semibold transition-colors",
          value === "Tornozelos do GR" ? "bg-[#0C3B1E] text-white border-[#0C3B1E]" : "bg-white text-[#0C3B1E] border-gray-200 hover:border-[#0C3B1E]")}>
        Tornozelos do GR
      </button>
    </div>
  );
}
