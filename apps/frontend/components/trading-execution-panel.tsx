"use client";

import { useEffect, useRef, useState } from "react";
import { getTradingJob, listDeployStrategies, startTradingRun } from "@/lib/api";
import type { BacktestJob, DeployStrategyRow } from "@/lib/types";

function isTerminal(status: string) {
  return status === "completed" || status === "failed";
}

export function TradingExecutionPanel() {
  const [strategies, setStrategies] = useState<DeployStrategyRow[]>([]);
  const [strategy, setStrategy] = useState("adaptive_rotation");
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const [dryRun, setDryRun] = useState(true);
  const [job, setJob] = useState<BacktestJob | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    void listDeployStrategies().then((rows) => {
      setStrategies(rows);
      if (rows.length) {
        setStrategy((prev) => (rows.some((r) => r.name === prev) ? prev : rows[0].name));
      }
    });
  }, []);

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  useEffect(() => {
    if (!jobId) return;
    const poll = async () => {
      try {
        const next = await getTradingJob(jobId);
        setJob(next);
        if (isTerminal(next.status) && pollRef.current) {
          clearInterval(pollRef.current);
          pollRef.current = null;
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : "Polling failed");
      }
    };
    void poll();
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(() => void poll(), 1200);
  }, [jobId]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    setJob(null);
    try {
      const res = await startTradingRun({
        strategy,
        date,
        dry_run: dryRun,
      });
      setJobId(res.job_id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to start paper run");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="panel space-y-6 rounded-md p-8">
      <h2 className="font-display text-heading-sm font-[360] text-starlight">Paper execution</h2>
      <form onSubmit={onSubmit} className="grid gap-4 md:grid-cols-4 md:items-end">
        <label className="flex flex-col gap-2 text-body-sm text-silver">
          Strategy
          <select
            value={strategy}
            onChange={(e) => setStrategy(e.target.value)}
            className="rounded-md border border-lead/50 bg-deep-space px-4 py-3 text-starlight"
          >
            {(strategies.length ? strategies : [{ name: "adaptive_rotation", config: "", runner: "" }]).map((s) => (
              <option key={s.name} value={s.name}>
                {s.name}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-2 text-body-sm text-silver">
          Decision date
          <input
            type="date"
            className="rounded-md border border-lead/50 bg-deep-space px-4 py-3 text-starlight"
            value={date}
            onChange={(e) => setDate(e.target.value)}
          />
        </label>
        <label className="flex items-center gap-3 text-body-sm text-silver">
          <input type="checkbox" checked={dryRun} onChange={(e) => setDryRun(e.target.checked)} />
          Dry run (recommended)
        </label>
        <button
          type="submit"
          disabled={submitting}
          className="rounded-[32px] bg-mercury-blue px-6 py-3 text-body-sm font-[480] text-pure-white disabled:opacity-60"
        >
          {submitting ? "Launching…" : dryRun ? "Preview paper orders" : "Execute paper rebalance"}
        </button>
      </form>

      {error ? <p className="text-body-sm text-red-200">{error}</p> : null}
      {job ? (
        <div className="space-y-3 rounded-md border border-lead/35 bg-deep-space/70 p-4 text-body-sm text-silver">
          <p>
            Job <code className="text-ghost-blue">{job.job_id}</code> — <span className="text-starlight">{job.status}</span>
          </p>
          {job.message ? <p className="text-red-200">{job.message}</p> : null}
          {job.stderr_tail ? (
            <pre className="max-h-40 overflow-auto rounded-md border border-lead/40 p-3 text-caption">{job.stderr_tail}</pre>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
