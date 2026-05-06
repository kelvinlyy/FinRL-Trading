from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math
import re
from typing import Any

import pandas as pd

from backend.services.strategy_registry import (
    config_path_for_strategy,
    list_deploy_strategies,
    resolve_strategy_output_dirs,
)

# apps/backend/services/ -> repo root
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data/fmp_daily"
# e.g. ars_portfolio_weights_2023-01-01_to_2024-12-31.csv, rsi_portfolio_weights_...
WEIGHTS_FILE_RE = re.compile(
    r"^(?P<prefix>[a-z0-9]+)_portfolio_weights_(?P<start>.+)_to_(?P<end>.+)\.csv$"
)

GROUP_MEMBERS = {
    "Growth Tech": ["AAPL", "MSFT", "NVDA", "META", "AMZN", "GOOGL", "TSLA"],
    "Real Assets": ["XOM", "CVX", "COP", "FCX", "BHP", "GLD", "SLV"],
    "Defensive": ["TLT", "IEF", "XLU", "XLV", "IAU", "SHY", "UUP"],
}

# Must match typical Adaptive Rotation config (e.g. max_active_groups: 2 in YAML).
# Residual small weights in a 3rd group can still be > 0 after rebalances; the chart
# should only mark the top-N groups by *total* weight as "activated".
MAX_TIMELINE_ACTIVE_GROUPS = 2

# First chart date where at least this fraction of capital is in the top-2 groups (excludes "dust").
_MIN_MEANINGFUL_GROUP_INVESTED = 0.06


@dataclass(frozen=True)
class BacktestRun:
    id: str
    strategy_slug: str
    legacy_id: str
    start: str
    end: str
    chart_path: Path
    trade_log_path: Path
    summary_path: Path
    weights_path: Path

    @property
    def label(self) -> str:
        return f"{self.strategy_slug}: {self.start} to {self.end}"


def _pick_chart_png(weights_dir: Path, legacy_id: str) -> Path:
    """Adaptive writes ``enhanced_backtest_*.png``; RSI/simple runners often write ``backtest_*.png``."""
    for name in (f"enhanced_backtest_{legacy_id}.png", f"backtest_{legacy_id}.png"):
        p = weights_dir / name
        if p.exists():
            return p
    return weights_dir / f"enhanced_backtest_{legacy_id}.png"


def _run_from_weights(weights_path: Path, strategy_slug: str) -> BacktestRun | None:
    match = WEIGHTS_FILE_RE.match(weights_path.name)
    if not match:
        return None

    start = match.group("start")
    end = match.group("end")
    legacy_id = f"{start}_to_{end}"
    weights_dir = weights_path.parent
    chart_path = _pick_chart_png(weights_dir, legacy_id)
    composite_id = f"{strategy_slug}__{legacy_id}"
    return BacktestRun(
        id=composite_id,
        strategy_slug=strategy_slug,
        legacy_id=legacy_id,
        start=start,
        end=end,
        chart_path=chart_path,
        trade_log_path=weights_dir / f"trade_log_{legacy_id}.csv",
        summary_path=weights_dir / f"backtest_{legacy_id}.csv",
        weights_path=weights_path,
    )


def _run_mtime(run: BacktestRun) -> float:
    paths = [run.weights_path, run.summary_path, run.chart_path]
    mtimes = [p.stat().st_mtime for p in paths if p.exists()]
    return max(mtimes) if mtimes else 0.0


def list_runs() -> list[BacktestRun]:
    by_id: dict[str, BacktestRun] = {}
    for row in list_deploy_strategies():
        slug = row["name"]
        weights_dir, _ = resolve_strategy_output_dirs(slug)
        if not weights_dir.is_dir():
            continue
        for weights_path in weights_dir.glob("*_portfolio_weights_*_to_*.csv"):
            run = _run_from_weights(weights_path, slug)
            if run:
                by_id[run.id] = run

    runs = list(by_id.values())
    return sorted(runs, key=_run_mtime, reverse=True)


def get_run(run_id: str) -> BacktestRun | None:
    runs = list_runs()
    for run in runs:
        if run.id == run_id:
            return run
    legacy_matches = [r for r in runs if r.legacy_id == run_id]
    if not legacy_matches:
        return None
    for slug in ("adaptive_rotation",):
        for run in legacy_matches:
            if run.strategy_slug == slug:
                return run
    return legacy_matches[0]


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


