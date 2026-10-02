import { useEffect, useRef, useState, type CSSProperties, type ReactNode } from "react";

type Direction = "up" | "down" | "left" | "right" | "scale" | "none";

interface RevealProps {
  children: ReactNode;
  /** Direction the element travels in from. */
  from?: Direction;
  /** Stagger, in milliseconds, before this element animates. */
  delay?: number;
  /** Travel distance in pixels. */
  distance?: number;
  /** Replay the animation every time the element re-enters the viewport. */
  repeat?: boolean;
  className?: string;
  /** Render as an inline element (for headings that must not nest divs). */
  inline?: boolean;
}

const OFFSETS: Record<Direction, (d: number) => string> = {
  up: (d) => `translate3d(0, ${d}px, 0)`,
  down: (d) => `translate3d(0, -${d}px, 0)`,
  left: (d) => `translate3d(${d}px, 0, 0)`,
  right: (d) => `translate3d(-${d}px, 0, 0)`,
  scale: () => "scale(0.94)",
  none: () => "none",
};

/**
 * Scroll-triggered entrance animation.
 *
 * Uses IntersectionObserver rather than a scroll listener so a long dashboard
 * with dozens of revealing panels stays off the main thread. Honours
 * `prefers-reduced-motion` by rendering the final state immediately.
 */
export function Reveal({
  children,
  from = "up",
  delay = 0,
  distance = 28,
  repeat = false,
  className = "",
  inline = false,
}: RevealProps) {
  const ref = useRef<HTMLElement>(null);
  const [visible, setVisible] = useState(false);
  const [reduced, setReduced] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduced(mq.matches);
    const onChange = () => setReduced(mq.matches);
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (reduced) {
      setVisible(true);
      return;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setVisible(true);
            if (!repeat) observer.unobserve(entry.target);
          } else if (repeat) {
            setVisible(false);
          }
        }
      },
      { threshold: 0.12, rootMargin: "0px 0px -60px 0px" },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [repeat, reduced]);

  const style: CSSProperties = {
    opacity: visible ? 1 : 0,
    transform: visible ? "none" : OFFSETS[from](distance),
    transition: reduced
      ? "none"
      : `opacity 700ms cubic-bezier(0.16, 1, 0.3, 1) ${delay}ms, transform 700ms cubic-bezier(0.16, 1, 0.3, 1) ${delay}ms`,
    willChange: visible ? "auto" : "opacity, transform",
  };

  const content = children;
  return inline ? (
    <span ref={ref as React.RefObject<HTMLSpanElement>} className={className} style={style}>
      {content}
    </span>
  ) : (
    <div ref={ref as React.RefObject<HTMLDivElement>} className={className} style={style}>
      {content}
    </div>
  );
}

/**
 * Splits a heading into words that float up one after another as it scrolls
 * into view. Words, not characters — screen readers still read the phrase and
 * the DOM stays small on long pages.
 */
export function RevealHeading({
  text,
  className = "",
  wordDelay = 55,
  as: Tag = "h1",
}: {
  text: string;
  className?: string;
  wordDelay?: number;
  as?: "h1" | "h2" | "h3";
}) {
  const words = text.split(" ");
  return (
    <Tag className={className} aria-label={text}>
      {words.map((word, i) => (
        <Reveal
          key={`${word}-${i}`}
          inline
          from="up"
          distance={20}
          delay={i * wordDelay}
          className="inline-block whitespace-pre"
        >
          {/* One string child, not two: adjacent text nodes serialise with
              separator comments on the server and break hydration. */}
          {i < words.length - 1 ? `${word} ` : word}
        </Reveal>
      ))}
    </Tag>
  );
}
