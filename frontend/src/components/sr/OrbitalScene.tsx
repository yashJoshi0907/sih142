import { useEffect, useRef } from "react";

interface Body {
  x: number;
  y: number;
}

/**
 * The hero's right-hand scene, rendered as 2D canvas rather than three.js.
 *
 * Same reasoning as the original 3D scene, different budget: the composition
 * is a fixed tableau (Earth low, instrument above it, tiles falling to the
 * console) rather than a fly-through, so layered gradients buy more than a
 * second render loop's worth of GPU.
 *
 * Everything here is drawn, not photographed: an Earth built from ocean and
 * landmass gradients with a sunlit limb, a radar sweep that reads as the
 * scan swath, an orbit chain, and a small satellite that holds station.
 */
export function OrbitalScene() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    let raf = 0;
    let width = 0;
    let height = 0;
    const pointer = { x: 0, y: 0 };
    const eased = { x: 0, y: 0 };

    const onPointerMove = (e: PointerEvent) => {
      pointer.x = (e.clientX / window.innerWidth) * 2 - 1;
      pointer.y = (e.clientY / window.innerHeight) * 2 - 1;
    };
    window.addEventListener("pointermove", onPointerMove, { passive: true });

    const syncSize = () => {
      const rect = canvas.getBoundingClientRect();
      const w = Math.max(1, Math.round(rect.width));
      const h = Math.max(1, Math.round(rect.height));
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      if (canvas.width !== w * dpr || canvas.height !== h * dpr) {
        canvas.width = w * dpr;
        canvas.height = h * dpr;
      }
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      width = w;
      height = h;
    };
    syncSize();
    const ro = new ResizeObserver(syncSize);
    ro.observe(canvas);

    // ── Satellite bodies ────────────────────────────────────────
    const satellite: Body = { x: 0, y: 0 };
    const tiles = Array.from({ length: 5 }, (_, i) => ({
      seed: i,
      phase: i * 1.13,
    }));

    const drawEarth = (cx: number, cy: number, r: number, t: number) => {
      // Ocean body
      const ocean = ctx.createRadialGradient(cx - r * 0.35, cy - r * 0.4, r * 0.1, cx, cy, r);
      ocean.addColorStop(0, "#123c66");
      ocean.addColorStop(0.55, "#0a2444");
      ocean.addColorStop(1, "#050f1e");
      ctx.fillStyle = ocean;
      ctx.beginPath();
      ctx.arc(cx, cy, r, 0, Math.PI * 2);
      ctx.fill();

      // Landmasses — a fixed set of blobby gradients clipped to the sphere.
      ctx.save();
      ctx.beginPath();
      ctx.arc(cx, cy, r, 0, Math.PI * 2);
      ctx.clip();
      const land: Array<[number, number, number, number, string]> = [
        [0.18, 0.1, 0.34, 0.26, "rgba(23, 74, 52, 0.85)"],
        [0.62, 0.3, 0.3, 0.22, "rgba(19, 66, 46, 0.8)"],
        [0.4, 0.62, 0.36, 0.24, "rgba(26, 78, 56, 0.75)"],
        [0.85, 0.72, 0.26, 0.2, "rgba(21, 70, 50, 0.7)"],
      ];
      for (const [ox, oy, rw, rh, color] of land) {
        const g = ctx.createRadialGradient(
          cx + (ox - 0.5) * 2 * r * 0.5,
          cy + (oy - 0.5) * 2 * r * 0.5,
          0,
          cx + (ox - 0.5) * 2 * r * 0.5,
          cy + (oy - 0.5) * 2 * r * 0.5,
          Math.max(rw, rh) * r,
        );
        g.addColorStop(0, color);
        g.addColorStop(1, "rgba(0, 0, 0, 0)");
        ctx.fillStyle = g;
        ctx.fillRect(cx - r, cy - r, r * 2, r * 2);
      }

      // Cloud streaks, slowly advected.
      const drift = reduced ? 0 : (t * 0.006) % 1;
      ctx.globalAlpha = 0.35;
      for (let i = 0; i < 5; i++) {
        const yy = cy - r * 0.7 + i * r * 0.34;
        const xx = cx - r + ((drift + i * 0.23) % 1.6) * r * 1.4 - r * 0.3;
        const g = ctx.createRadialGradient(xx, yy, 0, xx, yy, r * 0.34);
        g.addColorStop(0, "rgba(210, 228, 255, 0.7)");
        g.addColorStop(1, "rgba(210, 228, 255, 0)");
        ctx.fillStyle = g;
        ctx.save();
        ctx.translate(xx, yy);
        ctx.scale(1.9, 0.5);
        ctx.beginPath();
        ctx.arc(0, 0, r * 0.3, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
      }
      ctx.globalAlpha = 1;

      // Scan swath — the instrument's footprint, a soft meridian band.
      const sweep = reduced ? 0.35 : (t * 0.05) % 1;
      const sweepX = cx - r * 0.85 + sweep * r * 1.7;
      const sg = ctx.createLinearGradient(sweepX - r * 0.16, 0, sweepX + r * 0.16, 0);
      sg.addColorStop(0, "rgba(53, 224, 161, 0)");
      sg.addColorStop(0.5, "rgba(53, 224, 161, 0.24)");
      sg.addColorStop(1, "rgba(53, 224, 161, 0)");
      ctx.fillStyle = sg;
      ctx.fillRect(sweepX - r * 0.16, cy - r, r * 0.32, r * 2);
      ctx.restore();

      // Terminator shading — night creeps from the lower right.
      const shade = ctx.createRadialGradient(
        cx - r * 0.4,
        cy - r * 0.45,
        r * 0.2,
        cx + r * 0.15,
        cy + r * 0.15,
        r * 1.25,
      );
      shade.addColorStop(0, "rgba(0, 0, 0, 0)");
      shade.addColorStop(0.62, "rgba(2, 4, 10, 0.35)");
      shade.addColorStop(1, "rgba(2, 4, 10, 0.92)");
      ctx.fillStyle = shade;
      ctx.beginPath();
      ctx.arc(cx, cy, r, 0, Math.PI * 2);
      ctx.fill();

      // Sunlit limb — the one warm accent on the whole dark globe.
      ctx.save();
      ctx.beginPath();
      ctx.arc(cx, cy, r, 0, Math.PI * 2);
      ctx.clip();
      const limb = ctx.createRadialGradient(
        cx - r * 0.72,
        cy - r * 0.7,
        0,
        cx - r * 0.72,
        cy - r * 0.7,
        r * 0.85,
      );
      limb.addColorStop(0, "rgba(255, 196, 130, 0.5)");
      limb.addColorStop(0.45, "rgba(255, 150, 90, 0.14)");
      limb.addColorStop(1, "rgba(255, 150, 90, 0)");
      ctx.fillStyle = limb;
      ctx.fillRect(cx - r, cy - r, r * 2, r * 2);
      ctx.restore();

      // Atmosphere
      ctx.strokeStyle = "rgba(120, 190, 255, 0.35)";
      ctx.lineWidth = 1.2;
      ctx.beginPath();
      ctx.arc(cx, cy, r + 2.5, Math.PI * 0.7, Math.PI * 1.9);
      ctx.stroke();
      ctx.strokeStyle = "rgba(120, 190, 255, 0.12)";
      ctx.beginPath();
      ctx.arc(cx, cy, r + 6, Math.PI * 0.65, Math.PI * 1.95);
      ctx.stroke();
    };

    const drawSatellite = (x: number, y: number, s: number, t: number) => {
      const bob = reduced ? 0 : Math.sin(t * 0.0012) * 3;
      ctx.save();
      ctx.translate(x, y + bob);

      // Solar wings
      ctx.fillStyle = "#123049";
      ctx.strokeStyle = "rgba(92, 214, 255, 0.5)";
      ctx.lineWidth = 1;
      for (const side of [-1, 1]) {
        ctx.save();
        ctx.translate(side * s * 1.15, 0);
        ctx.fillRect(-s * 0.55, -s * 0.3, s * 1.1, s * 0.6);
        ctx.strokeRect(-s * 0.55, -s * 0.3, s * 1.1, s * 0.6);
        ctx.strokeStyle = "rgba(92, 214, 255, 0.22)";
        for (let i = 1; i < 3; i++) {
          ctx.beginPath();
          ctx.moveTo(-s * 0.55 + (i * s * 1.1) / 3, -s * 0.3);
          ctx.lineTo(-s * 0.55 + (i * s * 1.1) / 3, s * 0.3);
          ctx.stroke();
        }
        ctx.strokeStyle = "rgba(92, 214, 255, 0.5)";
        ctx.restore();
      }

      // Bus
      const body = ctx.createLinearGradient(-s * 0.5, -s * 0.5, s * 0.5, s * 0.5);
      body.addColorStop(0, "#39516e");
      body.addColorStop(1, "#1a2a40");
      ctx.fillStyle = body;
      ctx.strokeStyle = "rgba(160, 200, 240, 0.4)";
      ctx.fillRect(-s * 0.5, -s * 0.5, s, s);
      ctx.strokeRect(-s * 0.5, -s * 0.5, s, s);

      // Beacon
      ctx.fillStyle = reduced || Math.sin(t * 0.004) > 0 ? "#35e0a1" : "rgba(53, 224, 161, 0.15)";
      ctx.beginPath();
      ctx.arc(0, -s * 0.32, 1.6, 0, Math.PI * 2);
      ctx.fill();

      ctx.restore();
    };

    const drawTile = (x: number, y: number, size: number, seed: number, alpha: number) => {
      const rnd = (n: number) => {
        const v = Math.sin(seed * 99.7 + n * 12.9898) * 43758.5453;
        return v - Math.floor(v);
      };
      const n = 4;
      const cell = size / n;
      for (let iy = 0; iy < n; iy++) {
        for (let ix = 0; ix < n; ix++) {
          const v = rnd(iy * n + ix);
          ctx.globalAlpha = alpha;
          ctx.fillStyle = `hsl(${200 + v * 20} ${26 + v * 10}% ${14 + v * 12}%)`;
          ctx.fillRect(x + ix * cell, y + iy * cell, cell - 1, cell - 1);
        }
      }
      ctx.globalAlpha = 1;
      ctx.strokeStyle = `rgba(53, 224, 161, ${0.4 * alpha})`;
      ctx.lineWidth = 1;
      ctx.strokeRect(x - 1, y - 1, size + 2, size + 2);
    };

    const renderFrame = (ts: number) => {
      const t = reduced ? 1200 : ts;
      syncSize();
      ctx.clearRect(0, 0, width, height);

      eased.x += (pointer.x - eased.x) * 0.045;
      eased.y += (pointer.y - eased.y) * 0.045;
      const px = reduced ? 0 : eased.x;
      const py = reduced ? 0 : eased.y;

      const cx = width * 0.52 + px * 10;
      const cy = height * 0.62 + py * 6;
      const R = Math.min(width, height) * 0.34;

      // Orbit chain — three dotted rings, the middle one carrying the craft.
      ctx.save();
      for (const [rx, ry, rot, alpha] of [
        [1.55, 0.62, -0.28, 0.3],
        [1.75, 0.72, 0.16, 0.22],
        [1.32, 0.52, 0.4, 0.26],
      ] as const) {
        ctx.strokeStyle = `rgba(122, 150, 255, ${alpha})`;
        ctx.lineWidth = 1;
        ctx.setLineDash([2, 5]);
        ctx.beginPath();
        ctx.ellipse(cx, cy, R * rx, R * ry, rot, 0, Math.PI * 2);
        ctx.stroke();
      }
      ctx.setLineDash([]);

      // Satellite on the middle ring.
      const orbitT = reduced ? 0.6 : (t * 0.00006) % 1;
      const ang = orbitT * Math.PI * 2 + 0.8;
      satellite.x = cx + Math.cos(ang) * R * 1.75;
      satellite.y = cy + Math.sin(ang) * R * 0.72 * Math.sin(0.16) + Math.sin(ang) * R * 0.7;
      drawSatellite(satellite.x, satellite.y, R * 0.09, t);

      // Downlink beam from craft toward the globe.
      const beamA = reduced ? 0.1 : 0.16 + 0.08 * Math.sin(t * 0.002);
      const bg = ctx.createLinearGradient(satellite.x, satellite.y, cx, cy - R * 0.3);
      bg.addColorStop(0, `rgba(255, 92, 138, ${beamA})`);
      bg.addColorStop(1, "rgba(255, 92, 138, 0)");
      ctx.strokeStyle = bg;
      ctx.lineWidth = 1.4;
      ctx.setLineDash([1, 6]);
      ctx.beginPath();
      ctx.moveTo(satellite.x, satellite.y);
      ctx.lineTo(cx - R * 0.2, cy - R * 0.35);
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.restore();

      drawEarth(cx, cy, R, t);

      // Descending tiles — processed output falling toward the console.
      tiles.forEach((tile, i) => {
        const p = reduced ? i / tiles.length : (t * 0.00005 + i / tiles.length) % 1;
        const size = R * 0.24;
        const x = cx + R * 1.28 * Math.cos(tile.phase + p * 0.4) - size / 2;
        const y = cy - R * 1.5 + p * (height * 0.75) * 0.42;
        drawTile(x, y, size, tile.seed, Math.max(0, 0.85 - Math.abs(p - 0.35) * 1.1));
      });

      // Scene caption
      ctx.globalAlpha = 0.75;
      ctx.fillStyle = "#8e9ab5";
      ctx.font = "10px 'JetBrains Mono', monospace";
      ctx.fillText("ORBIT 786 · descending node · scan 42%", 8, height - 10);
      ctx.globalAlpha = 1;

      raf = requestAnimationFrame(renderFrame);
    };

    raf = requestAnimationFrame(renderFrame);

    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
      window.removeEventListener("pointermove", onPointerMove);
    };
  }, []);

  return <canvas ref={canvasRef} className="block h-full w-full" aria-hidden />;
}
