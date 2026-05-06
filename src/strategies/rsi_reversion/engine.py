"""RSI mean-reversion portfolio weights (long-only)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from .config_loader import RSIParams, RSIReversionConfig


def wilder_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Wilder RSI on closing prices (matches common TA libraries)."""
    delta = close.astype(float).diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    alpha = 1.0 / float(period)
    avg_gain = gain.ewm(alpha=alpha, adjust=False).mean()
    avg_loss = loss.ewm(alpha=alpha, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi


@dataclass
class RSIWeights:
    """Target weights for one rebalance date."""

    weights: dict[str, float]
    cash_weight: float
    regime: str
    rsi_snapshot: dict[str, float | None]
    notes: str


class RSIReversionEngine:
    """Computes long-only weights from RSI oversold scores."""

    def __init__(self, config: RSIReversionConfig):
        self.config = config
        self.params: RSIParams = config.rsi

    def run(
        self,
        price_panel: dict[str, pd.Series],
        as_of: pd.Timestamp,
        symbols: list[str],
    ) -> RSIWeights:
        """
        price_panel: symbol -> daily close series indexed by date.
        as_of: decision date (use data available through this date).
        """
        p = self.params
        scores: dict[str, float] = {}
        rsi_vals: dict[str, float | None] = {}

        for sym in symbols:
            if sym not in price_panel:
                rsi_vals[sym] = None
                continue
            s = price_panel[sym].sort_index()
            s = s.loc[:as_of].dropna()
            need = p.period + 2
            if len(s) < need:
                rsi_vals[sym] = None
                continue
            rsi_s = wilder_rsi(s, period=p.period)
            rsi_now = float(rsi_s.iloc[-1])
            rsi_vals[sym] = rsi_now

            if rsi_now >= p.exit_rsi_min:
                continue
            raw = max(0.0, p.entry_rsi_max - rsi_now)
            if raw > 0:
                scores[sym] = raw

        if not scores:
            return RSIWeights(
                weights={},
                cash_weight=1.0,
                regime="rsi_reversion",
                rsi_snapshot=rsi_vals,
                notes="no_eligible_oversold",
            )

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[: p.max_positions]
        top = dict(ranked)
        total = sum(top.values())
        inv = min(max(p.invested_cap, 0.0), 1.0)
        weights = {k: (v / total) * inv for k, v in top.items()}
        cash = 1.0 - sum(weights.values())

        return RSIWeights(
            weights=weights,
            cash_weight=float(cash),
            regime="rsi_reversion",
            rsi_snapshot=rsi_vals,
            notes="ok",
        )

    def audit_dict(self, as_of: str, out: RSIWeights) -> dict[str, Any]:
        return {
            "strategy": self.config.strategy.name,
            "version": self.config.strategy.version,
            "date": as_of,
            "regime": out.regime,
            "notes": out.notes,
            "rsi_params": {
                "period": self.params.period,
                "entry_rsi_max": self.params.entry_rsi_max,
                "exit_rsi_min": self.params.exit_rsi_min,
                "invested_cap": self.params.invested_cap,
                "max_positions": self.params.max_positions,
            },
            "rsi": out.rsi_snapshot,
            "weights": out.weights,
            "cash": out.cash_weight,
        }
