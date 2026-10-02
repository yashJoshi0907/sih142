const STATS = [
  { value: "×4", label: "Upscale factor" },
  { value: "2.5 m", label: "Output GSD" },
  { value: "290 km", label: "S-2 swath" },
  { value: "13", label: "Spectral bands" },
  { value: "5 d", label: "Revisit" },
  { value: "CPU", label: "Runs without GPU" },
] as const;

/** The mission constants, as one hairline-divided strip. */
export function StatRail() {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 border-y border-outline-variant/60">
      {STATS.map((s, i) => (
        <div
          key={s.label}
          className={`px-5 py-5 ${
            i % 2 === 1 ? "border-l border-outline-variant/40" : ""
          } sm:border-l sm:border-outline-variant/40 lg:[&:nth-child(1)]:border-l-0`}
        >
          <div className="font-telemetry-data text-xl font-semibold text-foreground">{s.value}</div>
          <div className="mt-1 font-label-caps text-[9px] uppercase tracking-[0.18em] text-muted-foreground">
            {s.label}
          </div>
        </div>
      ))}
    </div>
  );
}
