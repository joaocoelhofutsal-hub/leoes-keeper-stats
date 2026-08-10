import { cn } from "@/lib/utils";

export const slug = (s) => (s || "").replace(/\s+/g, "-").toLowerCase();

export function PanelBlock({ title, selected, children }) {
  return (
    <div>
      <div className="flex items-start justify-between gap-2 mb-1">
        <span className="font-cond font-extrabold uppercase text-[#0C3B1E] text-base leading-none shrink-0">{title}</span>
        <span className="text-[#0F3B43] text-[11px] font-semibold text-right leading-tight max-w-[58%]">{selected || "Sem seleção"}</span>
      </div>
      <div className="rounded-xl p-2" style={{ background: "linear-gradient(160deg,#0C3B1E,#0F3B43)" }}>
        {children}
      </div>
    </div>
  );
}

export function Tile({ active, onClick, children, testid, className }) {
  return (
    <button
      type="button"
      data-testid={testid}
      onClick={onClick}
      className={cn(
        "w-full min-h-[36px] rounded-lg text-[11px] font-semibold px-2 py-1 leading-tight text-center transition-colors flex items-center justify-center break-words",
        active ? "bg-[#F4C430] text-[#0C3B1E]" : "text-white hover:brightness-125",
        className
      )}
      style={active ? undefined : { background: "rgba(255,255,255,0.10)", boxShadow: "inset 0 0 0 1px rgba(255,255,255,0.18)" }}
    >
      {children}
    </button>
  );
}

export function TileGrid({ options, value, onChange, multi = false, cols = "grid-cols-2", testid, labelMap }) {
  const isSel = (o) => (multi ? (value || []).includes(o) : value === o);
  const toggle = (o) => {
    if (multi) {
      const cur = value || [];
      onChange(cur.includes(o) ? cur.filter((x) => x !== o) : [...cur, o]);
    } else {
      onChange(value === o ? "" : o);
    }
  };
  return (
    <div className={cn("grid gap-1.5", cols)}>
      {options.map((o) => (
        <Tile key={o} testid={`${testid}-${slug(o)}`} active={isSel(o)} onClick={() => toggle(o)}>
          {labelMap ? (labelMap[o] || o) : o}
        </Tile>
      ))}
    </div>
  );
}
