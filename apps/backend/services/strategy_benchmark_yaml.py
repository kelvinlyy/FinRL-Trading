"""Read / write only the ``benchmark`` block in a deploy-registered strategy YAML."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from backend.services.adaptive_yaml import (
    _atomic_write_text,
    _loose_benchmark_symbols,
    _parse_symbol_list,
    _writes_disabled,
)
from backend.services.strategy_registry import config_path_for_strategy

PROJECT_ROOT = Path(__file__).resolve().parents[3]
_MAX_BENCHMARK_SYMBOLS = 20


def load_strategy_benchmark_public(strategy: str) -> dict[str, Any]:
    path = config_path_for_strategy(strategy)
    with path.open(encoding="utf-8") as handle:
        raw: dict[str, Any] = yaml.safe_load(handle) or {}
    bench = raw.get("benchmark") or {}
    syms = _loose_benchmark_symbols(bench)
    label = syms[0] if len(syms) == 1 else " + ".join(syms)
    mtime = int(path.stat().st_mtime) if path.is_file() else 0
    return {
        "strategy": strategy,
        "config_file": str(path.relative_to(PROJECT_ROOT)),
        "config_mtime": mtime,
        "benchmark": bench,
        "excess_return_benchmark_symbols": syms,
        "benchmark_excess_label": label,
    }


def save_strategy_benchmark_public(strategy: str, symbols: list[Any]) -> dict[str, Any]:
    if _writes_disabled():
        raise PermissionError("YAML writes are disabled (FINRL_DISABLE_CONFIG_WRITE).")

    path = config_path_for_strategy(strategy)
    bench_clean = _parse_symbol_list(symbols, max_count=_MAX_BENCHMARK_SYMBOLS)

    with path.open(encoding="utf-8") as handle:
        raw: dict[str, Any] = yaml.safe_load(handle) or {}

    bench_block = raw.setdefault("benchmark", {})
    bench_block["excess_return_benchmark_symbols"] = bench_clean
    bench_block["excess_return_benchmark"] = bench_clean[0]

    dumped = yaml.dump(
        raw,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
        width=120,
    )
    _atomic_write_text(path, dumped)
    return load_strategy_benchmark_public(strategy)