def _optional_float(value: Any) -> float | None:
    """JSON-safe optional number for benchmark lines (omit invalid / missing instead of 0)."""
    try:
        if pd.isna(value):
            return None
        f = float(value)
        return f if math.isfinite(f) else None
    except (TypeError, ValueError):
        return None


def _strategy_yaml(strategy_slug: str) -> dict[str, Any]:
    import yaml

    path = config_path_for_strategy(strategy_slug)
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _strategy_display_name(strategy_slug: str) -> str:
    raw = _strategy_yaml(strategy_slug)
    meta = raw.get("strategy") or {}
    name = str(meta.get("name") or strategy_slug).strip() or strategy_slug
    ver = meta.get("version")
    if ver:
        return f"{name} ({ver})"
    return name


def _resolved_benchmark_symbols_for_strategy(strategy_slug: str) -> tuple[list[str], str]:
    """Benchmark composite symbols + label from **that** strategy's YAML (not always Adaptive Rotation)."""
    raw = _strategy_yaml(strategy_slug)
    bench = raw.get("benchmark") or {}
    extra = bench.get("excess_return_benchmark_symbols")
    if isinstance(extra, list) and extra:
        syms = [str(s).strip() for s in extra if str(s).strip()]
        if syms:
            label = bench.get("benchmark_excess_label") or (" + ".join(syms) if len(syms) > 1 else syms[0])
            return (syms, str(label))
    one = bench.get("excess_return_benchmark")
    if one is None or str(one).strip() == "":
        one = "SPY"
    one = str(one).strip()
    return ([one], one)


def _normalized_buyhold(
    equity_dates: pd.DatetimeIndex,
    price_df: pd.DataFrame,
    symbol: str,
) -> pd.Series | None:
    if symbol not in price_df.columns:
        return None
    series = price_df[symbol].dropna()
    start_series = series.loc[:equity_dates[0]]
    if start_series.empty:
        return None
    start_price = start_series.iloc[-1]
    return series.reindex(equity_dates, method="ffill") / start_price


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


def _compute_equity(weights_df: pd.DataFrame, strategy_slug: str) -> tuple[pd.DataFrame, str]:
    weights_df = weights_df.copy()
    weights_df["date"] = pd.to_datetime(weights_df["date"])

    meta_cols = {"date", "cash", "regime"}
    asset_cols = [column for column in weights_df.columns if column not in meta_cols]
    bench_syms, bench_label = _resolved_benchmark_symbols_for_strategy(strategy_slug)
    price_symbols = sorted(set(asset_cols) | set(bench_syms) | {"SPY", "QQQ"})
    price_df = _load_price_frame(price_symbols)

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

    norm_parts: list[pd.Series] = []
    for sym in bench_syms:
        s = _normalized_buyhold(equity.index, price_df, sym)
        if s is not None:
            norm_parts.append(s)
    if norm_parts:
        comp = pd.concat(norm_parts, axis=1).mean(axis=1)
        if not comp.isna().all():
            equity["benchmark_composite"] = comp

    for benchmark in ["SPY", "QQQ"]:
        if benchmark not in price_df.columns:
            continue
        series = price_df[benchmark].dropna()
        start_series = series.loc[:equity.index[0]]
        if start_series.empty:
            continue
        start_price = start_series.iloc[-1]
        equity[benchmark] = series.reindex(equity.index, method="ffill") / start_price

    return equity.reset_index(), bench_label


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
            g_total = group_totals.get(group, 0.0)
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
                # Sum of position weights in this group (for UI tie-break / hard cap)
                "group_weight_total": round(g_total, 8),
            })
    return rows


def _first_meaningful_group_holdings_date(weights_df: pd.DataFrame) -> str | None:
    """
    First rebalance date where the top two groups (by summed member weight) hold at least
    _MIN_MEANINGFUL_GROUP_INVESTED of the book together. Avoids treating tiny residual weights
    as "activation" on the first row.
    """
    df = _normalize_weights_frame(weights_df)
    asset_cols = _asset_columns(df)
    lookup = _canonical_symbol_lookup(asset_cols)
    for _, row in df.iterrows():
        group_totals: dict[str, float] = {}
        for group, symbols in GROUP_MEMBERS.items():
            total = 0.0
            for symbol in symbols:
                col = lookup.get(symbol.upper().strip())
                if col is None:
                    continue
                total += _to_float(row.get(col, 0))
            group_totals[group] = total
        ranked = sorted(group_totals.values(), reverse=True)
        top2 = sum(ranked[:MAX_TIMELINE_ACTIVE_GROUPS]) if ranked else 0.0
        if top2 >= _MIN_MEANINGFUL_GROUP_INVESTED:
            return pd.to_datetime(row["date"]).strftime("%Y-%m-%d")
    return None


