import Link from "next/link";
import { DataOverviewPanel } from "@/components/data-overview-panel";
import { SiteHeader } from "@/components/site-header";

export const dynamic = "force-dynamic";

export default function DataPage() {
  return (
    <main>
      <SiteHeader />
      <div className="mx-auto max-w-[1200px] px-6 py-16">
        <header className="mb-12 max-w-3xl space-y-4 border-b border-lead/25 pb-10">
          <p className="text-caption uppercase tracking-[0.24em] text-silver">Console</p>
          <h1 className="font-display text-heading-lg font-[360] text-starlight">Data layer</h1>
          <p className="text-subheading text-silver">
            Coverage of on-disk prices and SQLite stats from the shared Python stack. Configure universe on{" "}
            <Link href="/" className="text-ghost-blue underline-offset-4 hover:underline">
              Home
            </Link>
            .
          </p>
        </header>
        <DataOverviewPanel />
      </div>
    </main>
  );
}
