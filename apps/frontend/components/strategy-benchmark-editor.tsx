"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { getStrategyBenchmark, putStrategyBenchmark } from "@/lib/api";

function parseTickers(raw: string): string[] {
  const parts = raw
    .split(/[\n,;\t]+/)
    .map((s) => s.trim())
    .filter(Boolean);
  const seen = new Set<string>();
  const out: string[] = [];
  for (const p of parts) {
    const u = p.toUpperCase();
    if (!seen.has(u)) {
      seen.add(u);
      out.push(u);
    }
  }
  return out;
}

function symbolsToText(symbols: string[]): string {
  return symbols.join("\n");
}

type Props = { deployStrategy: string };

export function StrategyBenchmarkEditor({ deployStrategy }: Props) {
  const [benchText, setBenchText] = useState("");
  const [configFile, setConfigFile] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const benchPreview = useMemo(() => parseTickers(benchText), [benchText]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    setSuccess(null);
    try {
      const row = await getStrategyBenchmark(deployStrategy);
      if (!row) {
        setBenchText("");
        setConfigFile(null);
        setError(
          `Could not load benchmark for “${deployStrategy}”. Is the API running and the strategy registered in deploy.sh?`,
        );
        return;
      }
      setConfigFile(row.config_file);
      setBenchText(symbolsToText(row.excess_return_benchmark_symbols ?? []));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Load failed.");
    } finally {
      setLoading(false);
    }
  }, [deployStrategy]);

  useEffect(() => {
    void load();
  }, [load]);

  const onSave = async () => {
    setError(null);
    setSuccess(null);
    setSaving(true);
    try {
      const syms = parseTickers(benchText);
      if (!syms.length) {
        throw new Error("Benchmark needs at least one ticker.");
      }
      const next = await putStrategyBenchmark(deployStrategy, syms);
      setConfigFile(next.config_file);
      setBenchText(symbolsToText(next.excess_return_benchmark_symbols ?? []));
      setSuccess(`Saved benchmark to ${next.config_file}.`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="mt-12 rounded-md border border-lead/35 bg-midnight-slate/50 p-6 md:p-8">
      <p className="eyebrow">Benchmark</p>
      <h2 className="mt-2 font-display text-heading-sm font-[420] text-starlight">
        Excess return vs (equal-weight group)
      </h2>
      <p className="mt-3 max-w-3xl text-body-sm text-silver">
        Applies to the deploy strategy <code className="text-ghost-blue">{deployStrategy}</code> (its YAML under{" "}
        <code className="text-caption text-ghost-blue">benchmark.excess_return_benchmark_symbols</code>). Charts and
        composite curves use this for that strategy&apos;s runs. CSV coverage:{" "}
        <Link href="/data" className="text-ghost-blue underline-offset-4 hover:underline">
          Data
        </Link>
        .
      </p>
      {configFile ? (
        <p className="mt-2 text-caption text-silver">
          File: <code className="text-starlight/90">{configFile}</code>
        </p>
      ) : null}
      {loading ? <p className="mt-6 text-body-sm text-silver">Loading benchmark…</p> : null}
      {error ? (
        <p className="mt-4 rounded-md border border-red-500/40 bg-red-500/10 px-4 py-3 text-body-sm text-red-100">
          {error}
        </p>
      ) : null}
      {success ? (
        <p className="mt-4 rounded-md border border-emerald-500/40 bg-emerald-500/10 px-4 py-3 text-body-sm text-emerald-100">
          {success}
        </p>
      ) : null}
      {!loading ? (
        <>
          <label className="mt-6 block text-caption uppercase tracking-[0.18em] text-silver" htmlFor="strategy-bench">
            Benchmark tickers (comma or line-separated)
          </label>
          <textarea
            id="strategy-bench"
            rows={4}
            className="mt-2 w-full max-w-2xl rounded-md border border-lead/50 bg-deep-space px-4 py-3 font-mono text-body-sm text-starlight outline-none focus:border-ghost-blue"
            value={benchText}
            onChange={(e) => {
              setBenchText(e.target.value);
              setSuccess(null);
              setError(null);
            }}
          />
          <p className="mt-2 text-caption text-silver">
            Parsed ({benchPreview.length}):{" "}
            {benchPreview.length ? (
              <code className="text-mercury-blue">{benchPreview.join(", ")}</code>
            ) : (
              "—"
            )}
            {benchPreview.length > 1 ? (
              <span className="ml-2 text-silver/80">· composite: {benchPreview.join(" + ")}</span>
            ) : null}
          </p>
          <div className="mt-6 flex flex-wrap gap-4">
            <button
              type="button"
              disabled={saving}
              onClick={() => void onSave()}
              className="rounded-[32px] bg-mercury-blue px-6 py-4 text-body-sm font-[480] text-pure-white disabled:opacity-50"
            >
              {saving ? "Saving…" : "Save benchmark"}
            </button>
          </div>
        </>
      ) : null}
    </section>
  );
}
