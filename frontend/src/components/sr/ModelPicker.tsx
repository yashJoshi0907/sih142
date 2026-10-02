import type { ModelInfo } from "@/lib/sr-api";

interface ModelPickerProps {
  models: ModelInfo[];
  value: string;
  onChange: (name: string) => void;
  disabled?: boolean;
}

/**
 * Model selection as cards rather than a dropdown: the trade-off between the
 * models (detail vs radiometric fidelity, minutes vs seconds) is the one
 * decision the operator actually makes, so it deserves the screen space.
 */
export function ModelPicker({ models, value, onChange, disabled = false }: ModelPickerProps) {
  return (
    <div className="flex flex-col gap-2.5">
      {models.map((m) => {
        const selected = m.name === value;
        return (
          <button
            key={m.name}
            type="button"
            onClick={() => onChange(m.name)}
            disabled={disabled}
            aria-pressed={selected}
            className={`rounded-xl border p-4 text-left transition-all disabled:cursor-not-allowed disabled:opacity-50 ${
              selected
                ? "border-primary/60 bg-primary/[0.07] shadow-[inset_0_0_0_1px_rgba(53,224,161,0.25)]"
                : "border-outline-variant/80 bg-surface/60 hover:border-outline"
            }`}
          >
            <div className="flex items-center justify-between gap-3">
              <span className="flex items-center gap-2.5 font-headline-sm text-[15px] font-semibold text-foreground">
                <span
                  className={`h-2 w-2 shrink-0 rounded-full ${
                    selected ? "bg-primary shadow-[0_0_8px_rgba(53,224,161,0.9)]" : "bg-outline"
                  }`}
                />
                {m.name}
              </span>
              <span
                className={`shrink-0 rounded px-2 py-0.5 font-label-caps text-[9px] font-bold uppercase tracking-[0.12em] ${
                  m.physical_bias === "Balanced"
                    ? "border border-magenta-signal/40 bg-magenta-signal/10 text-magenta-signal"
                    : "border border-primary/40 bg-primary/10 text-primary"
                }`}
              >
                {m.physical_bias}
              </span>
            </div>
            <p className="mt-2 text-[13px] leading-relaxed text-on-surface-variant">
              {m.description}
            </p>
            <div className="mt-3 flex items-center justify-between font-label-caps text-[10px] uppercase tracking-[0.12em] text-muted-foreground">
              <span>{m.paper}</span>
              <span className={selected ? "text-primary" : undefined}>
                ×{m.scale} → {m.output_res_m} m GSD
              </span>
            </div>
          </button>
        );
      })}
    </div>
  );
}
