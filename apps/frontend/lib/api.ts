import type {
  AdaptiveRotationConfig,
  AdaptiveRotationWritePayload,
  BacktestJob,
  BacktestJobSummary,
  BacktestRun,
  DataCoverageDetail,
  DataOverview,
  DeployStrategyRow,
  ResultsIndex,
  RuntimePublicConfig,
  StrategyBenchmarkConfig,
  StrategyGroup,
  Trade,
  PortfolioOverview,
  TradingStatus,
  VisualizationData,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

/** Max wait for read-only / polling API calls. */
const API_FETCH_TIMEOUT_MS = Math.min(
  60_000,
  Math.max(1500, Number(process.env.NEXT_PUBLIC_API_FETCH_TIMEOUT_MS ?? 8000)),
);

/**
 * Longer ceiling for PUT/POST (YAML save, backtest enqueue). ``AbortSignal.timeout`` was cutting off
 * "Save universe" when the default read timeout was applied.
 */
const API_MUTATION_TIMEOUT_MS = Math.min(
  300_000,
  Math.max(10_000, Number(process.env.NEXT_PUBLIC_API_MUTATION_TIMEOUT_MS ?? 120_000)),
);

function _isAbortError(cause: unknown): boolean {
  if (cause instanceof DOMException && cause.name === "AbortError") return true;
  if (cause instanceof Error) {
    if (cause.name === "AbortError") return true;
    if (/aborted|timed out|timeout/i.test(cause.message)) return true;
  }
  return false;
}

function _apiFetchInit(extra?: RequestInit, opts?: { timeoutMs?: number }): RequestInit {
  const ms = opts?.timeoutMs ?? API_FETCH_TIMEOUT_MS;
  return {
    cache: "no-store",
    ...extra,
    signal: AbortSignal.timeout(ms),
  };
}

/** Thrown by job polling when the response is not OK or the request fails on the network. */
export class ApiRequestError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiRequestError";
  }
}

export class DataCoverageError extends Error {
  constructor(public readonly coverage: DataCoverageDetail) {
    super(coverage.message ?? "Local market data is incomplete for this backtest.");
    this.name = "DataCoverageError";
  }
}

function _isDataCoverageDetail(detail: unknown): detail is DataCoverageDetail {
  if (!detail || typeof detail !== "object" || Array.isArray(detail)) return false;
  return "missing_csv_for_symbols" in detail || "insufficient_date_coverage" in detail;
}

async function readErrorDetail(response: Response): Promise<string> {
  const err = (await response.json().catch(() => ({}))) as {
    detail?: string | Array<{ msg?: string }>;
  };
  if (typeof err.detail === "string") return err.detail;
  if (Array.isArray(err.detail)) return err.detail.map((d) => d.msg).filter(Boolean).join("; ") || response.statusText;
  return response.statusText;
}

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
    const response = await fetch(`${API_BASE}/api/results`, _apiFetchInit());
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
    const response = await fetch(`${API_BASE}/api/results/${id}`, _apiFetchInit());
    if (!response.ok) return (await getResults()).find((run) => run.id === id);
    return normalizeRun((await response.json()) as BacktestRun);
  } catch {
    return fallbackRuns.find((run) => run.id === id);
  }
}

export async function getTradeLog(id: string): Promise<Trade[]> {
  try {
    const response = await fetch(`${API_BASE}/api/results/${id}/trade-log`, _apiFetchInit());
    if (!response.ok) return [];
    const payload = (await response.json()) as { rows: Trade[] };
    return payload.rows;
  } catch {
    return [];
  }
}

export async function getVisualization(id: string): Promise<VisualizationData | undefined> {
  try {
    const response = await fetch(`${API_BASE}/api/results/${id}/visualization`, _apiFetchInit());
    if (!response.ok) return undefined;
    return response.json();
  } catch {
    return undefined;
  }
}

/** Live rotation universe, fallback sleeve, benchmark, and which baseline CSVs exist under data/fmp_daily. */
export async function getAdaptiveRotationConfig(): Promise<AdaptiveRotationConfig | null> {
  try {
    const response = await fetch(`${API_BASE}/api/config/adaptive-rotation`, _apiFetchInit());
    if (!response.ok) return null;
    return (await response.json()) as AdaptiveRotationConfig;
  } catch {
    return null;
  }
}

