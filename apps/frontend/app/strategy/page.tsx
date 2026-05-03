import { SiteHeader } from "@/components/site-header";

const groups = [
  {
    name: "Growth Tech",
    tickers: ["AAPL", "MSFT", "NVDA", "META", "AMZN", "GOOGL", "TSLA"],
    note: "Momentum engine. Competes for active allocation when relative strength vs QQQ is positive.",
  },
  {
    name: "Real Assets",
    tickers: ["XOM", "CVX", "COP", "FCX", "BHP", "GLD", "SLV"],
    note: "Inflation and commodity sleeve. Often provides leadership outside pure tech regimes.",
  },
  {
    name: "Defensive",
    tickers: ["TLT", "IEF", "XLU", "XLV", "IAU", "SHY", "UUP"],
    note: "Capital preservation sleeve. Activated when defensive assets outperform on a risk-adjusted basis.",
  },
];

export default function StrategyPage() {
  return (
    <main>
      <SiteHeader />
      <section className="mx-auto flex max-w-[1200px] flex-col gap-16 px-6 py-20">
        <div className="max-w-3xl">
          <p className="eyebrow">Strategy anatomy</p>
          <h1 className="mt-5 text-[42px] font-[360] leading-[1.15] tracking-[0.02em] text-starlight md:text-[65px] md:leading-[1.1]">
            A weekly rotation engine, not a black box.
          </h1>
          <p className="mt-6 text-subheading text-silver">
            The Adaptive Rotation strategy evaluates three fixed asset groups using point-in-time prices. It activates up to
            two groups each week, selects the strongest stocks inside each group, then applies regime and stop-loss controls.
          </p>
        </div>

        <section className="grid gap-4 md:grid-cols-3">
          {groups.map((group) => (
            <article key={group.name} className="rounded-md border border-lead/35 bg-midnight-slate p-6">
              <h2 className="text-heading-sm font-[420] text-starlight">{group.name}</h2>
              <p className="mt-3 text-body-sm text-silver">{group.note}</p>
              <div className="mt-8 flex flex-wrap gap-2">
                {group.tickers.map((ticker) => (
                  <span key={ticker} className="rounded-full bg-graphite px-3 py-1 text-caption text-starlight">
                    {ticker}
                  </span>
                ))}
              </div>
            </article>
          ))}
        </section>

        <section className="grid gap-8 border-y border-lead/35 py-12 md:grid-cols-2">
          <div>
            <p className="eyebrow">Activation rule</p>
            <h2 className="mt-4 text-heading font-[360] text-starlight">Groups must beat QQQ, then rank by information ratio.</h2>
          </div>
          <div className="space-y-5 text-body text-silver">
            <p>
              Every week, each group is treated as an equal-weight basket. The engine computes 12-week excess return against
              QQQ and a robust information ratio. Groups with negative excess return are filtered out.
            </p>
            <p>
              Up to two remaining groups are activated. If no group qualifies, the strategy falls back to a defensive basket
              of SPY, QQQ, IAU, XLU, and XLV.
            </p>
          </div>
        </section>

        <section className="grid gap-8 border-b border-lead/35 pb-12 md:grid-cols-2">
          <div>
            <p className="eyebrow">Stock selection</p>
            <h2 className="mt-4 text-heading font-[360] text-starlight">Residual momentum ranks stocks against their peers.</h2>
          </div>
          <div className="space-y-5 text-body text-silver">
            <p>
              Inside each active group, stock return is compared to group return. The residual is normalized with a robust
              MAD-based z-score, then the strongest stocks are selected for the portfolio.
            </p>
            <p>
              Regime controls alter risk budget: risk-on allows full exposure, neutral raises cash, risk-off reduces group
              caps, and fast risk-off reacts to short-term shocks.
            </p>
          </div>
        </section>
      </section>
    </main>
  );
}
