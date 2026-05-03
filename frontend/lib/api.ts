import type { BacktestRun, ResultsIndex, StrategyGroup, Trade, VisualizationData } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

const fallbackRuns: BacktestRun[] = [
  {
    id: "2024-01-01_to_2025-05-02",
    label: "2024-01-01 to 2025-05-02",
    start: "2024-01-01",
    end: "2025-05-02",
    chart_url: "/mock/enhanced_backtest_placeholder.svg",
    trade_log_url: "",
    summary_url: "",
    weights_url: "",
    files: {},
    counts: {
      summary_rows: 0,
      trade_rows: 441,
    },
  },
];

function absoluteApiUrl(path: string) {
  if (!path) return "";
  if (path.startsWith("http://") || path.startsWith("https://")) return path;
  return `${API_BASE}${path}`;
}

function normalizeRun(run: BacktestRun): BacktestRun {
  return {
    ...run,
    chart_url: absoluteApiUrl(run.chart_url),
    trade_log_url: absoluteApiUrl(run.trade_log_url),
    summary_url: absoluteApiUrl(run.summary_url),
    weights_url: run.weights_url ? absoluteApiUrl(run.weights_url) : "",
  };
}

export async function getResults(): Promise<BacktestRun[]> {
  try {
    const response = await fetch(`${API_BASE}/api/results`, { cache: "no-store" });
    if (!response.ok) return fallbackRuns;
    const payload = (await response.json()) as ResultsIndex;
    return payload.results.map(normalizeRun);
  } catch {
    return fallbackRuns;
  }
}

export async function getLatestRun(): Promise<BacktestRun> {
  const runs = await getResults();
  return runs[0] ?? fallbackRuns[0];
}

export async function getRuns(): Promise<BacktestRun[]> {
  return getResults();
}

export async function getRun(id: string): Promise<BacktestRun | undefined> {
  try {
    const response = await fetch(`${API_BASE}/api/results/${id}`, { cache: "no-store" });
    if (!response.ok) return (await getResults()).find((run) => run.id === id);
    return normalizeRun((await response.json()) as BacktestRun);
  } catch {
    return fallbackRuns.find((run) => run.id === id);
  }
}

export async function getTradeLog(id: string): Promise<Trade[]> {
  try {
    const response = await fetch(`${API_BASE}/api/results/${id}/trade-log`, { cache: "no-store" });
    if (!response.ok) return [];
    const payload = (await response.json()) as { rows: Trade[] };
    return payload.rows;
  } catch {
    return [];
  }
}

export async function getVisualization(id: string): Promise<VisualizationData | undefined> {
  try {
    const response = await fetch(`${API_BASE}/api/results/${id}/visualization`, { cache: "no-store" });
    if (!response.ok) return undefined;
    return response.json();
  } catch {
    return undefined;
  }
}

export const strategyGroups: StrategyGroup[] = [
  {
    name: "Growth Tech",
    tone: "Mercury Blue",
    tickers: ["AAPL", "MSFT", "NVDA", "META", "AMZN", "GOOGL", "TSLA"],
  },
  {
    name: "Real Assets",
    tone: "Graphite",
    tickers: ["XOM", "CVX", "COP", "FCX", "BHP", "GLD", "SLV"],
  },
  {
    name: "Defensive",
    tone: "Ghost Blue",
    tickers: ["TLT", "IEF", "XLU", "XLV", "IAU", "SHY", "UUP"],
  },
];
