from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = PROJECT_ROOT / "src/strategies/output/weights/adaptive_rotation"
RESULT_RE = re.compile(r"enhanced_backtest_(?P<start>.+)_to_(?P<end>.+)\.png$")


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
