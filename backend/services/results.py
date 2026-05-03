from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = PROJECT_ROOT / "src/strategies/output/weights/adaptive_rotation"
DATA_DIR = PROJECT_ROOT / "data/fmp_daily"
RESULT_RE = re.compile(r"enhanced_backtest_(?P<start>.+)_to_(?P<end>.+)\.png$")

GROUP_MEMBERS = {
    "Growth Tech": ["AAPL", "MSFT", "NVDA", "META", "AMZN", "GOOGL", "TSLA"],
    "Real Assets": ["XOM", "CVX", "COP", "FCX", "BHP", "GLD", "SLV"],
    "Defensive": ["TLT", "IEF", "XLU", "XLV", "IAU", "SHY", "UUP"],
}

# Must match typical Adaptive Rotation config (e.g. max_active_groups: 2 in YAML).
# Residual small weights in a 3rd group can still be > 0 after rebalances; the chart
# should only mark the top-N groups by *total* weight as "activated".
MAX_TIMELINE_ACTIVE_GROUPS = 2


@dataclass(frozen=True)
class BacktestRun:
    id: str
    start: str
    end: str
    chart_path: Path
    trade_log_path: Path
    summary_path: Path
    weights_path: Path

    @property
    def label(self) -> str:
        return f"{self.start} to {self.end}"


def _run_from_chart(chart_path: Path) -> BacktestRun | None:
    match = RESULT_RE.match(chart_path.name)
    if not match:
        return None

    start = match.group("start")
    end = match.group("end")
    run_id = f"{start}_to_{end}"
    return BacktestRun(
        id=run_id,
        start=start,
        end=end,
        chart_path=chart_path,
        trade_log_path=chart_path.with_name(f"trade_log_{run_id}.csv"),
        summary_path=chart_path.with_name(f"backtest_{run_id}.csv"),
        weights_path=chart_path.with_name(f"ars_portfolio_weights_{run_id}.csv"),
    )


def list_runs() -> list[BacktestRun]:
    if not RESULTS_DIR.exists():
        return []

    runs = []
    for chart_path in RESULTS_DIR.glob("enhanced_backtest_*_to_*.png"):
        run = _run_from_chart(chart_path)
        if run:
            runs.append(run)

    return sorted(runs, key=lambda run: run.chart_path.stat().st_mtime, reverse=True)


def get_run(run_id: str) -> BacktestRun | None:
    for run in list_runs():
        if run.id == run_id:
            return run
    return None


def latest_run() -> BacktestRun | None:
    runs = list_runs()
    return runs[0] if runs else None


def _read_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    df = pd.read_csv(path)
    return df.fillna("").to_dict(orient="records")


def _to_float(value: Any) -> float:
    try:
        if pd.isna(value):
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _load_price_frame(symbols: list[str]) -> pd.DataFrame:
    prices = {}
    for symbol in symbols:
        csv_path = DATA_DIR / f"{symbol}_daily.csv"
        if not csv_path.exists():
            continue
        df = pd.read_csv(csv_path)
        if "date" not in df.columns or "close" not in df.columns:
            continue
        df["date"] = pd.to_datetime(df["date"])
        prices[symbol] = df.set_index("date")["close"]
    return pd.DataFrame(prices)


def _compute_equity(weights_df: pd.DataFrame) -> pd.DataFrame:
    weights_df = weights_df.copy()
    weights_df["date"] = pd.to_datetime(weights_df["date"])

    meta_cols = {"date", "cash", "regime"}
    asset_cols = [column for column in weights_df.columns if column not in meta_cols]
    price_df = _load_price_frame(sorted(set(asset_cols + ["SPY", "QQQ"])))

    dates = weights_df["date"].to_list()
    portfolio_values = [1.0]
    for idx in range(len(dates) - 1):
        d0, d1 = dates[idx], dates[idx + 1]
        row = weights_df.iloc[idx]
        period_return = 0.0
        for symbol in asset_cols:
            weight = _to_float(row.get(symbol, 0))
            if weight <= 0 or symbol not in price_df.columns:
                continue
            p0 = price_df[symbol].loc[:d0].dropna()
            p1 = price_df[symbol].loc[:d1].dropna()
            if len(p0) and len(p1):
                period_return += weight * (p1.iloc[-1] / p0.iloc[-1] - 1)
        portfolio_values.append(portfolio_values[-1] * (1 + period_return))

    equity = pd.DataFrame({
        "date": dates,
        "strategy": portfolio_values,
        "regime": weights_df["regime"].fillna("unknown").to_list(),
    }).set_index("date")

    for benchmark in ["SPY", "QQQ"]:
        if benchmark not in price_df.columns:
            continue
        series = price_df[benchmark].dropna()
        start_series = series.loc[:equity.index[0]]
        if start_series.empty:
            continue
        start_price = start_series.iloc[-1]
        equity[benchmark] = series.reindex(equity.index, method="ffill") / start_price

    return equity.reset_index()


def _normalize_weights_frame(weights_df: pd.DataFrame) -> pd.DataFrame:
    """Strip column names, sort by date, and build case-insensitive symbol lookup."""
    df = weights_df.copy()
    df.columns = [c.strip() if isinstance(c, str) else c for c in df.columns]
    if "date" not in df.columns:
        return df
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    return df


def _asset_columns(df: pd.DataFrame) -> list[str]:
    meta_cols = {"date", "cash", "regime"}
    return [c for c in df.columns if c not in meta_cols]


