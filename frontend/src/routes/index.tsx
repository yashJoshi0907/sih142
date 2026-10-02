import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";

import { OrbitBackdrop } from "@/components/chrome/OrbitBackdrop";
import { ConsoleBar } from "@/components/chrome/ConsoleBar";
import { ConsoleFooter } from "@/components/chrome/ConsoleFooter";
import { StatRail } from "@/components/chrome/StatRail";
import { OrbitalScene } from "@/components/sr/OrbitalScene";
import { PixelPair } from "@/components/sr/Pixels";
import { Reveal, RevealHeading } from "@/components/motion/Reveal";
import { TiltCard } from "@/components/motion/TiltCard";
import { fetchModels, type ModelInfo } from "@/lib/sr-api";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "ARGUS — Sentinel-2 Super-Resolution Console" },
      {
        name: "description",
        content:
          "ARGUS turns 10 m Sentinel-2 tiles into 2.5 m analysis-ready imagery. Submit a tile, watch the job run, inspect PSNR/SSIM, download the enhanced GeoTIFF.",
      },
      { property: "og:title", content: "ARGUS — Sentinel-2 Super-Resolution Console" },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: Landing,
});

const APPLICATIONS = [
  {
    icon: "agriculture",
    title: "Precision Agriculture",
    body: "Sub-field crop stress, irrigation canal detection, and field boundaries at a scale one Sentinel pixel used to swallow.",
  },
  {
    icon: "location_city",
    title: "Urban Cartography",
    body: "Building footprints, road widths, and settlement edges resolved well enough to trace without guesswork.",
  },
  {
    icon: "water",
    title: "Hydrological Mapping",
    body: "Flood extent, river width, and wetland change mapped across a 290 km swath on every pass.",
  },
  {
    icon: "local_fire_department",
    title: "Disaster Intelligence",
    body: "Pre/post event change detection where the difference between 10 m and 2.5 m is a blocked road.",
  },
  {
    icon: "forest",
    title: "Forest & Carbon",
    body: "Deforestation alerts and canopy structure at field scale, with per-pixel uncertainty on every estimate.",
  },
  {
    icon: "security",
    title: "Intelligence Imagery",
    body: "Physical-bias models when radiometry must be trustworthy, diffusion when detail is the mission.",
  },
] as const;

const GUARANTEES = [
  {
    value: "PSNR",
    label: "Fidelity, not vibes",
    body: "Every job is scored against a bicubic control with PSNR and SSIM. The number travels with the product, so enhancement is never asserted without evidence.",
  },
  {
    value: "0",
    label: "Hallucinated bands",
    body: "Physical-bias models (DSen2, bicubic) are radiometrically consistent — the output integrates to the input. Diffusion models ship with uncertainty maps instead of promises.",
  },
  {
    value: "CPU",
    label: "No GPU required",
    body: "The whole pipeline runs on a laptop. A ground segment that needs a data centre to demo is a paper, not a product.",
  },
] as const;