function _formatConfigWriteDetail(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail))
    return detail.map((x: { msg?: string }) => x.msg).filter(Boolean).join("; ");
  return "";
}

export async function getStrategyBenchmark(strategy: string): Promise<StrategyBenchmarkConfig | null> {
  try {
    const enc = encodeURIComponent(strategy);
    const response = await fetch(`${API_BASE}/api/config/strategy-benchmark/${enc}`, _apiFetchInit());
    if (!response.ok) return null;
    return (await response.json()) as StrategyBenchmarkConfig;
  } catch {
    return null;
  }
}

/** Write benchmark block to the strategy's registered YAML (same-origin proxy in browser). */
export async function putStrategyBenchmark(
  strategy: string,
  symbols: string[],
): Promise<StrategyBenchmarkConfig> {
  const enc = encodeURIComponent(strategy);
  const url =
    typeof window === "undefined"
      ? `${API_BASE}/api/config/strategy-benchmark/${enc}`
      : `/api/config/strategy-benchmark/${enc}`;

  let response: Response;
  try {
    response = await fetch(
      url,
      _apiFetchInit(
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ excess_return_benchmark_symbols: symbols }),
        },
        { timeoutMs: API_MUTATION_TIMEOUT_MS },
      ),
    );
  } catch (cause) {
    if (_isAbortError(cause)) {
      throw new Error(
        `Save timed out after ${API_MUTATION_TIMEOUT_MS / 1000}s. If the UI is open, check INTERNAL_API_BASE_URL / backend health.`,
      );
    }
    throw cause;
  }
  const body = (await response.json().catch(() => ({}))) as { detail?: unknown };
  if (!response.ok) {
    const msg = _formatConfigWriteDetail(body.detail) || response.statusText;
    throw new Error(msg || `HTTP ${response.status}`);
  }
  return body as StrategyBenchmarkConfig;
}

/** Validate and write universe fields to AdaptiveRotationConf YAML on the API host. */
export async function putAdaptiveRotationConfig(payload: AdaptiveRotationWritePayload): Promise<AdaptiveRotationConfig> {
  /** Same-origin Next route proxies to FastAPI (avoids hung direct browser → :8000 saves). */
  const url =
    typeof window === "undefined"
      ? `${API_BASE}/api/config/adaptive-rotation`
      : "/api/config/adaptive-rotation";

  let response: Response;
  try {
    response = await fetch(
      url,
      _apiFetchInit(
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        },
        { timeoutMs: API_MUTATION_TIMEOUT_MS },
      ),
    );
  } catch (cause) {
    if (_isAbortError(cause)) {
      throw new Error(
        `Save timed out after ${API_MUTATION_TIMEOUT_MS / 1000}s. If the UI is open, the Next.js proxy should respond sooner — check INTERNAL_API_BASE_URL / backend health, or increase NEXT_PUBLIC_API_MUTATION_TIMEOUT_MS.`,
      );
    }
    throw cause;
  }
  const body = (await response.json().catch(() => ({}))) as { detail?: unknown };
  if (!response.ok) {
    const msg = _formatConfigWriteDetail(body.detail) || response.statusText;
    throw new Error(msg || `HTTP ${response.status}`);
  }
  return body as AdaptiveRotationConfig;
}

function _formatFastApiDetail(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail))
    return detail.map((x: { msg?: string }) => x.msg).filter(Boolean).join("; ");
  return "";
}

