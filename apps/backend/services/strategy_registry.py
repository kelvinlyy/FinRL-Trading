"""Strategy names registered in ``deploy.sh`` (keep in sync with STRATEGIES block)."""

from __future__ import annotations

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
_DEPLOY_SH = PROJECT_ROOT / "deploy.sh"
_LINE_RE = re.compile(
    r"^(?P<name>[a-zA-Z0-9_]+)\|(?P<config>src/strategies/[^\|]+\.yaml)\|(?P<runner>src/[^\|]+\.py)\s*$"
)


def list_deploy_strategies() -> list[dict[str, str]]:
    """
    Parse ``deploy.sh`` STRATEGIES rows: ``name|config.yaml|runner.py``.

    If ``deploy.sh`` is missing or no rows match, returns a single in-tree default.
    """
    if not _DEPLOY_SH.is_file():
        return _fallback()
    names_seen: set[str] = set()
    out: list[dict[str, str]] = []
    for raw in _DEPLOY_SH.read_text(encoding="utf-8", errors="replace").splitlines():
        m = _LINE_RE.match(raw.strip())
        if not m:
            continue
        n = m.group("name")
        if n in names_seen:
            continue
        names_seen.add(n)
        out.append({"name": n, "config": m.group("config"), "runner": m.group("runner")})
    return out if out else _fallback()


def _fallback() -> list[dict[str, str]]:
    return [
        {
            "name": "adaptive_rotation",
            "config": "src/strategies/AdaptiveRotationConf_v1.2.1.yaml",
            "runner": "src/strategies/run_adaptive_rotation_strategy.py",
        }
    ]


def strategy_names() -> tuple[str, ...]:
    return tuple(s["name"] for s in list_deploy_strategies())


def is_known_strategy(name: str) -> bool:
    return name in strategy_names()


def config_path_for_strategy(name: str) -> Path:
    """Filesystem path to the YAML registered for ``name`` in ``deploy.sh``."""
    for row in list_deploy_strategies():
        if row["name"] != name:
            continue
        path = PROJECT_ROOT / row["config"]
        if path.is_file():
            return path
        raise FileNotFoundError(f"Missing config file for strategy {name}: {path}")
    raise ValueError(f"Unknown strategy '{name}' (not listed in deploy.sh STRATEGIES)")


def resolve_strategy_output_dirs(strategy_name: str) -> tuple[Path, Path]:
    """
    Return ``(weights_dir, audit_dir)`` from the strategy YAML ``paths`` section.
    """
    import yaml

    cfg_path = config_path_for_strategy(strategy_name)
    with cfg_path.open(encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh) or {}
    paths = cfg.get("paths") or {}

    def _abs(rel_or_abs: str) -> Path:
        raw = Path(rel_or_abs)
        return raw.resolve() if raw.is_absolute() else (PROJECT_ROOT / raw).resolve()

    wd = str(paths.get("weights_dir") or "src/strategies/output/weights/adaptive_rotation")
    ad = str(paths.get("audit_dir") or "src/strategies/output/audit/adaptive_rotation")
    return _abs(wd), _abs(ad)
