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
        "mode": "paper_web_enabled",
        "execution_enabled": True,
        "can_paper_trade_from_cli": can_paper_trade,
        "alpaca": {
            "base_url": cfg.alpaca.base_url,
            "use_paper_trading": cfg.alpaca.use_paper_trading,
        },
        "next_steps": [
            "Configure APCA_API_KEY and APCA_API_SECRET in .env.",
            "Run a dry-run paper execution from the Trading page to preview orders.",
            "Disable dry-run only after reviewing execution logs and account protections.",
        ],
        "message": (
            "Paper trading can now be launched from the apps console. Keep dry-run enabled while "
            "validating weights, order plans, and account constraints."
        ),
    }
