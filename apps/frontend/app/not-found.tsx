import Link from "next/link";
import { SiteHeader } from "@/components/site-header";

export default function NotFound() {
  return (
    <main>
      <SiteHeader />
      <div className="mx-auto max-w-[560px] px-6 py-24 text-center">
        <p className="text-caption uppercase tracking-[0.24em] text-silver">404</p>
        <h1 className="mt-4 font-display text-heading-lg font-[360] text-starlight">This page could not be found.</h1>
        <p className="mt-4 text-body text-silver">
          This app only exposes Home (configure + run) and Results. Older URLs may redirect to Home.
        </p>
        <div className="mt-10 flex flex-wrap justify-center gap-4">
          <Link className="rounded-[32px] bg-mercury-blue px-6 py-4 text-body-sm font-[480] text-pure-white" href="/">
            Home
          </Link>
          <Link
            className="rounded-[40px] border border-lead/50 px-6 py-4 text-body-sm font-[480] text-starlight hover:border-ghost-blue"
            href="/results"
          >
            Results
          </Link>
        </div>
      </div>
    </main>
  );
}
