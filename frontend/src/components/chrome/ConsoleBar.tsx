import { useEffect, useState } from "react";
import { Link, useRouterState } from "@tanstack/react-router";

const LINKS = [
  { to: "/", label: "Overview" },
  { to: "/process", label: "Process" },
  { to: "/history", label: "History" },
  { to: "/analytics", label: "Analytics" },
] as const;

function isActive(pathname: string, to: string): boolean {
  if (to === "/") return pathname === "/";
  return pathname === to || pathname.startsWith(`${to}/`);
}

/**
 * The single console bar shared by every page.
 *
 * Sits above the starfield with a translucent panel; collapses its baseline
 * label on small screens. The active link is a filled chip, not an underline,
 * because on a dark ground the underline reads as a dead pixel.
 */
export function ConsoleBar() {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={`fixed inset-x-0 top-0 z-40 transition-all duration-500 ${
        scrolled
          ? "border-b border-outline-variant/80 bg-surface/85 backdrop-blur-xl"
          : "border-b border-transparent bg-transparent"
      }`}
    >
      <div className="mx-auto flex h-16 max-w-[1280px] items-center justify-between gap-4 px-5 sm:px-8">
        <Link to="/" className="group flex items-center gap-3">
          <span className="relative flex h-8 w-8 items-center justify-center rounded-md border border-primary/40 bg-primary/10">
            <span className="material-symbols-outlined text-[17px] text-primary">
              satellite_alt
            </span>
            <span className="absolute -right-0.5 -top-0.5 h-1.5 w-1.5 rounded-full bg-primary animate-blink-soft" />
          </span>
          <span className="flex flex-col leading-none">
            <span className="font-headline-sm text-[15px] font-semibold tracking-[0.24em] text-foreground">
              ARGUS
            </span>
            <span className="mt-1 hidden font-label-caps text-[9px] uppercase tracking-[0.22em] text-muted-foreground sm:block">
              Sentinel-2 Super-Resolution
            </span>
          </span>
        </Link>

        <nav className="flex items-center gap-1.5 rounded-full border border-outline-variant/70 bg-surface-low/70 p-1 backdrop-blur">
          {LINKS.map((link) => {
            const active = isActive(pathname, link.to);
            return (
              <Link
                key={link.to}
                to={link.to}
                className={`rounded-full px-3.5 py-1.5 font-label-caps text-[10px] font-semibold uppercase tracking-[0.16em] transition-colors sm:px-4 ${
                  active
                    ? "bg-primary/15 text-primary shadow-[inset_0_0_0_1px_rgba(53,224,161,0.35)]"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