function Landing() {
  const progressRef = useRef(0);
  const [models, setModels] = useState<ModelInfo[]>([]);

  useEffect(() => {
    const onScroll = () => {
      const span = Math.max(1, window.innerHeight * 1.4);
      progressRef.current = Math.min(1, window.scrollY / span);
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });

    fetchModels()
      .then(setModels)
      .catch(() => setModels([]));
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <div className="relative min-h-screen overflow-x-hidden text-on-surface">
      <OrbitBackdrop />
      <ConsoleBar />

      <main className="relative">
        {/* ── HERO ─────────────────────────────────────────────────── */}
        <section className="relative flex min-h-screen flex-col justify-center">
          <div className="pointer-events-none absolute inset-y-0 right-0 hidden w-[52%] lg:block">
            <div className="absolute inset-0 opacity-90 [mask-image:linear-gradient(to_left,black_55%,transparent)]">
              <OrbitalScene />
            </div>
          </div>

          <div className="relative mx-auto w-full max-w-[1280px] px-5 pb-20 pt-32 sm:px-8">
            <div className="max-w-2xl">
              <Reveal from="up">
                <div className="mb-7 inline-flex items-center gap-2.5 rounded-full border border-primary/30 bg-primary/8 px-3.5 py-1.5">
                  <span className="h-1.5 w-1.5 rounded-full bg-primary animate-blink-soft" />
                  <span className="font-label-caps text-[10px] font-semibold uppercase tracking-[0.22em] text-primary">
                    SIH 2026 · Problem 26142 · NTRO
                  </span>
                </div>
              </Reveal>

              <RevealHeading
                text="Ten-metre pixels,"
                as="h1"
                className="font-headline-lg text-[13vw] font-semibold leading-[0.98] tracking-tight text-foreground sm:text-[9vw] lg:text-[72px]"
              />
              <RevealHeading
                text="read at 2.5."
                as="h1"
                wordDelay={80}
                className="font-headline-lg text-[13vw] font-semibold leading-[0.98] tracking-tight text-primary sm:text-[9vw] lg:text-[72px]"
              />

              <Reveal from="up" delay={420}>
                <p className="mt-7 max-w-xl text-base leading-relaxed text-on-surface-variant">
                  Sentinel-2 sees the world at 10 metres a pixel. ARGUS runs satellite-specific
                  super-resolution on its tiles — diffusion when detail matters, physics when
                  radiometry does — and scores every output against a control, so what you download
                  is enhanced and accounted for.
                </p>
              </Reveal>

              <Reveal from="up" delay={540}>
                <div className="mt-9 flex flex-wrap items-center gap-3">
                  <Link
                    to="/process"
                    className="group inline-flex items-center gap-2.5 rounded-lg bg-primary px-6 py-3.5 font-label-caps text-[11px] font-bold uppercase tracking-[0.18em] text-on-primary shadow-[0_0_32px_-8px_rgba(53,224,161,0.55)] transition-all hover:shadow-[0_0_44px_-6px_rgba(53,224,161,0.7)] active:scale-[0.98]"
                  >
                    Run super-resolution
                    <span className="material-symbols-outlined text-[16px] transition-transform group-hover:translate-x-1">
                      arrow_forward
                    </span>
                  </Link>
                  <a
                    href="#models"
                    className="inline-flex items-center gap-2.5 rounded-lg border border-outline-variant px-6 py-3.5 font-label-caps text-[11px] font-bold uppercase tracking-[0.18em] text-on-surface-variant transition-colors hover:border-outline hover:text-foreground"
                  >
                    The model stack
                    <span className="material-symbols-outlined text-[16px]">south</span>
                  </a>
                </div>
              </Reveal>

              <Reveal from="up" delay={660}>
                <div className="mt-12">
                  <PixelPair seed={11} />
                </div>
              </Reveal>
            </div>
          </div>

          <Reveal from="up" delay={900} className="absolute bottom-6 inset-x-0">
            <div className="flex flex-col items-center gap-2 text-muted-foreground">
              <span className="font-label-caps text-[9px] uppercase tracking-[0.3em]">Scroll</span>
              <span className="h-9 w-px bg-gradient-to-b from-outline to-transparent" />
            </div>
          </Reveal>
        </section>

        {/* ── STAT RAIL ───────────────────────────────────────────── */}
        <section className="mx-auto max-w-[1280px] px-5 sm:px-8">
          <StatRail />
        </section>

        {/* ── APPLICATIONS ────────────────────────────────────────── */}
        <section className="mx-auto max-w-[1280px] px-5 pt-28 sm:px-8">
          <Reveal from="up">
            <span className="font-label-caps text-[10px] font-bold uppercase tracking-[0.3em] text-primary">
              01 — What it unlocks
            </span>
          </Reveal>
          <RevealHeading
            text="Everything that waits on resolution."
            as="h2"
            className="mt-4 mb-12 font-headline-lg text-[30px] font-semibold leading-[1.1] tracking-tight text-foreground md:text-[44px]"
          />
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {APPLICATIONS.map((app, i) => (
              <Reveal key={app.title} from="up" delay={i * 70}>
                <TiltCard
                  maxTilt={4}
                  lift={8}
                  glare={false}
                  className="h-full rounded-xl border border-outline-variant/80 bg-surface/70 p-6 backdrop-blur-sm transition-colors hover:border-outline"
                >
                  <span className="material-symbols-outlined text-[22px] text-primary/90">
                    {app.icon}
                  </span>
                  <h3 className="mt-4 font-headline-sm text-[17px] font-semibold text-foreground">
                    {app.title}
                  </h3>
                  <p className="mt-2 text-sm leading-relaxed text-on-surface-variant">{app.body}</p>
                </TiltCard>
              </Reveal>
            ))}
          </div>
        </section>

        {/* ── MODELS ──────────────────────────────────────────────── */}
        <section id="models" className="mx-auto max-w-[1280px] scroll-mt-24 px-5 pt-28 sm:px-8">
          <Reveal from="up">
            <span className="font-label-caps text-[10px] font-bold uppercase tracking-[0.3em] text-primary">
              02 — The model stack
            </span>
          </Reveal>
          <RevealHeading
            text="Three ways to sharpen a photon."
            as="h2"
            className="mt-4 mb-6 font-headline-lg text-[30px] font-semibold leading-[1.1] tracking-tight text-foreground md:text-[44px]"
          />
          <Reveal from="up" delay={100}>
            <p className="mb-12 max-w-2xl text-sm leading-relaxed text-on-surface-variant">
              No generic natural-image SR. Every model here was built or calibrated for Sentinel-2's
              bands, and the registry it serves is the same one the console runs.
            </p>
          </Reveal>

          <div className="grid gap-4 md:grid-cols-3">
            {(models.length > 0
              ? models
              : [
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
                ]
            ).map((m, i) => (
              <Reveal key={m.name} from="up" delay={i * 90}>
                <div className="flex h-full flex-col rounded-xl border border-outline-variant/80 bg-surface/70 p-6">
                  <div className="flex items-start justify-between gap-3">
                    <h3 className="font-headline-sm text-[17px] font-semibold text-foreground">
                      {m.name}
                    </h3>
                    <span
                      className={`shrink-0 rounded px-2 py-0.5 font-label-caps text-[9px] font-bold uppercase tracking-[0.14em] ${
                        m.physical_bias === "Balanced"
                          ? "border border-magenta-signal/40 bg-magenta-signal/10 text-magenta-signal"
                          : "border border-primary/40 bg-primary/10 text-primary"
                      }`}
                    >
                      {m.physical_bias}
                    </span>
                  </div>
                  <p className="mt-3 flex-1 text-sm leading-relaxed text-on-surface-variant">
                    {m.description}
                  </p>
                  <div className="mt-5 flex items-center justify-between border-t border-outline-variant/60 pt-4 font-label-caps text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
                    <span>{m.paper}</span>
                    <span className="text-primary">
                      ×{m.scale} → {m.output_res_m} m
                    </span>
                  </div>
                </div>
              </Reveal>
            ))}
          </div>
        </section>

        {/* ── GUARANTEES ──────────────────────────────────────────── */}
        <section className="mx-auto max-w-[1280px] px-5 pt-28 sm:px-8">
          <Reveal from="up">
            <span className="font-label-caps text-[10px] font-bold uppercase tracking-[0.3em] text-primary">
              03 — What is actually guaranteed
            </span>
          </Reveal>
          <RevealHeading
            text="Numbers that hold, not numbers that impress."
            as="h2"
            className="mt-4 mb-12 font-headline-lg text-[30px] font-semibold leading-[1.1] tracking-tight text-foreground md:text-[44px]"
          />
          <div className="grid gap-4 md:grid-cols-3">
            {GUARANTEES.map((g, i) => (
              <Reveal key={g.label} from="up" delay={i * 110}>
                <div className="h-full rounded-xl border border-outline-variant/80 bg-surface/70 p-7">
                  <div className="font-headline-lg text-[40px] font-semibold leading-none text-primary">
                    {g.value}
                  </div>
                  <div className="mt-3 font-label-caps text-[10px] font-bold uppercase tracking-[0.18em] text-foreground">
                    {g.label}
                  </div>
                  <p className="mt-2.5 text-sm leading-relaxed text-on-surface-variant">{g.body}</p>
                </div>
              </Reveal>
            ))}
          </div>
        </section>

        {/* ── CLOSING CTA ─────────────────────────────────────────── */}
        <section className="mx-auto max-w-[1280px] px-5 pt-28 sm:px-8">
          <Reveal from="scale">
            <div className="relative overflow-hidden rounded-2xl border border-primary/25 bg-gradient-to-br from-surface-low/90 to-surface/70 p-10 backdrop-blur-md md:p-14">
              <div
                className="pointer-events-none absolute -right-6 -top-10 select-none font-headline-lg text-[180px] leading-none text-primary/[0.05]"
                aria-hidden
              >
                ×4
              </div>
              <div className="relative max-w-2xl">
                <span className="font-label-caps text-[10px] font-bold uppercase tracking-[0.3em] text-primary">
                  04 — The console
                </span>
                <h2 className="mt-4 mb-5 font-headline-lg text-[30px] font-semibold leading-[1.1] tracking-tight text-foreground md:text-[40px]">
                  Bring a tile. Leave with 2.5 metres.
                </h2>
                <p className="text-sm leading-relaxed text-on-surface-variant md:text-base">
                  Upload a GeoTIFF or run the bundled sample. The job streams progress as it works,
                  lands in history with its metrics, and hands you the enhanced GeoTIFF — CRS and
                  band order intact.
                </p>
                <div className="mt-8 flex flex-wrap gap-3">
                  <Link
                    to="/process"
                    className="group inline-flex items-center gap-2.5 rounded-lg bg-primary px-6 py-3.5 font-label-caps text-[11px] font-bold uppercase tracking-[0.18em] text-on-primary transition-all hover:shadow-[0_0_44px_-6px_rgba(53,224,161,0.6)] active:scale-[0.98]"
                  >
                    Open the console
                    <span className="material-symbols-outlined text-[16px] transition-transform group-hover:translate-x-1">
                      arrow_forward
                    </span>
                  </Link>
                  <Link
                    to="/analytics"
                    className="inline-flex items-center gap-2.5 rounded-lg border border-outline-variant px-6 py-3.5 font-label-caps text-[11px] font-bold uppercase tracking-[0.18em] text-on-surface-variant transition-colors hover:border-outline hover:text-foreground"
                  >
                    See the analytics
                  </Link>
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
