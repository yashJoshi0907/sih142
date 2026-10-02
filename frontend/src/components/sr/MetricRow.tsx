interface Metric {
  label: string;
  value: string;
  tone?: "green" | "amber" | "plain";
}

/**
 * The post-run numbers, as one row of bordered chips. Values arrive
 * preformatted: the caller decides what "—" means for its data.
 */
export function MetricRow({ metrics }: { metrics: Metric[] }) {
  return (
    <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-4">
      {metrics.map((m, i) => (
        <div
          key={m.label}
          className="rounded-lg border border-outline-variant/80 bg-surface/70 px-4 py-3"
          style={{ animationDelay: `${i * 60}ms` }}
        >
          <div
            className={`font-telemetry-data text-lg font-semibold ${
              m.tone === "green"
                ? "text-primary"
                : m.tone === "amber"
                  ? "text-amber-signal"
                  : "text-foreground"
            }`}
          >
            {m.value}
          </div>
          <div className="mt-0.5 font-label-caps text-[9px] uppercase tracking-[0.16em] text-muted-foreground">
            {m.label}
          </div>
        </div>
      ))}
    </div>
  );
}
