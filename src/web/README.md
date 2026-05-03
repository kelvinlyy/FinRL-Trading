# FinRL Trading Dashboard (Web App)

## Overview

The web app is a **Streamlit-based dashboard** that provides an interactive UI for the FinRL Trading platform. It runs on port **8501** and is intended as a control panel for data management, strategy backtesting, live trading, and portfolio analysis.

> **Current status:** The dashboard is a **UI prototype**. Most pages display hard-coded sample data rather than connecting to the real strategy engine or live market data. See [Data Sources](#data-sources-mock-vs-real) below for details on what is real and what is mocked.

## How to Run

```bash
export PYTHONPATH=/path/to/project/src:/path/to/project
streamlit run src/web/app.py --server.port 8501 --server.headless true
```

Or via Docker:
```bash
docker compose up finrl-trading   # exposes port 8501
```

## Architecture

```
src/web/
├── app.py          # Main Streamlit application (all pages)
├── components.py   # Reusable UI components (charts, tables, cards)
├── __init__.py
└── README.md       # This file
```

### Dependencies

The web app imports from these project modules:

| Module | Import | Purpose |
|--------|--------|---------|
| `config.settings` | `get_config()` | App configuration (env vars, `.env` file) |
| `data.data_store` | `get_data_store()` | SQLite storage stats, cache management |
| `strategies.base_strategy` | `create_strategy()`, `StrategyConfig` | Strategy factory for backtesting |
| `backtest.backtest_engine` | `BacktestEngine`, `BacktestConfig` | Runs backtests from the UI |
| `trading.alpaca_manager` | `create_alpaca_account_from_env()` | Alpaca broker connection |
| `trading.trade_executor` | `TradeExecutor`, `ExecutionConfig` | Order execution |
| `utils.logging_utils` | `setup_logging()` | Logging configuration |

### Session State

The app uses Streamlit session state to persist data across page navigations:

- `st.session_state.config` — App configuration (loaded once on startup)
- `st.session_state.data_store` — Data store instance
- `st.session_state.backtest_result` — Most recent backtest result (set after running a backtest)

## Pages

### 1. Overview

The landing page showing a trading dashboard summary.

| Element | Data Source | Status |
|---------|-----------|--------|
| Key metrics (strategies, positions, portfolio value, P&L) | Hard-coded | Mock |
| Recent Activity table | Hard-coded DataFrame | Mock |
| Portfolio Performance chart | Random walk (`np.random.normal`) | Mock |

### 2. Data Management

Four tabs for managing market data.

| Tab | Functionality | Status |
|-----|--------------|--------|
| **Data Sources** | Button to fetch S&P 500 components and fundamentals via `data_fetcher`; CSV upload | Functional (requires FMP API key for fetcher) |
| **Data Processing** | Buttons to process raw data and generate ML datasets via `data_processor` | Wired but untested (expects specific file paths) |
| **Data Storage** | Displays SQLite storage stats as JSON; cache cleanup button | Functional |
| **Data Quality** | Quality metrics table | Mock (static scores) |

### 3. Strategy Backtesting

Backtest configuration form and results display.

| Element | Data Source | Status |
|---------|-----------|--------|
| Strategy selector (equal_weight, market_cap_weight, ml_strategy) | Config form | Functional |
| Date range, initial capital inputs | Config form | Functional |
| Backtest execution | `BacktestEngine` with **synthetic random price data** | Runs but uses fake data |
| Results: key metrics, equity chart, detailed metrics table | Computed from backtest result | Functional (values reflect random input) |

**Key limitation:** The `run_backtest()` function generates random price data inline rather than fetching real market data. The backtest engine itself works correctly — it's the data input that is synthetic.

### 4. Live Trading

Three tabs for Alpaca paper/live trading integration.

| Tab | Functionality | Status |
|-----|--------------|--------|
| **Portfolio** | Refresh button → loads account info and positions from Alpaca | Functional (requires Alpaca API keys in `.env`) |
| **Order Management** | Place order form (symbol, qty, side, type, limit price) | Functional (requires Alpaca API keys) |
| **Strategy Execution** | Execute sample equal-weight strategy button | Wired but references undefined `EqualWeightStrategy` class |

**Requires:** `APCA_API_KEY` and `APCA_API_SECRET` in `.env` to connect. Shows error message if not configured.

### 5. Portfolio Analysis

Four tabs with portfolio analytics.

| Tab | Functionality | Status |
|-----|--------------|--------|
| **Performance** | Equity line chart + metrics (total return, annual return, volatility, Sharpe) | Mock (random data) |
| **Risk Analysis** | Drawdown chart + risk metrics (max DD, VaR, CVaR) | Mock (random data) |
| **Attribution** | Return attribution bar chart by asset | Mock (static sample data) |
| **Benchmarking** | Portfolio vs SPY vs QQQ comparison chart | Mock (random data) |

### 6. Settings

Configuration panels (changes are UI-only and do not persist to disk).

| Tab | Controls | Status |
|-----|---------|--------|
| **General** | Logging level selector, theme selector | UI only (logging level does work in-session) |
| **Trading** | Max order value, max turnover slider, Alpaca API key inputs | UI only (not persisted) |
| **Data** | Data/cache directory paths, data source toggles | UI only (not persisted) |

## Reusable Components (`components.py`)

The `components.py` module provides Plotly chart builders and display helpers. These are **not currently used** by `app.py` (which builds its own charts inline) but are available for future integration.

| Component | Function | Description |
|-----------|----------|-------------|
| Portfolio summary cards | `display_portfolio_summary()` | 4-column metric cards |
| Performance chart | `create_performance_chart()` | Line chart with optional benchmarks |
| Returns distribution | `create_returns_distribution_chart()` | Histogram with break-even line |
| Drawdown chart | `create_drawdown_chart()` | Filled area drawdown visualization |
| Risk metrics table | `create_risk_metrics_table()` | Split performance/risk metric tables |
| Sector allocation | `create_sector_allocation_chart()` | Donut chart by sector |
| Strategy comparison | `create_strategy_comparison_chart()` | Multi-strategy overlay chart |
| Orders table | `display_orders_table()` | Formatted order history table |
| Correlation heatmap | `create_correlation_heatmap()` | Asset correlation matrix |
| Rolling Sharpe | `create_rolling_sharpe_chart()` | Rolling window Sharpe line chart |
| Data quality report | `display_data_quality_report()` | Quality score + issues + recommendations |
| Factor attribution | `create_factor_attribution_chart()` | Factor contribution bar chart |
| Alerts | `display_alerts()` | Color-coded alert messages |

## Data Sources: Mock vs Real

| Category | Mock | Real |
|----------|------|------|
| Overview metrics | All hard-coded | — |
| Backtest price data | Random walk | — |
| Portfolio Analysis charts | Random data | — |
| Data Quality scores | Static values | — |
| Attribution data | Static sample | — |
| Data Storage stats | — | SQLite `get_storage_stats()` |
| Data Sources fetch | — | FMP API via `data_fetcher` (requires API key) |
| Live Trading | — | Alpaca API (requires API keys) |
| Settings (log level) | — | In-session logging change |

## Comparison with Standalone Visualizer

The web app and the standalone backtest visualizer (`src/strategies/adaptive_rotation/visualizer.py`) serve different purposes:

| | Web App | Standalone Visualizer |
|---|---|---|
| **Output** | Interactive Streamlit UI | Static PNG + CSV |
| **Data** | Mostly mock/random | Real backtest results |
| **Triggered by** | Manual (`streamlit run`) | Auto after `deploy.sh` backtest |
| **Covers** | General platform UI (data, trading, settings) | Backtest-specific (equity, regime, groups, trades) |

## Known Issues

1. **Format strings:** Several `st.metric()` calls in `app.py` and `components.py` display literal format specifiers (e.g., `".2f"`) instead of formatted values. Fixed in `app.py` for key pages; `components.py` still has unfixed instances.
2. **Strategy Execution tab:** References `EqualWeightStrategy` which is not defined in `base_strategy.py`.
3. **Settings persistence:** None of the settings changes are saved to disk or `.env`.
4. **No connection to real strategy engine:** The backtest page doesn't use the Adaptive Rotation engine or real market data.
