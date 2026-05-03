"use client";

import { useCallback, useEffect, useState } from "react";
import { getDataOverview } from "@/lib/api";
import type { DataOverview } from "@/lib/types";

export function DataOverviewPanel() {
  const [data, setData] = useState<DataOverview | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    setErr(null);
    const o = await getDataOverview();
    if (!o) setErr("Could not load /api/data/overview (is the API on port 8000?)");
    setData(o);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="panel space-y-6 rounded-md p-8">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h2 className="font-display text-heading-sm font-[360] text-starlight">Local data</h2>
        <button
          type="button"
          onClick={() => void load()}
          className="rounded-[32px] border border-ghost-blue/50 px-5 py-2 text-body-sm text-starlight hover:border-mercury-blue"
        >
          Refresh
        </button>
      </div>
      {err ? <p className="text-body-sm text-red-200">{err}</p> : null}
      {data ? (
        <div className="space-y-6 text-body-sm text-silver">
          <div>
            <p className="text-caption uppercase tracking-[0.2em] text-silver">Yahoo CSV cache</p>
            <p className="mt-2">
              Folder <code className="text-ghost-blue">{data.fmp_daily.relative_dir}</code> —{" "}
              <span className="text-starlight">{data.fmp_daily.csv_count}</span>{" "}
              <code className="text-caption text-ghost-blue">*_daily.csv</code> files (~{data.fmp_daily.total_mb} MiB).
            </p>
          </div>
          <div>
            <p className="text-caption uppercase tracking-[0.2em] text-silver">DataStore (SQLite)</p>
            {data.data_store && "error" in data.data_store ? (
              <p className="mt-2 text-amber-200/90">{String(data.data_store.error)}</p>
            ) : data.data_store ? (
              <ul className="mt-2 list-inside list-disc space-y-1">
                <li>
                  <code className="text-ghost-blue">{String(data.data_store.database_path)}</code> — exists:{" "}
                  <span className="text-starlight">{String(data.data_store.database_exists)}</span>
                </li>
                {"database_size_mb" in data.data_store ? (
                  <li>
                    DB file size: <span className="text-starlight">{String(data.data_store.database_size_mb)}</span> MiB
                  </li>
                ) : null}
                <li>
                  <code className="text-caption text-silver/80">price_data</code> rows:{" "}
                  <span className="text-starlight">{String(data.data_store.price_records)}</span>
                </li>
                {"note" in data.data_store && data.data_store.note ? (
                  <li className="text-caption text-silver/80">{String(data.data_store.note)}</li>
                ) : null}
              </ul>
            ) : (
              <p className="mt-2">No stats.</p>
            )}
          </div>
          <div className="rounded-md border border-lead/40 bg-deep-space/50 p-4">
            <p className="text-caption uppercase tracking-[0.2em] text-silver">Download / refresh</p>
            <p className="mt-2 text-body-sm leading-relaxed">{data.download.message}</p>
          </div>
        </div>
      ) : !err ? (
        <p className="text-silver">Loading…</p>
      ) : null}
    </div>
  );
}
