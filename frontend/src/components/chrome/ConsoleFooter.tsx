export function ConsoleFooter() {
  return (
    <footer className="relative mt-24 border-t border-outline-variant/60">
      <div className="mx-auto flex max-w-[1280px] flex-col gap-2 px-5 py-8 sm:flex-row sm:items-center sm:justify-between sm:px-8">
        <div>
          <div className="font-headline-sm text-[13px] font-semibold tracking-[0.26em] text-primary">
            ARGUS
          </div>
          <p className="mt-1 font-label-caps text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
            Sentinel-2 Super-Resolution Ground Segment
          </p>
        </div>
        <p className="max-w-md font-label-caps text-[10px] leading-relaxed tracking-[0.06em] text-muted-foreground/80">
          Every metric shown is computed from the job that produced it. No number on this console is
          a placeholder.
        </p>
      </div>
    </footer>
  );
}
