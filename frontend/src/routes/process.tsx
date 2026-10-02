import { createFileRoute } from "@tanstack/react-router";
import { useCallback, useEffect, useRef, useState } from "react";

import { OrbitBackdrop } from "@/components/chrome/OrbitBackdrop";
import { ConsoleBar } from "@/components/chrome/ConsoleBar";
import { ConsoleFooter } from "@/components/chrome/ConsoleFooter";
import { MetricRow } from "@/components/sr/MetricRow";
import { ModelPicker } from "@/components/sr/ModelPicker";
import { Reveal } from "@/components/motion/Reveal";
import {
  ApiError,
  downloadUrl,
  fetchJob,
  fetchMetrics,
  fetchModels,
  streamJob,
  submitFileJob,
  submitSampleJob,
  type JobMetrics,
  type JobStatus,
  type ModelInfo,
  type ProgressEvent,
} from "@/lib/sr-api";

export const Route = createFileRoute("/process")({
  head: () => ({
    meta: [{ title: "Process Imagery — ARGUS" }],
  }),
  component: ProcessConsole,
});

type Source = "sample" | "upload";

const SAMPLE_STAGES = [
  "Reserving job slot",
  "Reading Sentinel-2 bands",
  "Normalising radiometry",
  "Running super-resolution",
  "Scoring against control",
  "Writing GeoTIFF",
];

