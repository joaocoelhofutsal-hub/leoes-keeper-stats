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
    <div className="space-y-1" data-testid={testid}>
      <div className="text-[11px] font-bold uppercase tracking-[0.12em] text-[#0F3B43]">{label}</div>
      <div className={cn("grid gap-1.5", cols)}>
        {options.map((opt) => (
          <button
            type="button"
            key={opt}
            data-testid={`${testid}-${opt.replace(/\s+/g, "-").toLowerCase()}`}
            onClick={() => toggle(opt)}
            className={cn(
              "select-tile min-h-[34px] rounded-md border px-1.5 py-1 text-[11px] sm:text-xs font-semibold leading-tight text-center break-words",
              isSelected(opt)
                ? "bg-[#0C3B1E] text-white border-[#0C3B1E] shadow-sm"
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
