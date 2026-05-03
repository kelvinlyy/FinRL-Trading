import type { BacktestRun } from "@/lib/types";
import { MetricCard } from "./metric-card";

function fmtPct(value: number | undefined) {
  if (value === undefined) return "—";
  return `${(value * 100).toFixed(2)}%`;
}

export function ResultsSummary({ run }: { run: BacktestRun }) {
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      <MetricCard label="Run window" value={run.label} />
      <MetricCard label="Trade log rows" value={`${run.counts?.trade_rows ?? 0}`} />
      <MetricCard label="Weekly snapshots" value={`${run.counts?.summary_rows ?? 0}`} />
      <MetricCard label="Data source" value="Yahoo CSV" />
    </div>
  );
}
