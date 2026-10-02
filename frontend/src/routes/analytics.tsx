import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";

import { OrbitBackdrop } from "@/components/chrome/OrbitBackdrop";
import { ConsoleBar } from "@/components/chrome/ConsoleBar";
import { ConsoleFooter } from "@/components/chrome/ConsoleFooter";
import { Reveal, RevealHeading } from "@/components/motion/Reveal";
import { fetchHistory, fetchMetrics, fetchModels, type ModelInfo } from "@/lib/sr-api";

export const Route = createFileRoute("/analytics")({
  head: () => ({ meta: [{ title: "Analytics — ARGUS" }] }),
  component: AnalyticsPage,
});

interface Observation {
  jobId: number;
  model: string;
  psnr: number | null;
  ssim: number | null;
  seconds: number | null;
}

function AnalyticsPage() {
  const [obs, setObs] = useState<Observation[] | null>(null);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [down, setDown] = useState(false);

  useEffect(() => {
    fetchModels()
      .then(setModels)
      .catch(() => setModels([]));
    (async () => {
      try {
        const jobs = await fetchHistory(200);
        const withMetrics = await Promise.all(
          jobs.map(async (j) => {
            try {
              const m = await fetchMetrics(j.job_id);
              return {
                jobId: j.job_id,
                model: j.model,
                psnr: m.psnr_vs_bicubic_db,
                ssim: m.ssim_vs_bicubic,
                seconds: m.inference_time_sec,
              } satisfies Observation;
            } catch {
              return {
                jobId: j.job_id,
                model: j.model,
                psnr: null,
                ssim: null,
                seconds: null,
              } satisfies Observation;
            }
          }),
        );
        setObs(withMetrics.filter((o) => o.psnr != null || o.seconds != null));
      } catch {
        setObs([]);
        setDown(true);
      }
    })();
  }, []);

  const byModel = useMemo(() => {
    const map = new Map<string, { psnr: number[]; ssim: number[]; sec: number[] }>();
    for (const o of obs ?? []) {
      const entry = map.get(o.model) ?? { psnr: [], ssim: [], sec: [] };
      if (o.psnr != null) entry.psnr.push(o.psnr);
      if (o.ssim != null) entry.ssim.push(o.ssim);
      if (o.seconds != null) entry.sec.push(o.seconds);
      map.set(o.model, entry);
    }
    return map;
  }, [obs]);

  const maxSeconds = Math.max(1, ...(obs ?? []).map((o) => o.seconds ?? 0));

  return (
    <div className="relative min-h-screen text-on-surface">
      <OrbitBackdrop />
      <ConsoleBar />

      <main className="mx-auto max-w-[1280px] px-5 pb-16 pt-28 sm:px-8">
        <Reveal from="up">
          <div className="mb-10">
            <span className="font-label-caps text-[10px] font-bold uppercase tracking-[0.3em] text-primary">
              Validation
            </span>
            <h1 className="mt-3 font-headline-lg text-4xl font-semibold tracking-tight text-foreground md:text-5xl">
              Analytics
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-relaxed text-on-surface-variant">
              What the pipeline has actually measured, aggregated by model — plus how to read each
              number without fooling yourself.
            </p>
          </div>
        </Reveal>

        {down && (
          <div className="mb-8 flex items-center gap-3 rounded-xl border border-amber-signal/30 bg-amber-signal/[0.06] px-5 py-4">
            <span className="material-symbols-outlined text-[18px] text-amber-signal">
              cloud_off
            </span>
            <p className="text-sm text-on-surface-variant">
              Processing backend unreachable — analytics are computed from the job database, so
              there is nothing honest to show until it answers.
            </p>
          </div>
        )}

        {obs && obs.length === 0 && !down && (
          <Reveal from="up" delay={80}>
            <div className="flex flex-col items-center gap-4 rounded-2xl border border-outline-variant/70 bg-surface/60 px-6 py-20 text-center">
              <span className="material-symbols-outlined animate-drift text-[40px] text-outline">
                monitoring
              </span>
              <p className="max-w-sm text-sm leading-relaxed text-on-surface-variant">
                No scored runs yet. Every job's PSNR/SSIM lands here the moment it finishes.
              </p>
              <Link
                to="/process"
                className="mt-2 inline-flex items-center gap-2 rounded-lg bg-primary px-5 py-3 font-label-caps text-[10px] font-bold uppercase tracking-[0.18em] text-on-primary transition-shadow hover:shadow-[0_0_32px_-8px_rgba(53,224,161,0.6)]"
              >
                Run the sample tile
                <span className="material-symbols-outlined text-[15px]">arrow_forward</span>
              </Link>
            </div>
          </Reveal>
        )}

        {obs && obs.length > 0 && (
          <div className="flex flex-col gap-6">
            {/* ── Model medians ─────────────────────────────────── */}
            <Reveal from="up" delay={60}>
              <section className="panel-raised p-6">
                <SectionHead
                  icon="leaderboard"
                  title="Models, ranked by what they cost and deliver"
                />
                <div className="mt-5 grid gap-4 md:grid-cols-3">
                  {[...byModel.entries()].map(([name, agg]) => {
                    const median = (xs: number[]) =>
                      xs.length === 0
                        ? null
                        : [...xs].sort((a, b) => a - b)[Math.floor(xs.length / 2)]!;
                    const info = models.find((m) => m.name === name);
                    return (
                      <div
                        key={name}
                        className="rounded-xl border border-outline-variant/80 bg-surface/70 p-5"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-headline-sm text-[15px] font-semibold text-foreground">
                            {name}
                          </span>
                          <span className="font-label-caps text-[9px] uppercase tracking-[0.12em] text-muted-foreground">
                            n = {Math.max(agg.psnr.length, agg.sec.length)}
                          </span>
                        </div>
                        <div className="mt-4 grid grid-cols-3 gap-2">
                          <Mini
                            label="PSNR"
                            value={
                              median(agg.psnr) != null ? `${median(agg.psnr)!.toFixed(1)}` : "—"
                            }
                            unit="dB"
                          />
                          <Mini
                            label="SSIM"
                            value={median(agg.ssim) != null ? median(agg.ssim)!.toFixed(3) : "—"}
                          />
                          <Mini
                            label="Time"
                            value={median(agg.sec) != null ? `${median(agg.sec)!.toFixed(0)}` : "—"}
                            unit="s"
                          />
                        </div>
                        <div className="mt-4 border-t border-outline-variant/60 pt-3 font-label-caps text-[9px] uppercase tracking-[0.14em] text-muted-foreground">
                          {info
                            ? `×${info.scale} → ${info.output_res_m} m GSD`
                            : "registry offline"}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </section>
            </Reveal>

            {/* ── Run-by-run ────────────────────────────────────── */}
            <Reveal from="up" delay={120}>
              <section className="panel-raised p-6">
                <SectionHead icon="ssid_chart" title="Every scored run" />
                <div className="mt-5 flex flex-col gap-2.5">
                  {[...obs]
                    .sort((a, b) => b.jobId - a.jobId)
                    .slice(0, 24)
                    .map((o) => (
                      <div
                        key={o.jobId}
                        className="grid grid-cols-[64px_1fr_120px] items-center gap-4"
                      >
                        <span className="font-telemetry-data text-xs text-muted-foreground">
                          #{String(o.jobId).padStart(3, "0")}
                        </span>
                        <div className="min-w-0">
                          <div className="mb-1.5 flex items-center justify-between font-label-caps text-[9px] uppercase tracking-[0.12em]">
                            <span className="truncate text-on-surface-variant">{o.model}</span>
                            <span className="text-primary">
                              {o.psnr != null ? `${o.psnr.toFixed(1)} dB` : "no score"}
                            </span>
                          </div>
                          <div className="h-1.5 overflow-hidden rounded-full bg-surface-high">
                            <div
                              className="h-full rounded-full bg-gradient-to-r from-primary/50 to-primary transition-[width] duration-700"
                              style={{
                                width:
                                  o.psnr != null
                                    ? `${Math.min(100, Math.max(4, ((o.psnr - 5) / 40) * 100))}%`
                                    : "4%",
                                opacity: o.psnr != null ? 1 : 0.35,
                              }}
                            />
                          </div>
                        </div>
                        <span className="text-right font-telemetry-data text-xs text-muted-foreground">
                          {o.seconds != null ? `${o.seconds.toFixed(1)} s` : "—"}
                        </span>
                      </div>
                    ))}
                </div>
                <p className="mt-5 border-t border-outline-variant/60 pt-4 font-label-caps text-[9px] uppercase tracking-[0.14em] text-muted-foreground">
                  Bar length maps PSNR over a 5–45 dB window · time column is wall-clock inference
                </p>
              </section>
            </Reveal>
          </div>
        )}

        {/* ── Reading the numbers ──────────────────────────────── */}
        <section className="mt-14">
          <Reveal from="up">
            <span className="font-label-caps text-[10px] font-bold uppercase tracking-[0.3em] text-primary">
              Field guide
            </span>
          </Reveal>
          <RevealHeading
            text="How to read the numbers."
            as="h2"
            className="mt-4 mb-8 font-headline-lg text-[28px] font-semibold leading-[1.1] tracking-tight text-foreground md:text-[40px]"
          />
          <div className="grid gap-4 md:grid-cols-3">
            {[
              {
                name: "PSNR",
                good: "> 30 dB",
                body: "Pixel fidelity against the bicubic control, in decibels. Higher is better; each +6 dB is roughly half the error. Below ~25 dB the product is barely better than plain resampling.",
              },
              {
                name: "SSIM",
                good: "→ 1.0",
                body: "Structural similarity — whether edges and texture survived, not just brightness. Two tiles can share a PSNR while one looks sharp and the other smeared; SSIM is what separates them.",
              },
              {
                name: "Back-projection error",
                good: "< 0.01 RMSE",
                body: "Downsample the product and compare to what the satellite actually saw. Low means the enhancement is physically consistent; high means the model invented radiometry.",
              },
            ].map((c, i) => (
              <Reveal key={c.name} from="up" delay={i * 90}>
                <div className="h-full rounded-xl border border-outline-variant/80 bg-surface/70 p-6">
                  <div className="flex items-baseline justify-between">
                    <span className="font-headline-sm text-[16px] font-semibold text-foreground">
                      {c.name}
                    </span>
                    <span className="font-label-caps text-[10px] font-bold uppercase tracking-[0.14em] text-primary">
                      {c.good}
                    </span>
                  </div>
                  <p className="mt-3 text-sm leading-relaxed text-on-surface-variant">{c.body}</p>
                </div>
              </Reveal>
            ))}
          </div>
        </section>

        {/* ── Trade-off ────────────────────────────────────────── */}
        <section className="mt-14">
          <Reveal from="scale">
            <div className="rounded-2xl border border-outline-variant/80 bg-surface/60 p-8 md:p-10">
              <span className="font-label-caps text-[10px] font-bold uppercase tracking-[0.3em] text-primary">
                The trade-off
              </span>
              <h3 className="mt-3 mb-6 font-headline-lg text-2xl font-semibold tracking-tight text-foreground md:text-3xl">
                Physical or logical — pick per mission.
              </h3>
              <div className="grid gap-6 md:grid-cols-2">
                <div>
                  <div className="mb-2 font-label-caps text-[10px] font-bold uppercase tracking-[0.18em] text-primary">
                    Physical models · DSen2, bicubic
                  </div>
                  <p className="text-sm leading-relaxed text-on-surface-variant">
                    Radiometrically faithful: downsample the output and you get the input back. Use
                    when downstream users compute indices — NDVI, water turbidity, burn severity —
                    from raw reflectances and cannot tolerate invented signal.
                  </p>
                </div>
                <div>
                  <div className="mb-2 font-label-caps text-[10px] font-bold uppercase tracking-[0.18em] text-magenta-signal">
                    Balanced models · LDSR-S2
                  </div>
                  <p className="text-sm leading-relaxed text-on-surface-variant">
                    Diffusion recovers detail the control never contained — at the cost of strict
                    physical consistency. Use when interpretation matters more than radiometry, and
                    read the per-pixel uncertainty map that ships with the product.
                  </p>
                </div>
              </div>
            </div>
          </Reveal>
        </section>
      </main>

      <ConsoleFooter />
    </div>
  );
}

function SectionHead({ icon, title }: { icon: string; title: string }) {
  return (
    <div className="flex items-center gap-2.5">
      <span className="material-symbols-outlined text-[18px] text-primary">{icon}</span>
      <h2 className="font-headline-sm text-[16px] font-semibold text-foreground">{title}</h2>
    </div>
  );
}

function Mini({ label, value, unit }: { label: string; value: string; unit?: string }) {
  return (
    <div className="rounded-lg border border-outline-variant/60 bg-surface-dim/60 px-3 py-2.5">
      <div className="font-telemetry-data text-[15px] font-semibold text-foreground">
        {value}
        {unit && <span className="ml-0.5 text-[10px] text-muted-foreground">{unit}</span>}
      </div>
      <div className="mt-0.5 font-label-caps text-[8px] uppercase tracking-[0.16em] text-muted-foreground">
        {label}
      </div>
    </div>
  );
}
