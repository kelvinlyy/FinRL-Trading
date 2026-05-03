"use client";

import { useCallback, useEffect, useState } from "react";
import { getRuntimePublicConfig } from "@/lib/api";
import type { RuntimePublicConfig } from "@/lib/types";

export function RuntimeConfigPanel() {
  const [cfg, setCfg] = useState<RuntimePublicConfig | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    setErr(null);
    const c = await getRuntimePublicConfig();
    if (!c) setErr("Could not load /api/config/runtime (is the API on port 8000?)");
    setCfg(c);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="panel space-y-6 rounded-md p-8">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h2 className="font-display text-heading-sm font-[360] text-starlight">Runtime (read-only)</h2>
        <button
          type="button"
          onClick={() => void load()}
          className="rounded-[32px] border border-ghost-blue/50 px-5 py-2 text-body-sm text-starlight hover:border-mercury-blue"
        >
          Refresh
        </button>
      </div>
      {err ? <p className="text-body-sm text-red-200">{err}</p> : null}
      {cfg ? (
        <div className="space-y-6 text-body-sm text-silver">
          <p>
            <span className="text-starlight">{cfg.app_name}</span> v{cfg.version} —{" "}
            <code className="text-ghost-blue">{cfg.environment}</code>
          </p>
          <div>
            <p className="text-caption uppercase tracking-[0.2em] text-silver">Paths</p>
            <ul className="mt-2 space-y-1 break-all font-mono text-caption">
              {Object.entries(cfg.paths).map(([k, v]) => (
                <li key={k}>
                  <span className="text-silver/80">{k}: </span>
                  <span className="text-ghost-blue">{v}</span>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <p className="text-caption uppercase tracking-[0.2em] text-silver">Credentials (booleans only)</p>
            <ul className="mt-2 space-y-1">
              {Object.entries(cfg.credentials_configured).map(([k, v]) => (
                <li key={k}>
                  {k}:{" "}
                  <span className={v ? "text-emerald-300/90" : "text-silver/70"}>{v ? "set" : "not set"}</span>
                </li>
              ))}
            </ul>
          </div>
          <p className="text-caption text-silver/80">
            Legacy Streamlit dashboard default port:{" "}
            <code className="text-ghost-blue">{cfg.web_legacy_streamlit_port}</code> — Next console uses{" "}
            <code className="text-ghost-blue">3000</code> (UI) and FastAPI <code className="text-ghost-blue">8000</code>.
          </p>
        </div>
      ) : !err ? (
        <p className="text-silver">Loading…</p>
      ) : null}
    </div>
  );
}
