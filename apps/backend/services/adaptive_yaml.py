"""Read / write Adaptive Rotation YAML for API / UI."""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = PROJECT_ROOT / "src/strategies/AdaptiveRotationConf_v1.2.1.yaml"
DATA_DIR = PROJECT_ROOT / "data" / "fmp_daily"

KNOWN_GROUP_IDS: tuple[str, ...] = (
    "group_a_growth_tech",
    "group_b_real_assets",
    "group_c_defensive",
)

GROUP_LABELS: dict[str, str] = {
    "group_a_growth_tech": "Growth Tech",
    "group_b_real_assets": "Real Assets",
    "group_c_defensive": "Defensive",
}

_MAX_SYMBOLS_PER_GROUP = 80
_MAX_FALLBACK_SYMBOLS = 40
_MAX_BENCHMARK_SYMBOLS = 20
_SYMBOL_RE = re.compile(r"^[A-Z0-9][A-Z0-9.\-]*$|^\^[A-Z0-9][A-Z0-9.\-]*$")


def _strip_symbols(seq: list[Any] | None) -> list[str]:
    if not seq:
        return []
    return [str(s).strip() for s in seq if str(s).strip()]


def _validate_symbol(sym: str) -> str:
    s = str(sym).strip().upper().replace(" ", "")
    if not s or len(s) > 20:
        raise ValueError(f"Invalid symbol (length 1–20): {sym!r}")
    if not _SYMBOL_RE.match(s):
        raise ValueError(f"Invalid symbol characters: {sym!r}")
    return s


def _parse_symbol_list(seq: list[Any], *, max_count: int) -> list[str]:
    if not seq:
        raise ValueError("At least one symbol is required.")
    seen: set[str] = set()
    out: list[str] = []
    for item in seq:
        v = _validate_symbol(str(item))
        if v not in seen:
            seen.add(v)
            out.append(v)
    if len(out) > max_count:
        raise ValueError(f"Too many symbols (max {max_count}).")
    return out


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _writes_disabled() -> bool:
    v = os.environ.get("FINRL_DISABLE_CONFIG_WRITE", "").strip().lower()
    return v in ("1", "true", "yes", "on")


def _loose_benchmark_symbols(bench: dict[str, Any]) -> list[str]:
    """Resolve benchmark tickers for API display (matches strategy loader semantics)."""
    extra = bench.get("excess_return_benchmark_symbols")
    if isinstance(extra, list):
        seen: set[str] = set()
        out: list[str] = []
        for s in _strip_symbols(extra):
            u = s.upper().replace(" ", "")
            if u and u not in seen:
                seen.add(u)
                out.append(u)
        if out:
            return out
    one = bench.get("excess_return_benchmark")
    if one is not None and str(one).strip():
        return [str(one).strip().upper().replace(" ", "")]
    return ["QQQ"]


def load_adaptive_rotation_public() -> dict[str, Any]:
    if not CONFIG_PATH.is_file():
        raise FileNotFoundError(str(CONFIG_PATH))

    with open(CONFIG_PATH, encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)

    groups: list[dict[str, Any]] = []
    for gid, grp in (raw.get("asset_groups") or {}).items():
        syms = _strip_symbols(grp.get("symbols"))
        groups.append(
            {
                "id": gid,
                "title": GROUP_LABELS.get(gid, gid.replace("_", " ").title()),
                "max_assets": grp.get("max_assets"),
                "symbols": syms,
            }
        )
    groups.sort(key=lambda g: g["id"])

    portfolio = raw.get("portfolio") or {}
    fb = portfolio.get("fallback") or {}
    bench = raw.get("benchmark") or {}
    bench_symbols = _loose_benchmark_symbols(bench)
    bench_label = bench_symbols[0] if len(bench_symbols) == 1 else " + ".join(bench_symbols)

    baseline_candidates = ["QQQ", "VOO", "SPY"]
    baseline_csv_present = []
    for sym in baseline_candidates:
        if (DATA_DIR / f"{sym}_daily.csv").is_file():
            baseline_csv_present.append(sym)

    mtime = int(CONFIG_PATH.stat().st_mtime) if CONFIG_PATH.is_file() else 0

    return {
        "config_file": str(CONFIG_PATH.relative_to(PROJECT_ROOT)),
        "data_daily_dir": str(DATA_DIR.relative_to(PROJECT_ROOT)),
        "config_mtime": mtime,
        "benchmark": bench,
        "excess_return_benchmark": bench_symbols[0],
        "excess_return_benchmark_symbols": bench_symbols,
        "benchmark_excess_label": bench_label,
        "portfolio_fallback": {
            "enabled": fb.get("enabled"),
            "symbols": _strip_symbols(fb.get("symbols")),
        },
        "asset_groups": groups,
        "baseline_price_csv_present": baseline_csv_present,
        "baseline_price_csv_candidates": baseline_candidates,
    }


