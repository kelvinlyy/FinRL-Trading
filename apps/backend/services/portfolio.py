from __future__ import annotations

from typing import Any

import pandas as pd

from backend.services.results import latest_run


def _to_float(v: Any) -> float:
    try:
        if pd.isna(v):
            return 0.0
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _latest_weights_snapshot(run_weights_csv: pd.DataFrame) -> list[dict[str, Any]]:
    if run_weights_csv.empty:
        return []
    df = run_weights_csv.copy()
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
        row = df.sort_values("date").iloc[-1]
    else:
        row = df.iloc[-1]
    excluded = {"date", "cash", "regime"}
    positions: list[dict[str, Any]] = []
    for col in df.columns:
        if col in excluded:
            continue
        w = _to_float(row.get(col))
        if w <= 0:
            continue
        positions.append({"symbol": col, "weight": w})
    positions.sort(key=lambda x: x["weight"], reverse=True)
    total_weight = sum(x["weight"] for x in positions) or 1.0
    for p in positions:
        p["weight_pct"] = round(p["weight"] * 100, 3)
        p["share_of_invested_pct"] = round((p["weight"] / total_weight) * 100, 3)
    return positions


def portfolio_overview() -> dict[str, Any]:
    run = latest_run()
    if run is None:
        return {
            "has_run": False,
            "message": "No backtest outputs were found. Run a backtest first.",
            "run": None,
            "kpis": {},
            "positions": [],
            "trades": {"count": 0, "latest": []},
        }

    summary_df = pd.read_csv(run.summary_path) if run.summary_path.exists() else pd.DataFrame()
    trade_df = pd.read_csv(run.trade_log_path) if run.trade_log_path.exists() else pd.DataFrame()
    weights_df = pd.read_csv(run.weights_path) if run.weights_path.exists() else pd.DataFrame()

    latest_positions = _latest_weights_snapshot(weights_df)
    top3_concentration = round(sum(p["weight"] for p in latest_positions[:3]) * 100, 3) if latest_positions else 0.0

    kpis: dict[str, Any] = {
        "summary_rows": int(len(summary_df)),
        "trade_rows": int(len(trade_df)),
        "active_positions": int(len(latest_positions)),
        "top3_weight_pct": top3_concentration,
    }
    if not summary_df.empty:
        row = summary_df.iloc[-1]
        for src, dst in (
            ("total_return", "total_return"),
            ("annual_return", "annual_return"),
            ("max_drawdown", "max_drawdown"),
            ("sharpe_ratio", "sharpe_ratio"),
            ("volatility", "volatility"),
        ):
            if src in summary_df.columns:
                kpis[dst] = _to_float(row.get(src))

    latest_trades: list[dict[str, Any]] = []
    if not trade_df.empty:
        t = trade_df.copy()
        if "date" in t.columns:
            t["date"] = pd.to_datetime(t["date"])
            t = t.sort_values("date", ascending=False)
        latest_trades = t.head(20).fillna("").to_dict(orient="records")

    return {
        "has_run": True,
        "message": "Portfolio analytics are sourced from the latest run outputs.",
        "run": {"id": run.id, "start": run.start, "end": run.end, "label": run.label},
        "kpis": kpis,
        "positions": latest_positions,
        "trades": {"count": int(len(trade_df)), "latest": latest_trades},
    }
