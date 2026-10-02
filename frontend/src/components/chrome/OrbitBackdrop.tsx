import { useEffect, useRef } from "react";

interface Star {
  x: number;
  y: number;
  r: number;
  baseAlpha: number;
  twinkleSpeed: number;
  phase: number;
}

/**
 * The fixed starfield behind every page.
 *
 * Canvas rather than 100 box-shadows because it stays off the compositor:
 * one rAF, one fill pass, and the star count is tuned to the viewport so a
 * 4K window costs the same as a laptop. Honours prefers-reduced-motion by
 * drawing a single static frame.
 *
 * A magenta drift occasionally crosses a star — that is a satellite pass,
 * and it is the one deliberate piece of theatre in the backdrop.
 */
export function OrbitBackdrop() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    let stars: Star[] = [];
    let dpr = Math.min(window.devicePixelRatio || 1, 2);
    let raf = 0;
    let width = 0;
    let height = 0;

    const seed = () => {
      // Density scales with area, capped so ultrawides don't overdraw.
      const count = Math.min(190, Math.round((width * height) / 14000));
      stars = Array.from({ length: count }, () => ({
        x: Math.random() * width,
        y: Math.random() * height,
        r: 0.4 + Math.random() * 1.1,
        baseAlpha: 0.25 + Math.random() * 0.55,
        twinkleSpeed: 0.3 + Math.random() * 1.1,
        phase: Math.random() * Math.PI * 2,
      }));
    };

    const syncSize = () => {
      const w = window.innerWidth;
      const h = window.innerHeight;
      if (w === width && h === height) return;
      width = w;
      height = h;
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = Math.round(w * dpr);
      canvas.height = Math.round(h * dpr);
      canvas.style.width = `${w}px`;
      canvas.style.height = `${h}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      seed();
    };

    syncSize();
    const ro = new ResizeObserver(syncSize);
    ro.observe(document.documentElement);

    const draw = (t: number) => {
      const time = t / 1000;
      ctx.clearRect(0, 0, width, height);

      for (const s of stars) {
        const a = reduced
          ? s.baseAlpha
          : s.baseAlpha * (0.66 + 0.34 * Math.sin(time * s.twinkleSpeed + s.phase));
        ctx.globalAlpha = Math.max(0, Math.min(1, a));
        ctx.fillStyle = "#dfe8ff";
        ctx.beginPath();
        ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
        ctx.fill();
      }

      // Satellite pass: one bright mote with a fading trail crossing the
      // upper third of the frame on a long period.
      if (!reduced) {
        const period = 26;
        const p = (time % period) / period;
        if (p < 0.42) {
          const px = ((p / 0.42) * 1.15 - 0.08) * width;
          const py = height * (0.16 + 0.08 * Math.sin(p * 9));
          const trail = 90;
          const grad = ctx.createLinearGradient(px - trail, py + 8, px, py);
          grad.addColorStop(0, "rgba(255, 92, 138, 0)");
          grad.addColorStop(1, "rgba(255, 92, 138, 0.5)");
          ctx.globalAlpha = 1;
          ctx.strokeStyle = grad;
          ctx.lineWidth = 1;
          ctx.beginPath();
          ctx.moveTo(px - trail, py + 8);
          ctx.lineTo(px, py);
          ctx.stroke();
          ctx.fillStyle = "#ffd7e2";
          ctx.beginPath();
          ctx.arc(px, py, 1.5, 0, Math.PI * 2);
          ctx.fill();
        }
      }

      ctx.globalAlpha = 1;
      raf = requestAnimationFrame(draw);
    };

    raf = requestAnimationFrame(draw);
    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
    };
  }, []);

  return (
    <div className="pointer-events-none fixed inset-0 z-0" aria-hidden>
      <canvas ref={canvasRef} className="block h-full w-full opacity-80" />
    </div>
  );
}
