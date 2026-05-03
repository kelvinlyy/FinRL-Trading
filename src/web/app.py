"""
FinRL Trading Dashboard
======================

Main Streamlit application for the FinRL Trading platform.
Provides interactive visualization and control of trading strategies.
"""

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import logging
from pathlib import Path
import json
import os
import re
import subprocess
import sys
from typing import Optional

# Import project modules
try:
    from ..config.settings import get_config
    from ..data.data_store import get_data_store
    from ..strategies.base_strategy import create_strategy, StrategyConfig
    from ..backtest.backtest_engine import BacktestEngine, BacktestConfig
    from ..trading.alpaca_manager import create_alpaca_account_from_env
    from ..trading.trade_executor import TradeExecutor, ExecutionConfig
    from ..utils.logging_utils import setup_logging
except ImportError:
    # Fallback for direct module testing
    from config.settings import get_config
    from data.data_store import get_data_store
    from strategies.base_strategy import create_strategy, StrategyConfig
    from backtest.backtest_engine import BacktestEngine, BacktestConfig
    from trading.alpaca_manager import create_alpaca_account_from_env
    from trading.trade_executor import TradeExecutor, ExecutionConfig
    try:
        from utils.logging_utils import setup_logging
    except ImportError:
        setup_logging = None

# Setup logging
logger = logging.getLogger(__name__)

