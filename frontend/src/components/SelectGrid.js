import { cn } from "@/lib/utils";

export function SelectGrid({ label, options, value, onChange, multi = false, cols = "grid-cols-2 md:grid-cols-4", testid }) {
  const isSelected = (opt) => (multi ? (value || []).includes(opt) : value === opt);
  const toggle = (opt) => {
    if (multi) {
      const cur = value || [];
      onChange(cur.includes(opt) ? cur.filter((x) => x !== opt) : [...cur, opt]);
    } else {
      onChange(value === opt ? "" : opt);
    }
  };
  return (
    <div className="space-y-2" data-testid={testid}>
      <div className="text-xs font-bold uppercase tracking-[0.15em] text-[#0F3B43]">{label}</div>
      <div className={cn("grid gap-2", cols)}>
        {options.map((opt) => (
          <button
            type="button"
            key={opt}
            data-testid={`${testid}-${opt.replace(/\s+/g, "-").toLowerCase()}`}
            onClick={() => toggle(opt)}
            className={cn(
              "select-tile min-h-[56px] rounded-xl border-2 px-3 py-2 text-sm font-semibold leading-tight text-center",
              isSelected(opt)
                ? "bg-[#0C3B1E] text-white border-[#0C3B1E] shadow-md"
                : "bg-white text-[#0C3B1E] border-gray-200 hover:border-[#0C3B1E]"
            )}
          >
            {opt}
          </button>
        ))}
      </div>
    </div>
  );
}
