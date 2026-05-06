"""
Deprecated Streamlit component module.

This file intentionally keeps the old import path alive while making it explicit that the
active web console is implemented in apps/frontend + apps/backend.
"""

from __future__ import annotations


def _deprecated(*_args, **_kwargs):
    raise RuntimeError(
        "src.web.components is deprecated. Use the apps stack instead: "
        "Next.js (apps/frontend) + FastAPI (apps/backend)."
    )


display_portfolio_summary = _deprecated
create_performance_chart = _deprecated
create_returns_distribution_chart = _deprecated
create_drawdown_chart = _deprecated
create_risk_metrics_table = _deprecated
create_sector_allocation_chart = _deprecated
create_strategy_comparison_chart = _deprecated
display_orders_table = _deprecated
create_correlation_heatmap = _deprecated
display_alerts = _deprecated
create_rolling_sharpe_chart = _deprecated
display_data_quality_report = _deprecated
create_factor_attribution_chart = _deprecated