def save_adaptive_rotation_public(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Merge universe fields into ``AdaptiveRotationConf_v1.2.1.yaml`` and rewrite the file.

    Raises:
        FileNotFoundError: Config path missing.
        PermissionError: When ``FINRL_DISABLE_CONFIG_WRITE`` is set.
        ValueError: Invalid payload (422 in API).
    """
    if _writes_disabled():
        raise PermissionError("YAML writes are disabled (FINRL_DISABLE_CONFIG_WRITE).")

    if not CONFIG_PATH.is_file():
        raise FileNotFoundError(str(CONFIG_PATH))

    ag_in = payload.get("asset_groups")
    if not isinstance(ag_in, list):
        raise ValueError("asset_groups must be a list.")
    by_id: dict[str, dict[str, Any]] = {}
    for item in ag_in:
        if not isinstance(item, dict):
            raise ValueError("Each asset_groups entry must be an object.")
        gid = str(item.get("id", "")).strip()
        if not gid:
            raise ValueError("Each group must have an id.")
        by_id[gid] = item

    if set(by_id) != set(KNOWN_GROUP_IDS):
        raise ValueError(f"asset_groups ids must be exactly: {list(KNOWN_GROUP_IDS)}")

    fb_in = payload.get("portfolio_fallback")
    if not isinstance(fb_in, dict):
        raise ValueError("portfolio_fallback must be an object.")
    bench_syms_in = payload.get("excess_return_benchmark_symbols")
    if not isinstance(bench_syms_in, list):
        raise ValueError("excess_return_benchmark_symbols must be a list.")
    bench_clean = _parse_symbol_list(bench_syms_in, max_count=_MAX_BENCHMARK_SYMBOLS)

    with open(CONFIG_PATH, encoding="utf-8") as handle:
        raw: dict[str, Any] = yaml.safe_load(handle) or {}

    bench_block = raw.setdefault("benchmark", {})
    bench_block["excess_return_benchmark_symbols"] = bench_clean
    bench_block["excess_return_benchmark"] = bench_clean[0]

    portfolio = raw.setdefault("portfolio", {})
    fb = portfolio.setdefault("fallback", {})
    fb["enabled"] = bool(fb_in.get("enabled"))
    syms_fb = fb_in.get("symbols")
    if not isinstance(syms_fb, list):
        raise ValueError("portfolio_fallback.symbols must be a list.")
    fb["symbols"] = _parse_symbol_list(syms_fb, max_count=_MAX_FALLBACK_SYMBOLS)
    fb.setdefault("allocation", "equal")

    asset_groups = raw.setdefault("asset_groups", {})
    for gid in KNOWN_GROUP_IDS:
        grp_body = by_id[gid]
        max_assets = grp_body.get("max_assets")
        try:
            max_i = int(max_assets)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid max_assets for {gid}.") from exc
        if not 1 <= max_i <= 20:
            raise ValueError(f"max_assets for {gid} must be between 1 and 20.")

        syms_g = grp_body.get("symbols")
        if not isinstance(syms_g, list):
            raise ValueError(f"symbols for {gid} must be a list.")
        cleaned = _parse_symbol_list(syms_g, max_count=_MAX_SYMBOLS_PER_GROUP)

        block = asset_groups.setdefault(gid, {})
        block["max_assets"] = max_i
        block["symbols"] = cleaned

    dumped = yaml.dump(
        raw,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
        width=120,
    )
    _atomic_write_text(CONFIG_PATH, dumped)
    return load_adaptive_rotation_public()
