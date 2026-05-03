import "server-only";

import fs from "node:fs";
import path from "node:path";
import { parse } from "yaml";
import type { AdaptiveRotationConfig } from "./types";

const CONFIG_FILENAME = "AdaptiveRotationConf_v1.2.1.yaml";

const GROUP_LABELS: Record<string, string> = {
  group_a_growth_tech: "Growth Tech",
  group_b_real_assets: "Real Assets",
  group_c_defensive: "Defensive",
};

const BASELINE_CANDIDATES = ["QQQ", "VOO", "SPY"] as const;

function stripSymbols(seq: unknown): string[] {
  if (!Array.isArray(seq)) return [];
  return seq.map((s) => String(s).trim()).filter(Boolean);
}

function looseBenchmarkSymbols(bench: Record<string, unknown>): string[] {
  const extra = bench.excess_return_benchmark_symbols;
  if (Array.isArray(extra)) {
    const seen = new Set<string>();
    const out: string[] = [];
    for (const s of stripSymbols(extra)) {
      const u = s.toUpperCase().replace(/\s+/g, "");
      if (u && !seen.has(u)) {
        seen.add(u);
        out.push(u);
      }
    }
    if (out.length) return out;
  }
  const one = bench.excess_return_benchmark;
  if (one != null && String(one).trim()) {
    return [String(one).trim().toUpperCase().replace(/\s+/g, "")];
  }
  return ["QQQ"];
}

function titleForGroupId(id: string): string {
  return GROUP_LABELS[id] ?? id.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function findConfigAbsolutePath(): string | null {
  const cwd = process.cwd();
  const candidates = [
    path.join(cwd, "src", "strategies", CONFIG_FILENAME),
    path.join(cwd, "..", "..", "src", "strategies", CONFIG_FILENAME),
    path.join(cwd, "..", "src", "strategies", CONFIG_FILENAME),
  ];
  for (const p of candidates) {
    const abs = path.resolve(p);
    if (fs.existsSync(abs) && fs.statSync(abs).isFile()) return abs;
  }
  return null;
}

function repoRootFromConfigPath(configPath: string): string {
  return path.resolve(configPath, "..", "..", "..");
}

/**
 * Load Adaptive Rotation public config from the repo YAML + scan data/fmp_daily.
 * Mirrors ``apps/backend/services/adaptive_yaml.load_adaptive_rotation_public`` so the
 * Universe page works when the FastAPI process is not running.
 */
export function loadAdaptiveRotationFromDisk(): AdaptiveRotationConfig | null {
  const configPath = findConfigAbsolutePath();
  if (!configPath) return null;

  let raw: unknown;
  try {
    raw = parse(fs.readFileSync(configPath, "utf8"));
  } catch {
    return null;
  }
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return null;
  const doc = raw as Record<string, unknown>;

  const repoRoot = repoRootFromConfigPath(configPath);
  const dataDir = path.join(repoRoot, "data", "fmp_daily");

  const assetGroupsRaw = doc.asset_groups;
  const groups: AdaptiveRotationConfig["asset_groups"] = [];
  if (assetGroupsRaw && typeof assetGroupsRaw === "object" && !Array.isArray(assetGroupsRaw)) {
    for (const [gid, grp] of Object.entries(assetGroupsRaw as Record<string, unknown>)) {
      if (!grp || typeof grp !== "object" || Array.isArray(grp)) continue;
      const g = grp as Record<string, unknown>;
      groups.push({
        id: gid,
        title: titleForGroupId(gid),
        max_assets: typeof g.max_assets === "number" ? g.max_assets : (g.max_assets as number | null) ?? null,
        symbols: stripSymbols(g.symbols),
      });
    }
  }
  groups.sort((a, b) => a.id.localeCompare(b.id));

  const portfolio = (doc.portfolio && typeof doc.portfolio === "object" && !Array.isArray(doc.portfolio)
    ? doc.portfolio
    : {}) as Record<string, unknown>;
  const fb = (portfolio.fallback && typeof portfolio.fallback === "object" && !Array.isArray(portfolio.fallback)
    ? portfolio.fallback
    : {}) as Record<string, unknown>;

  const bench = (doc.benchmark && typeof doc.benchmark === "object" && !Array.isArray(doc.benchmark)
    ? doc.benchmark
    : {}) as Record<string, unknown>;
  const benchSymbols = looseBenchmarkSymbols(bench);
  const benchLabel = benchSymbols.length === 1 ? benchSymbols[0] : benchSymbols.join(" + ");

  const baselinePresent: string[] = [];
  for (const sym of BASELINE_CANDIDATES) {
    const csv = path.join(dataDir, `${sym}_daily.csv`);
    if (fs.existsSync(csv) && fs.statSync(csv).isFile()) baselinePresent.push(sym);
  }

  let mtime = 0;
  try {
    mtime = Math.floor(fs.statSync(configPath).mtimeMs / 1000);
  } catch {
    mtime = 0;
  }

  return {
    config_file: path.relative(repoRoot, configPath).split(path.sep).join("/"),
    data_daily_dir: path.relative(repoRoot, dataDir).split(path.sep).join("/"),
    config_mtime: mtime,
    benchmark: bench as Record<string, unknown>,
    excess_return_benchmark: benchSymbols[0],
    excess_return_benchmark_symbols: benchSymbols,
    benchmark_excess_label: benchLabel,
    portfolio_fallback: {
      enabled: fb.enabled as boolean | null | undefined,
      symbols: stripSymbols(fb.symbols),
    },
    asset_groups: groups,
    baseline_price_csv_present: baselinePresent,
    baseline_price_csv_candidates: [...BASELINE_CANDIDATES],
  };
}
