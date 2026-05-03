import Link from "next/link";
import { getRun, getRuns, getVisualization } from "@/lib/api";
import { ResultsSummary } from "@/components/results-summary";
import { SiteHeader } from "@/components/site-header";
import { InteractiveBacktestChart } from "@/components/interactive-backtest-chart";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

function absoluteUrl(path: string | undefined) {
  if (!path) return "#";
  if (path.startsWith("http")) return path;
  return `${API_BASE}${path}`;
}

export default async function ResultsPage({
  searchParams,
}: {
  searchParams?: Promise<{ run?: string }>;
}) {
  const runs = await getRuns();
  const params = await searchParams;
  const selectedId = params?.run ?? runs[0]?.id;
  const [selectedRun, visualization] = await Promise.all([
    selectedId ? getRun(selectedId) : Promise.resolve(undefined),
    selectedId ? getVisualization(selectedId) : Promise.resolve(undefined),
  ]);

  return (
    <main>
      <SiteHeader />
      <div className="mx-auto flex max-w-[1200px] flex-col gap-20 px-6 py-20">
      <section className="space-y-6">
        <p className="text-caption uppercase tracking-[0.24em] text-silver">Results</p>
        <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-3xl space-y-5">
            <h1 className="font-display text-heading-lg font-[360] leading-[1.15] tracking-[0.02em] text-starlight">
              Backtest charts and exports.
            </h1>
            <p className="text-subheading leading-[1.4] text-silver">
              Interactive charts load from saved weights and daily price CSVs. Configure and launch new runs from{" "}
              <Link className="text-ghost-blue underline-offset-4 hover:underline" href="/">
                Home
              </Link>
              . A static matplotlib PNG appears here only when that dependency produced one.
            </p>
          </div>
          {selectedRun?.chart_url ? (
            <a
              href={absoluteUrl(selectedRun.chart_url)}
              className="w-fit rounded-[32px] bg-mercury-blue px-6 py-4 text-body-sm font-[480] text-pure-white"
            >
              Download PNG
            </a>
          ) : selectedRun ? (
            <p className="max-w-xs text-body-sm text-silver">
              No static PNG for this run (matplotlib optional). Use the chart below.
            </p>
          ) : null}
        </div>
      </section>

      {runs.length > 1 ? (
        <section className="space-y-4">
          <p className="text-caption uppercase tracking-[0.2em] text-silver">
            Select run
          </p>
          <div className="flex flex-wrap gap-3">
            {runs.map((run) => (
              <a
                key={run.id}
                href={`/results?run=${run.id}`}
                className={`rounded-[32px] border px-5 py-3 text-body-sm ${
                  run.id === selectedId
                    ? "border-mercury-blue bg-mercury-blue text-pure-white"
                    : "border-lead bg-graphite/50 text-starlight hover:border-ghost-blue"
                }`}
              >
                {run.label}
              </a>
            ))}
          </div>
        </section>
      ) : null}

      {selectedRun ? (
        <>
          <ResultsSummary run={selectedRun} />
          {visualization ? (
            <InteractiveBacktestChart data={visualization} />
          ) : (
            <section className="panel rounded-md p-8 text-silver">
              Visualization data is not available for this run.
            </section>
          )}
        </>
      ) : (
        <section className="border border-lead/50 bg-midnight-slate p-10">
          <h2 className="font-display text-heading font-[360] text-starlight">
            No generated runs found.
          </h2>
          <p className="mt-4 text-body text-silver">
            <Link className="text-mercury-blue underline-offset-4 hover:underline" href="/#run-backtest">
              Configure and run a backtest on Home
            </Link>{" "}
            or use the CLI to generate chart and CSV artifacts.
          </p>
        </section>
      )}
      </div>
    </main>
  );
}
