import Link from "next/link";
import { SiteHeader } from "@/components/site-header";
import { getTradingStatus } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function TradingPage() {
  const status = await getTradingStatus();

  return (
    <main>
      <SiteHeader />
      <div className="mx-auto max-w-[1200px] px-6 py-16">
        <header className="mb-12 max-w-3xl space-y-4 border-b border-lead/25 pb-10">
          <p className="text-caption uppercase tracking-[0.24em] text-silver">Console</p>
          <h1 className="font-display text-heading-lg font-[360] text-starlight">Trading readiness</h1>
          <p className="text-subheading text-silver">
            Live and paper execution stay CLI-only in this migration phase. This page is the canonical status surface for
            what is supported in the apps stack.
          </p>
        </header>

        <section className="panel space-y-6 rounded-md p-8">
          {status ? (
            <>
              <p className="text-body-sm text-silver">{status.message}</p>
              <ul className="list-inside list-disc space-y-1 text-body-sm text-silver">
                <li>
                  API execution enabled:{" "}
                  <span className={status.execution_enabled ? "text-emerald-300/90" : "text-amber-200"}>
                    {status.execution_enabled ? "yes" : "no"}
                  </span>
                </li>
                <li>
                  CLI paper-trade ready:{" "}
                  <span className={status.can_paper_trade_from_cli ? "text-emerald-300/90" : "text-amber-200"}>
                    {status.can_paper_trade_from_cli ? "yes" : "no"}
                  </span>
                </li>
                <li>
                  Alpaca URL: <code className="text-ghost-blue">{status.alpaca.base_url}</code>
                </li>
              </ul>
              <div>
                <p className="text-caption uppercase tracking-[0.2em] text-silver">Deferred implementation notes</p>
                <ol className="mt-2 list-inside list-decimal space-y-1 text-body-sm text-silver">
                  {status.next_steps.map((step) => (
                    <li key={step}>{step}</li>
                  ))}
                </ol>
              </div>
            </>
          ) : (
            <p className="text-body-sm text-red-200">Could not load /api/trading/status (is the API on port 8000?).</p>
          )}
        </section>
        <p className="mt-10 text-body-sm text-silver">
          Use <code className="text-ghost-blue">./deploy.sh --strategy adaptive_rotation --mode paper --dry-run</code> for
          paper-trading preview from the repo root.
        </p>
        <p className="mt-3 text-body-sm text-silver">
          <Link href="/" className="text-ghost-blue underline-offset-4 hover:underline">
            ← Home
          </Link>
        </p>
      </div>
    </main>
  );
}