# Configure page
st.set_page_config(
    page_title="FinRL Trading Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'config' not in st.session_state:
    st.session_state.config = get_config()
if 'data_store' not in st.session_state:
    st.session_state.data_store = get_data_store()

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ADAPTIVE_CONFIG = PROJECT_ROOT / "src/strategies/AdaptiveRotationConf_v1.2.1.yaml"
DEFAULT_ADAPTIVE_DATA_DIR = PROJECT_ROOT / "data/fmp_daily"
DEFAULT_ADAPTIVE_WEIGHTS_DIR = PROJECT_ROOT / "src/strategies/output/weights/adaptive_rotation"


def mock_tbd_notice(message: str = "This section currently uses mock/demo data and is TBD for real integration."):
    """Show a consistent marker for prototype sections."""
    st.warning(f"Mock / TBD: {message}")


def _format_money(value) -> str:
    try:
        return f"${float(value):,.2f}"
    except (TypeError, ValueError):
        return "$0.00"


def _format_pct(value) -> str:
    try:
        return f"{float(value):.2%}"
    except (TypeError, ValueError):
        return "0.00%"


def _safe_filename_date(value) -> str:
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    return str(value)


def _parse_backtest_filename(path: Path) -> dict:
    match = re.match(r"enhanced_backtest_(.+)_to_(.+)\.png", path.name)
    if not match:
        return {"label": path.name, "start": "", "end": ""}
    start, end = match.groups()
    return {"label": f"{start} to {end}", "start": start, "end": end}


def _list_adaptive_results() -> list[Path]:
    if not DEFAULT_ADAPTIVE_WEIGHTS_DIR.exists():
        return []
    return sorted(
        DEFAULT_ADAPTIVE_WEIGHTS_DIR.glob("enhanced_backtest_*_to_*.png"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )


def _read_trade_log_for_chart(chart_path: Path) -> Optional[pd.DataFrame]:
    info = _parse_backtest_filename(chart_path)
    if not info["start"] or not info["end"]:
        return None
    trade_path = chart_path.with_name(f"trade_log_{info['start']}_to_{info['end']}.csv")
    if not trade_path.exists():
        return None
    df = pd.read_csv(trade_path)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    return df


def run_adaptive_rotation_backtest(start_date, end_date, skip_download: bool = True):
    """Run the real Adaptive Rotation backtest pipeline via deploy.sh."""
    start = _safe_filename_date(start_date)
    end = _safe_filename_date(end_date)
    cmd = [
        "./deploy.sh",
        "--strategy", "adaptive_rotation",
        "--mode", "backtest",
        "--start", start,
        "--end", end,
    ]
    if skip_download:
        cmd.append("--skip-download")

    env = os.environ.copy()
    env["PYTHONPATH"] = f"{PROJECT_ROOT / 'src'}:{PROJECT_ROOT}:{env.get('PYTHONPATH', '')}"

    result = subprocess.run(
        cmd,
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=900,
    )

    st.session_state.adaptive_backtest_stdout = result.stdout
    st.session_state.adaptive_backtest_stderr = result.stderr

    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout or "Backtest command failed")

    chart = DEFAULT_ADAPTIVE_WEIGHTS_DIR / f"enhanced_backtest_{start}_to_{end}.png"
    trade_log = DEFAULT_ADAPTIVE_WEIGHTS_DIR / f"trade_log_{start}_to_{end}.csv"
    summary = DEFAULT_ADAPTIVE_WEIGHTS_DIR / f"backtest_{start}_to_{end}.csv"

    st.session_state.adaptive_backtest_result = {
        "start": start,
        "end": end,
        "chart": str(chart),
        "trade_log": str(trade_log),
        "summary": str(summary),
    }
    return st.session_state.adaptive_backtest_result


def main():
    """Main application function."""
    st.title("📈 FinRL Trading Dashboard")
    st.markdown("AI-powered quantitative trading platform")

    # Sidebar navigation
    with st.sidebar:
        st.header("Navigation")
        page = st.selectbox(
            "Select Page",
            ["Overview", "Data Management", "Strategy Backtesting",
             "Live Trading", "Portfolio Analysis", "Settings"]
        )

        st.divider()

        # Quick stats
        display_quick_stats()

    # Main content
    if page == "Overview":
        show_overview()
    elif page == "Data Management":
        show_data_management()
    elif page == "Strategy Backtesting":
        show_strategy_backtesting()
    elif page == "Live Trading":
        show_live_trading()
    elif page == "Portfolio Analysis":
        show_portfolio_analysis()
    elif page == "Settings":
        show_settings()


def display_quick_stats():
    """Display quick statistics in sidebar."""
    st.subheader("Quick Stats")

    try:
        # Get data store stats
        stats = st.session_state.data_store.get_storage_stats()

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Data Versions", stats.get('data_versions', 0))
        with col2:
            st.metric("Cache Entries", stats.get('cache_entries', 0))

        storage_mb = stats.get('storage_used_mb', 0)
        st.metric("Storage Used", f"{storage_mb:.1f} MB")

    except Exception as e:
        st.error(f"Could not load stats: {e}")


def show_overview():
    """Show overview dashboard."""
    st.header("Trading Overview")
    mock_tbd_notice("Overview metrics, recent activity, and portfolio chart are demo placeholders.")

    # Key metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Strategies", "5", "↗️ 2")
    with col2:
        st.metric("Active Positions", "12", "↗️ 3")
    with col3:
        st.metric("Portfolio Value", "$1,250,000", "+2.5%")
    with col4:
        st.metric("Today's P&L", "+$1,250", "+1.2%")

    # Recent activity
    st.subheader("Recent Activity")
    activity_data = pd.DataFrame({
        'Time': pd.date_range('2024-01-01 09:00', periods=5, freq='1h'),
        'Action': ['Strategy Execution', 'Portfolio Rebalance', 'Data Update', 'Order Filled', 'Strategy Backtest'],
        'Status': ['Success', 'Success', 'Success', 'Success', 'Completed'],
        'Details': ['ML Strategy executed', 'Quarterly rebalance', 'S&P 500 data updated', 'AAPL order filled', 'Backtest completed']
    })

    st.dataframe(activity_data, use_container_width=True)

    # Performance chart
    st.subheader("Portfolio Performance")
    dates = pd.date_range('2024-01-01', periods=30, freq='D')
    portfolio_values = 1000000 + np.cumsum(np.random.normal(1000, 5000, 30))

    fig = px.line(x=dates, y=portfolio_values, title="Portfolio Value Over Time")
    fig.update_layout(xaxis_title="Date", yaxis_title="Portfolio Value ($)")
    st.plotly_chart(fig, use_container_width=True)


def show_data_management():
    """Show data management interface."""
    st.header("Data Management")

    tab1, tab2, tab3, tab4 = st.tabs(["Data Sources", "Data Processing", "Data Storage", "Data Quality"])

    with tab1:
        st.subheader("Data Sources")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("WRDS Data")
            if st.button("Fetch S&P 500 Components"):
                with st.spinner("Fetching data..."):
                    try:
                        from ..data.data_fetcher import fetch_sp500_tickers
                        tickers = fetch_sp500_tickers()
                        st.success(f"Successfully fetched {len(tickers)} tickers")
                        st.info(f"Sample tickers: {tickers[:10]}")
                    except Exception as e:
                        st.error(f"Failed to fetch data: {e}")

            if st.button("Fetch Fundamental Data"):
                with st.spinner("Fetching fundamental data..."):
                    try:
                        from ..data.data_fetcher import fetch_fundamental_data
                        fundamentals = fetch_fundamental_data(
                            ['AAPL', 'MSFT', 'GOOGL'], '2020-01-01', '2023-12-31'
                        )
                        st.success(f"Successfully fetched {len(fundamentals)} records")
                    except Exception as e:
                        st.error(f"Failed to fetch data: {e}")

        with col2:
            st.subheader("Local Data")
            uploaded_file = st.file_uploader("Upload CSV file", type=['csv'])
            if uploaded_file is not None:
                df = pd.read_csv(uploaded_file)
                st.write(f"Uploaded {len(df)} rows")
                st.dataframe(df.head())

    with tab2:
        st.subheader("Data Processing")
        mock_tbd_notice("These buttons expect placeholder local CSV files and need a proper file/path workflow.")
        mock_tbd_notice(
            "These buttons call pipeline helpers with placeholder paths "
            "(`./data/fundamentals.csv`, `./data/prices.csv`)."
        )

        if st.button("Process Raw Data"):
            with st.spinner("Processing data..."):
                try:
                    from ..data.data_processor import process_fundamentals, process_prices

                    # Process sample data
                    mock_tbd_notice("Processing buttons expect local placeholder files; real ingestion pipeline is TBD.")
                    fundamentals = process_fundamentals("./data/fundamentals.csv")
                    prices = process_prices("./data/prices.csv")

                    st.success("Data processing completed")
                    st.write(f"Processed {len(fundamentals)} fundamental records")
                    st.write(f"Processed {len(prices)} price records")

                except Exception as e:
                    st.error(f"Data processing failed: {e}")

        if st.button("Generate ML Dataset"):
            with st.spinner("Creating ML dataset..."):
                try:
                    from ..data.data_processor import create_ml_dataset

                    X, y = create_ml_dataset("./data/fundamentals.csv", "./data/prices.csv")
                    st.success("ML dataset created")
                    st.write(f"Features shape: {X.shape}")
                    st.write(f"Target shape: {y.shape}")

                except Exception as e:
                    st.error(f"ML dataset creation failed: {e}")

    with tab3:
        st.subheader("Data Storage")

        # Display storage stats
        stats = st.session_state.data_store.get_storage_stats()
        st.json(stats)

        if st.button("Cleanup Expired Cache"):
            with st.spinner("Cleaning up cache..."):
                try:
                    st.session_state.data_store.cleanup_expired_cache()
                    st.success("Cache cleanup completed")
                except Exception as e:
                    st.error(f"Cache cleanup failed: {e}")

    with tab4:
        st.subheader("Data Quality")
        mock_tbd_notice("Data quality scores below are static sample values.")

        # Data quality checks
        st.subheader("Data Quality Metrics")

        # Sample quality metrics
        quality_data = pd.DataFrame({
            'Metric': ['Completeness', 'Accuracy', 'Consistency', 'Timeliness'],
            'Score': [95.2, 98.1, 92.3, 99.8],
            'Status': ['Good', 'Excellent', 'Good', 'Excellent']
        })

        st.dataframe(quality_data, use_container_width=True)


def show_strategy_backtesting():
    """Show strategy backtesting interface."""
    st.header("Strategy Backtesting")

    tab_real, tab_results, tab_mock = st.tabs([
        "Adaptive Rotation (Real)",
        "Saved Results",
        "Legacy Demo (Mock / TBD)",
    ])

    with tab_real:
        show_adaptive_rotation_backtest()

    with tab_results:
        show_adaptive_results_browser()

    with tab_mock:
        show_legacy_demo_backtest()


def show_adaptive_rotation_backtest():
    """Run the real Adaptive Rotation backtest and display generated artifacts."""
    st.subheader("Adaptive Rotation Backtest")
    st.success(
        "Real workflow: runs deploy.sh, fetches/uses Yahoo Finance CSV data, executes the "
        "Adaptive Rotation strategy, then displays the enhanced chart and trade log."
    )

    col1, col2 = st.columns([1, 2])

    with col1:
        start_date = st.date_input(
            "Start Date",
            datetime(2024, 1, 1),
            key="adaptive_start_date",
        )
        end_date = st.date_input(
            "End Date",
            datetime(2025, 5, 2),
            key="adaptive_end_date",
        )
        skip_download = st.checkbox(
            "Skip Yahoo download if data exists",
            value=True,
            help="Uses existing data/fmp_daily CSVs when checked. Uncheck to refresh from Yahoo Finance.",
        )
        st.caption(f"Config: `{DEFAULT_ADAPTIVE_CONFIG.relative_to(PROJECT_ROOT)}`")
        st.caption(f"Data dir: `{DEFAULT_ADAPTIVE_DATA_DIR.relative_to(PROJECT_ROOT)}`")

        if st.button("Run Adaptive Rotation Backtest", type="primary"):
            if start_date >= end_date:
                st.error("Start date must be before end date.")
            else:
                with st.spinner("Running real Adaptive Rotation backtest. This can take a few minutes..."):
                    try:
                        result = run_adaptive_rotation_backtest(start_date, end_date, skip_download)
                        st.success("Backtest completed and artifacts generated.")
                    except Exception as e:
                        st.error(f"Adaptive Rotation backtest failed: {e}")
                        result = None
                if result:
                    display_adaptive_result(result)

    with col2:
        result = st.session_state.get("adaptive_backtest_result")
        if result:
            display_adaptive_result(result)
        else:
            latest = _list_adaptive_results()
            if latest:
                st.info("No run selected yet. Showing latest saved result.")
                info = _parse_backtest_filename(latest[0])
                display_adaptive_result({
                    "start": info["start"],
                    "end": info["end"],
                    "chart": str(latest[0]),
                    "trade_log": str(latest[0].with_name(f"trade_log_{info['start']}_to_{info['end']}.csv")),
                    "summary": str(latest[0].with_name(f"backtest_{info['start']}_to_{info['end']}.csv")),
                })
            else:
                st.info("No Adaptive Rotation results found yet. Run a backtest to generate charts and trade logs.")

    stdout = st.session_state.get("adaptive_backtest_stdout")
    stderr = st.session_state.get("adaptive_backtest_stderr")
    if stdout or stderr:
        with st.expander("Backtest command output"):
            if stdout:
                st.code(stdout[-6000:])
            if stderr:
                st.code(stderr[-2000:])


def show_adaptive_results_browser():
    """Browse previously generated Adaptive Rotation outputs."""
    st.subheader("Saved Adaptive Rotation Results")
    results = _list_adaptive_results()
    if not results:
        st.info("No saved enhanced backtest charts found.")
        return

    labels = [_parse_backtest_filename(p)["label"] for p in results]
    selected_label = st.selectbox("Select saved result", labels)
    selected = results[labels.index(selected_label)]
    info = _parse_backtest_filename(selected)

    display_adaptive_result({
        "start": info["start"],
        "end": info["end"],
        "chart": str(selected),
        "trade_log": str(selected.with_name(f"trade_log_{info['start']}_to_{info['end']}.csv")),
        "summary": str(selected.with_name(f"backtest_{info['start']}_to_{info['end']}.csv")),
    })


def display_adaptive_result(result: dict):
    """Render enhanced chart, summary, and trade log for a real Adaptive Rotation result."""
    chart = Path(result.get("chart", ""))
    trade_log = Path(result.get("trade_log", ""))
    summary = Path(result.get("summary", ""))

    st.markdown(f"**Result:** `{result.get('start', '')}` to `{result.get('end', '')}`")

    if chart.exists():
        st.image(str(chart), caption="Enhanced Adaptive Rotation chart: equity, regime, groups, drawdown, trades")
    else:
        st.warning(f"Enhanced chart not found: `{chart}`")

    if summary.exists():
        with st.expander("Weekly summary CSV", expanded=False):
            summary_df = pd.read_csv(summary)
            st.dataframe(summary_df.tail(20), use_container_width=True)

    if trade_log.exists():
        trade_df = pd.read_csv(trade_log)
        if "date" in trade_df.columns:
            trade_df["date"] = pd.to_datetime(trade_df["date"]).dt.strftime("%Y-%m-%d")
        st.subheader("Trade Log")
        st.caption("Derived from week-to-week portfolio weight changes.")
        st.dataframe(trade_df, use_container_width=True)
    else:
        st.warning(f"Trade log not found: `{trade_log}`")


def show_legacy_demo_backtest():
    """Original demo backtest UI, explicitly marked as mock/TBD."""
    mock_tbd_notice(
        "This legacy demo uses random synthetic prices and static weights. "
        "Use the Adaptive Rotation tab for real Yahoo-data backtests."
    )

    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("Backtest Configuration")

        # Strategy selection
        strategy_type = st.selectbox(
            "Strategy Type",
            ["equal_weight", "market_cap_weight", "ml_strategy"]
        )

        # Backtest parameters
        start_date = st.date_input("Start Date", datetime(2020, 1, 1))
        end_date = st.date_input("End Date", datetime(2023, 12, 31))
        initial_capital = st.number_input("Initial Capital", value=1000000, step=100000)

        # ML strategy parameters
        if strategy_type == "ml_strategy":
            top_quantile = st.slider("Top Quantile", 0.5, 1.0, 0.75, 0.05)

        if st.button("Run Backtest"):
            with st.spinner("Running backtest..."):
                try:
                    run_backtest(
                        strategy_type=strategy_type,
                        start_date=start_date,
                        end_date=end_date,
                        initial_capital=initial_capital,
                        top_quantile=top_quantile if strategy_type == "ml_strategy" else 0.75
                    )
                except Exception as e:
                    st.error(f"Backtest failed: {e}")

    with col2:
        st.subheader("Backtest Results")

        # Display results if available
        if 'backtest_result' in st.session_state:
            result = st.session_state.backtest_result

            # Key metrics
            metrics_cols = st.columns(4)
            with metrics_cols[0]:
                final_val = result.portfolio_values.iloc[-1] if hasattr(result, 'portfolio_values') and len(result.portfolio_values) > 0 else 0
                st.metric("Final Value", _format_money(final_val))
            with metrics_cols[1]:
                st.metric("Total Return", _format_pct(result.metrics.get('total_return', 0)))
            with metrics_cols[2]:
                st.metric("Annual Return", _format_pct(result.metrics.get('annual_return', 0)))
            with metrics_cols[3]:
                st.metric("Sharpe Ratio", f"{result.metrics.get('sharpe_ratio', 0):.2f}")

            # Performance chart
            if hasattr(result, 'portfolio_values'):
                fig = px.line(
                    x=result.portfolio_values.index,
                    y=result.portfolio_values.values,
                    title="Portfolio Value"
                )
                st.plotly_chart(fig, use_container_width=True)

            # Detailed metrics
            st.subheader("Detailed Metrics")
            metrics_df = pd.DataFrame({
                'Metric': list(result.metrics.keys()),
                'Value': [f"{v:.4f}" for v in result.metrics.values()]
            })
            st.dataframe(metrics_df)


def run_backtest(strategy_type, start_date, end_date, initial_capital, top_quantile):
    """Run backtest with given parameters."""
    # Create strategy
    config = StrategyConfig(name=f"{strategy_type} Backtest")
    strategy = create_strategy(strategy_type, config)

    # Create backtest configuration
    backtest_config = BacktestConfig(
        start_date=start_date.strftime("%Y-%m-%d"),
        end_date=end_date.strftime("%Y-%m-%d"),
        initial_capital=initial_capital
    )

    # Load sample data (in practice, load real data)
    dates = pd.date_range(start_date, end_date, freq='D')
    price_data = pd.DataFrame({
        'datadate': dates,
        'adj_close': 100 + np.cumsum(np.random.normal(0, 0.02, len(dates)))
    })

    # Sample weight signals
    weight_signals = pd.DataFrame({
        'date': pd.date_range(start_date, end_date, freq='QE'),
        'AAPL': 0.5,
        'MSFT': 0.3,
        'GOOGL': 0.2
    })

    # Run backtest
    engine = BacktestEngine(backtest_config)
    result = engine.run_backtest(strategy, price_data, weight_signals)

    # Store result
    st.session_state.backtest_result = result

    st.success("Backtest completed successfully!")


def show_live_trading():
    """Show live trading interface."""
    st.header("Live Trading")

    # Check if trading is configured
    try:
        account = create_alpaca_account_from_env()
        st.success(f"Connected to Alpaca account (Paper: {account.is_paper})")

        tab1, tab2, tab3 = st.tabs(["Portfolio", "Order Management", "Strategy Execution"])

        with tab1:
            st.subheader("Current Portfolio")

            if st.button("Refresh Portfolio"):
                with st.spinner("Loading portfolio..."):
                    try:
                        from ..trading.alpaca_manager import AlpacaManager
                        manager = AlpacaManager([account])

                        # Get account info
                        account_info = manager.get_account_info()
                        positions = manager.get_positions()

                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Portfolio Value", _format_money(account_info.get('portfolio_value', 0)))
                        with col2:
                            st.metric("Cash", _format_money(account_info.get('cash', 0)))
                        with col3:
                            st.metric("Buying Power", _format_money(account_info.get('buying_power', 0)))

                        # Positions table
                        if positions:
                            positions_df = pd.DataFrame(positions)
                            st.dataframe(positions_df[['symbol', 'qty', 'avg_entry_price', 'market_value', 'unrealized_pl']], use_container_width=True)
                        else:
                            st.info("No open positions")

                    except Exception as e:
                        st.error(f"Failed to load portfolio: {e}")

        with tab2:
            st.subheader("Order Management")

            # Place order form
            with st.form("place_order"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    symbol = st.text_input("Symbol", "AAPL").upper()
                with col2:
                    quantity = st.number_input("Quantity", min_value=1, value=10)
                with col3:
                    side = st.selectbox("Side", ["buy", "sell"])

                order_type = st.selectbox("Order Type", ["market", "limit"])
                limit_price = st.number_input("Limit Price", min_value=0.01, step=0.01) if order_type == "limit" else None

                submitted = st.form_submit_button("Place Order")
                if submitted:
                    try:
                        from ..trading.alpaca_manager import AlpacaManager, OrderRequest
                        manager = AlpacaManager([account])

                        order = OrderRequest(
                            symbol=symbol,
                            quantity=quantity,
                            side=side,
                            order_type=order_type,
                            limit_price=limit_price
                        )

                        response = manager.place_order(order)
                        st.success(f"Order placed: {response.order_id}")

                    except Exception as e:
                        st.error(f"Failed to place order: {e}")

        with tab3:
            st.subheader("Strategy Execution")
            mock_tbd_notice(
                "Sample strategy execution references a placeholder strategy and is TBD for real order generation."
            )

            # Strategy execution
            if st.button("Execute Sample Strategy"):
                with st.spinner("Executing strategy..."):
                    try:
                        from ..trading.trade_executor import TradeExecutor
                        from ..strategies.base_strategy import StrategyConfig, EqualWeightStrategy

                        manager = AlpacaManager([account])
                        executor = TradeExecutor(manager)

                        # Create sample strategy
                        config = StrategyConfig(name="Sample Equal Weight")
                        strategy = EqualWeightStrategy(config)

                        # Sample data
                        sample_data = {
                            'fundamentals': pd.DataFrame({
                                'gvkey': ['AAPL', 'MSFT', 'GOOGL'],
                                'datadate': ['2024-01-01'] * 3
                            })
                        }

                        result = executor.execute_strategy(strategy, sample_data)
                        st.success(f"Strategy executed: {len(result.orders_placed)} orders placed")

                    except Exception as e:
                        st.error(f"Strategy execution failed: {e}")

    except Exception as e:
        st.error(f"Trading not configured: {e}")
        st.info("Please set up Alpaca API credentials in environment variables")


def show_portfolio_analysis():
    """Show portfolio analysis interface."""
    st.header("Portfolio Analysis")
    mock_tbd_notice("Portfolio analytics use random/sample data. Use Strategy Backtesting > Adaptive Rotation for real backtest analytics.")

    # Sample portfolio data
    dates = pd.date_range('2024-01-01', periods=100, freq='D')
    portfolio_values = 1000000 + np.cumsum(np.random.normal(2000, 8000, 100))

    tab1, tab2, tab3, tab4 = st.tabs(["Performance", "Risk Analysis", "Attribution", "Benchmarking"])

    with tab1:
        st.subheader("Performance Analysis")

        # Performance chart
        fig = px.line(x=dates, y=portfolio_values, title="Portfolio Performance")
        st.plotly_chart(fig, use_container_width=True)

        # Performance metrics
        returns = pd.Series(portfolio_values).pct_change().dropna()
        total_return = (portfolio_values[-1] / portfolio_values[0]) - 1
        annual_return = returns.mean() * 252
        volatility = returns.std() * np.sqrt(252)
        sharpe = annual_return / volatility if volatility > 0 else 0

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Return", _format_pct(total_return))
        with col2:
            st.metric("Annual Return", _format_pct(annual_return))
        with col3:
            st.metric("Volatility", _format_pct(volatility))
        with col4:
            st.metric("Sharpe Ratio", f"{sharpe:.2f}")

    with tab2:
        st.subheader("Risk Analysis")

        # Drawdown analysis
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max

        fig = px.line(x=dates[1:], y=drawdown, title="Portfolio Drawdown")
        fig.update_layout(yaxis_title="Drawdown", yaxis_tickformat=".2%")
        st.plotly_chart(fig, use_container_width=True)

        # Risk metrics
        max_drawdown = drawdown.min()
        var_95 = np.percentile(returns, 5)
        cvar_95 = returns[returns <= var_95].mean()

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Max Drawdown", _format_pct(max_drawdown))
        with col2:
            st.metric("VaR (95%)", _format_pct(var_95))
        with col3:
            st.metric("CVaR (95%)", _format_pct(cvar_95))

    with tab3:
        st.subheader("Attribution Analysis")
        mock_tbd_notice("Attribution values are static samples.")

        # Sample attribution data
        attribution_data = pd.DataFrame({
            'Asset': ['AAPL', 'MSFT', 'GOOGL', 'Bonds', 'Cash'],
            'Weight': [0.3, 0.25, 0.2, 0.15, 0.1],
            'Return': [0.15, 0.12, 0.18, 0.03, 0.02],
            'Contribution': [0.045, 0.03, 0.036, 0.0045, 0.002]
        })

        fig = px.bar(attribution_data, x='Asset', y='Contribution',
                    title="Return Attribution by Asset")
        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(attribution_data, use_container_width=True)

    with tab4:
        st.subheader("Benchmarking")
        mock_tbd_notice("Benchmark comparison uses random sample data.")

        # Sample benchmark comparison
        benchmark_data = pd.DataFrame({
            'Date': dates,
            'Portfolio': portfolio_values,
            'SPY': 1000000 + np.cumsum(np.random.normal(1500, 6000, 100)),
            'QQQ': 1000000 + np.cumsum(np.random.normal(1800, 7000, 100))
        })

        fig = px.line(benchmark_data, x='Date', y=['Portfolio', 'SPY', 'QQQ'],
                     title="Portfolio vs Benchmarks")
        st.plotly_chart(fig, use_container_width=True)


def show_settings():
    """Show settings interface."""
    st.header("Settings")
    mock_tbd_notice("Settings controls are UI-only unless noted; most changes are not persisted to .env or config files.")
    mock_tbd_notice("Settings controls are mostly UI-only and do not persist to `.env` or config files yet.")

    tab1, tab2, tab3 = st.tabs(["General", "Trading", "Data"])

    with tab1:
        st.subheader("General Settings")

        # Logging level
        log_level = st.selectbox("Logging Level", ["DEBUG", "INFO", "WARNING", "ERROR"])
        if st.button("Apply Logging Level"):
            logging.getLogger().setLevel(getattr(logging, log_level))
            st.success(f"Logging level set to {log_level}")

        # Theme
        theme = st.selectbox("Theme", ["Light", "Dark"])
        if st.button("Apply Theme"):
            st.success(f"Theme set to {theme}")

    with tab2:
        st.subheader("Trading Settings")

        # Risk limits
        max_order_value = st.number_input("Max Order Value ($)", value=100000, step=10000)
        max_portfolio_turnover = st.slider("Max Portfolio Turnover (%)", 0.0, 1.0, 0.5, 0.05)

        if st.button("Save Trading Settings"):
            st.success("Trading settings saved")

        # API Configuration
        st.subheader("API Configuration")
        api_key = st.text_input("Alpaca API Key", type="password")
        api_secret = st.text_input("Alpaca API Secret", type="password")
        use_paper = st.checkbox("Use Paper Trading", value=True)

        if st.button("Save API Settings"):
            st.success("API settings saved")

    with tab3:
        st.subheader("Data Settings")

        # Data paths
        data_dir = st.text_input("Data Directory", value="./data")
        cache_dir = st.text_input("Cache Directory", value="./data/cache")

        if st.button("Save Data Settings"):
            st.success("Data settings saved")

        # Data sources
        st.subheader("Data Sources")
        enable_wrds = st.checkbox("Enable WRDS", value=True)
        enable_alpha_vantage = st.checkbox("Enable Alpha Vantage", value=False)

        if st.button("Save Data Source Settings"):
            st.success("Data source settings saved")


if __name__ == "__main__":
    main()
