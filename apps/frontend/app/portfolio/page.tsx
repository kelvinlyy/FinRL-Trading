import Link from "next/link";
import { SiteHeader } from "@/components/site-header";
import { getPortfolioOverview } from "@/lib/api";

export const dynamic = "force-dynamic";

function toPct(v: number | undefined) {
  if (typeof v !== "number" || Number.isNaN(v)) return "n/a";
  return `${(v * 100).toFixed(2)}%`;
}

export default async function PortfolioPage() {
  const overview = await getPortfolioOverview();
  return (
    <main>
      <SiteHeader />
      <div className="mx-auto max-w-[1200px] px-6 py-16">
        <header className="mb-12 max-w-3xl space-y-4 border-b border-lead/25 pb-10">
          <p className="text-caption uppercase tracking-[0.24em] text-silver">Console</p>
          <h1 className="font-display text-heading-lg font-[360] text-starlight">Portfolio analysis</h1>
          <p className="text-subheading text-silver">
            Portfolio metrics and chart analysis are centered in{" "}
            <Link href="/results" className="text-ghost-blue underline-offset-4 hover:underline">
              Results
            </Link>
            . This page now summarizes latest-run exposures and trading activity.
          </p>
        </header>

        <section className="panel space-y-4 rounded-md p-8 text-body-sm text-silver">
          {!overview?.has_run ? (
            <p>No run data found yet. Launch a backtest from Home or check `src/strategies/output/weights/adaptive_rotation`.</p>
          ) : (
            <>
              <p>
                Latest run: <code className="text-ghost-blue">{overview.run?.label}</code>
              </p>
              <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
                <p>Total return: {toPct(overview.kpis.total_return)}</p>
                <p>Annual return: {toPct(overview.kpis.annual_return)}</p>
                <p>Max drawdown: {toPct(overview.kpis.max_drawdown)}</p>
                <p>Sharpe ratio: {overview.kpis.sharpe_ratio?.toFixed?.(3) ?? "n/a"}</p>
                <p>Active positions: {overview.kpis.active_positions ?? 0}</p>
                <p>Top-3 concentration: {overview.kpis.top3_weight_pct?.toFixed?.(2) ?? "0.00"}%</p>
              </div>
              <div>
                <p className="mb-2 text-caption uppercase tracking-[0.2em] text-silver">Current allocation</p>
                <ul className="grid gap-1 md:grid-cols-2">
                  {overview.positions.slice(0, 12).map((p) => (
                    <li key={p.symbol}>
                      <code className="text-ghost-blue">{p.symbol}</code>: {p.weight_pct.toFixed(2)}%
                    </li>
                  ))}
                </ul>
              </div>
            </>
          )}
        </section>
      </div>
    </main>
  );
}
