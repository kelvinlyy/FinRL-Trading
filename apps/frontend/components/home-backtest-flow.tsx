"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ConfigureUniverseEditor } from "@/components/configure-universe-editor";
import { RunBacktestPanel } from "@/components/run-backtest-panel";
import { StrategyBenchmarkEditor } from "@/components/strategy-benchmark-editor";
import { listDeployStrategies } from "@/lib/api";
import type { AdaptiveRotationConfig, DeployStrategyRow } from "@/lib/types";

/** Deploy strategy that uses the Adaptive Rotation YAML editor (rotating asset groups). */
const ROLLING_DEPLOY_STRATEGY_ID = "adaptive_rotation";

export function HomeBacktestFlow({ initialAdaptiveConfig }: { initialAdaptiveConfig: AdaptiveRotationConfig | null }) {
  const [deployStrategies, setDeployStrategies] = useState<DeployStrategyRow[]>([]);
  const [deployStrategy, setDeployStrategy] = useState("adaptive_rotation");

  useEffect(() => {
    void listDeployStrategies().then((rows) => {
      setDeployStrategies(rows);
      setDeployStrategy((prev) => {
        if (rows.length === 0) return prev;
        return rows.some((r) => r.name === prev) ? prev : rows[0].name;
      });
    });
  }, []);

  const showRollingParameters = deployStrategy === ROLLING_DEPLOY_STRATEGY_ID;

  return (
    <>
      <section id="run-backtest" className="scroll-mt-28 border-b border-lead/25 pb-20">
        <div className="mb-10 max-w-3xl space-y-4">
          <p className="text-caption uppercase tracking-[0.2em] text-silver">Run</p>
          <h2 className="font-display text-heading font-[360] text-starlight">Backtest job</h2>
          <p className="text-subheading text-silver">
            Pick a deploy strategy first, then set dates or a single decision day. The browser job runs the same{" "}
            <code className="text-caption text-ghost-blue">deploy.sh</code> pipeline as the CLI: it will{" "}
            <span className="text-starlight">download missing daily CSVs</span> into{" "}
            <code className="text-caption text-ghost-blue">data/fmp_daily</code> when needed, then write outputs under your
            strategy&apos;s config paths.
          </p>
        </div>
        <RunBacktestPanel
          deployStrategies={deployStrategies}
          deployStrategy={deployStrategy}
          onDeployStrategyChange={setDeployStrategy}
        />
      </section>

      <section id="configure" className="mt-20 scroll-mt-28">
        <p className="mb-6 text-caption uppercase tracking-[0.2em] text-silver">Parameters</p>
        {showRollingParameters ? (
          <>
            <header className="mb-10 max-w-3xl space-y-4">
              <h2 className="font-display text-heading font-[360] text-starlight">Adaptive Rotation universe</h2>
              <p className="text-subheading text-silver">
                Edit tickers and sleeves for <code className="text-caption text-ghost-blue">adaptive_rotation</code>. Other
                strategies use their YAML on disk from <code className="text-caption text-ghost-blue">deploy.sh</code>{" "}
                registrations. Inspect CSV coverage on{" "}
                <Link href="/data" className="text-ghost-blue underline-offset-4 hover:underline">
                  Data
                </Link>
                .
              </p>
            </header>
            {initialAdaptiveConfig ? (
              <ConfigureUniverseEditor key={initialAdaptiveConfig.config_mtime ?? 0} initialConfig={initialAdaptiveConfig} />
            ) : (
              <div className="rounded-md border border-amber-500/40 bg-amber-500/10 p-6 text-body-sm text-starlight">
                Could not find or parse{" "}
                <code className="text-caption text-ghost-blue">src/strategies/AdaptiveRotationConf_v1.2.1.yaml</code> from
                this Next.js working directory. Run <code className="text-caption text-ghost-blue">npm run dev</code> from{" "}
                <code className="text-caption text-ghost-blue">apps/frontend</code> (or set cwd so the repo{" "}
                <code className="text-caption text-ghost-blue">src/strategies</code> tree is discoverable), then hard-refresh.
                Saving changes still requires the FastAPI stack on port 8000.
              </div>
            )}
          </>
        ) : (
          <div className="max-w-3xl space-y-4 rounded-md border border-lead/35 bg-midnight-slate/50 p-6 md:p-8">
            <h2 className="font-display text-heading-sm font-[420] text-starlight">Strategy parameters</h2>
            <p className="text-body-sm text-silver">
              The in-browser universe editor applies to <code className="text-ghost-blue">adaptive_rotation</code>{" "}
              (rotating asset groups). For <code className="text-ghost-blue">{deployStrategy}</code>, adjust the registered
              config file in the repo and use{" "}
              <Link href="/data" className="text-ghost-blue underline-offset-4 hover:underline">
                Data
              </Link>{" "}
              to confirm CSV coverage before you run.
            </p>
          </div>
        )}
        <StrategyBenchmarkEditor deployStrategy={deployStrategy} />
      </section>
    </>
  );
}
