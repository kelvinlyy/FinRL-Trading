"""Read-only live-trading readiness metadata for the web console."""

from __future__ import annotations

from typing import Any


def trading_status_public() -> dict[str, Any]:
    """Return non-secret status fields; never triggers broker execution."""
    from src.config.settings import get_config

    cfg = get_config()
    can_paper_trade = bool(
        cfg.alpaca.use_paper_trading
        and cfg.alpaca.api_key
        and str(cfg.alpaca.api_key).strip()
        and cfg.alpaca.api_secret
        and str(cfg.alpaca.api_secret).strip()
    )

    return {
        "mode": "deferred",
        "execution_enabled": False,
        "can_paper_trade_from_cli": can_paper_trade,
        "alpaca": {
            "base_url": cfg.alpaca.base_url,
            "use_paper_trading": cfg.alpaca.use_paper_trading,
        },
        "next_steps": [
            "Configure APCA_API_KEY and APCA_API_SECRET in .env.",
            "Run deploy.sh in paper mode from the repo root.",
            "Audit generated signal and execution logs before enabling any live capital path.",
        ],
        "message": (
            "Live/paper trading remains CLI-only for now. The apps console intentionally exposes "
            "read-only readiness status and does not submit broker orders."
        ),
    }
