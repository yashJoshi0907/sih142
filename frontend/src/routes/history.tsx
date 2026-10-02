import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";

import { OrbitBackdrop } from "@/components/chrome/OrbitBackdrop";
import { ConsoleBar } from "@/components/chrome/ConsoleBar";
import { ConsoleFooter } from "@/components/chrome/ConsoleFooter";
import { Reveal } from "@/components/motion/Reveal";
import {
  downloadUrl,
  fetchHistory,
  fetchMetrics,
  type HistoryEntry,
  type JobMetrics,
} from "@/lib/sr-api";

export const Route = createFileRoute("/history")({
  head: () => ({ meta: [{ title: "Job History — ARGUS" }] }),
  component: HistoryPage,
});

const STATUS_META: Record<string, { label: string; dot: string; text: string }> = {
  done: { label: "Done", dot: "bg-primary", text: "text-primary" },
  running: { label: "Running", dot: "bg-amber-signal animate-pulse", text: "text-amber-signal" },
  failed: { label: "Failed", dot: "bg-signal-red", text: "text-signal-red" },
};

const FALLBACK_STATUS = {
  label: "Queued",
  dot: "bg-outline",
  text: "text-muted-foreground",
} as const;

function HistoryPage() {
  const [jobs, setJobs] = useState<HistoryEntry[] | null>(null);
  const [down, setDown] = useState(false);
  const [metricsFor, setMetricsFor] = useState<Record<number, JobMetrics | null>>({});
  const [openRow, setOpenRow] = useState<number | null>(null);

  const load = () => {
    setDown(false);
    fetchHistory(80)
      .then(setJobs)
      .catch(() => {
        setJobs([]);
        setDown(true);
      });
  };

  useEffect(load, []);

  const toggleRow = (id: number) => {
    setOpenRow((cur) => {
      const next = cur === id ? null : id;
      if (next !== null && !(id in metricsFor)) {
        fetchMetrics(id)
          .then((m) => setMetricsFor((prev) => ({ ...prev, [id]: m })))
          .catch(() => setMetricsFor((prev) => ({ ...prev, [id]: null })));
      }
      return next;
    });
  };

  const formatTime = (iso: string | null) => {
    if (!iso) return "—";
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    return d.toLocaleString(undefined, {
      month: "short",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <div className="relative min-h-screen text-on-surface">
      <OrbitBackdrop />
      <ConsoleBar />

      <main className="mx-auto max-w-[1280px] px-5 pb-16 pt-28 sm:px-8">
        <Reveal from="up">
          <div className="mb-10">
            <span className="font-label-caps text-[10px] font-bold uppercase tracking-[0.3em] text-primary">
              Job ledger
            </span>
            <h1 className="mt-3 font-headline-lg text-4xl font-semibold tracking-tight text-foreground md:text-5xl">
              History
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-relaxed text-on-surface-variant">
              Every job the console has run, newest first, with its metrics as committed by the
              pipeline. Expand a row for the numbers behind it.
            </p>
          </div>
        </Reveal>

        {down && (
          <div className="mb-6 flex items-center gap-3 rounded-xl border border-amber-signal/30 bg-amber-signal/[0.06] px-5 py-4">
            <span className="material-symbols-outlined text-[18px] text-amber-signal">
              cloud_off
            </span>
            <p className="text-sm text-on-surface-variant">
              Processing backend unreachable — showing nothing rather than stale history.{" "}
              <button
                onClick={load}
                className="font-semibold text-amber-signal underline underline-offset-4"
              >
                Retry
              </button>
            </p>
          </div>
        )}

        {jobs && jobs.length === 0 && !down && (
          <Reveal from="up" delay={80}>
            <div className="flex flex-col items-center gap-4 rounded-2xl border border-outline-variant/70 bg-surface/60 px-6 py-20 text-center">
              <span className="material-symbols-outlined animate-drift text-[40px] text-outline">
                satellite_alt
              </span>
              <p className="max-w-sm text-sm leading-relaxed text-on-surface-variant">
                No jobs in the ledger yet. Run the sample tile from the console and it will land
                here with its metrics.
              </p>
              <Link
                to="/process"
                className="mt-2 inline-flex items-center gap-2 rounded-lg bg-primary px-5 py-3 font-label-caps text-[10px] font-bold uppercase tracking-[0.18em] text-on-primary transition-shadow hover:shadow-[0_0_32px_-8px_rgba(53,224,161,0.6)]"
              >
                Open the console
                <span className="material-symbols-outlined text-[15px]">arrow_forward</span>
              </Link>
            </div>
          </Reveal>
        )}

        {jobs && jobs.length > 0 && (
          <Reveal from="up" delay={60}>
            <div className="overflow-hidden rounded-2xl border border-outline-variant/80 bg-surface/60 backdrop-blur-sm">
              {/* Head */}
              <div className="hidden grid-cols-[64px_1fr_130px_150px_120px_44px] gap-3 border-b border-outline-variant/70 bg-surface-low/60 px-5 py-3 font-label-caps text-[9px] font-bold uppercase tracking-[0.18em] text-muted-foreground md:grid">
                <span>Job</span>
                <span>Tile</span>
                <span>Model</span>
                <span>Submitted</span>
                <span>Status</span>
                <span />
              </div>

              {jobs.map((j, i) => {
                const meta = STATUS_META[j.status] ?? FALLBACK_STATUS;
                const open = openRow === j.job_id;
                const m = metricsFor[j.job_id];
                return (
                  <div
                    key={j.job_id}
                    className={`border-b border-outline-variant/40 transition-colors last:border-b-0 ${
                      open ? "bg-surface-low/50" : "hover:bg-surface-low/30"
                    }`}
                  >
                    <button
                      type="button"
                      onClick={() => toggleRow(j.job_id)}
                      className="grid w-full grid-cols-[44px_1fr_28px] gap-3 px-5 py-4 text-left md:grid-cols-[64px_1fr_130px_150px_120px_44px] md:items-center"
                      style={{ animationDelay: `${Math.min(i, 12) * 30}ms` }}
                    >
                      <span className="font-telemetry-data text-sm font-semibold text-foreground">
                        #{String(j.job_id).padStart(3, "0")}
                      </span>
                      <span className="min-w-0">
                        <span className="block truncate text-sm text-foreground">{j.filename}</span>
                        <span className="mt-0.5 block font-label-caps text-[9px] uppercase tracking-[0.14em] text-muted-foreground md:hidden">
                          {j.model} · {formatTime(j.created_at)}
                        </span>
                      </span>
                      <span className="hidden font-label-caps text-[10px] uppercase tracking-[0.1em] text-on-surface-variant md:block">
                        {j.model}
                      </span>
                      <span className="hidden font-label-caps text-[10px] tracking-[0.06em] text-muted-foreground md:block">
                        {formatTime(j.created_at)}
                      </span>
                      <span
                        className={`flex items-center gap-2 font-label-caps text-[10px] font-bold uppercase tracking-[0.14em] ${meta.text}`}
                      >
                        <span className={`h-1.5 w-1.5 rounded-full ${meta.dot}`} />
                        {meta.label}
                        <span
                          className={`material-symbols-outlined ml-auto hidden text-[16px] text-muted-foreground transition-transform md:block ${
                            open ? "rotate-180" : ""
                          }`}
                        >
                          expand_more
                        </span>
                      </span>
                      <span className="hidden justify-end md:flex">
                        <span
                          className={`material-symbols-outlined text-[16px] text-muted-foreground transition-transform ${
                            open ? "rotate-180" : ""
                          }`}
                        >
                          expand_more
                        </span>
                      </span>
                    </button>

                    {open && (
                      <div className="grid gap-4 border-t border-outline-variant/40 bg-surface-dim/40 px-5 py-5 sm:grid-cols-2 md:grid-cols-4">
                        <Detail
                          label="PSNR vs bicubic"
                          value={
                            m?.psnr_vs_bicubic_db != null
                              ? `${m.psnr_vs_bicubic_db.toFixed(2)} dB`
                              : "—"
                          }
                        />
                        <Detail
                          label="SSIM"
                          value={m?.ssim_vs_bicubic != null ? m.ssim_vs_bicubic.toFixed(4) : "—"}
                        />
                        <Detail
                          label="Inference"
                          value={
                            m?.inference_time_sec != null
                              ? `${m.inference_time_sec.toFixed(1)} s`
                              : "—"
                          }
                        />
                        <Detail
                          label="Output GSD"
                          value={
                            m?.output_resolution_m != null ? `${m.output_resolution_m} m` : "—"
                          }
                        />
                        <div className="sm:col-span-2 md:col-span-4">
                          {j.status === "done" ? (
                            <a
                              href={downloadUrl(j.job_id)}
                              className="inline-flex items-center gap-2 rounded-lg border border-primary/40 bg-primary/10 px-4 py-2 font-label-caps text-[10px] font-bold uppercase tracking-[0.16em] text-primary transition-colors hover:bg-primary/20"
                            >
                              <span className="material-symbols-outlined text-[15px]">
                                download
                              </span>
                              Enhanced GeoTIFF
                            </a>
                          ) : (
                            <span className="font-label-caps text-[10px] uppercase tracking-[0.16em] text-muted-foreground">
                              {j.status === "failed"
                                ? "No product — job failed"
                                : "No product yet — job not complete"}
                            </span>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </Reveal>
        )}

        {!jobs && !down && (
          <div className="flex items-center justify-center py-24">
            <span
              className="h-8 w-8 rounded-full border-2 border-outline-variant border-t-primary"
              style={{ animation: "spin 0.9s linear infinite" }}
            />
          </div>
        )}
      </main>

      <ConsoleFooter />
    </div>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-outline-variant/60 bg-surface/60 px-4 py-3">
      <div className="font-telemetry-data text-base font-semibold text-foreground">{value}</div>
      <div className="mt-0.5 font-label-caps text-[9px] uppercase tracking-[0.16em] text-muted-foreground">
        {label}
      </div>
    </div>
  );
}
