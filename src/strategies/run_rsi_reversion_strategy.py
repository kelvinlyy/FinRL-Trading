"""
RSI mean-reversion strategy runner (long-only, modular alongside adaptive rotation).

CLI mirrors ``run_adaptive_rotation_strategy.py`` so ``deploy.sh`` can dispatch the same flags.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.strategies.rsi_reversion import RSIReversionEngine, load_config
from src.strategies.rsi_reversion.config_loader import universe_symbols

# Reuse equity stats / chart from adaptive runner (same CSV shape).
from src.strategies.run_adaptive_rotation_strategy import _generate_performance_report


def load_price_panel(data_dir: Path, symbols: list[str]) -> dict[str, pd.Series]:
    out: dict[str, pd.Series] = {}
    for sym in symbols:
        fp = data_dir / f"{sym}_daily.csv"
        if not fp.is_file():
            continue
        df = pd.read_csv(fp)
        df["date"] = pd.to_datetime(df["date"])
        out[sym] = df.set_index("date")["close"].astype(float).sort_index()
    return out


def run_single_date(config_path: str, as_of_date: str, data_dir: str | None = None) -> None:
    cfg = load_config(config_path)
    root = Path(data_dir or cfg.paths.data_root)
    symbols = universe_symbols(cfg)
    panel = load_price_panel(root, symbols)
    engine = RSIReversionEngine(cfg)

    as_of = pd.Timestamp(as_of_date)
    out = engine.run(panel, as_of, symbols)

    print(f"\n{'='*60}")
    print("RSI mean-reversion — single date")
    print(f"{'='*60}")
    print(f"Date: {as_of_date}  |  notes: {out.notes}")
    print(f"Cash: {out.cash_weight:.2%}  |  invested: {1.0 - out.cash_weight:.2%}")
    for sym, w in sorted(out.weights.items(), key=lambda x: -x[1]):
        rsi_v = out.rsi_snapshot.get(sym)
        rsi_s = f"{rsi_v:.1f}" if rsi_v is not None else "n/a"
        print(f"  {sym:8s}  weight={w:7.2%}  RSI={rsi_s}")

    weights_dir = Path(cfg.paths.weights_dir)
    weights_dir.mkdir(parents=True, exist_ok=True)
    audit_dir = Path(cfg.paths.audit_dir)
    audit_dir.mkdir(parents=True, exist_ok=True)

    audit_path = audit_dir / f"audit_{as_of_date}.json"
    with audit_path.open("w", encoding="utf-8") as f:
        json.dump(engine.audit_dict(as_of_date, out), f, indent=2, default=str)
    print(f"\nAudit: {audit_path}")

    signal_path = weights_dir / f"signal_{as_of_date}.json"
    signal_data = {
        "date": as_of_date,
        "regime": out.regime,
        "invested": float(sum(out.weights.values())),
        "cash": out.cash_weight,
        "weights": out.weights,
    }
    with signal_path.open("w", encoding="utf-8") as f:
        json.dump(signal_data, f, indent=2, default=str)
    print(f"Signal: {signal_path}")


def run_backtest(
    config_path: str,
    start_date: str,
    end_date: str,
    data_dir: str | None = None,
    freq: str = "W-FRI",
    daily_fast_track: bool = True,
) -> None:
    _ = daily_fast_track  # deploy.sh passes this for adaptive; unused here.
    cfg = load_config(config_path)
    root = Path(data_dir or cfg.paths.data_root)
    symbols = universe_symbols(cfg)
    panel = load_price_panel(root, symbols)
    if not panel:
        raise FileNotFoundError(f"No price CSVs found under {root} for symbols {symbols}")

    engine = RSIReversionEngine(cfg)
    decision_dates = pd.date_range(start_date, end_date, freq=freq)

    weights_dir = Path(cfg.paths.weights_dir)
    audit_dir = Path(cfg.paths.audit_dir)
    weights_dir.mkdir(parents=True, exist_ok=True)
    audit_dir.mkdir(parents=True, exist_ok=True)

    rows_summary: list[dict[str, object]] = []
    rows_detail: list[dict[str, object]] = []

    for i, date in enumerate(decision_dates, 1):
        date = pd.Timestamp(date)
        try:
            out = engine.run(panel, date, symbols)
        except Exception as e:
            print(f"   Warning: {date.date()} — {e}")
            continue

        aud_path = audit_dir / f"audit_{date.strftime('%Y-%m-%d')}.json"
        with aud_path.open("w", encoding="utf-8") as f:
            json.dump(engine.audit_dict(date.strftime("%Y-%m-%d"), out), f, indent=2, default=str)

        invested = float(sum(out.weights.values()))
        rows_summary.append(
            {
                "date": date,
                "invested": invested,
                "cash": out.cash_weight,
                "regime": out.regime,
                "num_assets": len(out.weights),
            }
        )
        row: dict[str, object] = {
            "date": date,
            "cash": out.cash_weight,
            "regime": out.regime,
        }
        for sym in symbols:
            row[sym] = float(out.weights.get(sym, 0.0))
        rows_detail.append(row)

        if i % 20 == 0 or i == len(decision_dates):
            print(f"   Progress: {i}/{len(decision_dates)} rebalance dates processed")

    if not rows_detail:
        print("No backtest rows produced (check date range and data).")
        return

    summary_df = pd.DataFrame(rows_summary)
    detail_df = pd.DataFrame(rows_detail)

    summary_file = weights_dir / f"backtest_{start_date}_to_{end_date}.csv"
    summary_df.to_csv(summary_file, index=False)
    print(f"\nBacktest summary saved to: {summary_file}")

    weights_file = weights_dir / f"rsi_portfolio_weights_{start_date}_to_{end_date}.csv"
    detail_df.to_csv(weights_file, index=False)
    print(f"Detailed weights saved to: {weights_file}")
    print(f"Audit logs saved to: {audit_dir}")

    _generate_performance_report(detail_df, start_date, end_date, str(root), weights_dir)


def main() -> None:
    parser = argparse.ArgumentParser(description="RSI mean-reversion strategy runner")
    parser.add_argument(
        "--config",
        type=str,
        default="src/strategies/RSIReversionConf.yaml",
        help="Path to RSI YAML config",
    )
    parser.add_argument("--data-dir", type=str, default=None, help="CSV directory (default: config paths.data_root)")
    parser.add_argument("--date", type=str, help="Single decision date YYYY-MM-DD")
    parser.add_argument("--backtest", action="store_true", help="Run historical simulation")
    parser.add_argument("--start", type=str, help="Backtest start")
    parser.add_argument("--end", type=str, help="Backtest end")
    parser.add_argument(
        "--freq",
        type=str,
        default="W-FRI",
        help="Rebalance frequency (pandas offset; default W-FRI)",
    )
    parser.add_argument(
        "--no-daily-fast-track",
        action="store_true",
        help="Ignored for RSI (kept for deploy.sh compatibility with adaptive runner)",
    )
    args = parser.parse_args()

    try:
        if args.backtest:
            if not args.start or not args.end:
                parser.error("Backtest requires --start and --end")
            run_backtest(
                args.config,
                args.start,
                args.end,
                data_dir=args.data_dir,
                freq=args.freq,
                daily_fast_track=not args.no_daily_fast_track,
            )
        elif args.date:
            run_single_date(args.config, args.date, data_dir=args.data_dir)
        else:
            parser.error("Specify --date or --backtest")
    except Exception:
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
