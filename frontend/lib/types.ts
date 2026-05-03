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
};

export type RegimeBand = {
  start: string;
  end: string;
  regime: string;
};

export type VisualizationData = {
  run: BacktestRun;
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

