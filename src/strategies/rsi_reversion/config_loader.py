"""YAML config for RSI mean-reversion strategy."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass
class StrategyMeta:
    name: str
    version: str


@dataclass
class PathsConfig:
    data_root: str
    output_root: str
    state_dir: str
    audit_dir: str
    weights_dir: str


@dataclass
class DatesConfig:
    start_date: str
    end_date: str | None


@dataclass
class RSIParams:
    period: int
    # Long-only: score = max(0, entry_rsi_max - rsi); zero allocation if rsi >= exit_rsi_min
    entry_rsi_max: float
    exit_rsi_min: float
    invested_cap: float
    max_positions: int


@dataclass
class BenchmarkConfig:
    excess_return_benchmark: str


@dataclass
class RSIReversionConfig:
    strategy: StrategyMeta
    paths: PathsConfig
    dates: DatesConfig
    rsi: RSIParams
    benchmark: BenchmarkConfig
    raw: dict[str, Any]


def _paths(d: dict[str, Any]) -> PathsConfig:
    p = d.get("paths", {})
    return PathsConfig(
        data_root=str(p.get("data_root", "./data/fmp_daily")),
        output_root=str(p.get("output_root", "./src/strategies/output")),
        state_dir=str(p.get("state_dir", "./src/strategies/output/state/rsi_reversion")),
        audit_dir=str(p.get("audit_dir", "./src/strategies/output/audit/rsi_reversion")),
        weights_dir=str(p.get("weights_dir", "./src/strategies/output/weights/rsi_reversion")),
    )


def _strategy_meta(d: dict[str, Any]) -> StrategyMeta:
    s = d.get("strategy", {})
    return StrategyMeta(
        name=str(s.get("name", "rsi_mean_reversion")),
        version=str(s.get("version", "v1.0.0")),
    )


def _dates(d: dict[str, Any]) -> DatesConfig:
    dt = d.get("dates", {})
    end = dt.get("end_date")
    return DatesConfig(
        start_date=str(dt.get("start_date", "2017-01-01")),
        end_date=str(end) if end else None,
    )


def _rsi(d: dict[str, Any]) -> RSIParams:
    r = d.get("rsi", {})
    return RSIParams(
        period=int(r.get("period", 14)),
        entry_rsi_max=float(r.get("entry_rsi_max", 40.0)),
        exit_rsi_min=float(r.get("exit_rsi_min", 70.0)),
        invested_cap=float(r.get("invested_cap", 0.95)),
        max_positions=int(r.get("max_positions", 8)),
    )


def _benchmark(d: dict[str, Any]) -> BenchmarkConfig:
    b = d.get("benchmark", {})
    return BenchmarkConfig(
        excess_return_benchmark=str(b.get("excess_return_benchmark", "SPY")),
    )


def load_config(config_path: str | Path) -> RSIReversionConfig:
    path = Path(config_path)
    with path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    return RSIReversionConfig(
        strategy=_strategy_meta(raw),
        paths=_paths(raw),
        dates=_dates(raw),
        rsi=_rsi(raw),
        benchmark=_benchmark(raw),
        raw=raw,
    )


def universe_symbols(cfg: RSIReversionConfig) -> list[str]:
    """All tradeable symbols from asset_groups (same layout as adaptive rotation)."""
    syms: list[str] = []
    for group in cfg.raw.get("asset_groups", {}).values():
        if not isinstance(group, dict):
            continue
        for s in group.get("symbols", []) or []:
            syms.append(str(s))
    return sorted(set(syms))


def download_symbols(cfg: RSIReversionConfig) -> set[str]:
    """Symbols required for yfinance download (universe + benchmark + chart refs)."""
    s = set(universe_symbols(cfg))
    s.add(cfg.benchmark.excess_return_benchmark)
    s.update(["^GSPC", "^VIX", "SPY", "QQQ"])
    return s
