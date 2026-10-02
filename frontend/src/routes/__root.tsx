import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  Outlet,
  Link,
  createRootRouteWithContext,
  useRouter,
  HeadContent,
  Scripts,
} from "@tanstack/react-router";
import { useEffect, type ReactNode } from "react";

import appCss from "../styles.css?url";
import { reportRuntimeError } from "../lib/error-reporting";

function NotFoundComponent() {
  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="max-w-md text-center">
        <div className="font-label-caps text-[10px] uppercase tracking-[0.3em] text-primary mb-3">
          Signal lost
        </div>
        <h1 className="font-headline-lg text-6xl font-semibold text-foreground">404</h1>
        <h2 className="mt-4 font-headline-sm text-lg text-foreground/90">Tile not in catalogue</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          The page you're looking for doesn't exist or has been moved out of the ground segment.
        </p>
        <div className="mt-6">
          <Link
            to="/"
            className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 font-label-caps text-[11px] font-semibold uppercase tracking-[0.14em] text-on-primary transition-colors hover:bg-primary/90"
          >
            Return to base
          </Link>
        </div>
      </div>
    </div>
  );
}

function ErrorComponent({ error, reset }: { error: Error; reset: () => void }) {
  console.error(error);
  const router = useRouter();
  useEffect(() => {
    reportRuntimeError(error, { boundary: "tanstack_root_error_component" });
  }, [error]);

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="max-w-md text-center">
        <div className="font-label-caps text-[10px] uppercase tracking-[0.3em] text-signal-red mb-3">
          Fault detected
        </div>
        <h1 className="font-headline-md text-xl font-semibold tracking-tight text-foreground">
          This page didn't load
        </h1>
        <p className="mt-2 text-sm text-muted-foreground">
          The console hit an error on our side. Try again, or head back to base.
        </p>
        <div className="mt-6 flex flex-wrap justify-center gap-2">
          <button
            onClick={() => {
              router.invalidate();
              reset();
            }}
            className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 font-label-caps text-[11px] font-semibold uppercase tracking-[0.14em] text-on-primary transition-colors hover:bg-primary/90"
          >
            Try again
          </button>
          <a
            href="/"
            className="inline-flex items-center justify-center rounded-md border border-border px-4 py-2 font-label-caps text-[11px] font-semibold uppercase tracking-[0.14em] text-foreground transition-colors hover:bg-accent"
          >
            Go home
          </a>
        </div>
      </div>
    </div>
  );
}

export const Route = createRootRouteWithContext<{ queryClient: QueryClient }>()({
  head: () => ({
    meta: [
      { charSet: "utf-8" },
      { name: "viewport", content: "width=device-width, initial-scale=1" },
      { title: "ARGUS · Satellite Super-Resolution Console" },
      {
        name: "description",
        content:
          "ARGUS is the ground segment for Sentinel-2 super-resolution: submit a tile, watch the SR job run, inspect PSNR/SSIM and download the enhanced GeoTIFF.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
    links: [
      { rel: "stylesheet", href: appCss },
      { rel: "preconnect", href: "https://fonts.googleapis.com" },
      { rel: "preconnect", href: "https://fonts.gstatic.com", crossOrigin: "anonymous" },
      {
        rel: "stylesheet",
        href: "https://fonts.googleapis.com/css2?family=Archivo:wght@400;500;600;700&family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600;9..144,700&family=JetBrains+Mono:wght@400;500;600;700&display=swap",
      },
      {
        rel: "stylesheet",
        href: "https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200&display=swap",
      },
      { rel: "icon", href: "/favicon.png", type: "image/png" },
      { rel: "icon", href: "/favicon.ico", type: "image/x-icon" },
    ],
  }),
  shellComponent: RootShell,
  component: RootComponent,
  notFoundComponent: NotFoundComponent,
  errorComponent: ErrorComponent,
});

function RootShell({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <head>
        <HeadContent />
      </head>
      <body>
        {children}
        <Scripts />
      </body>
    </html>
  );
}

function RootComponent() {
  const { queryClient } = Route.useRouteContext();

  return (
    <QueryClientProvider client={queryClient}>
      {/* ── Dusk Orbit backdrop ──────────────────────────────────────
          Three layers: deep-space gradient, a faint terminator glow low in
          the frame, and grain so big dark fields don't band on OLED. */}
      <div className="pointer-events-none fixed inset-0 z-0" aria-hidden>
        <div
          className="absolute inset-0"
          style={{
            background:
              "radial-gradient(ellipse 120% 70% at 80% -10%, rgba(28, 44, 92, 0.5) 0%, rgba(28, 44, 92, 0) 55%)," +
              "radial-gradient(ellipse 90% 55% at 12% 112%, rgba(19, 92, 74, 0.28) 0%, rgba(19, 92, 74, 0) 60%)," +
              "linear-gradient(180deg, #05070f 0%, #060913 55%, #04060c 100%)",
          }}
        />
        <div className="noise-veil absolute inset-0" />
      </div>

      <div className="relative z-10">
        <Outlet />
      </div>
    </QueryClientProvider>
  );
}