function ProcessConsole() {
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [model, setModel] = useState<string>("LDSR-S2 (ESA)");
  const [source, setSource] = useState<Source>("sample");
  const [file, setFile] = useState<File | null>(null);
  const [job, setJob] = useState<JobStatus | null>(null);
  const [metrics, setMetrics] = useState<JobMetrics | null>(null);
  const [progress, setProgress] = useState<ProgressEvent | null>(null);
  const [stageIndex, setStageIndex] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const stageTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    fetchModels()
      .then((list) => {
        setModels(list);
        if (list.length > 0 && !list.some((m) => m.name === model)) {
          setModel(list[0]!.name);
        }
      })
      .catch(() => {
        setModels(FALLBACK_MODELS);
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // While a job runs, walk the named stage list on a timer so the console
  // shows *where* it is even for indeterminate stretches of the pipeline.
  useEffect(() => {
    if (!running) {
      if (stageTimer.current) clearInterval(stageTimer.current);
      return undefined;
    }
    setStageIndex(0);
    stageTimer.current = setInterval(() => {
      setStageIndex((i) => Math.min(i + 1, SAMPLE_STAGES.length - 1));
    }, 2600);
    return () => {
      if (stageTimer.current) clearInterval(stageTimer.current);
    };
  }, [running]);

  const runJob = useCallback(async (): Promise<void> => {
    setError(null);
    setMetrics(null);
    setJob(null);
    setRunning(true);
    setProgress({ percent: null, stage: "queued", message: "Reserving job slot…" });
    try {
      const { job_id } =
        source === "sample" ? await submitSampleJob(model) : await submitFileJob(file!, model);

      const final = await streamJob(job_id, (e) => setProgress(e));
      setJob(final);
      if (final.status === "done") {
        setMetrics(await fetchMetrics(job_id).catch(() => null));
      } else {
        setError(final.error ?? "The job failed without a message.");
      }
    } catch (e) {
      setError(
        e instanceof ApiError
          ? e.message
          : "Could not reach the processing backend. Is `python api.py` running?",
      );
    } finally {
      setRunning(false);
      setProgress(null);
    }
  }, [model, source, file]);

  const canRun =
    !running && models.length > 0 && (source === "sample" || (file !== null && file.size > 0));

  const selectedModel = models.find((m) => m.name === model) ?? null;
  const percent = progress?.percent ?? null;
  const detail = selectedModel
    ? `×${selectedModel.scale} → ${selectedModel.output_res_m} m GSD · ${selectedModel.paper}`
    : null;

  return (
    <div className="relative min-h-screen text-on-surface">
      <OrbitBackdrop />
      <ConsoleBar />

      <main className="mx-auto max-w-[1280px] px-5 pb-16 pt-28 sm:px-8">
        <Reveal from="up">
          <div className="mb-10 flex flex-wrap items-end justify-between gap-4">
            <div>
              <span className="font-label-caps text-[10px] font-bold uppercase tracking-[0.3em] text-primary">
                Processing console
              </span>
              <h1 className="mt-3 font-headline-lg text-4xl font-semibold tracking-tight text-foreground md:text-5xl">
                Process a tile
              </h1>
              <p className="mt-3 max-w-2xl text-sm leading-relaxed text-on-surface-variant">
                Pick a source, pick a model, run. Progress streams from the job itself — the console
                never guesses how long a model will take.
              </p>
            </div>
            {detail && (
              <div className="font-label-caps text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
                {detail}
              </div>
            )}
          </div>
        </Reveal>

        <div className="grid gap-6 lg:grid-cols-[420px_1fr]">
          {/* ── Left: configuration ─────────────────────────────── */}
          <div className="flex flex-col gap-6">
            <Reveal from="up" delay={80}>
              <Panel title="Source" icon="draw">
                <div className="mb-4 grid grid-cols-2 gap-1.5 rounded-lg border border-outline-variant/70 bg-surface-low/60 p-1.5">
                  {(
                    [
                      { id: "sample", label: "Sample tile", icon: "inventory_2" },
                      { id: "upload", label: "Upload GeoTIFF", icon: "upload_file" },
                    ] as const
                  ).map((opt) => (
                    <button
                      key={opt.id}
                      type="button"
                      onClick={() => setSource(opt.id)}
                      className={`flex items-center justify-center gap-2 rounded-md px-3 py-2 font-label-caps text-[10px] font-semibold uppercase tracking-[0.14em] transition-colors ${
                        source === opt.id
                          ? "bg-primary/15 text-primary shadow-[inset_0_0_0_1px_rgba(53,224,161,0.3)]"
                          : "text-muted-foreground hover:text-foreground"
                      }`}
                    >
                      <span className="material-symbols-outlined text-[15px]">{opt.icon}</span>
                      {opt.label}
                    </button>
                  ))}
                </div>

                {source === "sample" ? (
                  <div className="rounded-lg border border-outline-variant/80 bg-surface-low/50 p-4">
                    <div className="flex items-center gap-3">
                      <span className="material-symbols-outlined text-[20px] text-primary">
                        verified
                      </span>
                      <div>
                        <div className="text-sm font-semibold text-foreground">
                          sample_sentinel2.tif
                        </div>
                        <div className="mt-0.5 font-label-caps text-[9px] uppercase tracking-[0.14em] text-muted-foreground">
                          512×512 · 4-band · 10 m GSD
                        </div>
                      </div>
                    </div>
                    <p className="mt-2.5 text-xs leading-relaxed text-on-surface-variant">
                      Bundled Sentinel-2 tile, generated deterministically. Ideal for a first run.
                    </p>
                  </div>
                ) : (
                  <div
                    onDragOver={(e) => {
                      e.preventDefault();
                      setDragOver(true);
                    }}
                    onDragLeave={() => setDragOver(false)}
                    onDrop={(e) => {
                      e.preventDefault();
                      setDragOver(false);
                      const f = e.dataTransfer.files?.[0];
                      if (f) setFile(f);
                    }}
                    onClick={() => fileInputRef.current?.click()}
                    className={`flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed p-6 text-center transition-colors ${
                      dragOver
                        ? "border-primary/60 bg-primary/[0.06]"
                        : file
                          ? "border-primary/40 bg-surface-low/50"
                          : "border-outline-variant bg-surface-low/30 hover:border-outline"
                    }`}
                  >
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept=".tif,.tiff,image/tiff"
                      className="hidden"
                      onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                    />
                    <span className="material-symbols-outlined text-[22px] text-primary">
                      {file ? "check_circle" : "cloud_upload"}
                    </span>
                    <div className="text-sm font-semibold text-foreground">
                      {file ? file.name : "Drop a Sentinel-2 GeoTIFF"}
                    </div>
                    <div className="font-label-caps text-[9px] uppercase tracking-[0.14em] text-muted-foreground">
                      {file
                        ? `${(file.size / 1024).toFixed(1)} KB · click to replace`
                        : ".tif / .tiff · click to browse"}
                    </div>
                  </div>
                )}
              </Panel>
            </Reveal>

            <Reveal from="up" delay={140}>
              <Panel title="Model" icon="neurology">
                <ModelPicker models={models} value={model} onChange={setModel} disabled={running} />
                {model === "LDSR-S2 (ESA)" && (
                  <p className="mt-3 flex items-start gap-2 rounded-lg border border-amber-signal/30 bg-amber-signal/[0.07] px-3.5 py-2.5 text-xs leading-relaxed text-amber-signal">
                    <span className="material-symbols-outlined text-[15px]">hourglass_top</span>
                    Diffusion inference takes 2–5 minutes on CPU. The console streams progress as it
                    runs.
                  </p>
                )}
              </Panel>
            </Reveal>

            <Reveal from="up" delay={200}>
              <button
                type="button"
                onClick={runJob}
                disabled={!canRun}
                className="group flex w-full items-center justify-center gap-2.5 rounded-xl bg-primary px-6 py-4 font-label-caps text-[11px] font-bold uppercase tracking-[0.2em] text-on-primary shadow-[0_0_36px_-10px_rgba(53,224,161,0.6)] transition-all hover:shadow-[0_0_48px_-8px_rgba(53,224,161,0.75)] active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-40 disabled:shadow-none"
              >
                <span className="material-symbols-outlined text-[17px]">
                  {running ? "hourglass_empty" : "satellite_alt"}
                </span>
                {running ? "Job running" : "Run super-resolution"}
              </button>
              {source === "upload" && !file && (
                <p className="mt-2 text-center font-label-caps text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
                  Upload a tile to arm the run
                </p>
              )}
            </Reveal>
          </div>

          {/* ── Right: results ──────────────────────────────────── */}
          <Reveal from="up" delay={120} className="min-w-0">
            <div className="panel-raised flex h-full min-h-[560px] flex-col p-6">
              {running && <RunProgress progress={progress} stageIndex={stageIndex} />}

              {!running && error && (
                <div className="flex flex-1 flex-col items-center justify-center gap-3 text-center">
                  <span className="material-symbols-outlined text-[34px] text-signal-red">
                    satellite_alert
                  </span>
                  <div className="max-w-sm text-sm leading-relaxed text-on-surface-variant">
                    {error}
                  </div>
                  <button
                    type="button"
                    onClick={runJob}
                    className="mt-2 rounded-lg border border-outline px-4 py-2 font-label-caps text-[10px] font-semibold uppercase tracking-[0.16em] text-foreground transition-colors hover:bg-surface-mid"
                  >
                    Try again
                  </button>
                </div>
              )}

              {!running && !error && !job && <EmptyState />}

              {!running && !error && job && (
                <ResultPanel job={job} metrics={metrics} models={models} />
              )}
            </div>
          </Reveal>
        </div>
      </main>

      <ConsoleFooter />
    </div>
  );
}

/* ── Pieces ─────────────────────────────────────────────────── */

function Panel({
  title,
  icon,
  children,
}: {
  title: string;
  icon: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-xl border border-outline-variant/80 bg-surface/70 p-5 backdrop-blur-sm">
      <div className="mb-4 flex items-center gap-2.5 border-b border-outline-variant/60 pb-3">
        <span className="material-symbols-outlined text-[17px] text-primary">{icon}</span>
        <span className="font-label-caps text-[10px] font-bold uppercase tracking-[0.22em] text-foreground">
          {title}
        </span>
      </div>
      {children}
    </div>
  );
}

function RunProgress({
  progress,
  stageIndex,
}: {
  progress: ProgressEvent | null;
  stageIndex: number;
}) {
  const pct = progress?.percent ?? null;
  const stage = progress?.stage ?? "working";
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-7 py-10">
      {/* Dish */}
      <div className="relative h-36 w-36">
        <div className="absolute inset-0 rounded-full border border-primary/15" />
        <div className="absolute inset-4 rounded-full border border-primary/10" />
        <div className="absolute inset-8 rounded-full border border-primary/10" />
        <div
          className="absolute inset-0 rounded-full border-t-2 border-primary/70"
          style={{ animation: "spin 1.6s linear infinite" }}
        />
        <div
          className="absolute inset-5 rounded-full border-b-2 border-magenta-signal/40"
          style={{ animation: "spin 2.4s linear infinite reverse" }}
        />
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="font-telemetry-data text-lg font-semibold text-primary">
            {pct !== null ? `${Math.round(pct)}%` : "···"}
          </span>
        </div>
      </div>

      <div className="w-full max-w-md">
        <div className="mb-2 flex items-center justify-between font-label-caps text-[9px] uppercase tracking-[0.18em] text-muted-foreground">
          <span className="text-primary">{stage}</span>
          <span>{pct !== null ? `${Math.round(pct)}%` : "indeterminate"}</span>
        </div>
        <div className="relative h-1.5 overflow-hidden rounded-full bg-surface-high">
          {pct !== null ? (
            <div
              className="h-full rounded-full bg-primary transition-[width] duration-500"
              style={{ width: `${Math.max(2, pct)}%` }}
            />
          ) : (
            <div className="absolute inset-y-0 w-1/3 animate-sheen rounded-full bg-gradient-to-r from-transparent via-primary/60 to-transparent" />
          )}
        </div>
      </div>

      <div className="grid w-full max-w-md grid-cols-2 gap-1.5">
        {SAMPLE_STAGES.map((s, i) => (
          <div
            key={s}
            className={`flex items-center gap-2 rounded-md border px-3 py-2 font-label-caps text-[9px] uppercase tracking-[0.12em] transition-colors ${
              i < stageIndex
                ? "border-primary/30 bg-primary/[0.06] text-primary"
                : i === stageIndex
                  ? "border-primary/50 bg-primary/[0.1] text-primary"
                  : "border-outline-variant/60 text-muted-foreground/60"
            }`}
          >
            <span className="material-symbols-outlined text-[13px]">
              {i < stageIndex ? "check" : i === stageIndex ? "pending" : "radio_button_unchecked"}
            </span>
            {s}
          </div>
        ))}
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4 text-center">
      <div className="relative">
        <span className="material-symbols-outlined animate-drift text-[44px] text-outline">
          satellite_alt
        </span>
      </div>
      <p className="max-w-xs text-sm leading-relaxed text-on-surface-variant">
        Nothing processed yet. Configure the source and model on the left, then run.
      </p>
      <p className="font-label-caps text-[9px] uppercase tracking-[0.2em] text-muted-foreground/70">
        Awaiting first job
      </p>
    </div>
  );
}

function ResultPanel({
  job,
  metrics,
  models,
}: {
  job: JobStatus;
  metrics: JobMetrics | null;
  models: ModelInfo[];
}) {
  const m = models.find((x) => x.name === job.model);
  return (
    <div className="flex flex-1 flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg border border-primary/40 bg-primary/10">
            <span className="material-symbols-outlined text-[18px] text-primary">task_alt</span>
          </span>
          <div>
            <div className="font-headline-sm text-[16px] font-semibold text-foreground">
              Job #{job.job_id} complete
            </div>
            <div className="font-label-caps text-[9px] uppercase tracking-[0.16em] text-muted-foreground">
              {job.filename} · {job.model}
            </div>
          </div>
        </div>
        <a
          href={downloadUrl(job.job_id)}
          className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2.5 font-label-caps text-[10px] font-bold uppercase tracking-[0.16em] text-on-primary transition-shadow hover:shadow-[0_0_28px_-6px_rgba(53,224,161,0.6)]"
        >
          <span className="material-symbols-outlined text-[15px]">download</span>
          Enhanced GeoTIFF
        </a>
      </div>

      <MetricRow
        metrics={[
          {
            label: "PSNR vs bicubic",
            value:
              metrics?.psnr_vs_bicubic_db != null
                ? `${metrics.psnr_vs_bicubic_db.toFixed(2)} dB`
                : "—",
            tone: "green",
          },
          {
            label: "SSIM",
            value: metrics?.ssim_vs_bicubic != null ? metrics.ssim_vs_bicubic.toFixed(4) : "—",
            tone: "green",
          },
          {
            label: "Inference",
            value:
              metrics?.inference_time_sec != null
                ? `${metrics.inference_time_sec.toFixed(1)} s`
                : "—",
          },
          {
            label: "Output GSD",
            value:
              metrics?.output_resolution_m != null
                ? `${metrics.output_resolution_m} m`
                : m
                  ? `${m.output_res_m} m`
                  : "—",
          },
        ]}
      />

      {/* Output preview — served straight from the backend. */}
      <div className="grid flex-1 grid-cols-1 gap-4 sm:grid-cols-2">
        <Frame label="Input · 10 m" src={`/api/job/${job.job_id}/thumbnail?kind=input`} />
        <Frame
          label={`Output · ${m?.output_res_m ?? "?"} m`}
          src={`/api/job/${job.job_id}/thumbnail?kind= sr`}
          accent
        />
      </div>

      <p className="font-label-caps text-[9px] uppercase tracking-[0.16em] text-muted-foreground">
        Output preserves the source CRS and band order · scored against a bicubic control
      </p>
    </div>
  );
}

function Frame({ label, src, accent = false }: { label: string; src: string; accent?: boolean }) {
  const [failed, setFailed] = useState(false);
  return (
    <div className="relative flex min-h-[220px] flex-1 items-center justify-center overflow-hidden rounded-xl border border-outline-variant/80 bg-surface-dim">
      <span
        className={`absolute left-3 top-3 z-10 rounded border px-2 py-0.5 font-label-caps text-[9px] font-bold uppercase tracking-[0.14em] ${
          accent
            ? "border-primary/40 bg-primary/15 text-primary"
            : "border-outline bg-surface-high/90 text-on-surface-variant"
        }`}
      >
        {label}
      </span>
      {!failed ? (
        <img
          src={src}
          alt={label}
          onError={() => setFailed(true)}
          className="h-full w-full object-cover"
        />
      ) : (
        <div className="flex flex-col items-center gap-2 p-6 text-center">
          <span className="material-symbols-outlined text-[24px] text-outline">image</span>
          <span className="font-label-caps text-[9px] uppercase tracking-[0.16em] text-muted-foreground">
            Preview unavailable
          </span>
        </div>
      )}
    </div>
  );
}

const FALLBACK_MODELS: ModelInfo[] = [
  {
    name: "LDSR-S2 (ESA)",
    scale: 4,
    output_res_m: 2.5,
    description:
      "ESA's latent diffusion SR for Sentinel-2. Best detail recovery, ships with per-pixel uncertainty maps.",
    physical_bias: "Balanced",
    paper: "ESA OpenSR (2024)",
  },
  {
    name: "DSen2",
    scale: 2,
    output_res_m: 5,
    description:
      "Deep Sentinel-2 SR. Physics-first: outputs stay radiometrically consistent with the input.",
    physical_bias: "Physical",
    paper: "Lanaras et al., ISPRS 2020",
  },
  {
    name: "Bicubic Baseline",
    scale: 2,
    output_res_m: 5,
    description:
      "Classical resampling. Always available, zero hallucination, and the control every job is scored against.",
    physical_bias: "Physical",
    paper: "Classical",
  },
];
