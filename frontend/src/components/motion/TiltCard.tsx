import { useCallback, useRef, useState, type ReactNode } from "react";

interface TiltCardProps {
  children: ReactNode;
  className?: string;
  /** Maximum rotation in degrees at the corners. */
  maxTilt?: number;
  /** How far the card lifts toward the viewer, in pixels. */
  lift?: number;
  /** Draw the moving specular highlight. */
  glare?: boolean;
  onClick?: () => void;
  selected?: boolean;
  disabled?: boolean;
  ariaLabel?: string;
}

/**
 * A panel that tilts in 3D toward the pointer.
 *
 * Transforms are written straight to the node in a rAF callback rather than
 * through React state, so dragging across a grid of these does not re-render
 * the tree. Falls back to a flat card on touch and for reduced-motion users.
 */
export function TiltCard({
  children,
  className = "",
  maxTilt = 7,
  lift = 10,
  glare = true,
  onClick,
  selected = false,
  disabled = false,
  ariaLabel,
}: TiltCardProps) {
  const ref = useRef<HTMLDivElement>(null);
  const glareRef = useRef<HTMLDivElement>(null);
  const frame = useRef<number>(0);
  const [hovering, setHovering] = useState(false);

  const apply = useCallback(
    (px: number, py: number) => {
      const el = ref.current;
      if (!el) return;
      cancelAnimationFrame(frame.current);
      frame.current = requestAnimationFrame(() => {
        const rx = (0.5 - py) * maxTilt * 2;
        const ry = (px - 0.5) * maxTilt * 2;
        el.style.transform = `perspective(900px) rotateX(${rx.toFixed(2)}deg) rotateY(${ry.toFixed(2)}deg) translateZ(${lift}px)`;
        if (glareRef.current) {
          glareRef.current.style.background = `radial-gradient(circle at ${(px * 100).toFixed(1)}% ${(py * 100).toFixed(1)}%, rgba(255,255,255,0.55), rgba(255,255,255,0) 55%)`;
        }
      });
    },
    [maxTilt, lift],
  );

  const handleMove = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      if (disabled || e.pointerType === "touch") return;
      if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
      const rect = e.currentTarget.getBoundingClientRect();
      apply((e.clientX - rect.left) / rect.width, (e.clientY - rect.top) / rect.height);
    },
    [apply, disabled],
  );

  const reset = useCallback(() => {
    setHovering(false);
    cancelAnimationFrame(frame.current);
    const el = ref.current;
    if (el) el.style.transform = "perspective(900px) rotateX(0deg) rotateY(0deg) translateZ(0)";
    if (glareRef.current) glareRef.current.style.background = "transparent";
  }, []);

  const interactive = Boolean(onClick) && !disabled;

  return (
    <div
      ref={ref}
      role={interactive ? "button" : undefined}
      tabIndex={interactive ? 0 : undefined}
      aria-pressed={interactive ? selected : undefined}
      aria-label={ariaLabel}
      onPointerMove={handleMove}
      onPointerEnter={() => !disabled && setHovering(true)}
      onPointerLeave={reset}
      onBlur={reset}
      onClick={disabled ? undefined : onClick}
      onKeyDown={(e) => {
        if (!interactive) return;
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onClick?.();
        }
      }}
      className={[
        "relative transition-shadow duration-300 will-change-transform",
        interactive ? "cursor-pointer" : "",
        disabled ? "opacity-60" : "",
        hovering ? "shadow-xl z-10" : "shadow-sm",
        className,
      ].join(" ")}
      style={{
        transformStyle: "preserve-3d",
        transition: hovering
          ? undefined
          : "transform 450ms cubic-bezier(0.16, 1, 0.3, 1), box-shadow 300ms",
      }}
    >
      {children}
      {glare && (
        <div
          ref={glareRef}
          aria-hidden
          className="pointer-events-none absolute inset-0 rounded-[inherit] opacity-40 mix-blend-soft-light"
        />
      )}
    </div>
  );
}