export async function startBacktestRun(payload: {
  start?: string;
  end?: string;
  date?: string;
  strategy?: string;
  mode?: "backtest" | "single";
}): Promise<{ job_id: string; status: string }> {
  let response: Response;
  try {
    response = await fetch(
      `${API_BASE}/api/backtest/run`,
      _apiFetchInit(
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        },
        { timeoutMs: API_MUTATION_TIMEOUT_MS },
      ),
    );
  } catch (cause) {
    if (_isAbortError(cause)) {
      throw new Error(
        `Backtest request timed out after ${API_MUTATION_TIMEOUT_MS / 1000}s (API at ${API_BASE}). ` +
          `Increase NEXT_PUBLIC_API_MUTATION_TIMEOUT_MS if the server is slow to respond.`,
      );
    }
    throw cause;
  }
  const body = (await response.json().catch(() => ({}))) as { detail?: unknown };
  if (!response.ok) {
    if (_isDataCoverageDetail(body.detail)) {
      throw new DataCoverageError(body.detail);
    }
    const msg = _formatFastApiDetail(body.detail) || response.statusText;
    throw new Error(msg || `HTTP ${response.status}`);
  }
  return body as { job_id: string; status: string };
}

export async function listBacktestJobs(): Promise<BacktestJobSummary[]> {
  try {
    const response = await fetch(`${API_BASE}/api/backtest/jobs`, _apiFetchInit());
    if (!response.ok) return [];
    const payload = (await response.json()) as { jobs: BacktestJobSummary[] };
    return payload.jobs ?? [];
  } catch {
    return [];
  }
}

export async function getDataOverview(): Promise<DataOverview | null> {
  try {
    const response = await fetch(`${API_BASE}/api/data/overview`, _apiFetchInit());
    if (!response.ok) return null;
    return (await response.json()) as DataOverview;
  } catch {
    return null;
  }
}

export async function getRuntimePublicConfig(): Promise<RuntimePublicConfig | null> {
  try {
    const response = await fetch(`${API_BASE}/api/config/runtime`, _apiFetchInit());
    if (!response.ok) return null;
    return (await response.json()) as RuntimePublicConfig;
  } catch {
    return null;
  }
}

export async function getTradingStatus(): Promise<TradingStatus | null> {
  try {
    const response = await fetch(`${API_BASE}/api/trading/status`, _apiFetchInit());
    if (!response.ok) return null;
    return (await response.json()) as TradingStatus;
  } catch {
    return null;
  }
}

export async function getPortfolioOverview(): Promise<PortfolioOverview | null> {
  try {
    const response = await fetch(`${API_BASE}/api/portfolio/overview`, _apiFetchInit());
    if (!response.ok) return null;
    return (await response.json()) as PortfolioOverview;
  } catch {
    return null;
  }
}

export async function startTradingRun(payload: {
  strategy?: string;
  date?: string;
  dry_run?: boolean;
  account_name?: string;
}): Promise<{ job_id: string; status: string }> {
  const response = await fetch(
    `${API_BASE}/api/trading/run`,
    _apiFetchInit(
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      },
      { timeoutMs: API_MUTATION_TIMEOUT_MS },
    ),
  );
  const body = (await response.json().catch(() => ({}))) as { detail?: unknown };
  if (!response.ok) {
    const msg = _formatFastApiDetail(body.detail) || response.statusText;
    throw new Error(msg || `HTTP ${response.status}`);
  }
  return body as { job_id: string; status: string };
}

export async function getTradingJob(jobId: string): Promise<BacktestJob> {
  const response = await fetch(`${API_BASE}/api/trading/jobs/${jobId}`, _apiFetchInit());
  if (!response.ok) {
    const detail = await readErrorDetail(response);
    throw new ApiRequestError(detail || `HTTP ${response.status}`, response.status);
  }
  return response.json() as Promise<BacktestJob>;
}

export async function listDeployStrategies(): Promise<DeployStrategyRow[]> {
  try {
    const response = await fetch(`${API_BASE}/api/backtest/strategies`, _apiFetchInit());
    if (!response.ok) return [];
    const body = (await response.json()) as { strategies?: DeployStrategyRow[] };
    return body.strategies ?? [];
  } catch {
    return [];
  }
}

export async function getBacktestJob(jobId: string): Promise<BacktestJob> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}/api/backtest/jobs/${jobId}`, _apiFetchInit());
  } catch (cause) {
    const msg = cause instanceof Error ? cause.message : "Network error";
    throw new ApiRequestError(msg, 0);
  }
  if (!response.ok) {
    const detail = await readErrorDetail(response);
    throw new ApiRequestError(detail || `HTTP ${response.status}`, response.status);
  }
  return response.json() as Promise<BacktestJob>;
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
