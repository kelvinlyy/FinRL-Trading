import Link from "next/link";
import { HomeBacktestFlow } from "@/components/home-backtest-flow";
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
            Choose a deploy strategy and run window first. For Adaptive Rotation, tune universe YAML below the job. Inspect
            local CSV / SQLite stats on{" "}
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

        <HomeBacktestFlow initialAdaptiveConfig={cfg} />
      </div>
    </main>
  );
}
