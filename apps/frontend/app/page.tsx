import Link from "next/link";
import { ConfigureUniverseEditor } from "@/components/configure-universe-editor";
import { RunBacktestPanel } from "@/components/run-backtest-panel";
import { SiteHeader } from "@/components/site-header";
import { loadAdaptiveRotationFromDisk } from "@/lib/load-adaptive-rotation-disk";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  const cfg = loadAdaptiveRotationFromDisk();

  return (
    <main>
      <SiteHeader />
      <div className="mx-auto max-w-[1200px] px-6 py-16">
        <header className="mb-16 max-w-3xl space-y-4 border-b border-lead/25 pb-12">
          <p className="text-caption uppercase tracking-[0.24em] text-silver">FinRL-X</p>
          <h1 className="font-display text-heading-lg font-[360] leading-[1.12] tracking-[0.02em] text-starlight">
            Configure your backtest, then run it.
          </h1>
          <p className="text-subheading text-silver">
            One place for Adaptive Rotation parameters and the browser job. Inspect local CSV / SQLite stats on{" "}
            <Link href="/data" className="text-ghost-blue underline-offset-4 hover:underline">
              Data
            </Link>
            , runtime flags on{" "}
            <Link href="/settings" className="text-ghost-blue underline-offset-4 hover:underline">
              Settings
            </Link>
            . After a range backtest finishes, open{" "}
            <Link href="/results" className="text-ghost-blue underline-offset-4 hover:underline">
              Results
            </Link>{" "}
            for charts and exports.
          </p>
        </header>

        {!cfg ? (
          <div className="rounded-md border border-amber-500/40 bg-amber-500/10 p-6 text-body-sm text-starlight">
            Could not find or parse{" "}
            <code className="text-caption text-ghost-blue">src/strategies/AdaptiveRotationConf_v1.2.1.yaml</code> from
            this Next.js working directory. Run <code className="text-caption text-ghost-blue">npm run dev</code> from{" "}
            <code className="text-caption text-ghost-blue">apps/frontend</code> (or set cwd so the repo{" "}
            <code className="text-caption text-ghost-blue">src/strategies</code> tree is discoverable), then hard-refresh.
            Saving changes still requires the FastAPI stack on port 8000.
          </div>
        ) : (
          <>
            <section id="configure" className="scroll-mt-28">
              <p className="mb-6 text-caption uppercase tracking-[0.2em] text-silver">Parameters</p>
              <ConfigureUniverseEditor key={cfg.config_mtime ?? 0} initialConfig={cfg} />
            </section>

            <section id="run-backtest" className="mt-20 scroll-mt-28 border-t border-lead/25 pt-16">
              <div className="mb-10 max-w-3xl space-y-4">
                <p className="text-caption uppercase tracking-[0.2em] text-silver">Run</p>
                <h2 className="font-display text-heading font-[360] text-starlight">Backtest job</h2>
                <p className="text-subheading text-silver">
                  Uses on-disk prices in <code className="text-caption text-ghost-blue">data/fmp_daily</code> (no Yahoo
                  fetch from this UI). Missing tickers or short ranges are reported before the job starts. Outputs go to{" "}
                  <code className="text-caption text-ghost-blue">src/strategies/output/weights/adaptive_rotation</code>.
                </p>
              </div>
              <RunBacktestPanel />
            </section>
          </>
        )}
      </div>
    </main>
  );
}
