export type BacktestRun = {
  id: string;
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
  SPY?: number;
  QQQ?: number;
  regime?: string;
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
  /** First date row in the weights CSV (YYYY-MM-DD). */
  weights_first_date?: string | null;
  /**
   * First date where top-2 groups hold a meaningful fraction of the book (from API).
   * Used for the grey "before activation" band when early rows are mostly cash/dust.
   */
  first_meaningful_group_holdings_date?: string | null;
  equity: EquityPoint[];
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

