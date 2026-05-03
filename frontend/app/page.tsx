import Link from "next/link";
import { SiteHeader } from "@/components/site-header";
import { MetricCard } from "@/components/metric-card";
import { ResultsSummary } from "@/components/results-summary";
import { getResults } from "@/lib/api";

export default async function HomePage() {
  const results = await getResults();
  const latest = results[0];

  return (
    <main>
      <SiteHeader />
      <section className="mx-auto flex min-h-[78vh] max-w-[1200px] flex-col justify-center px-6 py-24 md:py-32">
        <p className="mb-16 text-caption uppercase tracking-[0.24em] text-silver">
          FinRL-X / Adaptive Rotation
        </p>
        <div className="max-w-[880px]">
          <h1 className="text-[49px] font-light leading-[1.1] tracking-[0.02em] text-starlight md:text-[65px]">
            A twilight command center for reading strategy behavior.
          </h1>
          <p className="mt-6 max-w-[720px] text-[21px] font-light leading-[1.35] text-silver">
            Review real Adaptive Rotation backtests, group rotations, regime shifts,
            and every buy or sell produced by the strategy.
          </p>
        </div>
        <div className="mt-40 flex flex-wrap gap-16">
          <Link className="rounded-[32px] bg-mercury-blue px-6 py-4 text-body-sm font-[480] text-pure-white" href="/results">
            View latest backtest
          </Link>
          <Link className="rounded-[40px] bg-ghost-blue/15 px-6 py-4 text-body-sm font-[480] text-starlight" href="/strategy">
            Understand the strategy
          </Link>
        </div>
      </section>

      <section className="mx-auto max-w-[1200px] px-6 pb-28">
        <div className="grid gap-16 md:grid-cols-4">
          <MetricCard
            label="Saved runs"
            value={String(results.length)}
            detail="Read from backend outputs"
          />
          <MetricCard
            label="Latest period"
            value={latest ? `${latest.start} → ${latest.end}` : "No runs"}
            detail="Adaptive Rotation"
          />
          <MetricCard
            label="Trade log"
            value={latest ? `${latest.counts?.trade_rows ?? 0}` : "0"}
            detail="Buy/sell rows"
          />
          <MetricCard
            label="Data mode"
            value="Real"
            detail="Yahoo CSV + generated artifacts"
          />
        </div>

        {latest ? (
          <div className="mt-80">
            <ResultsSummary run={latest} />
          </div>
        ) : (
          <div className="mt-80 border-y border-lead/40 py-32 text-silver">
            No saved Adaptive Rotation outputs found. Run the Python backtest to
            generate enhanced chart and trade-log artifacts.
          </div>
        )}
      </section>
    </main>
  );
}
