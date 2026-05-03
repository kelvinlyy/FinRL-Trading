"use client";

import type { BacktestJob } from "@/lib/types";

type Props = {
  job: BacktestJob | null;
  /** True while the run is not finished (queued / running / unknown in-flight). */
  active: boolean;
};

export function BacktestProgressBar({ job, active }: Props) {
  const failed = job?.status === "failed";
  const progress = job?.progress;
  const pct = Math.min(100, Math.max(0, progress?.pct ?? (active ? 4 : 0)));
  const label = progress?.label ?? (active ? "Starting…" : "");
  const indeterminate = Boolean(active && (!progress || progress.indeterminate));

  if (!active && !job) {
    return null;
  }

  return (
    <div className="space-y-2" role="status" aria-live="polite" aria-busy={active}>
      <div className="relative h-2.5 w-full overflow-hidden rounded-full bg-lead/45">
        {indeterminate && !failed ? (
          <div
            className="backtest-progress-indeterminate-bar absolute top-0 h-full w-[36%] rounded-full bg-mercury-blue shadow-[0_0_12px_rgba(82,102,235,0.45)]"
            aria-hidden="true"
          />
        ) : (
          <div
            className={`h-full rounded-full transition-[width] duration-500 ease-out ${
              failed ? "bg-red-500/90" : "bg-mercury-blue shadow-[0_0_10px_rgba(82,102,235,0.35)]"
            }`}
            style={{ width: `${failed ? 100 : pct}%` }}
          />
        )}
      </div>
      {label ? <p className="text-caption tracking-wide text-silver">{label}</p> : null}
    </div>
  );
}