def _canonical_symbol_lookup(asset_cols: list[str]) -> dict[str, str]:
    """Map UPPER(symbol) -> actual CSV column name (handles spacing/case drift)."""
    out: dict[str, str] = {}
    for col in asset_cols:
        key = col.upper().strip()
        out.setdefault(key, col)
    return out


def _group_timeline(weights_df: pd.DataFrame) -> list[dict[str, Any]]:
    df = _normalize_weights_frame(weights_df)
    asset_cols = _asset_columns(df)
    lookup = _canonical_symbol_lookup(asset_cols)
    rows: list[dict[str, Any]] = []
    weight_eps = 1e-9
    for _, row in df.iterrows():
        # Per-group capital weight (sum of member positions)
        group_totals: dict[str, float] = {}
        for group, symbols in GROUP_MEMBERS.items():
            total = 0.0
            for symbol in symbols:
                col = lookup.get(symbol.upper().strip())
                if col is None:
                    continue
                total += _to_float(row.get(col, 0))
            group_totals[group] = total

        # At most MAX_TIMELINE_ACTIVE_GROUPS with non-trivial weight (matches strategy design)
        ranked = sorted(
            group_totals.items(),
            key=lambda x: (-x[1], x[0]),
        )
        active_group_names = {
            g for g, t in ranked[:MAX_TIMELINE_ACTIVE_GROUPS] if t > weight_eps
        }

        for group, symbols in GROUP_MEMBERS.items():
            held: list[str] = []
            if group in active_group_names:
                for symbol in symbols:
                    col = lookup.get(symbol.upper().strip())
                    if col is None:
                        continue
                    if _to_float(row.get(col, 0)) > weight_eps:
                        held.append(symbol)
            rows.append({
                "date": row["date"].strftime("%Y-%m-%d"),
                "group": group,
                "active": bool(held),
                "held_stocks": held,
            })
    return rows


def read_summary(run: BacktestRun) -> list[dict[str, Any]]:
    return _read_csv(run.summary_path)


def read_trade_log(run: BacktestRun) -> list[dict[str, Any]]:
    return _read_csv(run.trade_log_path)


def read_weights(run: BacktestRun) -> list[dict[str, Any]]:
    return _read_csv(run.weights_path)


def run_metadata(run: BacktestRun) -> dict[str, Any]:
    summary = read_summary(run)
    trade_log = read_trade_log(run)

    return {
        "id": run.id,
        "label": run.label,
        "start": run.start,
        "end": run.end,
        "chart_url": f"/api/results/{run.id}/chart",
        "trade_log_url": f"/api/results/{run.id}/trade-log",
        "summary_url": f"/api/results/{run.id}/summary",
        "weights_url": f"/api/results/{run.id}/weights",
        "visualization_url": f"/api/results/{run.id}/visualization",
        "files": {
            "chart": str(run.chart_path.relative_to(PROJECT_ROOT)),
            "trade_log": str(run.trade_log_path.relative_to(PROJECT_ROOT)),
            "summary": str(run.summary_path.relative_to(PROJECT_ROOT)),
            "weights": str(run.weights_path.relative_to(PROJECT_ROOT)),
        },
        "counts": {
            "summary_rows": len(summary),
            "trade_rows": len(trade_log),
        },
    }


def visualization_data(run: BacktestRun) -> dict[str, Any]:
    if not run.weights_path.exists():
        return {
            "run": run_metadata(run),
            "initial_capital": 1000.0,
            "equity": [],
            "drawdown": [],
            "group_timeline": [],
            "trades": read_trade_log(run),
        }

    weights_df = _normalize_weights_frame(pd.read_csv(run.weights_path))
    equity_df = _compute_equity(weights_df)
    strategy = equity_df["strategy"]
    drawdown = (strategy - strategy.cummax()) / strategy.cummax()

    equity_rows = []
    for _, row in equity_df.iterrows():
        equity_rows.append({
            "date": pd.to_datetime(row["date"]).strftime("%Y-%m-%d"),
            "strategy": _to_float(row.get("strategy")),
            "SPY": _to_float(row.get("SPY")) if "SPY" in equity_df.columns else None,
            "QQQ": _to_float(row.get("QQQ")) if "QQQ" in equity_df.columns else None,
            "regime": row.get("regime", "unknown"),
        })

    drawdown_rows = [
        {
            "date": pd.to_datetime(equity_df.iloc[idx]["date"]).strftime("%Y-%m-%d"),
            "value": _to_float(value),
        }
        for idx, value in enumerate(drawdown)
    ]

    return {
        "run": run_metadata(run),
        "initial_capital": 1000.0,
        "equity": equity_rows,
        "drawdown": drawdown_rows,
        "regimes": _regime_spans(equity_rows),
        "group_timeline": _group_timeline(weights_df),
        "trades": read_trade_log(run),
    }


def _regime_spans(equity_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    spans: list[dict[str, Any]] = []
    if not equity_rows:
        return spans

    current = equity_rows[0].get("regime", "unknown")
    start = equity_rows[0]["date"]
    previous = equity_rows[0]["date"]

    for row in equity_rows[1:]:
        regime = row.get("regime", "unknown")
        if regime != current:
            spans.append({"start": start, "end": previous, "regime": current})
            start = row["date"]
            current = regime
        previous = row["date"]

    spans.append({"start": start, "end": previous, "regime": current})
    return spans
