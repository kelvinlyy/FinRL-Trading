"use client";

import Link from "next/link";
import { useCallback, useMemo, useState } from "react";
import { putAdaptiveRotationConfig } from "@/lib/api";
import type { AdaptiveRotationConfig, AdaptiveRotationWritePayload } from "@/lib/types";

function parseTickers(raw: string): string[] {
  const parts = raw.split(/[\n,;\t]+/).map((s) => s.trim()).filter(Boolean);
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

function groupTextsFromConfig(cfg: AdaptiveRotationConfig): Record<string, string> {
  const o: Record<string, string> = {};
  for (const g of cfg.asset_groups) {
    o[g.id] = symbolsToText(g.symbols);
  }
  return o;
}

function benchTextFromConfig(cfg: AdaptiveRotationConfig): string {
  const syms = cfg.excess_return_benchmark_symbols;
  if (syms && syms.length > 0) {
    return symbolsToText(syms);
  }
  if (cfg.excess_return_benchmark) {
    return String(cfg.excess_return_benchmark).trim();
  }
  return "QQQ";
}

export function ConfigureUniverseEditor({ initialConfig }: { initialConfig: AdaptiveRotationConfig }) {
  const [config, setConfig] = useState<AdaptiveRotationConfig>(initialConfig);
  const [fbText, setFbText] = useState(() => symbolsToText(initialConfig.portfolio_fallback.symbols));
  const [benchText, setBenchText] = useState(() => benchTextFromConfig(initialConfig));
  const [groupTexts, setGroupTexts] = useState(() => groupTextsFromConfig(initialConfig));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const benchPreview = useMemo(() => parseTickers(benchText), [benchText]);
  const fallbackPreview = useMemo(() => parseTickers(fbText), [fbText]);
  const groupPreviews = useMemo(() => {
    const m: Record<string, string[]> = {};
    for (const g of config.asset_groups) {
      m[g.id] = parseTickers(groupTexts[g.id] ?? "");
    }
    return m;
  }, [config.asset_groups, groupTexts]);

  const setMaxAssets = useCallback((id: string, max_assets: number) => {
    const n = Math.min(20, Math.max(1, Math.floor(Number(max_assets)) || 1));
    setConfig((prev) => ({
      ...prev,
      asset_groups: prev.asset_groups.map((g) => (g.id === id ? { ...g, max_assets: n } : g)),
    }));
    setSuccess(null);
    setError(null);
  }, []);

  const onSave = async () => {
    setError(null);
    setSuccess(null);
    setSaving(true);
    try {
      const benchSyms = parseTickers(benchText);
      if (!benchSyms.length) {
        throw new Error("Excess benchmark group needs at least one ticker.");
      }
      const payload: AdaptiveRotationWritePayload = {
        excess_return_benchmark_symbols: benchSyms,
        portfolio_fallback: {
          enabled: config.portfolio_fallback.enabled === true,
          symbols: parseTickers(fbText),
        },
        asset_groups: config.asset_groups.map((g) => ({
          id: g.id,
          max_assets: Math.min(20, Math.max(1, Number(g.max_assets) || 1)),
          symbols: parseTickers(groupTexts[g.id] ?? ""),
        })),
      };
      for (const g of payload.asset_groups) {
        if (!g.symbols.length) {
          throw new Error(`Group ${g.id} needs at least one ticker.`);
        }
      }
      if (!payload.portfolio_fallback.symbols.length) {
        throw new Error("Fallback needs at least one ticker.");
      }
      const next = await putAdaptiveRotationConfig(payload);
      setConfig(next);
      setBenchText(benchTextFromConfig(next));
      setFbText(symbolsToText(next.portfolio_fallback.symbols));
      setGroupTexts(groupTextsFromConfig(next));
      setSuccess("Saved. YAML on disk was updated (full-file rewrite). Add or refresh CSVs under data/fmp_daily as needed.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <section className="mb-12 rounded-md border border-lead/35 bg-midnight-slate/80 p-6 md:p-8">
        <h2 className="font-display text-heading-sm font-[420] text-starlight">Edit combination</h2>
        <p className="mt-3 text-body-sm text-silver">
          Saving runs validation and writes{" "}
          <code className="text-caption text-ghost-blue">{config.config_file}</code>. The file is emitted with PyYAML
          (structure preserved; comments and manual formatting in that file may be lost). Set{" "}
          <code className="text-caption text-starlight/90">FINRL_DISABLE_CONFIG_WRITE=1</code> in the API environment
          to block writes. Price files still live under{" "}
          <code className="text-caption text-ghost-blue">{config.data_daily_dir}</code> — use{" "}
          <Link href="/#run-backtest" className="text-ghost-blue hover:underline">
            Run backtest
          </Link>{" "}
          to verify coverage.
        </p>
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
        <div className="mt-8 flex flex-wrap gap-4">
          <button
            type="button"
            disabled={saving}
            onClick={() => void onSave()}
            className="rounded-[32px] bg-mercury-blue px-6 py-4 text-body-sm font-[480] text-pure-white disabled:opacity-50"
          >
            {saving ? "Saving…" : "Save universe"}
          </button>
        </div>
      </section>

      <section className="mb-12 rounded-md border border-lead/35 bg-midnight-slate/50 p-6 md:p-8">
        <p className="eyebrow">Fallback sleeve</p>
        <h2 className="mt-2 font-display text-heading-sm font-[420] text-starlight">portfolio.fallback</h2>
        <label className="mt-6 flex cursor-pointer items-center gap-3 text-body-sm text-silver">
          <input
            type="checkbox"
            className="h-4 w-4 rounded border-lead text-mercury-blue"
            checked={config.portfolio_fallback.enabled === true}
            onChange={(e) => {
              setConfig((c) => ({
                ...c,
                portfolio_fallback: { ...c.portfolio_fallback, enabled: e.target.checked },
              }));
              setSuccess(null);
              setError(null);
            }}
          />
          Enabled
        </label>
        <label className="mt-6 block text-caption uppercase tracking-[0.18em] text-silver" htmlFor="fb-syms">
          Symbols (comma or line-separated)
        </label>
        <textarea
          id="fb-syms"
          rows={4}
          className="mt-2 w-full max-w-2xl rounded-md border border-lead/50 bg-deep-space px-4 py-3 font-mono text-body-sm text-starlight outline-none focus:border-ghost-blue"
          value={fbText}
          onChange={(e) => {
            setFbText(e.target.value);
            setSuccess(null);
            setError(null);
          }}
        />
        <p className="mt-2 text-caption text-silver">
          Parsed ({fallbackPreview.length}):{" "}
          {fallbackPreview.length ? (
            <code className="text-mercury-blue">{fallbackPreview.join(", ")}</code>
          ) : (
            "—"
          )}
        </p>
      </section>

      <section className="mb-12">
        <p className="eyebrow">Rotating groups</p>
        <h2 className="mt-2 font-display text-heading font-[360] text-starlight">asset_groups</h2>
        <div className="mt-10 grid gap-6 md:grid-cols-1 lg:grid-cols-3">
          {config.asset_groups.map((g) => {
            const preview = groupPreviews[g.id] ?? [];
            return (
              <article key={g.id} className="rounded-md border border-lead/35 bg-midnight-slate p-6">
                <h3 className="font-display text-heading-sm font-[420] text-starlight">{g.title}</h3>
                <p className="mt-2 text-caption uppercase tracking-[0.18em] text-silver">{g.id}</p>
                <label className="mt-6 block text-caption uppercase tracking-[0.18em] text-silver" htmlFor={`ma-${g.id}`}>
                  Max assets active
                </label>
                <input
                  id={`ma-${g.id}`}
                  type="number"
                  min={1}
                  max={20}
                  className="mt-2 w-full max-w-[120px] rounded-md border border-lead/50 bg-deep-space px-4 py-2 font-mono text-body-sm text-starlight outline-none focus:border-ghost-blue"
                  value={g.max_assets ?? 2}
                  onChange={(e) => setMaxAssets(g.id, Number(e.target.value))}
                />
                <label className="mt-6 block text-caption uppercase tracking-[0.18em] text-silver" htmlFor={`sy-${g.id}`}>
                  Symbols
                </label>
                <textarea
                  id={`sy-${g.id}`}
                  rows={10}
                  className="mt-2 w-full rounded-md border border-lead/50 bg-deep-space px-4 py-3 font-mono text-body-sm text-starlight outline-none focus:border-ghost-blue"
                  value={groupTexts[g.id] ?? ""}
                  onChange={(e) => {
                    setGroupTexts((prev) => ({ ...prev, [g.id]: e.target.value }));
                    setSuccess(null);
                    setError(null);
                  }}
                />
                <p className="mt-2 text-caption text-silver">
                  Parsed ({preview.length})
                  {preview.length ? (
                    <>
                      : <span className="font-mono text-starlight/80">{preview.slice(0, 8).join(", ")}</span>
                      {preview.length > 8 ? "…" : ""}
                    </>
                  ) : null}
                </p>
              </article>
            );
          })}
        </div>
      </section>

      <section className="mb-12 rounded-md border border-lead/30 bg-graphite/15 p-6">
        <p className="eyebrow">Chart baselines</p>
        <p className="mt-2 text-body-sm text-silver">
          Buy-and-hold lines use closes from{" "}
          <code className="text-caption text-ghost-blue">{config.data_daily_dir}</code> when these files exist:{" "}
          <code className="text-caption text-starlight/90">
            {config.baseline_price_csv_candidates.map((s) => `${s}_daily.csv`).join(", ")}
          </code>
          . Present:{" "}
          {config.baseline_price_csv_present.length ? (
            <code className="text-caption text-mercury-blue">{config.baseline_price_csv_present.join(", ")}</code>
          ) : (
            <span>none of the listed candidates</span>
          )}
          . Editing tickers above does not create CSVs.
        </p>
      </section>

      <section className="rounded-md border border-lead/35 bg-midnight-slate/50 p-6 md:p-8">
        <p className="eyebrow">Benchmark</p>
        <h2 className="mt-2 font-display text-heading-sm font-[420] text-starlight">Excess return vs (equal-weight group)</h2>
        <p className="mt-3 max-w-3xl text-body-sm text-silver">
          Same mechanics as a rotation sleeve: daily returns are averaged across these tickers, then each group is
          scored versus that composite. YAML keys:{" "}
          <code className="text-caption text-ghost-blue">benchmark.excess_return_benchmark_symbols</code> and{" "}
          <code className="text-caption text-ghost-blue">benchmark.excess_return_benchmark</code> (first symbol,
          legacy).
        </p>
        <label className="mt-6 block text-caption uppercase tracking-[0.18em] text-silver" htmlFor="bench">
          Benchmark tickers (comma or line-separated)
        </label>
        <textarea
          id="bench"
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
      </section>
    </>
  );
}
