# ARGUS — Satellite Super-Resolution Console

ARGUS is the ground-segment web console for the SIH 2026 / problem 26142 pipeline:
submit a Sentinel-2 tile, watch the super-resolution job stream progress live,
inspect PSNR / SSIM / SAM metrics against the control, and download the
enhanced GeoTIFF.

## Stack

- **Vite + TanStack Start** (React 19, file-based routing, SSR shell)
- **Tailwind CSS v4** with a custom "Dusk Orbit" design system
  (`src/styles.css`) — Fraunces for display type, Archivo for UI,
  JetBrains Mono for telemetry
- **FastAPI backend** (`../sr_api.py`) exposes `/api/*`; the dev server
  proxies it, so no CORS setup is needed

## Routes

| Route        | Purpose                                              |
| ------------ | ---------------------------------------------------- |
| `/`          | Overview — the mission brief and model stack         |
| `/process`   | Processing console — submit a tile, stream job state |
| `/history`   | Job archive with per-run metrics and downloads       |
| `/analytics` | Aggregate quality statistics across the archive      |

## Development

```sh
npm install
npm run dev        # vite on :3000, proxies /api -> localhost:8000
```

Start the API first (repo root):

```sh
python -m uvicorn sr_api:app --host 0.0.0.0 --port 8000
```

## Production

```sh
npm run build      # SSR bundle via nitro
npm run preview
```

`vercel.json` is included for one-click deploys of the SSR output.
