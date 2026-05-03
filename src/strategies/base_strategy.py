from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Optional
import pandas as pd

@dataclass
class StrategyResult:
    strategy_name: str
    weights: pd.DataFrame
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class StrategyConfig:
    name: str = "BaseStrategy"

class BaseStrategy:
    """Minimal base strategy interface."""

    def __init__(self, config: StrategyConfig):
        self.config = config

    def generate_weights(self, data: Dict[str, pd.DataFrame], target_date: Optional[str] = None) -> StrategyResult:
        raise NotImplementedError("generate_weights must be implemented by subclasses")


def create_strategy(strategy_type: str, config: Optional[StrategyConfig] = None) -> BaseStrategy:
    """Create a strategy instance by name for web/backtest callers."""
    if config is None:
        config = StrategyConfig(name=strategy_type)

    registry: Dict[str, type] = {}
    try:
        from strategies.ml_strategy import MLStockSelectorStrategy
        registry["ml_strategy"] = MLStockSelectorStrategy
        registry["ml_stock_selector"] = MLStockSelectorStrategy
    except Exception:
        pass

    strategy_cls = registry.get(strategy_type)
    if strategy_cls is not None:
        return strategy_cls(config)

    return BaseStrategy(config)