def read_summary(run: BacktestRun) -> list[dict[str, Any]]:
    return _read_csv(run.summary_path)


def read_trade_log(run: BacktestRun) -> list[dict[str, Any]]:
    return _read_csv(run.trade_log_path)


def read_weights(run: BacktestRun) -> list[dict[str, Any]]:
    return _read_csv(run.weights_path)


def run_metadata(run: BacktestRun) -> dict[str, Any]:
    summary = read_summary(run)
    trade_log = read_trade_log(run)

    chart_url = f"/api/results/{run.id}/chart" if run.chart_path.exists() else ""
    return {
        "id": run.id,
        "strategy": run.strategy_slug,
        "legacy_id": run.legacy_id,
        "label": run.label,
        "start": run.start,
        "end": run.end,
        "chart_url": chart_url,
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
            "max_timeline_active_groups": 0,
            "show_group_timeline": run.strategy_slug == "adaptive_rotation",
            "weights_first_date": None,
            "first_meaningful_group_holdings_date": None,
            "equity": [],
            "equity_series": [],
            "drawdown": [],
            "group_timeline": [],
            "trades": read_trade_log(run),
        }

    weights_df = _normalize_weights_frame(pd.read_csv(run.weights_path))
    equity_df, bench_label = _compute_equity(weights_df, run.strategy_slug)
    strategy = equity_df["strategy"]
    drawdown = (strategy - strategy.cummax()) / strategy.cummax()

    equity_rows = []
    for _, row in equity_df.iterrows():
        er: dict[str, Any] = {
            "date": pd.to_datetime(row["date"]).strftime("%Y-%m-%d"),
            "strategy": _to_float(row.get("strategy")),
            "regime": row.get("regime", "unknown"),
        }
        if "benchmark_composite" in equity_df.columns:
            er["benchmark_composite"] = _optional_float(row.get("benchmark_composite"))
        if "SPY" in equity_df.columns:
            er["SPY"] = _optional_float(row.get("SPY"))
        if "QQQ" in equity_df.columns:
            er["QQQ"] = _optional_float(row.get("QQQ"))
        equity_rows.append(er)

    strat_label = _strategy_display_name(run.strategy_slug)
    equity_series: list[dict[str, str]] = [
        {"key": "strategy", "label": strat_label, "color": "#5266eb"},
    ]
    if "benchmark_composite" in equity_df.columns:
        equity_series.append({
            "key": "benchmark_composite",
            "label": f"Benchmark ({bench_label})",
            "color": "#d4a534",
        })
    for k, lab, col in (("SPY", "SPY", "#c3c3cc"), ("QQQ", "QQQ", "#f0b95b")):
        if k in equity_df.columns:
            equity_series.append({"key": k, "label": lab, "color": col})

    drawdown_rows = [
        {
            "date": pd.to_datetime(equity_df.iloc[idx]["date"]).strftime("%Y-%m-%d"),
            "value": _to_float(value),
        }
        for idx, value in enumerate(drawdown)
    ]

    weights_first = pd.to_datetime(weights_df.iloc[0]["date"]).strftime("%Y-%m-%d")
    # GICS-style lanes only apply to Adaptive Rotation; RSI and others use different construction.
    show_groups = run.strategy_slug == "adaptive_rotation"
    if show_groups:
        group_tl = _group_timeline(weights_df)
        max_g = MAX_TIMELINE_ACTIVE_GROUPS
        first_meaningful = _first_meaningful_group_holdings_date(weights_df)
    else:
        group_tl = []
        max_g = 0
        first_meaningful = None

    return {
        "run": run_metadata(run),
        "initial_capital": 1000.0,
        "max_timeline_active_groups": max_g,
        "show_group_timeline": show_groups,
        "weights_first_date": weights_first,
        "first_meaningful_group_holdings_date": first_meaningful,
        "equity": equity_rows,
        "equity_series": equity_series,
        "drawdown": drawdown_rows,
        "regimes": _regime_spans(equity_rows),
        "group_timeline": group_tl,
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
