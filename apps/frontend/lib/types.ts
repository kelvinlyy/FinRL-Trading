export type BacktestRun = {
  id: string;
  /** Deploy strategy id from deploy.sh (e.g. adaptive_rotation, rsi_reversion). */
  strategy?: string;
  legacy_id?: string;
  label: string;
  start: string;
  end: string;
  chart_url: string;
  trade_log_url: string;
  summary_url: string;
  weights_url?: string;
  files?: Record<string, string>;
  counts?: {
    summary_rows: number;
    trade_rows: number;
  };
};

export type ResultsIndex = {
  results: BacktestRun[];
};

export type Trade = {
  date: string;
  symbol: string;
  action: string;
  prev_weight: number;
  new_weight: number;
  delta: number;
  regime: string;
  group: string;
};

export type EquityPoint = {
  date: string;
  strategy: number;
  /** Equal-weight normalized composite of YAML excess-return benchmark symbols. */
  benchmark_composite?: number;
  SPY?: number;
  QQQ?: number;
  regime?: string;
};

/** Declares which equity curves to draw (from API; chart falls back if absent). */
export type EquitySeriesMeta = {
  key: string;
  label: string;
  color: string;
};

export type DrawdownPoint = {
  date: string;
  value: number;
};

export type GroupActivation = {
  date: string;
  group: string;
  active: boolean;
  held_stocks: string[];
  /** Sum of weights in this group for this rebalance row (from API). */
  group_weight_total?: number;
};

export type RegimeBand = {
  start: string;
  end: string;
  regime: string;
};

export type VisualizationData = {
  run: BacktestRun;
  /** Starting portfolio notional for scaling hover values (default 1000). */
  initial_capital?: number;
  /** Cap on simultaneous group lanes (matches Adaptive Rotation max_active_groups). */
  max_timeline_active_groups?: number;
  show_group_timeline?: boolean;
  /** First date row in the weights CSV (YYYY-MM-DD). */
  weights_first_date?: string | null;
  /**
   * First date where top-2 groups hold a meaningful fraction of the book (from API).
   * Used for the grey "before activation" band when early rows are mostly cash/dust.
   */
  first_meaningful_group_holdings_date?: string | null;
  equity: EquityPoint[];
  /** Series order, labels, and colors for the equity chart (strategy + benchmarks). */
  equity_series?: EquitySeriesMeta[];
  drawdown: DrawdownPoint[];
  regimes: RegimeBand[];
  group_timeline: GroupActivation[];
  trades: Trade[];
};

export type StrategyGroup = {
  name: string;
  tone: string;
  tickers: string[];
};

export type BacktestJobStatus = "queued" | "running" | "completed" | "failed";

export type BacktestJobProgress = {
  pct: number;
  label: string;
  phase: string;
  indeterminate?: boolean;
};

export type BacktestJobSummary = {
  job_id: string;
  status: string;
  start: string;
  end: string;
  strategy?: string;
  mode?: string;
  single_date?: string | null;
  updated_at?: string | null;
  result_run_id?: string | null;
};

export type DataCoverageDetail = {
  ok?: boolean;
  message?: string;
  data_dir?: string;
  config_path?: string;
  backtest_start?: string;
  backtest_end?: string;
  symbols_required?: number;
  missing_csv_for_symbols?: string[];
  insufficient_date_coverage?: Array<Record<string, unknown>>;
};

/** Response from GET /api/config/adaptive-rotation (live YAML + data dir scan). */
export type AdaptiveRotationConfig = {
  config_file: string;
  data_daily_dir: string;
  /** File mtime (seconds); bump remounts the editor after external saves. */
  config_mtime?: number;
  benchmark: Record<string, unknown>;
  /** First symbol (legacy YAML anchor); composite uses `excess_return_benchmark_symbols`. */
  excess_return_benchmark?: string | null;
  /** Equal-weight excess benchmark group (group strength / IR vs this composite). */
  excess_return_benchmark_symbols?: string[];
  /** Human-readable composite label, e.g. `QQQ + SPY`. */
  benchmark_excess_label?: string;
  portfolio_fallback: {
    enabled?: boolean | null;
    symbols: string[];
  };
  asset_groups: Array<{
    id: string;
    title: string;
    max_assets?: number | null;
    symbols: string[];
  }>;
  baseline_price_csv_present: string[];
  baseline_price_csv_candidates: string[];
};

/** Body for PUT /api/config/adaptive-rotation */
export type AdaptiveRotationWritePayload = {
  excess_return_benchmark_symbols: string[];
  portfolio_fallback: { enabled: boolean; symbols: string[] };
  asset_groups: Array<{ id: string; max_assets: number; symbols: string[] }>;
};

export type BacktestJob = {
  job_id: string;
  status: BacktestJobStatus;
  start: string;
  end: string;
  strategy?: string;
  mode?: string;
  single_date?: string | null;
  created_at: string;
  updated_at: string;
  returncode: number | null;
  result_run_id: string | null;
  message: string | null;
  stdout_tail: string | null;
  stderr_tail: string | null;
  progress?: BacktestJobProgress;
};

export type DataOverview = {
  fmp_daily: {
    csv_count: number;
    total_bytes: number;
    total_mb: number;
    relative_dir: string;
  };
  data_store: Record<string, unknown> | null;
  download: { api_trigger: boolean; message: string };
};

export type DeployStrategyRow = {
  name: string;
  config: string;
  runner: string;
};

export type RuntimePublicConfig = {
  app_name: string;
  version: string;
  environment: string;
  paths: Record<string, string>;
  credentials_configured: Record<string, boolean>;
  alpaca: { base_url: string; use_paper_trading: boolean };
  web_legacy_streamlit_port: number;
};

export type TradingStatus = {
  mode: "deferred" | "paper_web_enabled";
  execution_enabled: boolean;
  can_paper_trade_from_cli: boolean;
  alpaca: {
    base_url: string;
    use_paper_trading: boolean;
  };
  next_steps: string[];
  message: string;
};

export type PortfolioOverview = {
  has_run: boolean;
  message: string;
  run: { id: string; start: string; end: string; label: string } | null;
  kpis: Record<string, number>;
  positions: Array<{ symbol: string; weight: number; weight_pct: number; share_of_invested_pct: number }>;
  trades: { count: number; latest: Array<Record<string, unknown>> };
};

