"""Aggregate read-only data-layer stats for the console API (FMP daily CSVs + SQLite summary)."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]
FMP_DAILY = PROJECT_ROOT / "data" / "fmp_daily"


@dataclass
class FmpDailyStats:
    csv_count: int
    total_bytes: int
    relative_dir: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "csv_count": self.csv_count,
            "total_bytes": self.total_bytes,
            "total_mb": round(self.total_bytes / (1024 * 1024), 3) if self.total_bytes else 0.0,
            "relative_dir": self.relative_dir,
        }


def scan_fmp_daily_stats(data_dir: Path | None = None) -> FmpDailyStats:
    root = data_dir or FMP_DAILY
    count = 0
    total = 0
    if root.is_dir():
        for p in root.iterdir():
            if p.is_file() and p.suffix.lower() == ".csv" and p.name.endswith("_daily.csv"):
                count += 1
                try:
                    total += p.stat().st_size
                except OSError:
                    pass
    rel = str(root.relative_to(PROJECT_ROOT)) if root.is_relative_to(PROJECT_ROOT) else str(root)
    return FmpDailyStats(csv_count=count, total_bytes=total, relative_dir=rel)


def data_store_stats_safe() -> dict[str, Any] | None:
    """
    Light-weight DB row count + file size (avoids ``DataStore`` import chain / optional deps like tzlocal).

    For full ``DataStore.get_storage_stats()`` behavior, use the Python library in-process scripts.
    """
    try:
        from src.config.settings import get_config

        cfg = get_config()
        base = Path(cfg.data.base_dir)
        if not base.is_absolute():
            base = PROJECT_ROOT / base
        db_path = base / "finrl_trading.db"
        try:
            rel_db = str(db_path.relative_to(PROJECT_ROOT))
        except ValueError:
            rel_db = str(db_path)
        if not db_path.is_file():
            return {
                "database_path": rel_db,
                "database_exists": False,
                "price_records": 0,
                "note": "SQLite file not created yet (first DataStore use will create it).",
            }
        size_mb = db_path.stat().st_size / (1024 * 1024)
        price_count = 0
        with sqlite3.connect(db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='price_data'"
            )
            if cur.fetchone():
                cur.execute("SELECT COUNT(*) FROM price_data")
                price_count = int(cur.fetchone()[0])
        return {
            "database_path": rel_db,
            "database_exists": True,
            "database_size_mb": round(size_mb, 3),
            "price_records": price_count,
        }
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc), "hint": "Uses src.config.settings for DATA_BASE_DIR and sqlite3 on finrl_trading.db."}


def build_data_overview() -> dict[str, Any]:
    fmp = scan_fmp_daily_stats()
    return {
        "fmp_daily": fmp.to_dict(),
        "data_store": data_store_stats_safe(),
        "download": {
            "api_trigger": False,
            "message": (
                "Price refresh is not started from this API (would run a long blocking Yahoo pipeline). "
                "From the repo root run: ./deploy.sh --strategy adaptive_rotation --mode backtest "
                "--start <YYYY-MM-DD> --end <YYYY-MM-DD> and omit --skip-download to repopulate "
                f"{fmp.relative_dir}/."
            ),
        },
    }
