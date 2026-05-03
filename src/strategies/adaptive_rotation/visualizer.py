"""
Enhanced Backtest Visualizer
============================

Generates multi-panel charts from backtest outputs:
  1. Equity curve with regime background bands
  2. Group activation timeline with selected stocks
  3. Trade log (buys/sells derived from weight diffs)
  4. Drawdown panel

Reads existing output files:
  - ars_portfolio_weights_*.csv  (weekly weights + regime)
  - audit_*.json                 (group strength, rankings, regime details)
  - data/fmp_daily/*_daily.csv   (prices for equity computation)

Author: Cursor Cloud Agent
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
from matplotlib.gridspec import GridSpec


REGIME_COLORS = {
    'risk_on':       '#e6f4ea',
    'neutral':       '#fef7e0',
    'risk_off':      '#fce8e6',
    'fast_risk_off': '#f8d7da',
}

REGIME_LABELS = {
    'risk_on':       'Risk-On',
    'neutral':       'Neutral',
    'risk_off':      'Risk-Off',
    'fast_risk_off': 'Fast Risk-Off',
}

GROUP_DISPLAY = {
    'group_a_growth_tech': ('Growth Tech', '#2563eb'),
    'group_b_real_assets': ('Real Assets', '#d97706'),
    'group_c_defensive':   ('Defensive',   '#059669'),
}

GROUP_ORDER = ['group_a_growth_tech', 'group_b_real_assets', 'group_c_defensive']

GROUP_MEMBERS = {
    'group_a_growth_tech': ['AAPL', 'MSFT', 'NVDA', 'META', 'AMZN', 'GOOGL', 'TSLA'],
    'group_b_real_assets': ['XOM', 'CVX', 'COP', 'FCX', 'BHP', 'GLD', 'SLV'],
    'group_c_defensive':   ['TLT', 'IEF', 'XLU', 'XLV', 'IAU', 'SHY', 'UUP'],
}


def _load_weights(weights_csv: str) -> pd.DataFrame:
    df = pd.read_csv(weights_csv)
    df['date'] = pd.to_datetime(df['date'])
    return df


def _load_audit_logs(audit_dir: str, dates: List[pd.Timestamp]) -> Dict[str, dict]:
    audit_path = Path(audit_dir)
    logs = {}
    for d in dates:
        f = audit_path / f"audit_{d.strftime('%Y-%m-%d')}.json"
        if f.exists():
            with open(f) as fh:
                logs[d.strftime('%Y-%m-%d')] = json.load(fh)
    return logs


def _compute_equity(weights_df: pd.DataFrame, data_dir: str) -> pd.DataFrame:
    meta_cols = ['date', 'cash', 'regime']
    asset_cols = [c for c in weights_df.columns if c not in meta_cols]

    prices = {}
    data_path = Path(data_dir)
    for sym in asset_cols:
        csv_path = data_path / f"{sym}_daily.csv"
        if csv_path.exists():
            df = pd.read_csv(csv_path)
            df['date'] = pd.to_datetime(df['date'])
            prices[sym] = df.set_index('date')['close']

    price_df = pd.DataFrame(prices)
    dates = weights_df['date'].values

    portfolio_values = [1.0]
    for i in range(len(dates) - 1):
        d0, d1 = pd.Timestamp(dates[i]), pd.Timestamp(dates[i + 1])
        row = weights_df.iloc[i]
        period_return = 0.0
        for sym in asset_cols:
            w = row[sym]
            if w > 0 and sym in price_df.columns:
                p0_s = price_df[sym].loc[:d0].dropna()
                p1_s = price_df[sym].loc[:d1].dropna()
                if len(p0_s) > 0 and len(p1_s) > 0:
                    period_return += w * (p1_s.iloc[-1] / p0_s.iloc[-1] - 1)
        portfolio_values.append(portfolio_values[-1] * (1 + period_return))

    equity = pd.DataFrame({
        'date': pd.to_datetime(dates),
        'portfolio': portfolio_values,
    }).set_index('date')

    for bench in ['SPY', 'QQQ']:
        csv_path = data_path / f"{bench}_daily.csv"
        if csv_path.exists():
            df = pd.read_csv(csv_path)
            df['date'] = pd.to_datetime(df['date'])
            series = df.set_index('date')['close']
            start_price = series.loc[:equity.index[0]].iloc[-1]
            equity[bench] = series.reindex(equity.index, method='ffill') / start_price

    return equity


def _derive_trades(weights_df: pd.DataFrame) -> pd.DataFrame:
    meta_cols = ['date', 'cash', 'regime']
    asset_cols = [c for c in weights_df.columns if c not in meta_cols]

    trades = []
    for i in range(1, len(weights_df)):
        d = weights_df.iloc[i]['date']
        regime = weights_df.iloc[i]['regime']
        for sym in asset_cols:
            w_prev = weights_df.iloc[i - 1][sym]
            w_curr = weights_df.iloc[i][sym]
            delta = w_curr - w_prev
            if abs(delta) < 1e-6:
                continue
            action = 'BUY' if delta > 0 else 'SELL'
            if w_prev == 0 and w_curr > 0:
                action = 'BUY (new)'
            elif w_prev > 0 and w_curr == 0:
                action = 'SELL (exit)'
            elif delta > 0:
                action = 'BUY (add)'
            else:
                action = 'SELL (trim)'

            group = _symbol_to_group(sym)
            trades.append({
                'date': d,
                'symbol': sym,
                'action': action,
                'prev_weight': w_prev,
                'new_weight': w_curr,
                'delta': delta,
                'regime': regime,
                'group': group,
            })

    return pd.DataFrame(trades)


def _symbol_to_group(sym: str) -> str:
    for gname, members in GROUP_MEMBERS.items():
        if sym in members:
            return GROUP_DISPLAY.get(gname, (gname,))[0]
    return 'Fallback'


def _extract_group_timeline(weights_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    meta_cols = ['date', 'cash', 'regime']
    asset_cols = [c for c in weights_df.columns if c not in meta_cols]

    for _, row in weights_df.iterrows():
        d = row['date']
        for gname in GROUP_ORDER:
            members = GROUP_MEMBERS.get(gname, [])
            held = [s for s in members if s in asset_cols and row.get(s, 0) > 0]
            active = len(held) > 0
            rows.append({
                'date': d,
                'group': gname,
                'active': active,
                'held_stocks': ', '.join(held) if held else '',
                'num_held': len(held),
            })

    return pd.DataFrame(rows)


def generate_enhanced_chart(
    weights_csv: str,
    audit_dir: str,
    data_dir: str,
    output_path: str,
    start_date: str = None,
    end_date: str = None,
):
    """
    Generate the enhanced multi-panel backtest chart.

    Args:
        weights_csv: Path to ars_portfolio_weights CSV
        audit_dir: Path to audit log directory
        data_dir: Path to daily price CSV directory
        output_path: Where to save the output PNG
        start_date: Backtest start date string
        end_date: Backtest end date string
    """
    weights_df = _load_weights(weights_csv)
    equity = _compute_equity(weights_df, data_dir)
    trades_df = _derive_trades(weights_df)
    timeline_df = _extract_group_timeline(weights_df)

    cummax = equity['portfolio'].cummax()
    drawdown = (equity['portfolio'] - cummax) / cummax

    years = (equity.index[-1] - equity.index[0]).days / 365.25
    ann_ret = (equity['portfolio'].iloc[-1]) ** (1 / years) - 1
    weekly_rets = equity['portfolio'].pct_change().dropna()
    ann_vol = weekly_rets.std() * np.sqrt(52)
    sharpe = ann_ret / ann_vol if ann_vol > 0 else 0
    max_dd = drawdown.min()
    calmar = ann_ret / abs(max_dd) if max_dd != 0 else 0

    fig = plt.figure(figsize=(18, 24))
    gs = GridSpec(5, 1, figure=fig, height_ratios=[4, 1.2, 2.5, 0.3, 4],
                  hspace=0.28)

    title = f'Adaptive Rotation Strategy — Enhanced Backtest'
    if start_date and end_date:
        title += f' ({start_date} to {end_date})'
    fig.suptitle(title, fontsize=16, fontweight='bold', y=0.98)

    # ── Panel 1: Equity curve with regime bands ──
    ax1 = fig.add_subplot(gs[0])
    _plot_regime_bands(ax1, weights_df)

    ax1.plot(equity.index, equity['portfolio'],
             label=f'Strategy ({equity["portfolio"].iloc[-1]:.2f}x)',
             color='#1e40af', linewidth=2.2, zorder=5)
    if 'SPY' in equity.columns:
        ax1.plot(equity.index, equity['SPY'],
                 label=f'SPY ({equity["SPY"].iloc[-1]:.2f}x)',
                 color='#6b7280', linewidth=1.2, alpha=0.7, zorder=4)
    if 'QQQ' in equity.columns:
        ax1.plot(equity.index, equity['QQQ'],
                 label=f'QQQ ({equity["QQQ"].iloc[-1]:.2f}x)',
                 color='#f59e0b', linewidth=1.2, alpha=0.7, zorder=4)

    _annotate_key_trades(ax1, trades_df, equity)

    ax1.set_ylabel('Growth of $1', fontsize=12)
    ax1.legend(fontsize=10, loc='upper left', framealpha=0.9)
    ax1.grid(True, alpha=0.25)
    ax1.set_title('Equity Curve & Market Regime', fontsize=12, pad=8)

    regime_patches = [mpatches.Patch(color=c, alpha=0.5, label=REGIME_LABELS[k])
                      for k, c in REGIME_COLORS.items()]
    ax1_regime_legend = ax1.legend(
        handles=regime_patches, fontsize=8, loc='upper right',
        title='Regime', title_fontsize=9, framealpha=0.9)
    ax1.add_artist(ax1_regime_legend)
    ax1.legend(fontsize=10, loc='upper left', framealpha=0.9)

    # ── Panel 2: Drawdown ──
    ax2 = fig.add_subplot(gs[1], sharex=ax1)
    ax2.fill_between(equity.index, drawdown.values, 0, color='#ef4444', alpha=0.35)
    ax2.plot(equity.index, drawdown.values, color='#dc2626', linewidth=0.8)
    ax2.set_ylabel('Drawdown', fontsize=11)
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.0%}'))
    ax2.grid(True, alpha=0.25)
    ax2.set_title('Drawdown', fontsize=12, pad=4)

    # ── Panel 3: Group activation timeline ──
    ax3 = fig.add_subplot(gs[2], sharex=ax1)
    _plot_group_timeline(ax3, timeline_df)

    # ── Spacer ──
    ax_spacer = fig.add_subplot(gs[3])
    ax_spacer.set_visible(False)

    # ── Panel 4: Trade log table ──
    ax4 = fig.add_subplot(gs[4])
    _plot_trade_table(ax4, trades_df)

    # Format x-axis
    for ax in [ax1, ax2, ax3]:
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    plt.setp(ax3.get_xticklabels(), rotation=45, ha='right')

    stats_text = (
        f'Ann. Return: {ann_ret:.1%}  |  Sharpe: {sharpe:.2f}  |  '
        f'Max DD: {max_dd:.1%}  |  Calmar: {calmar:.2f}  |  '
        f'Trades: {len(trades_df)}'
    )
    fig.text(0.5, 0.005, stats_text, ha='center', fontsize=11,
             bbox=dict(boxstyle='round,pad=0.4', facecolor='#f0f9ff', edgecolor='#bfdbfe'))

    plt.savefig(output_path, dpi=150, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    print(f"Enhanced chart saved to: {output_path}")

    trade_csv = str(Path(output_path).with_name(
        Path(output_path).stem.replace('enhanced_backtest', 'trade_log') + '.csv'))
    if len(trades_df) > 0:
        trades_df.to_csv(trade_csv, index=False)
        print(f"Trade log saved to: {trade_csv}")

    return trades_df


def _plot_regime_bands(ax, weights_df: pd.DataFrame):
    dates = weights_df['date'].values
    regimes = weights_df['regime'].values

    i = 0
    while i < len(dates):
        regime = regimes[i]
        j = i
        while j < len(dates) and regimes[j] == regime:
            j += 1
        start = pd.Timestamp(dates[i])
        end = pd.Timestamp(dates[min(j, len(dates) - 1)])
        color = REGIME_COLORS.get(regime, '#ffffff')
        ax.axvspan(start, end, alpha=0.45, color=color, zorder=0)
        i = j


def _annotate_key_trades(ax, trades_df: pd.DataFrame, equity: pd.DataFrame):
    if trades_df.empty:
        return

    buys = trades_df[trades_df['action'].str.contains('BUY \\(new\\)')]
    sells = trades_df[trades_df['action'].str.contains('SELL \\(exit\\)')]

    buy_dates = buys.groupby('date').agg({'symbol': lambda x: ', '.join(x)}).reset_index()
    sell_dates = sells.groupby('date').agg({'symbol': lambda x: ', '.join(x)}).reset_index()

    for _, row in buy_dates.iterrows():
        d = row['date']
        if d in equity.index:
            y = equity.loc[d, 'portfolio']
            ax.annotate('▲', xy=(d, y), fontsize=7, color='#16a34a',
                        ha='center', va='bottom', zorder=10)

    for _, row in sell_dates.iterrows():
        d = row['date']
        if d in equity.index:
            y = equity.loc[d, 'portfolio']
            ax.annotate('▼', xy=(d, y), fontsize=7, color='#dc2626',
                        ha='center', va='top', zorder=10)


def _plot_group_timeline(ax, timeline_df: pd.DataFrame):
    ax.set_title('Group Activation & Stock Selection', fontsize=12, pad=4)

    for idx, gname in enumerate(GROUP_ORDER):
        gdf = timeline_df[timeline_df['group'] == gname].copy()
        display_name, color = GROUP_DISPLAY.get(gname, (gname, '#888888'))
        y_pos = len(GROUP_ORDER) - 1 - idx

        dates = gdf['date'].values
        active = gdf['active'].values
        held = gdf['held_stocks'].values

        i = 0
        while i < len(dates):
            if active[i]:
                j = i
                while j < len(dates) and active[j]:
                    j += 1
                start = pd.Timestamp(dates[i])
                end = pd.Timestamp(dates[min(j - 1, len(dates) - 1)])
                width = (end - start).days
                if width < 3:
                    width = 3
                    end = start + pd.Timedelta(days=3)
                ax.barh(y_pos, width=(end - start).days,
                        left=start, height=0.7,
                        color=color, alpha=0.6, edgecolor=color, linewidth=0.5)

                stocks_at_start = held[i]
                bar_days = (end - start).days
                if stocks_at_start and bar_days > 20:
                    bar_mid = start + (end - start) / 2
                    ax.text(bar_mid, y_pos, stocks_at_start,
                            ha='center', va='center', fontsize=6,
                            color='white', fontweight='bold',
                            zorder=10)
                i = j
            else:
                i += 1

    ax.set_yticks(range(len(GROUP_ORDER)))
    ax.set_yticklabels([GROUP_DISPLAY[g][0] for g in reversed(GROUP_ORDER)],
                       fontsize=10)
    ax.set_ylim(-0.5, len(GROUP_ORDER) - 0.5)
    ax.grid(True, axis='x', alpha=0.25)
    ax.set_axisbelow(True)


def _plot_trade_table(ax, trades_df: pd.DataFrame):
    ax.set_title('Trade Log (Buys & Sells)', fontsize=12, pad=4)
    ax.axis('off')

    if trades_df.empty:
        ax.text(0.5, 0.5, 'No trades recorded', ha='center', va='center',
                fontsize=12, color='#888888')
        return

    significant = trades_df[
        trades_df['action'].str.contains('new|exit')
    ].copy()

    if significant.empty:
        significant = trades_df.copy()

    significant = significant.sort_values('date')

    if len(significant) > 40:
        half = 20
        display = pd.concat([significant.head(half), significant.tail(half)])
        truncated = True
    else:
        display = significant
        truncated = False

    table_data = []
    for _, row in display.iterrows():
        d = row['date'].strftime('%Y-%m-%d') if isinstance(row['date'], pd.Timestamp) else str(row['date'])
        action = row['action']
        sym = row['symbol']
        w = f"{row['new_weight']:.1%}" if 'new' in action.lower() or 'add' in action.lower() else f"{row['prev_weight']:.1%} → 0"
        group = row['group']
        regime = row['regime']
        table_data.append([d, action, sym, w, group, regime])

    if truncated:
        mid = len(table_data) // 2
        table_data.insert(mid, ['...', f'({len(significant) - 60} more trades)', '...', '...', '...', '...'])

    col_labels = ['Date', 'Action', 'Symbol', 'Weight', 'Group', 'Regime']

    table = ax.table(
        cellText=table_data,
        colLabels=col_labels,
        loc='center',
        cellLoc='center',
    )

    table.auto_set_font_size(False)
    table.set_fontsize(7)
    table.scale(1.0, 1.1)

    for (row, col), cell in table.get_celld().items():
        cell.set_edgecolor('#e5e7eb')
        if row == 0:
            cell.set_facecolor('#1e3a5f')
            cell.set_text_props(color='white', fontweight='bold', fontsize=8)
        else:
            text = cell.get_text().get_text()
            if 'BUY' in text:
                cell.set_facecolor('#dcfce7')
            elif 'SELL' in text:
                cell.set_facecolor('#fee2e2')
            elif text == '...':
                cell.set_facecolor('#f3f4f6')

    table.auto_set_column_width(list(range(len(col_labels))))


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Generate enhanced backtest chart')
    parser.add_argument('--weights', required=True, help='Path to weights CSV')
    parser.add_argument('--audit-dir', required=True, help='Path to audit log dir')
    parser.add_argument('--data-dir', required=True, help='Path to daily price CSVs')
    parser.add_argument('--output', required=True, help='Output PNG path')
    parser.add_argument('--start', default=None)
    parser.add_argument('--end', default=None)
    args = parser.parse_args()

    generate_enhanced_chart(
        weights_csv=args.weights,
        audit_dir=args.audit_dir,
        data_dir=args.data_dir,
        output_path=args.output,
        start_date=args.start,
        end_date=args.end,
    )
