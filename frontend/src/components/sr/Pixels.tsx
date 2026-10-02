import { useMemo } from "react";

/**
 * Deterministic PRNG so the landscape doesn't re-roll on every render pass —
 * the pair of tiles should read as the same piece of terrain, not confetti.
 */
function mulberry32(seed: number) {
  let a = seed >>> 0;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

type HSL = [number, number, number];

/**
 * Builds a low-res value-noise field once, then samples it bilinearly at any
 * grid size. That is what makes the two tiles read as the *same* terrain:
 * the 6×6 grid and the 16×16 grid are samples of one underlying field, not
 * two independent random fills.
 */
function useTerrainField(seed: number, coarse: number) {
  return useMemo(() => {
    const rand = mulberry32(seed);
    const grid: number[][] = [];
    for (let y = 0; y < coarse; y++) {
      const row: number[] = [];
      for (let x = 0; x < coarse; x++) row.push(rand());
      grid.push(row);
    }
    const sample = (u: number, v: number) => {
      const gx = u * (coarse - 1);
      const gy = v * (coarse - 1);
      const x0 = Math.floor(gx);
      const y0 = Math.floor(gy);
      const x1 = Math.min(x0 + 1, coarse - 1);
      const y1 = Math.min(y0 + 1, coarse - 1);
      const fx = gx - x0;
      const fy = gy - y0;
      const top = grid[y0]![x0]! * (1 - fx) + grid[y0]![x1]! * fx;
      const bot = grid[y1]![x0]! * (1 - fx) + grid[y1]![x1]! * fx;
      return top * (1 - fy) + bot * fy;
    };
    return sample;
  }, [seed, coarse]);
}

const COARSE_PALETTE: HSL[] = [
  [205, 32, 17],
  [196, 30, 20],
  [168, 28, 19],
  [150, 26, 22],
  [96, 24, 20],
];

const FINE_PALETTE: HSL[] = [
  [203, 38, 24],
  [192, 36, 28],
  [162, 32, 26],
  [144, 30, 30],
  [94, 28, 27],
];

function toCss(hsl: HSL, jitter: number): string {
  const [h, s, l] = hsl;
  return `hsl(${h + jitter * 6} ${s + jitter * 8}% ${l + jitter * 5}%)`;
}

interface PixelPairProps {
  /** Re-seeds the terrain so each instance on the page differs. */
  seed?: number;
}

/**
 * The one idea of the product, drawn instead of stated: the same terrain at
 * 10 m/pixel and at 2.5 m/pixel. Cells get a slow phase-offset shimmer so the
 * pair reads as live sensor output rather than two static swatches.
 */
export function PixelPair({ seed = 7 }: PixelPairProps) {
  const coarseField = useTerrainField(seed, 6);
  const fineField = useTerrainField(seed + 101, 16);

  const coarse = useMemo(() => {
    const cells: string[] = [];
    for (let y = 0; y < 6; y++) {
      for (let x = 0; x < 6; x++) {
        const v = coarseField(x / 5, y / 5);
        cells.push(toCss(COARSE_PALETTE[Math.floor(v * COARSE_PALETTE.length)]!, v));
      }
    }
    return cells;
  }, [coarseField]);

  const fine = useMemo(() => {
    const cells: string[] = [];
    for (let y = 0; y < 16; y++) {
      for (let x = 0; x < 16; x++) {
        const v = fineField(x / 15, y / 15);
        cells.push(toCss(FINE_PALETTE[Math.floor(v * FINE_PALETTE.length)]!, v));
      }
    }
    return cells;
  }, [fineField]);

  return (
    <div className="flex items-center gap-3 sm:gap-4">
      <PixelTile label="10 m · input" cells={coarse} grid={6} size={86} coarse />
      <div className="flex flex-col items-center gap-1">
        <span className="material-symbols-outlined text-[20px] text-primary">double_arrow</span>
        <span className="font-label-caps text-[9px] font-semibold tracking-[0.18em] text-primary">
          ×4 SR
        </span>
      </div>
      <PixelTile label="2.5 m · output" cells={fine} grid={16} size={86} />
    </div>
  );
}

function PixelTile({
  label,
  cells,
  grid,
  size,
  coarse = false,
}: {
  label: string;
  cells: string[];
  grid: number;
  size: number;
  coarse?: boolean;
}) {
  return (
    <div className="flex flex-col items-center gap-2">
      <div
        className="overflow-hidden rounded-md border border-outline-variant"
        style={{
          width: size,
          height: size,
          display: "grid",
          gridTemplateColumns: `repeat(${grid}, 1fr)`,
        }}
      >
        {cells.map((color, i) => (
          <div
            key={i}
            className={coarse ? "" : "animate-pulse-slow"}
            style={{
              background: color,
              animationDelay: coarse ? undefined : `${(i % 7) * 0.21 + (i % 3) * 0.13}s`,
            }}
          />
        ))}
      </div>
      <span className="font-label-caps text-[9px] uppercase tracking-[0.16em] text-muted-foreground">
        {label}
      </span>
    </div>
  );
}
