import Link from "next/link";
import { SiteHeader } from "@/components/site-header";

export default function PortfolioPage() {
  return (
    <main>
      <SiteHeader />
      <div className="mx-auto max-w-[1200px] px-6 py-16">
        <header className="mb-12 max-w-3xl space-y-4 border-b border-lead/25 pb-10">
          <p className="text-caption uppercase tracking-[0.24em] text-silver">Console</p>
          <h1 className="font-display text-heading-lg font-[360] text-starlight">Portfolio analysis</h1>
          <p className="text-subheading text-silver">
            Portfolio metrics and chart analysis are now centered in{" "}
            <Link href="/results" className="text-ghost-blue underline-offset-4 hover:underline">
              Results
            </Link>
            . Dedicated multi-account portfolio analytics from legacy Streamlit are intentionally deferred.
          </p>
        </header>

        <section className="panel space-y-4 rounded-md p-8 text-body-sm text-silver">
          <p>
            Canonical path today: inspect run-level performance, drawdown, regimes, timeline, and trade log in{" "}
            <code className="text-ghost-blue">/results</code>.
          </p>
          <p>
            Deferred areas: broker account-level P&amp;L aggregation, live position decomposition, and intraday exposure
            monitoring.
          </p>
          <p>
            This explicit placeholder replaces the old implicit Streamlit-only path so the apps stack remains the single
            web entry point.
          </p>
        </section>
      </div>
    </main>
  );
}
