"""
Verify ``data/fmp_daily`` CSVs exist and cover the requested backtest window.

Matches symbol discovery in ``deploy.sh`` (Adaptive Rotation + benchmarks).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG = PROJECT_ROOT / "src/strategies/AdaptiveRotationConf_v1.2.1.yaml"
DEFAULT_DATA_DIR = PROJECT_ROOT / "data" / "fmp_daily"


def _symbols_from_config(config_path: Path) -> list[str]:
    import yaml

    with open(config_path, encoding="utf-8") as handle:
        config = yaml.safe_load(handle)

    symbols: set[str] = set()
    for _group_name, group in (config.get("asset_groups") or {}).items():
        for sym in (group.get("symbols") or []):
            symbols.add(str(sym).strip())

    fallback = (config.get("portfolio") or {}).get("fallback") or {}
    for sym in fallback.get("symbols") or []:
        symbols.add(str(sym).strip())

    bench = config.get("benchmark") or {}
    extra = bench.get("excess_return_benchmark_symbols")
    if isinstance(extra, list) and extra:
        for sym in extra:
            t = str(sym).strip()
            if t:
                symbols.add(t)
    elif "excess_return_benchmark" in bench and bench.get("excess_return_benchmark") is not None:
        symbols.add(str(bench["excess_return_benchmark"]).strip())

    symbols.update(["^GSPC", "^VIX", "SPY", "QQQ"])
    return sorted(symbols)


def _config_history_weeks(config_path: Path) -> int:
    import yaml

    with open(config_path, encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    hist = config.get("history") or {}
    weeks = int(hist.get("minimum_history_weeks", 26))
    return max(weeks, 1)


@dataclass
class DataCoverageReport:
    ok: bool
    data_dir: str
    config_path: str
    backtest_start: str
    backtest_end: str
    symbols_required: int
    missing_files: list[str] = field(default_factory=list)
    insufficient_range: list[dict[str, Any]] = field(default_factory=list)

    def to_detail_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "message": (
                "Local Yahoo CSV data under data/fmp_daily is incomplete for this backtest. "
                "Fix the issues below, or run once from the repo root: "
                "./deploy.sh --strategy adaptive_rotation --mode backtest --start <s> --end <e> "
                "(omit --skip-download) to refresh downloads."
            ),
            "data_dir": self.data_dir,
            "config_path": self.config_path,
            "backtest_start": self.backtest_start,
            "backtest_end": self.backtest_end,
            "symbols_required": self.symbols_required,
            "missing_csv_for_symbols": self.missing_files,
            "insufficient_date_coverage": self.insufficient_range,
        }


def check_backtest_data_coverage(
    backtest_start: str,
    backtest_end: str,
    *,
    config_path: Path | None = None,
    data_dir: Path | None = None,
) -> DataCoverageReport:
    from backend.services.backtest_jobs import _validate_iso_date

    _validate_iso_date("start", backtest_start)
    _validate_iso_date("end", backtest_end)
    if pd.Timestamp(backtest_start) >= pd.Timestamp(backtest_end):
        raise ValueError("start must be before end")

    cfg = config_path or DEFAULT_CONFIG
    root = data_dir or DEFAULT_DATA_DIR
    if not cfg.is_file():
        raise FileNotFoundError(f"Strategy config not found: {cfg}")

    symbols = _symbols_from_config(cfg)
    lookback_weeks = _config_history_weeks(cfg)
    start_bt = pd.Timestamp(backtest_start)
    end_bt = pd.Timestamp(backtest_end)
    lookback_start = start_bt - timedelta(weeks=lookback_weeks)

    missing: list[str] = []
    bad_range: list[dict[str, Any]] = []

    for sym in symbols:
        path = root / f"{sym}_daily.csv"
        if not path.is_file():
            missing.append(sym)
            continue

        try:
            dates = pd.read_csv(path, usecols=["date"], parse_dates=["date"], encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            bad_range.append(
                {
                    "symbol": sym,
                    "csv_path": str(path.relative_to(PROJECT_ROOT)),
                    "issue": "unreadable_csv",
                    "detail": str(exc),
                }
            )
            continue

        if dates.empty:
            bad_range.append(
                {
                    "symbol": sym,
                    "csv_path": str(path.relative_to(PROJECT_ROOT)),
                    "issue": "empty_csv",
                }
            )
            continue

        csv_min = pd.Timestamp(dates["date"].min()).normalize()
        csv_max = pd.Timestamp(dates["date"].max()).normalize()
        start_n = start_bt.normalize()
        end_n = end_bt.normalize()
        lb_n = lookback_start.normalize()

        if csv_max < end_n:
            bad_range.append(
                {
                    "symbol": sym,
                    "csv_path": str(path.relative_to(PROJECT_ROOT)),
                    "issue": "ends_before_backtest_end",
                    "csv_date_min": csv_min.strftime("%Y-%m-%d"),
                    "csv_date_max": csv_max.strftime("%Y-%m-%d"),
                    "needs_data_through": backtest_end,
                }
            )
        if csv_min > start_n:
            bad_range.append(
                {
                    "symbol": sym,
                    "csv_path": str(path.relative_to(PROJECT_ROOT)),
                    "issue": "starts_after_backtest_start",
                    "csv_date_min": csv_min.strftime("%Y-%m-%d"),
                    "csv_date_max": csv_max.strftime("%Y-%m-%d"),
                    "needs_data_from": backtest_start,
                }
            )
        elif csv_min > lb_n:
            bad_range.append(
                {
                    "symbol": sym,
                    "csv_path": str(path.relative_to(PROJECT_ROOT)),
                    "issue": "short_lookback_vs_config",
                    "csv_date_min": csv_min.strftime("%Y-%m-%d"),
                    "csv_date_max": csv_max.strftime("%Y-%m-%d"),
                    "backtest_start": backtest_start,
                    "minimum_history_weeks": lookback_weeks,
                    "recommended_earliest_date": lb_n.strftime("%Y-%m-%d"),
                }
            )

    ok = not missing and not bad_range
    return DataCoverageReport(
        ok=ok,
        data_dir=str(root.relative_to(PROJECT_ROOT)),
        config_path=str(cfg.relative_to(PROJECT_ROOT)),
        backtest_start=backtest_start,
        backtest_end=backtest_end,
        symbols_required=len(symbols),
        missing_files=missing,
        insufficient_range=bad_range,
    )


def check_single_date_data_coverage(
    decision_date: str,
    *,
    config_path: Path | None = None,
    data_dir: Path | None = None,
) -> DataCoverageReport:
    """
    Same CSV rules as a range backtest, using YAML ``minimum_history_weeks`` before ``decision_date``.

    ``deploy.sh`` single mode still needs history through ``decision_date``; we validate
    ``[decision_date - weeks, decision_date]`` with the same logic as ``check_backtest_data_coverage``.
    """
    from backend.services.backtest_jobs import _validate_iso_date

    _validate_iso_date("date", decision_date)
    cfg = config_path or DEFAULT_CONFIG
    lookback_weeks = _config_history_weeks(cfg)
    end_bt = pd.Timestamp(decision_date)
    lookback_start = (end_bt - timedelta(weeks=lookback_weeks)).strftime("%Y-%m-%d")
    return check_backtest_data_coverage(
        lookback_start,
        decision_date,
        config_path=cfg,
        data_dir=data_dir,
    )
