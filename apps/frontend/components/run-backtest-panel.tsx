"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { BacktestProgressBar } from "@/components/backtest-progress-bar";
import { ApiRequestError, DataCoverageError, getBacktestJob, startBacktestRun } from "@/lib/api";
import type { BacktestJob, DataCoverageDetail, DeployStrategyRow } from "@/lib/types";

export type RunBacktestPanelProps = {
  /** Strategy rows from ``listDeployStrategies`` (parent fetch avoids duplicate requests). */
  deployStrategies: DeployStrategyRow[];
  deployStrategy: string;
  onDeployStrategyChange: (name: string) => void;
};

function DataGapPanel({ detail }: { detail: DataCoverageDetail }) {
  return (
    <div className="rounded-md border border-amber-500/35 bg-amber-500/10 p-5 text-body-sm text-starlight">
      {detail.message ? <p className="font-[480] text-amber-100">{detail.message}</p> : null}
      <p className="mt-2 text-caption text-silver">
        Data folder <code className="text-ghost-blue">{detail.data_dir}</code> — symbols from{" "}
        <code className="text-ghost-blue">{detail.config_path}</code> — backtest window{" "}
        <code className="text-ghost-blue">
          {detail.backtest_start} → {detail.backtest_end}
        </code>
        {typeof detail.symbols_required === "number" ? (
          <span className="block pt-1">({detail.symbols_required} tickers required)</span>
        ) : null}
      </p>
      {detail.missing_csv_for_symbols?.length ? (
        <div className="mt-4">
          <p className="text-caption uppercase tracking-[0.2em] text-silver">Missing CSV files</p>
          <ul className="mt-2 list-inside list-disc text-silver">
            {detail.missing_csv_for_symbols.map((s) => (
              <li key={s}>
                <code className="text-starlight/90">{s}_daily.csv</code>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {detail.insufficient_date_coverage?.length ? (
        <div className="mt-4">
          <p className="text-caption uppercase tracking-[0.2em] text-silver">Date coverage issues</p>
          <ul className="mt-2 space-y-3 text-silver">
            {detail.insufficient_date_coverage.map((row, i) => (
              <li key={i}>
                <code className="text-starlight/90">{String(row.symbol)}</code> —{" "}
                <span className="text-silver/90">{String(row.issue)}</span>
                {"csv_date_min" in row ? (
                  <span className="mt-1 block text-caption">
                    CSV dates {String(row.csv_date_min)} → {String(row.csv_date_max)}
                    {"needs_data_through" in row ? (
                      <span> — extend through {String(row.needs_data_through)}</span>
                    ) : null}
                    {"needs_data_from" in row ? (
                      <span> — need prices from {String(row.needs_data_from)}</span>
                    ) : null}
                    {"recommended_earliest_date" in row ? (
                      <span>
                        {" "}
                        — config asks ~{String(row.minimum_history_weeks)}w lookback before{" "}
                        {String(row.backtest_start)} (extend CSV to ≥ {String(row.recommended_earliest_date)})
                      </span>
                    ) : null}
                  </span>
                ) : null}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}

const ACTIVE_JOB_STORAGE_KEY = "finrl-web-backtest-job-id";

function isTerminal(status: string) {
  return status === "completed" || status === "failed";
}

function rememberActiveJobId(jobId: string) {
  try {
    localStorage.setItem(ACTIVE_JOB_STORAGE_KEY, jobId);
  } catch {
    /* quota / private mode */
  }
}

function forgetActiveJobId() {
  try {
    localStorage.removeItem(ACTIVE_JOB_STORAGE_KEY);
  } catch {
    /* ignore */
  }
}

export function RunBacktestPanel({
  deployStrategies,
  deployStrategy,
  onDeployStrategyChange,
}: RunBacktestPanelProps) {
  const strategy = deployStrategy;
  const setStrategy = onDeployStrategyChange;
  const strategies = deployStrategies;

  const strategySelectRows = useMemo(() => {
    const base: DeployStrategyRow[] = strategies.length
      ? strategies
      : [{ name: "adaptive_rotation", config: "", runner: "" }];
    if (strategy && !base.some((r) => r.name === strategy)) {
      return [{ name: strategy, config: "", runner: "" }, ...base];
    }
    return base;
  }, [strategies, strategy]);
  const [mode, setMode] = useState<"backtest" | "single">("backtest");
  const [singleDate, setSingleDate] = useState("2024-12-31");
  const [start, setStart] = useState("2024-01-01");
  const [end, setEnd] = useState("2024-12-31");
  const [jobId, setJobId] = useState<string | null>(null);
  const [job, setJob] = useState<BacktestJob | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [dataGap, setDataGap] = useState<DataCoverageDetail | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pollFailCountRef = useRef(0);

  const clearPoll = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  useEffect(() => {
    return () => clearPoll();
  }, [clearPoll]);

  useEffect(() => {
    try {
      const saved = localStorage.getItem(ACTIVE_JOB_STORAGE_KEY);
      if (saved) {
        setJobId(saved);
      }
    } catch {
      /* ignore */
    }
  }, []);

  const pollJob = useCallback(
    async (id: string) => {
      try {
        const next = await getBacktestJob(id);
        pollFailCountRef.current = 0;
        setJob(next);
        if (isTerminal(next.status)) {
          clearPoll();
          rememberActiveJobId(id);
        }
      } catch (err) {
        if (err instanceof ApiRequestError && err.status === 404) {
          clearPoll();
          forgetActiveJobId();
          setDataGap(null);
          const runHint =
            mode === "backtest"
              ? `${start}_to_${end}`
              : `single_${singleDate}`;
          setFormError(
            `Job not found on the server (often after an API restart). If the job already finished, look for “${runHint}” on disk or in logs.`,
          );
          return;
        }
        pollFailCountRef.current += 1;
        if (pollFailCountRef.current >= 12) {
          clearPoll();
          const hint =
            err instanceof ApiRequestError && err.status === 0
              ? `Cannot reach the API (${err.message}). Check that the backend is running on port 8000.`
              : err instanceof Error
                ? err.message
                : "Polling failed.";
          setFormError(hint);
        }
      }
    },
    [clearPoll, start, end, mode, singleDate],
  );

  useEffect(() => {
    if (!jobId) return;
    pollFailCountRef.current = 0;
    void pollJob(jobId);
    clearPoll();
    pollRef.current = setInterval(() => {
      void pollJob(jobId);
    }, 1000);
    return () => clearPoll();
  }, [jobId, pollJob, clearPoll]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);
    setDataGap(null);
    setSubmitting(true);
    setJob(null);
    setJobId(null);
    try {
      const res = await startBacktestRun(
        mode === "backtest"
          ? { start, end, strategy, mode: "backtest" }
          : { date: singleDate, strategy, mode: "single" },
      );
      setJobId(res.job_id);
      rememberActiveJobId(res.job_id);
    } catch (err) {
      if (err instanceof DataCoverageError) {
        setDataGap(err.coverage);
      } else {
        setFormError(err instanceof Error ? err.message : "Failed to start backtest");
      }
    } finally {
      setSubmitting(false);
    }
  }

  const busy = submitting || (Boolean(jobId) && (!job || !isTerminal(job.status)));
  const progressActive = submitting || (Boolean(jobId) && (!job || !isTerminal(job.status)));

  return (
    <div className="space-y-10">
      <form onSubmit={onSubmit} className="panel space-y-8 rounded-md p-8 md:p-10">
        <label className="flex max-w-2xl flex-col gap-2 text-body-sm text-silver">
          Strategy
          <select
            value={strategy}
            onChange={(ev) => setStrategy(ev.target.value)}
            className="rounded-md border border-lead/50 bg-deep-space px-4 py-3 text-starlight outline-none focus:border-mercury-blue"
          >
            {(strategySelectRows).map((s) => (
              <option key={s.name} value={s.name}>
                {s.name}
              </option>
            ))}
          </select>
        </label>

        <div>
          <p className="eyebrow">Deploy job</p>
          <h2 className="mt-3 font-display text-heading font-[360] text-starlight">Mode, dates, and launch</h2>
          <p className="mt-4 text-body text-silver">
            Each job runs <code className="text-caption text-ghost-blue">deploy.sh</code> on the server: it downloads any
            missing Yahoo CSVs into <code className="text-caption text-ghost-blue">data/fmp_daily</code>, then runs your
            strategy. The first run can take longer while data is fetched.
          </p>
          {strategies.length <= 1 ? (
            <p className="mt-3 text-body-sm text-silver/80">
              Only <code className="text-ghost-blue">adaptive_rotation</code> is registered in{" "}
              <code className="text-ghost-blue">deploy.sh</code> today; add strategies there to expose more runners (UC1 /
              UC2 hooks).
            </p>
          ) : null}
          <p className="mt-3 text-body-sm text-silver/90">
            Refreshing this page does not cancel the run: the job is tracked on disk and the worker keeps executing in the
            background. Your browser restores the active job id from local storage so polling continues.
          </p>
        </div>

        <label className="flex max-w-md flex-col gap-2 text-body-sm text-silver">
          Mode
          <select
            value={mode}
            onChange={(ev) => setMode(ev.target.value as "backtest" | "single")}
            className="rounded-md border border-lead/50 bg-deep-space px-4 py-3 text-starlight outline-none focus:border-mercury-blue"
          >
            <option value="backtest">Backtest (date range)</option>
            <option value="single">Single date (signal JSON)</option>
          </select>
        </label>

        {mode === "backtest" ? (
          <div className="grid gap-6 md:grid-cols-2">
            <label className="flex flex-col gap-2 text-body-sm text-silver">
              Start date
              <input
                type="date"
                value={start}
                onChange={(ev) => setStart(ev.target.value)}
                className="rounded-md border border-lead/50 bg-deep-space px-4 py-3 text-starlight outline-none focus:border-mercury-blue"
                required
              />
            </label>
            <label className="flex flex-col gap-2 text-body-sm text-silver">
              End date
              <input
                type="date"
                value={end}
                onChange={(ev) => setEnd(ev.target.value)}
                className="rounded-md border border-lead/50 bg-deep-space px-4 py-3 text-starlight outline-none focus:border-mercury-blue"
                required
              />
            </label>
          </div>
        ) : (
          <label className="flex max-w-md flex-col gap-2 text-body-sm text-silver">
            Decision date
            <input
              type="date"
              value={singleDate}
              onChange={(ev) => setSingleDate(ev.target.value)}
              className="rounded-md border border-lead/50 bg-deep-space px-4 py-3 text-starlight outline-none focus:border-mercury-blue"
              required
            />
          </label>
        )}

        {dataGap ? <DataGapPanel detail={dataGap} /> : null}

        {progressActive && !job ? (
          <div className="pt-2">
            <BacktestProgressBar job={null} active />
          </div>
        ) : null}

        {formError ? (
          <p className="rounded-md border border-red-500/40 bg-red-500/10 px-4 py-3 text-body-sm text-red-200">{formError}</p>
        ) : null}

        <div className="flex flex-wrap items-center gap-4">
          <button
            type="submit"
            disabled={busy}
            className="rounded-[32px] bg-mercury-blue px-6 py-4 text-body-sm font-[480] text-pure-white disabled:cursor-not-allowed disabled:opacity-50"
          >
            {busy ? "Running…" : mode === "single" ? "Run single-day signal" : "Run backtest"}
          </button>
          {job?.status === "completed" && job.result_run_id && job.mode !== "single" ? (
            <Link
              href={`/results?run=${encodeURIComponent(job.result_run_id)}`}
              className="rounded-[32px] border border-ghost-blue/50 px-6 py-4 text-body-sm font-[480] text-starlight hover:border-mercury-blue"
            >
              Open results
            </Link>
          ) : null}
          {job?.status === "completed" && job.mode === "single" && job.result_run_id ? (
            <span className="text-body-sm text-silver">
              Single run <code className="text-ghost-blue">{job.result_run_id}</code> — audit JSON under{" "}
              <code className="text-caption text-ghost-blue">src/strategies/output/audit/adaptive_rotation/audit_*.json</code>{" "}
              (paper mode uses <code className="text-caption text-ghost-blue">signal_*.json</code> via deploy only).
            </span>
          ) : null}
        </div>
      </form>

      {job ? (
        <section className="panel space-y-4 rounded-md p-8">
          <BacktestProgressBar job={job} active={!isTerminal(job.status)} />
          <div className="flex flex-wrap items-baseline justify-between gap-4">
            <h3 className="font-display text-heading-sm font-[360] text-starlight">Job status</h3>
            <span className="text-caption uppercase tracking-[0.2em] text-silver">{job.status}</span>
          </div>
          <p className="text-body-sm text-silver">
            Job <code className="text-starlight/90">{job.job_id}</code>
            {job.strategy ? (
              <>
                {" "}
                — <code className="text-ghost-blue">{job.strategy}</code> / {job.mode ?? "backtest"}
              </>
            ) : null}
          </p>
          {job.message ? <p className="text-body-sm text-red-200">{job.message}</p> : null}
          {job.stderr_tail ? (
            <div>
              <p className="mb-2 text-caption uppercase tracking-[0.2em] text-silver">Stderr (tail)</p>
              <pre className="max-h-64 overflow-auto rounded-md border border-lead/40 bg-deep-space/80 p-4 text-caption leading-relaxed text-silver">
                {job.stderr_tail}
              </pre>
            </div>
          ) : null}
          {job.stdout_tail ? (
            <details className="text-body-sm text-silver">
              <summary className="cursor-pointer text-starlight">Stdout (tail)</summary>
              <pre className="mt-3 max-h-48 overflow-auto rounded-md border border-lead/40 bg-deep-space/80 p-4 text-caption leading-relaxed">
                {job.stdout_tail}
              </pre>
            </details>
          ) : null}
        </section>
      ) : null}
    </div>
  );
}
