import Link from "next/link";
import { RuntimeConfigPanel } from "@/components/runtime-config-panel";
import { SiteHeader } from "@/components/site-header";

export const dynamic = "force-dynamic";

export default function SettingsPage() {
  return (
    <main>
      <SiteHeader />
      <div className="mx-auto max-w-[1200px] px-6 py-16">
        <header className="mb-12 max-w-3xl space-y-4 border-b border-lead/25 pb-10">
          <p className="text-caption uppercase tracking-[0.24em] text-silver">Console</p>
          <h1 className="font-display text-heading-lg font-[360] text-starlight">Settings</h1>
          <p className="text-subheading text-silver">
            Non-secret runtime metadata from <code className="text-caption text-ghost-blue">src/config/settings.py</code>{" "}
            and environment. Edit <code className="text-caption text-ghost-blue">.env</code> on the host; this page does
            not expose secret values.
          </p>
        </header>
        <RuntimeConfigPanel />
        <p className="mt-10 text-body-sm text-silver">
          <Link href="/" className="text-ghost-blue underline-offset-4 hover:underline">
            ← Home
          </Link>
        </p>
      </div>
    </main>
  );
}
